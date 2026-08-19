"""
Lớp service: API mức cao cho UI. Giấu chi tiết DB/queue.

Pipeline điển hình:
  create_project -> import_video -> enqueue_auto (phân tích + tìm highlight)
  -> (duyệt clip) -> enqueue_export
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
from pathlib import Path
from typing import Optional

from app.core.analysis import STEPS, analysis_status
from app.core.ffmpeg_utils import probe
from app.database import db
from app.queue.worker import WorkerPool
from config import PROJECTS_DIR


def _slug(name: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", name.strip(), flags=re.UNICODE)
    return s.strip("_") or "project"


def _file_hash(path: str, chunk: int = 1 << 20) -> str:
    """Hash nhanh: kích thước + đầu/cuối file (đủ cho smart-skip)."""
    p = Path(path)
    h = hashlib.sha1()
    h.update(str(p.stat().st_size).encode())
    with open(p, "rb") as f:
        h.update(f.read(chunk))
        if p.stat().st_size > chunk * 2:
            f.seek(-chunk, 2)
            h.update(f.read(chunk))
    return h.hexdigest()[:16]


# ---- Project ----
def create_project(name: str, grp: str = "") -> int:
    assets = PROJECTS_DIR / f"{_slug(name)}"
    i = 1
    base = assets
    while assets.exists():
        assets = Path(f"{base}_{i}")
        i += 1
    assets.mkdir(parents=True, exist_ok=True)
    return db.insert(
        "INSERT INTO projects (name, assets_dir, grp) VALUES (?,?,?)",
        (name, str(assets), (grp or "").strip()),
    )


def list_projects(grp: str | None = None) -> list:
    """Danh sách kênh. grp=None -> TẤT CẢ (hành vi cũ);
    grp='Tên nhóm' -> chỉ kênh thuộc nhóm đó ('' = chưa phân nhóm)."""
    if grp is None:
        return db.query("SELECT * FROM projects ORDER BY created_at DESC")
    return db.query("SELECT * FROM projects WHERE grp=? ORDER BY created_at DESC",
                    (grp,))


def list_groups() -> list[str]:
    """Tên NHÓM kênh distinct (bỏ rỗng = 'chưa phân nhóm'), sort a-z."""
    rows = db.query("SELECT DISTINCT grp FROM projects "
                    "WHERE grp IS NOT NULL AND grp<>'' ORDER BY grp")
    return [r["grp"] for r in rows]


def set_project_group(project_id: int, grp: str) -> None:
    """Gán kênh vào NHÓM (''= bỏ nhóm). Nhóm tồn tại khi có kênh thuộc nó."""
    db.execute("UPDATE projects SET grp=? WHERE id=?",
               ((grp or "").strip(), int(project_id)))


def project_group(project_id: int) -> str:
    row = db.query_one("SELECT grp FROM projects WHERE id=?", (int(project_id),))
    return (row["grp"] or "") if row else ""


def set_project_export_dir(project_id: int, path: str) -> None:
    """Đặt THƯ MỤC LƯU RIÊNG cho 1 kênh (user tự chọn ổ/đường dẫn). path=''
    -> BỎ riêng, kênh về mặc định chung ('Đã xuất/<Kênh>/<video>'). Khi có
    path: mọi Part của kênh cắt xong vào THẲNG path (không tạo folder video)."""
    db.execute("UPDATE projects SET export_dir=? WHERE id=?",
               ((path or "").strip(), int(project_id)))


def project_export_dir(project_id: int) -> str:
    """Thư mục lưu riêng của kênh; '' = mặc định chung (Đã xuất/<Kênh>)."""
    row = db.query_one("SELECT export_dir FROM projects WHERE id=?",
                       (int(project_id),))
    return (row["export_dir"] or "").strip() if row else ""


def rename_group(old: str, new: str) -> str:
    """Đổi TÊN NHÓM: mọi kênh thuộc `old` chuyển sang `new` (new trùng nhóm
    sẵn có -> GỘP 2 nhóm, hợp lệ). Trả '' nếu OK, lỗi thì chuỗi thông báo."""
    old = (old or "").strip()
    new = (new or "").strip()
    if not old:
        return "Chưa chọn nhóm để sửa."
    if not new:
        return "Tên nhóm mới không được để trống."
    if new == old:
        return ""
    db.execute("UPDATE projects SET grp=? WHERE grp=?", (new, old))
    return ""


def dissolve_group(name: str) -> int:
    """XOÁ NHÓM: các kênh trong nhóm về 'Chưa phân nhóm' (grp='') — KHÔNG xoá
    kênh/video/clip nào. Trả số kênh đã gỡ khỏi nhóm."""
    name = (name or "").strip()
    if not name:
        return 0
    n = len(db.query("SELECT id FROM projects WHERE grp=?", (name,)))
    db.execute("UPDATE projects SET grp='' WHERE grp=?", (name,))
    return n


def rename_project(project_id: int, new_name: str) -> str:
    """Đổi TÊN kênh (chỉ dòng DB — assets_dir giữ nguyên; thư mục 'Đã xuất/<tên
    cũ>' cũng giữ nguyên vì đường xuất dựng từ TÊN lúc xuất -> clip MỚI sẽ vào
    thư mục tên mới). Trả '' nếu OK, ngược lại là thông báo lỗi để UI hiện."""
    name = (new_name or "").strip()
    if not name:
        return "Tên kênh không được để trống."
    dup = db.query_one("SELECT id FROM projects WHERE name=? AND id<>?",
                       (name, project_id))
    if dup:
        return f"Đã có kênh khác tên “{name}” — chọn tên khác."
    cur = db.execute("UPDATE projects SET name=? WHERE id=?",
                     (name, project_id))
    try:
        if not cur.rowcount:
            return "Kênh này không còn tồn tại."
    except Exception:  # noqa: BLE001 - rowcount lỗi hiếm -> coi như OK
        pass
    return ""


# ---- Video ----
def import_video(project_id: int, src_path: str) -> int:
    info = probe(src_path)
    fh = _file_hash(src_path)
    # smart-skip: cùng project + cùng file đã import -> trả lại id cũ
    existing = db.query_one(
        "SELECT id FROM videos WHERE project_id=? AND file_hash=?",
        (project_id, fh),
    )
    if existing:
        return int(existing["id"])
    return db.insert(
        """INSERT INTO videos (project_id, src_path, file_hash, duration,
                               width, height, fps, has_audio)
           VALUES (?,?,?,?,?,?,?,?)""",
        (project_id, src_path, fh, info.duration, info.width, info.height,
         info.fps, 1 if info.has_audio else 0),
    )


def list_videos(project_id: int) -> list:
    return db.query("SELECT * FROM videos WHERE project_id=? ORDER BY id",
                    (project_id,))


def search_channels(q: str, limit: int = 300) -> list:
    """TÌM KÊNH THEO TÊN TRÊN MỌI NHÓM (anh Hùng 31/07: "phần lọc kênh có hoạt
    động đâu" — vì ô lọc cũ chỉ lọc TRONG NHÓM đang chọn, gõ tên kênh ở nhóm
    khác là không ra gì, tưởng hỏng).

    Trả [{id, name, grp}] — khớp CHỨA-chuỗi, không phân biệt hoa/thường; kênh
    có tên bắt đầu bằng chuỗi tìm được xếp TRƯỚC (gõ 'cam' thì 'camX' lên đầu,
    'Bodycam' sau). q rỗng -> [] (caller tự hiện danh sách nhóm hiện tại).
    Hàm thuần đọc DB — test được."""
    tu = (q or "").strip().casefold()
    if not tu:
        return []
    rows = db.query("SELECT id, name, grp FROM projects ORDER BY grp, name")
    dau, giua = [], []
    for r in rows:
        ten = (r["name"] or "").casefold()
        if ten.startswith(tu):
            dau.append(r)
        elif tu in ten:
            giua.append(r)
    ra = [{"id": int(r["id"]), "name": r["name"] or "", "grp": r["grp"] or ""}
          for r in (dau + giua)]
    return ra[:limit]


def find_basic_cut_videos(grp: str | None = None) -> list:
    """QUÉT mọi kênh (hoặc 1 nhóm) tìm video mà clip HIỆN CÓ đều là 'Cắt cơ
    bản' (llm_used=False) — tức lỡ ra clip KHÔNG qua AI (anh Hùng 30/07: nhiều
    kênh bị thế do bug hết-lượt-rơi-heuristic, đã sửa từ v2.6.14). Trả list
    dict đã sắp theo kênh:
      {video_id, project_id, channel, src_path, exists}
    exists=False -> video gốc đã bị dọn (xuất xong xoá) -> cần khôi phục từ
    Thùng rác trước khi phân tích lại. Hàm CHỈ ĐỌC (không đổi gì) — test được.

    Định nghĩa 'cắt cơ bản': video có >=1 clip đang hiện (status<>'archived')
    và KHÔNG clip nào có signals.llm_used=True. Clip 'archived' (kết quả lần
    cũ đã xuất, đã cất kho từ v2.6.13) KHÔNG tính — nếu tính, video từng làm
    lại bằng Aic vẫn bị coi là cơ bản."""
    where = ""
    params: list = []
    if grp is not None:
        where = "AND p.grp=? "
        params = [grp]
    rows = db.query(
        "SELECT c.video_id AS vid, c.signals AS sig, v.project_id AS pid, "
        "v.src_path AS src, p.name AS chan, p.id AS pid2 "
        "FROM clips c JOIN videos v ON v.id=c.video_id "
        "JOIN projects p ON p.id=v.project_id "
        f"WHERE c.status<>'archived' {where}"
        "ORDER BY p.name, c.video_id", tuple(params))
    by_vid: dict = {}
    for r in rows:
        d = by_vid.setdefault(int(r["vid"]), {
            "project_id": int(r["pid"]), "channel": r["chan"] or "",
            "src_path": r["src"] or "", "ai": False, "order": len(by_vid)})
        sig = db.loads(r["sig"], {}) or {}
        if sig.get("llm_used"):
            d["ai"] = True
    out = []
    for vid, d in sorted(by_vid.items(), key=lambda kv: kv[1]["order"]):
        if d["ai"]:
            continue                       # đã có clip AI -> bỏ qua
        src = d["src_path"]
        out.append({
            "video_id": vid, "project_id": d["project_id"],
            "channel": d["channel"], "src_path": src,
            "exists": bool(src) and os.path.exists(src)})
    return out


# ---- Enqueue (qua worker pool) ----
def enqueue_analysis(pool: WorkerPool, video_id: int, project_id: int,
                     force: bool = False) -> Optional[int]:
    return pool.enqueue(
        "analyze", {"video_id": video_id, "force": force},
        project_id=project_id, video_id=video_id,
        needs_gpu=True,  # transcribe/face nặng -> ưu tiên hàng đợi GPU nếu có
        priority=10,
        dedup_key=None if force else f"analyze:{video_id}",
    )


def enqueue_auto(pool: WorkerPool, video_id: int, project_id: int,
                 preset: Optional[dict] = None) -> Optional[int]:
    """Nút 'Tạo clip tự động': phân tích (nếu chưa) + tìm highlight trong 1 job."""
    # dedup: bấm 2 lần khi job đang chờ/chạy -> KHÔNG tạo job trùng (2 job auto
    # song song sẽ gọi LLM 2 lần + ghi đè lẫn nhau bảng clips). skip_if_done=False
    # để sau khi xong vẫn bấm "Tạo clip" lại được (tạo lại gợi ý mới).
    return pool.enqueue(
        "auto", {"video_id": video_id, "preset": preset or {}},
        project_id=project_id, video_id=video_id, needs_gpu=True, priority=10,
        dedup_key=f"auto:{video_id}", skip_if_done=False,
    )


def enqueue_auto_mixed(pool: WorkerPool, video_id: int, project_id: int,
                       preset: Optional[dict] = None) -> Optional[int]:
    """Nút 'Mixed-Cut': phân tích (nếu chưa) + ghép khoảnh khắc hay nhất."""
    return pool.enqueue(
        "auto_mixed", {"video_id": video_id, "preset": preset or {}},
        project_id=project_id, video_id=video_id, needs_gpu=True, priority=10,
        dedup_key=f"automix:{video_id}", skip_if_done=False,
    )


def enqueue_auto_recap(pool: WorkerPool, video_id: int, project_id: int,
                       preset: Optional[dict] = None) -> Optional[int]:
    """Nút '🎙 Reup thuyết minh': phân tích (nếu chưa) + AI viết kịch bản
    thuyết minh (preset kèm recap_style/recap_ratio/recap_count). Dedup như
    auto — recap_count vào dedup key để đổi 'Số clip' rồi bấm lại vẫn chạy
    (job cũ khác count đang chờ không nuốt mất lần bấm mới)."""
    try:                                # 0 = "Tự động theo độ dài" (hợp lệ,
        cnt = int((preset or {}).get("recap_count", 0) or 0)   # đừng ép về 2)
    except (TypeError, ValueError):
        cnt = 0
    return pool.enqueue(
        "auto_recap", {"video_id": video_id, "preset": preset or {}},
        project_id=project_id, video_id=video_id, needs_gpu=True, priority=10,
        dedup_key=f"autorecap:{video_id}:c{cnt}", skip_if_done=False,
    )


def enqueue_thay_giong(pool: WorkerPool, video_path: str, dich_sang: str,
                       voice: str = "", cach_tach: str = "auto",
                       thay_goc: bool = True, kenh: str = "",
                       thung_rac: str = "", thu_muc_lam: str = "",
                       ) -> Optional[int]:
    """THAY GIỌNG NÓI cho MỘT video — job chạy ở LÀN RIÊNG (worker.LAN_TG).

    Mỗi video một job (không gộp cả thư mục vào một job): tắt app giữa chừng
    thì các video chưa làm vẫn nằm trong DB và chạy tiếp khi mở lại.

    `dedup_key` khoá theo ĐƯỜNG DẪN + ngôn ngữ + giọng: bấm Chạy hai lần trên
    cùng thư mục thì lần thứ hai TRẢ VỀ ID JOB CŨ (không đẻ job trùng, cũng
    KHÔNG trả None — bài học "enqueue trả jid CŨ khi trùng, không trả None").
    `skip_if_done=False` để sau này vẫn chạy lại được sang ngôn ngữ khác.
    `max_attempts=1`: một lượt tốn hàng phút + lượt Groq, tự thử lại 3 lần là
    đốt lượt của 300 kênh cho một video hỏng thật.
    """
    duong = os.path.abspath(str(video_path))
    khoa = f"thaygiong:{duong.lower()}:{dich_sang}:{voice}"
    return pool.enqueue(
        "thay_giong",
        {"video": duong, "dich_sang": dich_sang, "voice": voice,
         "cach_tach": cach_tach, "thay_goc": bool(thay_goc), "kenh": kenh,
         "thung_rac": thung_rac, "thu_muc_lam": thu_muc_lam},
        needs_gpu=False, priority=5,
        dedup_key=khoa, skip_if_done=False, max_attempts=1,
    )


def enqueue_export(pool: WorkerPool, clip_id: int, video_id: int,
                   project_id: int, out_w: int = 1080, out_h: int = 1920,
                   mode: str = "face", zoom: float = 1.0,
                   crop_rect=None, text_overlays=None, overlay_png=None,
                   # ĐƠN THUỐC vẽ lại lớp chữ (layers/tiêu đề/part/logo...).
                   # KHÔNG đưa vào `extra` (hash chống trùng): nội dung ảnh đã
                   # được `ovl` (cỡ + mtime của file PNG) đại diện rồi; thêm
                   # vào đây là ĐỔI dedup_key của MỌI clip cũ -> 200-300 kênh
                   # xuất lại từ đầu.
                   ovl_spec=None,
                   video_rect=None, bg: str = "blur",
                   trim_black: bool = False, part_no: int = 0,
                   out_name: str = "", captions: bool = False,
                   cap_style: Optional[dict] = None,
                   blur_amt: int = 22, speed: float = 1.0,
                   pitch: float = 1.0, out_dir: str = "",
                   hook_first: bool = False, bgm_path: str = "",
                   bgm_vol: float = 0.15, orig_vol: float = 1.0,
                   dub_lang: str = "",
                   dub_voice: str = "", dub_mute: bool = False,
                   dub_mode: str = "natural",
                   recap_voice: str = "", recap_pace: str = "",
                   recap_pitch: str = "", recap_volume: float = 1.15,
                   recap_emotion: bool = True, recap_dim: float = 0.14,
                   fx_fade: bool = True, fx_whoosh: bool = True,
                   # CHUYỂN CẢNH ở chỗ ghép đoạn (xfade): tat|nhe|vua|manh.
                   # Phải vào `extra` (sig dedup) — đổi mức là clip KHÁC hẳn,
                   # không vào sig thì bấm xuất lại bị smart-skip, user tưởng
                   # "chọn rồi mà không thấy đổi".
                   chuyen_canh: str = "nhe",
                   # HIỆU ỨNG ĐIỂM NHẤN: tat|nhe|vua|manh. Cũng phải vào `extra`
                   # (sig dedup) vì đổi mức là clip KHÁC hẳn — không vào sig thì
                   # bấm xuất lại bị smart-skip, user tưởng "chọn rồi mà không
                   # thấy đổi" (đúng lỗi đã gặp với chuyen_canh).
                   hieu_ung: str = "nhe",
                   fx_sfx_dir: str = "", flip_h: bool = False,
                   fit_src: bool = False,
                   # CHE CHỮ CHÁY SẴN TRONG HÌNH (`app/core/che_chu.py`) —
                   # cùng khuôn `flip_h`/`fx_sfx_dir`: cờ CHỐT lúc xếp job nên
                   # mẫu bị sửa/xoá giữa chừng cũng không đổi kết quả clip.
                   # `None` = LỐI GỌI KHÔNG TRUYỀN -> payload KHÔNG mang khoá
                   # `che_chu` -> `m1.doc_che_chu` đi ĐƯỜNG LÙI (tra mẫu theo
                   # tên). Giữ `None` chứ không phải `False` là CỐ Ý: `False`
                   # nghĩa là "đã chốt: TẮT" và sẽ BỊT đường lùi của mọi lối
                   # gọi cũ chưa kịp nối.
                   che_chu: Optional[bool] = None,
                   che_chu_cach: str = "",
                   che_chu_muc: Optional[float] = None,
                   # QUÉT CẢ KHUNG (chữ ở TRÊN/GÓC) thay vì chỉ dải ĐÁY.
                   # `None` = không chốt -> theo env `BQ_CHE_TOAN_KHUNG`
                   # (mặc định TẮT). Cùng lý do ba-trạng-thái như `che_chu`.
                   che_chu_toan_khung: Optional[bool] = None,
                   flat_export: bool = False,
                   force: bool = False) -> Optional[int]:
    """force=True: xuất lại kể cả khi từng xuất xong y hệt (nút 'Xuất lại' /
    'Xuất clip này' — user chủ động muốn file mới, vd đã lỡ xóa file cũ)."""
    # sig phải phủ MỌI thứ ảnh hưởng kết quả: cả mốc cắt start/end của clip
    # (user kéo sửa trim rồi xuất lại) + NỘI DUNG chữ (overlay_png là đường dẫn
    # cố định _ovl_{clip_id}.png nên phải hash nội dung file) + nơi lưu.
    row = db.query_one("SELECT start_sec, end_sec FROM clips WHERE id=?",
                       (clip_id,))
    se = f"{row['start_sec']:.3f}-{row['end_sec']:.3f}" if row else "?"
    ovl = ""
    if overlay_png:
        try:
            st = Path(overlay_png).stat()
            ovl = f"{st.st_size}:{st.st_mtime_ns}"
        except OSError:
            pass
    extra = hashlib.sha1(
        repr((text_overlays, cap_style, out_name, out_dir, ovl,
              hook_first, bgm_path, bgm_vol, orig_vol,
              dub_lang, dub_voice, dub_mute, dub_mode,
              recap_voice, recap_pace, recap_pitch,
              round(float(recap_volume or 0), 3), bool(recap_emotion),
              round(float(recap_dim or 0), 3),
              fx_fade, fx_whoosh, fx_sfx_dir, flip_h, fit_src,
              str(chuyen_canh or ""), str(hieu_ung or ""),
              bool(flat_export))).encode()
    ).hexdigest()[:12]
    # CHE CHỮ vào hash chống trùng — nếu không thì bật ô trong Chỉnh mẫu rồi
    # bấm "Xuất cả kênh" là clip đã xuất bị SMART-SKIP, user phải bấm "Xuất
    # lại" từng clip mới ăn (lỗi thật, đúng họ với chuyen_canh/hieu_ung).
    # CHỈ GÓP KHI THẬT SỰ BẬT, và nối vào ĐUÔI `sig` chứ không thêm phần tử
    # vào tuple `extra`: thêm vào tuple là đổi hash của MỌI clip cũ -> 200-300
    # kênh xuất lại từ đầu. Cách này giữ `sig` GIỐNG TỪNG KÝ TỰ bản trước khi
    # cờ TẮT, mà bật/tắt/đổi cách/đổi mức vẫn ĐỔI hash.
    _cc_sig = ""
    if che_chu:
        from app.core import che_chu as _CC
        # Kẹp qua `chuan_*` TRƯỚC khi băm: hai mức 0,30 và 0,50 đều bị sàn kéo
        # về 0,60 nên ra clip GIỐNG HỆT — băm giá trị thô là đẻ job xuất lại
        # cho một thay đổi không tồn tại.
        _cc_m = _CC.MUC_MO_MAC_DINH if che_chu_muc is None else che_chu_muc
        _cc_sig = (f":cc{_CC.chuan_cach(che_chu_cach)}"
                   f"{_CC.chuan_muc_mo(_cc_m):.2f}")
        # QUÉT CẢ KHUNG đổi HẲN vùng che -> phải đổi hash, nếu không thì bật ô
        # xong bấm "Xuất cả kênh" là bị smart-skip (đúng lỗi v2.25.0 đã gặp).
        # Nối vào ĐUÔI và CHỈ khi BẬT -> `sig` của mẫu che-dải-đáy giữ nguyên
        # TỪNG KÝ TỰ, không đẻ job xuất lại cho 200-300 kênh.
        if che_chu_toan_khung:
            _cc_sig += "tk"
    sig = (f"{se}:{mode}:{zoom}:{crop_rect}:{video_rect}:{bg}:{trim_black}:"
           f"cap{int(captions)}:{blur_amt}:{speed}:{pitch}:{extra}{_cc_sig}")
    tai = {"clip_id": clip_id, "out_w": out_w, "out_h": out_h,
         "mode": mode, "zoom": zoom, "crop_rect": crop_rect,
         "text_overlays": text_overlays or [], "overlay_png": overlay_png,
         "ovl_spec": ovl_spec or {},
         "video_rect": video_rect, "bg": bg, "trim_black": trim_black,
         "part_no": part_no, "out_name": out_name, "captions": captions,
         "cap_style": cap_style or {}, "blur_amt": blur_amt,
         "speed": speed, "pitch": pitch, "out_dir": out_dir,
         "hook_first": hook_first, "bgm_path": bgm_path, "bgm_vol": bgm_vol,
         "orig_vol": orig_vol,
         "dub_lang": dub_lang, "dub_voice": dub_voice, "dub_mute": dub_mute,
         "dub_mode": dub_mode,
         "recap_voice": recap_voice, "recap_pace": recap_pace,
         "recap_pitch": recap_pitch, "recap_volume": recap_volume,
         "recap_emotion": recap_emotion, "recap_dim": recap_dim,
         "fx_fade": fx_fade, "fx_whoosh": fx_whoosh,
         "chuyen_canh": chuyen_canh, "hieu_ung": hieu_ung,
         "fx_sfx_dir": fx_sfx_dir, "flip_h": flip_h, "fit_src": fit_src,
         "flat": bool(flat_export)}
    if che_chu is not None:
        # CHỈ đặt khoá khi lối gọi ĐÃ CHỐT cờ. Đặt vô điều kiện là bịt đường
        # lùi "tra mẫu theo tên" của mọi lối gọi chưa nối (`doc_che_chu` chọn
        # đường bằng `"che_chu" in payload`).
        tai["che_chu"] = bool(che_chu)
        tai["che_chu_cach"] = che_chu_cach or ""
        tai["che_chu_muc"] = che_chu_muc
        # GIỮ `None` nếu lối gọi không chốt (ba trạng thái) — `doc_che_chu`
        # phân biệt bằng `is not None`, ép `bool()` là mất đường theo env.
        tai["che_chu_toan_khung"] = che_chu_toan_khung
    return pool.enqueue(
        "m1_export_clip", tai,
        project_id=project_id, video_id=video_id,
        needs_gpu=False, priority=3,   # cắt/xuất libx264 -> lane CPU (luồng cắt riêng)
        dedup_key=f"export:{clip_id}:{out_w}x{out_h}:p{part_no}:{sig}",
        skip_if_done=not force,
    )


# ---- Truy vấn cho UI ----
def list_clips(video_id: int) -> list:
    # Theo thứ tự THỜI GIAN (đoạn đầu -> cuối) để Part 1,2,3 đúng thứ tự.
    # BỎ clip 'archived' = kết quả các LẦN PHÂN TÍCH TRƯỚC (đã xuất, đã lưu
    # kho). Hàm này quyết định CẢ danh sách hiện lên, số Part, VÀ những gì
    # "Xuất cả kênh"/tự-xuất sẽ xuất — để lọt clip cũ vào là user đặt 3 part
    # mà ra 7-8 part, lẫn cả clip "Cắt cơ bản" không tiêu đề của lần trước
    # (lỗi thật anh Hùng 30/07). Xem m1_highlight._delete_suggested.
    return db.query(
        "SELECT * FROM clips WHERE video_id=? AND status<>'archived' "
        "ORDER BY start_sec, id",
        (video_id,),
    )


# ---- Mẫu (template/preset) cho Module 1 ----
def save_template(name: str, data: dict) -> None:
    """Lưu/ghi đè mẫu theo tên (khung + các lớp chữ).

    CẮT khoảng trắng đầu/cuối. LỖI THẬT 31/07/2026 (rà lại mẫu-theo-kênh):
    `set_project_template` CÓ cắt tên khi gán cho kênh, còn hàm này thì KHÔNG —
    lưu mẫu tên ' mẫu A ' rồi gán cho kênh thành 'mẫu A' -> tra không thấy ->
    kênh âm thầm rơi về mẫu trang chính, clip ra sai mẫu mà không ai biết.

    GỠ mọi khoá `_` TẠM trước khi lưu (hiện có `_ten_mau` — dấu tên mẫu do
    `_tpl_for_project` đóng vào BẢN SAO để ghi nhật ký). Lý do: lúc xuất,
    `self.layout_tpl` mang bản sao có dấu; user mở Chỉnh mẫu rồi Lưu ngay lúc
    đó là dấu bị ghi vào mẫu TRÊN ĐĨA — mẫu của kênh A đi lang thang trong mẫu
    dùng chung. Dấu là thứ TẠM, đừng để nó sống lâu hơn 1 lượt xuất.
    (cổng 28 bắt được 06/08/2026)"""
    sach = {k: v for k, v in (data or {}).items()
            if not str(k).startswith("_")}
    db.execute(
        "INSERT INTO presets (name, module, data) VALUES (?, 'm1', ?) "
        "ON CONFLICT(name) DO UPDATE SET data=excluded.data",
        ((name or "").strip(), db.dumps(sach)),
    )


def list_templates() -> list:
    return db.query("SELECT name FROM presets WHERE module='m1' ORDER BY name")


def get_template(name: str) -> Optional[dict]:
    # TRIM CẢ 2 ĐẦU: mẫu CŨ đã lưu kèm khoảng trắng (từ trước bản vá
    # save_template) vẫn tra ra được -> không bắt user gán lại mẫu cho từng kênh.
    row = db.query_one(
        "SELECT data FROM presets WHERE TRIM(name)=TRIM(?) AND module='m1'",
        (name,))
    return db.loads(row["data"]) if row else None


def delete_template(name: str) -> None:
    db.execute("DELETE FROM presets WHERE TRIM(name)=TRIM(?) AND module='m1'",
               (name,))


# ---- MẪU RIÊNG THEO KÊNH (anh Hùng 31/07) ----
def set_project_template(project_id: int, name: str) -> None:
    """Gán mẫu cho 1 kênh. name='' = dùng mẫu đang chọn trên trang chính."""
    db.execute("UPDATE projects SET tpl_name=? WHERE id=?",
               ((name or "").strip(), int(project_id)))


def project_template_name(project_id) -> str:
    """Tên mẫu đã gán cho kênh ('' nếu chưa gán). Không ném lỗi."""
    try:
        r = db.query_one("SELECT tpl_name FROM projects WHERE id=?",
                         (int(project_id),))
    except (TypeError, ValueError):
        return ""
    return ((r["tpl_name"] if r else "") or "").strip()


# ---- AI XEM HÌNH RIÊNG THEO KÊNH (anh Hùng 09/08/2026) ----
#: giá trị hợp lệ của `projects.xem_hinh`. Dùng None chứ KHÔNG dùng '' hay -1:
#: SQLite NULL là thứ duy nhất phân biệt được "chưa ai đụng tới" với "user đã
#: chủ động chọn TẮT" — mà phân biệt đó chính là điều kiện để sau này đổi mặc
#: định toàn cục (bật cho tất cả) mà không giẫm lên lựa chọn của anh Hùng.
def set_project_vision(project_id: int, bat) -> None:
    """Đặt AI XEM HÌNH cho 1 kênh.

    `bat`: True/1 = BẬT · False/0 = TẮT · None = XOÁ lựa chọn riêng (kênh đi
    theo mặc định app như chưa từng đụng tới)."""
    v = None if bat is None else (1 if bat else 0)
    db.execute("UPDATE projects SET xem_hinh=? WHERE id=?",
               (v, int(project_id)))


def project_vision(project_id) -> Optional[bool]:
    """AI XEM HÌNH của kênh: True = bật riêng · False = tắt riêng ·
    **None = kênh chưa đụng tới -> theo mặc định app**. KHÔNG BAO GIỜ ném lỗi
    (DB cũ chưa có cột / DB vỡ -> None = y như cũ)."""
    try:
        r = db.query_one("SELECT xem_hinh FROM projects WHERE id=?",
                         (int(project_id),))
    except (TypeError, ValueError):
        return None
    if not r:
        return None
    try:
        v = r["xem_hinh"]
    except (KeyError, IndexError):
        return None
    if v is None or v == "":
        return None
    try:
        return bool(int(v))
    except (TypeError, ValueError):
        return None


def project_template(project_id) -> Optional[dict]:
    """MẪU (dict) của kênh, hoặc None nếu kênh chưa gán / mẫu đã bị xoá.

    Trả None -> caller dùng mẫu đang chọn như CŨ. Nhờ vậy xoá mẫu đi thì dây
    chuyền vẫn chạy (chỉ mất phần riêng), KHÔNG bao giờ chết vì thiếu mẫu."""
    ten = project_template_name(project_id)
    if not ten:
        return None
    return get_template(ten)


def clear_finished_jobs() -> int:
    """Xóa lịch sử job ĐÃ XONG/lỗi/hủy khỏi danh sách tiến trình. GIỮ việc đang
    chạy/chờ. Trả số dòng đã xóa."""
    cur = db.execute(
        "DELETE FROM jobs WHERE status IN ('done','failed','canceled','skipped')")
    try:
        return cur.rowcount if cur else 0
    except Exception:  # noqa: BLE001
        return 0


def job_state(job_id: int) -> str:
    """Trạng thái 1 job ('done'/'failed'/'running'/'pending'/...); '' nếu không có.
    Dùng cho TỰ ĐỘNG XUẤT: theo dõi job phân tích, xong thì kích hoạt xuất."""
    if not job_id:
        return ""
    row = db.query_one("SELECT status FROM jobs WHERE id=?", (job_id,))
    return row["status"] if row else ""


def job_states(job_ids) -> dict:
    """{job_id: status} cho NHIỀU job trong 1 query — timer UI theo dõi hàng
    chục job chờ tự-xuất mà query từng cái mỗi 1.5s thì phí. Job không còn
    trong DB sẽ VẮNG MẶT trong dict (caller coi như '')."""
    ids = [int(j) for j in (job_ids or []) if j]
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    rows = db.query(f"SELECT id, status FROM jobs WHERE id IN ({marks})", ids)
    return {int(r["id"]): r["status"] for r in rows}


def list_jobs(limit: int = 100) -> list:
    # kèm tên KÊNH + đường dẫn video để thanh tiến trình hiện rõ việc nào của ai
    return db.query(
        "SELECT j.*, p.name AS chan_name, v.src_path AS vid_path "
        "FROM jobs j "
        "LEFT JOIN projects p ON p.id = j.project_id "
        "LEFT JOIN videos v ON v.id = j.video_id "
        "ORDER BY "
        "CASE j.status WHEN 'running' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END, "
        "j.id DESC LIMIT ?", (limit,),
    )


_JOB_COT = ("SELECT j.*, p.name AS chan_name, v.src_path AS vid_path FROM jobs j "
            "LEFT JOIN projects p ON p.id = j.project_id "
            "LEFT JOIN videos v ON v.id = j.video_id ")


def list_jobs_top(n_chay: int = 24, n_xong: int = 12) -> tuple:
    """(việc ĐANG CHẠY/CHỜ, việc VỪA XONG/LỖI) — mỗi bên lấy ĐÚNG số cần vẽ.

    Vì sao tách 2 query (đo 06/08/2026, cảnh 200 kênh): bản cũ lấy CHUNG
    `list_jobs(limit=200)` rồi mới chia. Khi có 300 việc đang chạy/chờ thì 200
    dòng bị chiếm hết bởi việc đang chạy -> **danh sách MẤT SẠCH việc "✅ Xong"**
    (user tưởng chưa xong cái nào). Lấy riêng thì bên nào cũng đủ, mà còn nhẹ
    hơn: chỉ đọc đúng số dòng sẽ vẽ thay vì 200 dòng rồi bỏ 164."""
    chay = db.query(
        _JOB_COT + "WHERE j.status IN ('running','pending') ORDER BY "
        "CASE j.status WHEN 'running' THEN 0 ELSE 1 END, j.id DESC LIMIT ?",
        (max(1, int(n_chay)),))
    # việc LỖI xếp TRƯỚC: danh sách bị cắt trần nên nếu xếp thuần theo id thì
    # hàng chục việc "✅ Xong" đẩy việc LỖI ra khỏi bảng -> user không thấy để
    # bấm "Thử lại". Lỗi mới là thứ cần nhìn nhất.
    xong = db.query(
        _JOB_COT + "WHERE j.status IN ('done','failed','canceled','skipped') "
        "ORDER BY CASE j.status WHEN 'failed' THEN 0 ELSE 1 END, j.id DESC "
        "LIMIT ?", (max(1, int(n_xong)),))
    return chay, xong


def queue_counts() -> dict:
    """Đếm job cho BẢNG ĐẾM TRẠNG THÁI khu Tiến trình (1 query GROUP BY nhẹ,
    có idx_jobs_status).

    - analyzing / exporting: đang chạy (running) — xuất = m1_export_clip,
      còn lại là giai đoạn phân tích (khớp màu giai đoạn ở queue_panel).
    - waiting: mọi việc pending (kèm tách wait_analyze / wait_export).
    - done / failed: CHỈ đếm việc tạo HÔM NAY (created_at của SQLite là
      datetime('now') = UTC -> quy đổi 0h local sang UTC để so sánh).
    - canceled / skipped: KHÔNG tính vào bất kỳ ô nào.
    """
    from datetime import datetime, timezone
    day0 = (datetime.now()
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
    rows = db.query(
        "SELECT status, type, COUNT(*) AS n FROM jobs "
        "WHERE status IN ('running','pending') "
        "   OR (status IN ('done','failed') AND created_at >= ?) "
        "GROUP BY status, type", (day0,))
    c = {"analyzing": 0, "exporting": 0, "waiting": 0,
         "wait_analyze": 0, "wait_export": 0, "done": 0, "failed": 0}
    for r in rows:
        st, jt, n = r["status"], r["type"], int(r["n"])
        if st == "running":
            c["exporting" if jt == "m1_export_clip" else "analyzing"] += n
        elif st == "pending":
            c["waiting"] += n
            c["wait_export" if jt == "m1_export_clip" else "wait_analyze"] += n
        elif st == "done":
            c["done"] += n
        elif st == "failed":
            c["failed"] += n
    return c


# ---- Hoạt động theo KÊNH (nhãn cạnh combo Kênh + bảng "Tình hình các kênh") ----
def channel_activity() -> dict:
    """Tình hình job của TOÀN BỘ kênh trong vài query GROUP BY (dùng
    idx_jobs_project, KHÔNG query từng kênh — user chạy nhiều kênh cùng lúc).

    Trả dict[project_id] = {
        "running": n, "pending": n,
        "failed_recent": n,        # job failed trong 24h qua
        "exported": n,             # tổng clip đã xuất xong (m1_export_clip done)
        "videos": n,               # tổng VIDEO trong kênh (COUNT videos)
        "clips": n,                # tổng CLIP đã tạo (COUNT clips, mọi status)
        "last_done": "YYYY-MM-DD HH:MM:SS" (UTC, như SQLite ghi) | None,
        "last_done_type": type của job done gần nhất ("auto"/"m1_export_clip"...),
    } — mọi project đều có mặt (kênh chưa có job = toàn 0/None).
    """
    from datetime import datetime, timedelta, timezone
    # SQLite datetime('now') ghi UTC -> mốc 24h cũng phải tính bằng UTC
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)
              ).strftime("%Y-%m-%d %H:%M:%S")
    # last_done ĐỌC THẲNG từ kênh (bền vững qua 'Xóa lịch sử'), KHÔNG suy ra
    # từ bảng jobs nữa.
    act = {int(p["id"]): {"running": 0, "pending": 0, "failed_recent": 0,
                          "exported": 0, "videos": 0, "clips": 0,
                          "last_done": p["last_done_at"],
                          "last_done_type": p["last_done_type"] or ""}
           for p in db.query(
               "SELECT id, last_done_at, last_done_type FROM projects")}
    for r in db.query(
            "SELECT project_id AS pid, "
            "SUM(status='running') AS running, "
            "SUM(status='pending') AS pending, "
            "SUM(status='failed' AND COALESCE(finished_at, created_at) >= ?) "
            "  AS failed_recent "
            "FROM jobs WHERE project_id IS NOT NULL GROUP BY project_id",
            (cutoff,)):
        a = act.get(int(r["pid"]))
        if a is None:          # job của project vừa bị xóa (race) -> bỏ qua
            continue
        a["running"] = int(r["running"] or 0)
        a["pending"] = int(r["pending"] or 0)
        a["failed_recent"] = int(r["failed_recent"] or 0)
    # tổng VIDEO / tổng CLIP đã tạo / CLIP ĐÃ XUẤT từng kênh — đếm từ bảng
    # clips (export_path) chứ KHÔNG từ jobs, nên 'Xóa lịch sử' không làm mất
    # số 'Đã xuất'. (mỗi cột 1 query GROUP BY, vẫn nhẹ)
    for r in db.query("SELECT project_id AS pid, COUNT(*) AS n "
                      "FROM videos GROUP BY project_id"):
        a = act.get(int(r["pid"]))
        if a is not None:
            a["videos"] = int(r["n"])
    for r in db.query(
            "SELECT v.project_id AS pid, COUNT(*) AS n, "
            "SUM(c.export_path IS NOT NULL AND c.export_path<>'') AS exported "
            "FROM clips c JOIN videos v ON v.id = c.video_id "
            "WHERE c.status<>'archived' "   # kho lưu trữ không tính vào đuôi combo
            "GROUP BY v.project_id"):
        a = act.get(int(r["pid"]))
        if a is not None:
            a["clips"] = int(r["n"])
            a["exported"] = int(r["exported"] or 0)
    return act


# ---- Hoạt động theo TỪNG VIDEO trong 1 kênh (đuôi combo Video + nhãn +
# ---- bảng chi tiết video trong dialog "Tình hình các kênh") ----
def video_activity(project_id: int) -> dict:
    """Tình hình job/clip của TỪNG VIDEO trong kênh `project_id` — vài query
    GROUP BY video_id GIỚI HẠN theo project_id (idx_jobs_project /
    idx_clips_video), KHÔNG query từng video (kênh nhiều video vẫn nhẹ).

    Trả dict[video_id] = {
        "running": n,        # job đang chạy (mọi loại)
        "run_export": n,     # trong đó job XUẤT clip đang chạy (phân biệt
                             # 'đang cắt/phân tích' với 'đang xuất' trên UI)
        "pending": n,
        "failed_recent": n,  # job failed trong 24h qua
        "clips": n,          # clip đã tạo (mọi status)
        "exported": n,       # job xuất xong (m1_export_clip done)
        "last_done": "YYYY-MM-DD HH:MM:SS" (UTC như SQLite ghi) | None,
        "last_done_type": type của job done gần nhất,
    } — MỌI video của kênh đều có mặt (video chưa làm gì = toàn 0/None).
    """
    from datetime import datetime, timedelta, timezone
    # SQLite datetime('now') ghi UTC -> mốc 24h cũng phải tính bằng UTC
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)
              ).strftime("%Y-%m-%d %H:%M:%S")
    # last_done ĐỌC THẲNG từ video (bền vững qua 'Xóa lịch sử').
    act = {int(v["id"]): {"running": 0, "run_export": 0, "pending": 0,
                          "failed_recent": 0, "clips": 0, "exported": 0,
                          "last_done": v["last_done_at"],
                          "last_done_type": v["last_done_type"] or ""}
           for v in db.query(
               "SELECT id, last_done_at, last_done_type FROM videos "
               "WHERE project_id=?", (project_id,))}
    for r in db.query(
            "SELECT video_id AS vid, "
            "SUM(status='running') AS running, "
            "SUM(status='running' AND type='m1_export_clip') AS run_export, "
            "SUM(status='pending') AS pending, "
            "SUM(status='failed' AND COALESCE(finished_at, created_at) >= ?) "
            "  AS failed_recent "
            "FROM jobs WHERE project_id=? AND video_id IS NOT NULL "
            "GROUP BY video_id", (cutoff, project_id)):
        a = act.get(int(r["vid"]))
        if a is None:          # job của video vừa bị xóa (race) -> bỏ qua
            continue
        a["running"] = int(r["running"] or 0)
        a["run_export"] = int(r["run_export"] or 0)
        a["pending"] = int(r["pending"] or 0)
        a["failed_recent"] = int(r["failed_recent"] or 0)
    # clip đã tạo + clip ĐÃ XUẤT (export_path) đếm từ bảng clips -> 'Đã xuất'
    # không mất khi 'Xóa lịch sử'.
    for r in db.query(
            "SELECT c.video_id AS vid, COUNT(*) AS n, "
            "SUM(c.export_path IS NOT NULL AND c.export_path<>'') AS exported "
            "FROM clips c JOIN videos v ON v.id = c.video_id "
            "WHERE v.project_id=? AND c.status<>'archived' "
            "GROUP BY c.video_id", (project_id,)):
        a = act.get(int(r["vid"]))
        if a is not None:
            a["clips"] = int(r["n"])
            a["exported"] = int(r["exported"] or 0)
    return act


def rel_time_vi(iso_str, short: bool = False) -> str:
    """'2026-07-12 08:00:00' (UTC — như SQLite datetime('now') ghi) -> chuỗi
    tương đối tiếng Việt: 'vừa xong' (<90s), 'X phút trước' (<60ph),
    'X giờ trước' (<24h), 'hôm qua', 'N ngày trước'. None/hỏng -> ''.
    short=True: dạng gọn cho đuôi combo ('12ph', '3h', 'hôm qua')."""
    from datetime import datetime, timezone
    if not iso_str:
        return ""
    s = str(iso_str).strip().replace("T", " ")
    s = s.split(".")[0].split("+")[0].strip()      # bỏ .ms / +tz nếu có
    try:
        t = datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc)
    except ValueError:
        return ""
    sec = (datetime.now(timezone.utc) - t).total_seconds()
    if sec < 0:                 # lệch đồng hồ nhẹ -> coi như vừa xong
        sec = 0
    if sec < 90:
        return "vừa xong"
    if sec < 3600:
        m = int(sec // 60)
        return f"{m}ph" if short else f"{m} phút trước"
    if sec < 86400:
        h = int(sec // 3600)
        return f"{h}h" if short else f"{h} giờ trước"
    d = int(sec // 86400)
    if d == 1:
        return "hôm qua"
    return f"{d} ngày" if short else f"{d} ngày trước"


# ---- Trạng thái phân tích ----
def video_analyzed(video_id: int) -> bool:
    """True nếu video đã chạy xong lõi phân tích (mọi bước done/skipped)."""
    st = analysis_status(video_id)
    if not st:
        return False
    return all(st.get(kind) in ("done", "skipped") for kind, _ in STEPS)


def video_analysis_label(video_id: int) -> str:
    """Nhãn ngắn cho UI: chưa / đang / xong / lỗi."""
    st = analysis_status(video_id)
    if not st:
        return "○ chưa phân tích"
    if any(v == "running" for v in st.values()):
        return "⏳ đang phân tích"
    if any(v == "failed" for v in st.values()):
        return "⚠ phân tích lỗi"
    if video_analyzed(video_id):
        return "✓ đã phân tích"
    return "○ chưa xong"


# ---- Xóa (dọn dữ liệu) ----
def _project_dir(project_id: int) -> Optional[Path]:
    row = db.query_one("SELECT assets_dir FROM projects WHERE id=?", (project_id,))
    return Path(row["assets_dir"]) if row else None


def cache_dir(assets_dir) -> str:
    """Thư mục con _cache chứa ảnh tạm (thumbnail/preview/lớp chữ) — KHÔNG để lẫn
    vào thư mục người dùng nhìn. Tạo nếu chưa có."""
    d = Path(assets_dir) / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def project_cache_dir(project_id: int) -> Optional[str]:
    pdir = _project_dir(project_id)
    return cache_dir(pdir) if pdir else None


def project_dir(project_id: int) -> Optional[str]:
    """Thư mục gốc của Kênh (chứa các folder con theo từng video)."""
    pdir = _project_dir(project_id)
    return str(pdir) if pdir else None


def delete_clip(clip_id: int) -> None:
    """Xóa 1 clip: file đã xuất + thumbnail + dòng DB."""
    row = db.query_one(
        """SELECT cl.export_path, p.assets_dir FROM clips cl
           JOIN videos v ON v.id=cl.video_id JOIN projects p ON p.id=v.project_id
           WHERE cl.id=?""", (clip_id,))
    if row:
        for f in (row["export_path"],
                  str(Path(cache_dir(row["assets_dir"])) / f"_thumb_{clip_id}.jpg")):
            if f:
                try:
                    Path(f).unlink(missing_ok=True)
                except OSError:
                    pass
    db.execute("DELETE FROM clips WHERE id=?", (clip_id,))


def _cancel_jobs(pool: Optional[WorkerPool], where: str, params: tuple) -> None:
    """Hủy job đang chờ/chạy trước khi xóa video/kênh — nếu không, dòng job bị
    cascade-xóa khỏi panel nhưng tiến trình phân tích/ffmpeg VẪN chạy ngầm và
    có thể tạo lại thư mục 'ma' sau khi xóa."""
    if not pool:
        return
    for j in db.query(
            f"SELECT id FROM jobs WHERE status IN ('pending','running') "
            f"AND {where}", params):
        pool.cancel(int(j["id"]))


def delete_video(video_id: int, pool: Optional[WorkerPool] = None) -> None:
    """
    Xóa 1 video khỏi project: hủy job liên quan, xóa file clip đã xuất +
    thumbnail + file audio tạm, rồi xóa dòng DB (cascade analysis/clips/jobs).
    """
    _cancel_jobs(pool, "video_id=?", (video_id,))
    proj = db.query_one("SELECT project_id FROM videos WHERE id=?", (video_id,))
    pdir = _project_dir(proj["project_id"]) if proj else None
    # xóa file clip + thumbnail trên đĩa
    for c in db.query("SELECT id, export_path FROM clips WHERE video_id=?",
                      (video_id,)):
        if c["export_path"]:
            try:
                Path(c["export_path"]).unlink(missing_ok=True)
            except OSError:
                pass
        if pdir:
            try:
                (Path(cache_dir(pdir)) / f"_thumb_{c['id']}.jpg").unlink(
                    missing_ok=True)
            except OSError:
                pass
    # xóa audio tạm nếu còn (nằm trong _cache/; dọn thêm chỗ cũ cho bản trước)
    if pdir:
        for wav in (pdir / "_cache" / f"audio_{video_id}.wav",
                    pdir / f"audio_{video_id}.wav"):
            try:
                wav.unlink(missing_ok=True)
            except OSError:
                pass
    db.execute("DELETE FROM videos WHERE id=?", (video_id,))  # cascade


def cleanup_stale_temp(days: float = 3.0) -> int:
    """Dọn FILE TẠM MỒ CÔI trong projects/*/_cache lúc khởi động (chạy nền).

    Đo thật cho thấy file tạm tích tụ khi job bị hủy/app bị tắt giữa chừng:
    audio_*.wav (29-38MB/video), _dub_*.wav (~30-50MB/clip), _ovl_*.png,
    _cap_*.ass, _vlf_*.jpg. Job đang chạy luôn tạo file MỚI (mtime hiện tại)
    nên chỉ xóa file cũ hơn `days` ngày — an toàn tuyệt đối với job đang chạy
    lẫn job sẽ retry. Kèm: giữ tối đa 3 bản studio_backup_*.db mới nhất.
    Trả về số file đã xóa (để log/test)."""
    import time
    from config import DATA_DIR, PROJECTS_DIR
    cutoff = time.time() - days * 86400
    n = 0
    pats = ("_ovl_*.png", "_cap_*.ass", "_dub_*.wav", "_vlf_*.jpg",
            "audio_*.wav")
    try:
        cache_dirs = list(PROJECTS_DIR.glob("*/_cache"))
    except OSError:
        cache_dirs = []
    for cd in cache_dirs:
        for pat in pats:
            try:
                for f in cd.glob(pat):
                    try:
                        if f.stat().st_mtime < cutoff:
                            f.unlink()
                            n += 1
                    except OSError:
                        pass
            except OSError:
                pass
    # backup DB (tạo khi cứu DB hỏng): giữ 3 bản mới nhất, xóa phần còn lại
    try:
        baks = sorted(DATA_DIR.glob("studio_backup_*.db"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        for f in baks[3:]:
            try:
                f.unlink()
                n += 1
            except OSError:
                pass
    except OSError:
        pass
    return n


def delete_project(project_id: int, pool: Optional[WorkerPool] = None) -> None:
    """Xóa cả project: hủy job, xóa thư mục assets + dòng DB (cascade toàn bộ).

    ═══ CỬA HỞ ĐÃ VÁ 19/08/2026 (cổng 80) — CỬA NGUY HIỂM NHẤT TRONG SỐ 5 ═══
    `_project_dir` trả thẳng ``Path(row["assets_dir"])`` không kiểm gì. Một
    dòng DB có `assets_dir` **rỗng** cho ra ``Path("")`` = ``WindowsPath('.')``
    -> `pdir.exists()` True -> `rmtree(".")` **XOÁ THƯ MỤC ĐANG LÀM VIỆC**,
    đúng tai nạn `giong_ngoai._don` cùng ngày. Khác ba cửa kia ở chỗ đây là
    đường NGƯỜI DÙNG BẤM ("Xoá kênh"), và dữ liệu vào đến từ DB — mà DB này
    đã từng vỡ (30/07) nên "dòng có giá trị lạ" không phải chuyện giả định.
    """
    _cancel_jobs(pool, "project_id=?", (project_id,))
    pdir = _project_dir(project_id)
    db.execute("DELETE FROM projects WHERE id=?", (project_id,))  # cascade
    if pdir is not None:
        from app.core.xoa_an_toan import don_thu_muc
        don_thu_muc(pdir)


# ══════════════ 👍/👎 GU CỦA CHỦ KÊNH (AI học sở thích) ══════════════
# Anh Hùng 06/08/2026: "AI cắt nhiều đoạn lấy hài quá không cần thiết". Chấm
# điểm bằng thang chung thì mãi ra gu chung; nay ghi lại chính lựa chọn của anh
# rồi ĐƯA VÀO PROMPT của kênh đó làm ví dụ mẫu. Rẻ: không thêm lượt API.
def dat_gu_clip(clip_id: int, vote: int) -> None:
    """Ghi 👍 (vote=1) / 👎 (vote=-1) cho 1 clip; vote=0 = BỎ đánh giá.

    Lưu kèm TÓM TẮT (tiêu đề + câu thoại đầu + độ dài + số đoạn) để bài học
    sống sót khi clip bị xoá/phân tích lại. Bấm lại thì GHI ĐÈ (chỉ mục UNIQUE
    theo clip_id) — không nhân bản ý kiến.
    """
    cid = int(clip_id)
    if int(vote) == 0:
        db.execute("DELETE FROM clip_gu WHERE clip_id=?", (cid,))
        return
    r = db.query_one(
        "SELECT c.title, c.signals, c.transcript, c.reason, c.start_sec, "
        "c.end_sec, v.project_id FROM clips c JOIN videos v ON v.id=c.video_id "
        "WHERE c.id=?", (cid,))
    if not r:
        return
    sig = db.loads(r["signals"], {}) or {}
    segs = sig.get("segments") or []
    # ưu tiên LỜI THOẠI THẬT trong đoạn — dạy gu tốt hơn là lấy câu AI tự biện
    # luận; không có thoại (video ASMR) thì mới dùng `reason`.
    thoai = " ".join(str(r["transcript"] or r["reason"] or "").split())[:180]
    dai = max(0.0, float(r["end_sec"] or 0) - float(r["start_sec"] or 0))
    db.execute(
        "INSERT INTO clip_gu(project_id,clip_id,vote,title,thoai,dai,n_seg) "
        "VALUES(?,?,?,?,?,?,?) ON CONFLICT(clip_id) DO UPDATE SET "
        "vote=excluded.vote, title=excluded.title, thoai=excluded.thoai, "
        "dai=excluded.dai, n_seg=excluded.n_seg, "
        "created_at=datetime('now')",
        (int(r["project_id"] or 0), cid, 1 if int(vote) > 0 else -1,
         str(r["title"] or "")[:160], thoai, dai, len(segs)))


def gu_clip(clip_id: int) -> int:
    """👍=1 / 👎=-1 / chưa đánh giá=0 (để UI tô nút đang chọn)."""
    r = db.query_one("SELECT vote FROM clip_gu WHERE clip_id=?", (int(clip_id),))
    return int(r["vote"]) if r else 0


def nhap_so_lieu(duong_dan: str, project_id: int, nguon: str = "") -> tuple:
    """📊 NHẬP FILE SỐ LIỆU THẬT (CSV/JSON xuất từ TikTok/YouTube).

    Trả `(số dòng đã nhập, lý do)`. App **KHÔNG tự lấy được** view (không có
    API, không đăng nhập được kênh của anh Hùng) nên đây là cửa duy nhất.
    Định dạng file: xem `app.ai.so_lieu.huong_dan()`.
    """
    from app.ai import so_lieu as _sl
    return _sl.nhap_vao_db(duong_dan, int(project_id), db, nguon=nguon)


def so_lieu_kenh(project_id) -> dict:
    """Số liệu thật của kênh -> `{"tot": [...], "te": [...], "n": tổng}`."""
    from app.ai import so_lieu as _sl
    return _sl.so_lieu_cua_kenh(project_id, db)


def gu_cua_kenh(project_id, gioi_han: int = 6) -> dict:
    """Ví dụ 👍/👎 GẦN NHẤT của kênh -> {"thich": [...], "khong": [...]}.

    Lấy MỚI NHẤT vì gu đổi theo thời gian; giới hạn số ví dụ để prompt không
    phình (prompt chọn đoạn đã sát mức 413 với model lớn — xem config.py)."""
    ra = {"thich": [], "khong": []}
    if project_id is None:
        return ra
    for v, khoa in ((1, "thich"), (-1, "khong")):
        for r in db.query(
                "SELECT title, thoai, dai, n_seg FROM clip_gu WHERE "
                "project_id=? AND vote=? ORDER BY id DESC LIMIT ?",
                (int(project_id), v, int(gioi_han))):
            ra[khoa].append({"title": str(r["title"] or ""),
                             "thoai": str(r["thoai"] or ""),
                             "dai": float(r["dai"] or 0),
                             "n_seg": int(r["n_seg"] or 0)})
    return ra
