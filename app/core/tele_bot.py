"""BOT TELEGRAM QUẢN LÝ DÂY CHUYỀN — xem tiến độ + điều khiển từ điện thoại.

CẤU HÌNH (anh Hùng tự dán vào `<DATA_DIR>/.env`, app KHÔNG tự ghi mã nào):
    TELEGRAM_BOT_TOKEN=<token lấy ở @BotFather>
    TELEGRAM_CHAT_IDS=<id chat được phép điều khiển, nhiều id cách bằng dấu phẩy>
Chưa có id -> bot chỉ trả lời "id của bạn là X, thêm vào .env" và KHÔNG làm
lệnh nào: ai biết tên bot cũng không điều khiển được máy.

BA LUẬT SỐNG CÒN (lý do bot này được phép chạy chung với dây chuyền 300 kênh):
1. **Bot hỏng thì app KHÔNG hỏng.** Mọi thứ chạy ở 2 luồng daemon riêng, mọi
   vòng lặp bọc `except Exception`, mạng lỗi thì lùi dần (tối đa 60s). Không
   đụng một widget Qt nào (đụng Qt từ luồng nền là sập 0xC0000409).
2. **Bot không có đường điều khiển RIÊNG.** Tạm dừng / chạy tiếp / huỷ 1 job
   đi đúng hàm của `WorkerPool` mà nút trong app dùng. Tạm dừng chỉ ngừng LẤY
   VIỆC MỚI — việc đang chạy chạy hết, không kill, không mất nửa chừng.
   Lệnh CHẠY DÂY CHUYỀN đi qua hàng đợi luồng giao diện (`goi_ui`) tới đúng
   `_pipe_run(nen=True)` của nút ▶ Chạy — bot không tự quét/nhận video.
3. **Không có lệnh phá huỷ hàng loạt.** Không "huỷ tất cả", không xoá file:
   muốn ngừng hẳn thì /tamdung (đảo ngược được bằng /chaytiep).
"""
from __future__ import annotations

import os
import queue
import re
import shutil
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Optional

API = "https://api.telegram.org/bot{tok}/{m}"
NHIP_THEO_DOI = 30          # giây giữa 2 lượt soi dây chuyền
KET_PHUT = 25               # job chạy không đổi tiến độ quá số phút này = kẹt
O_TRONG_GB = 20             # ổ dữ liệu còn dưới số này -> báo
GOM_LOI_GIAY = 90           # gom lỗi trong cửa sổ này thành 1 tin
DONG_HAN_GIAY = 120         # nút xác nhận "Đóng app" chỉ có hiệu lực bấy nhiêu giây

_TEN_LOAI = {"auto": "phân tích + cắt", "m1_export_clip": "xuất Part",
             "auto_mixed": "cắt ghép", "auto_recap": "kể chuyện",
             "thay_giong": "thay giọng", "analyze": "phân tích"}

_bot: Optional["BotQuanLy"] = None


def _cfg() -> tuple[str, set[int]]:
    tok = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    ids = set()
    for x in (os.environ.get("TELEGRAM_CHAT_IDS") or "").replace(";", ",").split(","):
        x = x.strip()
        if x.lstrip("-").isdigit():
            ids.add(int(x))
    return tok, ids


def _ghi_log(dong: str) -> None:
    try:
        from config import LOGS_DIR
        Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)
        f = Path(LOGS_DIR) / f"telegram_{datetime.now():%Y%m%d}.log"
        with f.open("a", encoding="utf-8") as fh:
            fh.write(f"[{datetime.now():%H:%M:%S}] {dong}\n")
    except Exception:  # noqa: BLE001
        pass


def _so(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


def _phut(giay: float) -> str:
    giay = max(0, int(giay))
    h, m = divmod(giay // 60, 60)
    return f"{h} giờ {m} phút" if h else f"{m} phút"


# ---------------------------------------------------------------- dữ liệu --
def _db():
    from app.database import db
    return db


def _ten_job(r) -> str:
    """'phân tích + cắt · Kênh A · video.mp4' — đủ để anh Hùng nhận ra."""
    loai = _TEN_LOAI.get(r["type"], r["type"])
    ten_k = (r["kenh"] or "") if "kenh" in r.keys() else ""
    vid = Path(r["src"] or "").name if "src" in r.keys() and r["src"] else ""
    return " · ".join(x for x in (loai, ten_k, vid[:45]) if x)


_SQL_JOB = ("SELECT j.id, j.type, j.status, j.progress, j.message, j.error, "
            "j.started_at, j.finished_at, j.created_at, p.name AS kenh, "
            "v.src_path AS src FROM jobs j LEFT JOIN projects p ON p.id=j.project_id "
            "LEFT JOIN videos v ON v.id=j.video_id ")


def tong_quan() -> dict:
    """Số liệu 1 lần đọc DB — dùng chung cho /tiendo, tin báo, test."""
    db = _db()
    q = db.query
    dem = {r["status"]: r["n"] for r in q(
        "SELECT status, COUNT(*) n FROM jobs WHERE status IN ('pending','running') "
        "GROUP BY status")}
    hom_nay = {(r["type"], r["status"]): r["n"] for r in q(
        "SELECT type, status, COUNT(*) n FROM jobs WHERE "
        "date(finished_at,'localtime')=date('now','localtime') GROUP BY type, status")}
    cho = {r["type"]: r["n"] for r in q(
        "SELECT type, COUNT(*) n FROM jobs WHERE status='pending' GROUP BY type")}
    # thời gian TB mỗi loại job, đo trên việc xong 24h qua -> ước còn bao lâu
    tb = {r["type"]: r["s"] for r in q(
        "SELECT type, AVG((julianday(finished_at)-julianday(started_at))*86400) s "
        "FROM jobs WHERE status='done' AND finished_at>=datetime('now','-1 day') "
        "AND started_at IS NOT NULL GROUP BY type")}
    chay = q(_SQL_JOB + "WHERE j.status='running' ORDER BY j.started_at")
    loi = q(_SQL_JOB + "WHERE j.status='failed' AND "
            "date(j.finished_at,'localtime')=date('now','localtime') "
            "ORDER BY j.id DESC LIMIT 300")
    so = {r["status"]: r["n"] for r in q(
        "SELECT status, COUNT(*) n FROM pipeline_files WHERE "
        "date(coalesce(done_at,taken_at),'localtime')=date('now','localtime') "
        "GROUP BY status")}
    return {"pending": dem.get("pending", 0), "running": dem.get("running", 0),
            "hom_nay": hom_nay, "cho": cho, "tb": tb, "chay": chay, "loi": loi,
            "so": so, "corrupt": bool(getattr(db, "corrupt_live", False))}


def uoc_con_lai(d: dict, luong: tuple[int, int, int]) -> Optional[float]:
    """Giây ước còn lại: Σ(chờ × TB) chia số luồng của làn. None = chưa đủ số."""
    from app.queue.worker import LOAI_LAN_TG
    gpu = cpu = tg = 0.0
    for t, n in d["cho"].items():
        s = d["tb"].get(t)
        if not s:
            return None
        if t in LOAI_LAN_TG:
            tg += n * s
        elif t == "m1_export_clip":
            cpu += n * s
        else:
            gpu += n * s
    lg, lc, lt = (max(1, x) for x in luong)
    return max(gpu / lg, cpu / lc, tg / lt)


def _o_dia() -> tuple[str, float]:
    from config import DATA_DIR
    o = Path(DATA_DIR).anchor or str(DATA_DIR)
    return o, shutil.disk_usage(o).free / 1e9


_CHO_NHAN_CACHE: list = [0.0, None]
_CHO_NHAN_LOCK = threading.Lock()


def _goc_day_chuyen() -> str:
    """Thư mục gốc dây chuyền (kênh không đặt thư mục riêng = <gốc>/<tên kênh>)."""
    try:
        from app.ui.appsettings import app_settings
        return str(app_settings().value("pipe_root", "") or "")
    except Exception:  # noqa: BLE001
        return ""


def dem_cho_nhan(ttl: float = 60.0) -> dict:
    """Video CÒN NẰM trong thư mục các kênh bật dây chuyền mà CHƯA được nhận
    -> {"video", "kenh", "con_suat", "het_suat", "loi"}.

    01/11/2026 (anh Hùng: "nhiều video vẫn đang chờ chưa phân tích mà bot
    không báo gì, cứ báo xong"): bot chỉ đếm bảng `jobs`, video chưa nhận thì
    chưa có job -> báo "HẾT hàng chờ" trong khi thư mục còn đầy.
    Luật đếm KHỚP ĐÚNG dây chuyền (rà soát cùng ngày, bản đầu lệch 4 chỗ):
      * thư mục = `pipeline.resolve_src_dir(gốc, tên, pipe_src|export_dir)`
        (kênh KHÔNG đặt thư mục riêng dùng <gốc>/<tên>);
      * chỉ file video HOÀN CHỈNH + đứng yên >= STABLE_AGE_SEC (đang tải thì
        chưa tính), bỏ file tạm và file "Part N" do app xuất;
      * đã có sổ taken/done/dup/bad theo TÊN FILE -> không tính (file 'dup'
        nằm lại thư mục nhưng dây chuyền không bao giờ nhận lại);
      * hạn mức ngày chỉ áp khi `pipe_daily >= 2` (đúng `plan_channel`;
        mặc định cột là 1 = KHÔNG giới hạn).
    Lỗi đọc 1 kênh KHÔNG được làm mất số các kênh khác: đếm vào "loi" để tin
    báo nói "chưa đếm được" thay vì "✅ hết"."""
    now = time.time()
    with _CHO_NHAN_LOCK:
        if _CHO_NHAN_CACHE[1] is not None and now - _CHO_NHAN_CACHE[0] < ttl:
            return dict(_CHO_NHAN_CACHE[1])
    out = {"video": 0, "kenh": 0, "con_suat": 0, "het_suat": 0, "loi": 0}
    try:
        from app.core import pipeline as P
        db = _db()
        if getattr(db, "corrupt_live", False):
            out["loi"] = 1
            return out
        root = _goc_day_chuyen()
        da: dict = {}
        for x in db.query("SELECT project_id, file_name FROM pipeline_files "
                          "WHERE status IN ('taken','done','dup','bad')"):
            da.setdefault(int(x["project_id"]), set()).add(x["file_name"])
        hom_nay: dict = {}
        for x in db.query("SELECT project_id, COUNT(*) n FROM pipeline_files "
                          "WHERE status IN ('taken','done','error') AND "
                          "date(taken_at,'localtime')=date('now','localtime') "
                          "GROUP BY project_id"):
            hom_nay[int(x["project_id"])] = int(x["n"])
        rows = db.query(
            "SELECT id, name, pipe_src, export_dir, COALESCE(pipe_daily,0) AS daily "
            "FROM projects WHERE COALESCE(pipe_on,0)=1 AND COALESCE(pipe_hidden,0)=0")
    except Exception:  # noqa: BLE001
        out["loi"] = 1
        return out
    for r in rows:
        try:
            ov = (r["pipe_src"] or "").strip() or (r["export_dir"] or "").strip()
            if not ov and not root:
                continue
            d = P.resolve_src_dir(root, r["name"], ov)
            if not d.is_dir():
                continue
            ten = []
            with os.scandir(d) as it:
                for e in it:
                    if not e.is_file() or os.path.splitext(e.name)[1].lower() not in P.VIDEO_EXTS:
                        continue
                    if P.is_tmp_file(e.name) or P._PART_RE.match(e.name) or e.name.startswith("_"):
                        continue
                    st = e.stat()
                    if st.st_size > 0 and now - st.st_mtime >= P.STABLE_AGE_SEC:
                        ten.append(e.name)
            con = [t for t in ten if t not in da.get(int(r["id"]), set())]
            if not con:
                continue
            out["video"] += len(con)
            out["kenh"] += 1
            daily = int(r["daily"] or 0)
            if daily >= 2 and hom_nay.get(int(r["id"]), 0) >= daily:
                out["het_suat"] += len(con)
            else:
                out["con_suat"] += len(con)
        except Exception:  # noqa: BLE001 - 1 kênh lỗi: đếm lỗi, đọc tiếp kênh khác
            out["loi"] += 1
    with _CHO_NHAN_LOCK:
        _CHO_NHAN_CACHE[0], _CHO_NHAN_CACHE[1] = now, dict(out)
    return out


def dong_cho_nhan() -> str:
    c = dem_cho_nhan()
    if c.get("loi") and not c["video"]:
        return f"Thư mục kênh: chưa đọc được {c['loi']} kênh — không chắc còn video chờ hay không."
    if not c["video"]:
        return "Thư mục kênh: không còn video nào chưa nhận."
    s = (f"📂 Thư mục kênh còn <b>{c['video']}</b> video CHƯA phân tích "
         f"({c['kenh']} kênh)")
    if c["con_suat"]:
        s += f" · <b>{c['con_suat']}</b> video còn suất hôm nay -> bấm ▶ Chạy (hoặc /chay)"
    if c["het_suat"]:
        s += f" · {c['het_suat']} video đợi suất ngày mai"
    return s


def bao_cao_tien_do(pool=None) -> str:
    d = tong_quan()
    hn = d["hom_nay"]
    may = socket.gethostname()
    dung = bool(pool and pool.dang_tam_dung())
    dong = [f"📊 <b>Tiến độ — {may}</b>  ({datetime.now():%H:%M})"]
    if dung:
        dong.append("⏸ <b>ĐANG TẠM DỪNG</b> — không nhận việc mới. Gõ /chaytiep để chạy.")
    if d["corrupt"]:
        dong.append("🛑 <b>CƠ SỞ DỮ LIỆU HỎNG</b> — khởi động lại app để tự chữa.")
    xong_v = hn.get(("auto", "done"), 0) + hn.get(("auto_mixed", "done"), 0) \
        + hn.get(("auto_recap", "done"), 0)
    xong_p = hn.get(("m1_export_clip", "done"), 0)
    loi_n = sum(n for (t, s), n in hn.items() if s == "failed")
    dong.append(f"Hôm nay: <b>{xong_v}</b> video phân tích xong · <b>{xong_p}</b> Part "
                f"xuất xong · {loi_n} việc lỗi")
    so = d["so"]
    if so:
        dong.append(f"Dây chuyền hôm nay: {so.get('done', 0)} video xong · "
                    f"{so.get('error', 0)} chờ xem lại · {so.get('taken', 0)} đang làm")
    dong.append(f"Đang chạy <b>{d['running']}</b> · đang chờ <b>{d['pending']}</b>")
    dong.append(dong_cho_nhan())
    if d["cho"]:
        dong.append("  chờ: " + ", ".join(
            f"{n} {_TEN_LOAI.get(t, t)}" for t, n in sorted(d["cho"].items())))
    if pool is not None and d["pending"]:
        eta = uoc_con_lai(d, (max(1, pool._lane_limit(True)),
                               max(1, pool._lane_limit(False)),
                               max(1, pool._lane_limit_tg())))
        if eta is not None:
            dong.append(f"  ước còn ~<b>{_phut(eta)}</b> (theo tốc độ 24h qua)")
    for r in d["chay"][:6]:
        pct = int(round((r["progress"] or 0) * 100))
        dong.append(f"▶ #{r['id']} {pct}% · {_html(_ten_job(r))}\n    "
                    f"<i>{_html((r['message'] or '')[:90])}</i>")
    if len(d["chay"]) > 6:
        dong.append(f"  … và {len(d['chay']) - 6} việc nữa")
    try:
        o, free = _o_dia()
        dong.append(f"Ổ {o} còn {free:.0f} GB" + ("  ⚠ SẮP ĐẦY" if free < O_TRONG_GB else ""))
    except Exception:  # noqa: BLE001
        pass
    return "\n".join(dong)


def bao_cao_loi() -> str:
    db = _db()
    rows = db.query(_SQL_JOB + "WHERE j.status='failed' ORDER BY j.id DESC LIMIT 10")
    xem = db.query("SELECT p.name, f.file_name, f.note FROM pipeline_files f "
                   "LEFT JOIN projects p ON p.id=f.project_id WHERE f.status='error' "
                   "ORDER BY f.id DESC LIMIT 8")
    if not rows and not xem:
        return "✅ Không có việc lỗi nào."
    dong = []
    if rows:
        dong.append("❌ <b>10 việc lỗi gần nhất</b>")
        for r in rows:
            dong.append(f"#{r['id']} {_html(_ten_job(r))}\n    "
                        f"<i>{_html((r['error'] or r['message'] or '')[:160])}</i>")
    if xem:
        dong.append("\n🔎 <b>Video dây chuyền chờ xem lại</b> (gốc được giữ nguyên)")
        for r in xem:
            dong.append(f"• {_html(r['name'] or '')}: {_html((r['file_name'] or '')[:40])}"
                        f"\n    <i>{_html((r['note'] or '')[:140])}</i>")
    return "\n".join(dong)


def bao_cao_may(pool=None) -> str:
    dong = [f"🖥 <b>Máy {socket.gethostname()}</b>"]
    try:
        import psutil
        dong.append(f"CPU {psutil.cpu_percent(interval=0.5):.0f}% · RAM "
                    f"{psutil.virtual_memory().percent:.0f}%")
        ff = sum(1 for p in psutil.process_iter(["name"])
                 if (p.info.get("name") or "").lower().startswith("ffmpeg"))
        dong.append(f"ffmpeg đang chạy: {ff}")
    except Exception:  # noqa: BLE001
        pass
    try:
        o, free = _o_dia()
        dong.append(f"Ổ {o} còn {free:.0f} GB")
    except Exception:  # noqa: BLE001
        pass
    if pool is not None:
        g, c, t = pool.dem_dang_chay()
        dong.append(f"Luồng: phân tích {g}/{pool._lane_limit(True)} · xuất "
                    f"{c}/{pool._lane_limit(False)} · thay giọng {t}/{pool._lane_limit_tg()}")
        dong.append("Trạng thái: " + ("⏸ TẠM DỪNG" if pool.dang_tam_dung() else "▶ đang nhận việc"))
    try:
        from app.version import __version__
        dong.append(f"Phiên bản app {__version__}")
    except Exception:  # noqa: BLE001
        pass
    return "\n".join(dong)


def _html(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ds_nhom() -> list[dict]:
    """[{'grp','bat','tong','xong','loi'}] — nhóm kênh + số kênh BẬT dây
    chuyền + hôm nay xong/lỗi bao nhiêu video. 1 truy vấn."""
    rows = _db().query(
        "SELECT COALESCE(p.grp,'') g, SUM(p.pipe_on=1 AND p.pipe_hidden=0) bat, "
        "COUNT(*) tong, "
        "(SELECT COUNT(*) FROM pipeline_files f JOIN projects q ON q.id=f.project_id "
        " WHERE COALESCE(q.grp,'')=COALESCE(p.grp,'') AND f.status='done' AND "
        " date(f.done_at,'localtime')=date('now','localtime')) xong, "
        "(SELECT COUNT(*) FROM pipeline_files f JOIN projects q ON q.id=f.project_id "
        " WHERE COALESCE(q.grp,'')=COALESCE(p.grp,'') AND f.status='error' AND "
        " date(coalesce(f.done_at,f.taken_at),'localtime')=date('now','localtime')) loi "
        "FROM projects p GROUP BY COALESCE(p.grp,'') ORDER BY bat DESC, g")
    return [{"grp": r["g"], "bat": int(r["bat"] or 0), "tong": int(r["tong"] or 0),
             "xong": int(r["xong"] or 0), "loi": int(r["loi"] or 0)} for r in rows]


def _ten_nhom(g: str) -> str:
    return g if g else "Chưa phân nhóm"


def xem_truoc_nhom(g, root: str = "", dang_bay: set | None = None) -> dict:
    """XEM TRƯỚC 1 nhóm trước khi bấm Chạy: từng kênh có bao nhiêu video CHỜ
    CẮT, đang chạy dở, đang tải; hôm nay xong/lỗi bao nhiêu; kênh tắt/thư mục
    hỏng. Đếm bằng ĐÚNG công thức cột "Chờ cắt" + hộp xác nhận ▶ Chạy của app
    (resolve_src_dir + scan_dir, TRỪ video đang chạy dở) để số trên điện thoại
    khớp số trên app. Chỉ stat thư mục — không băm, không đụng Qt.
    g = None / "__ALL__" -> mọi nhóm."""
    from app.core import pipeline as P
    dang_bay = dang_bay or set()
    tat_ca = g is None or g == "__ALL__"
    rows = _db().query(
        "SELECT id, name, COALESCE(grp,'') grp, pipe_on, pipe_hidden, "
        "COALESCE(pipe_src,'') pipe_src, COALESCE(export_dir,'') export_dir "
        "FROM projects " + ("" if tat_ca else "WHERE COALESCE(grp,'')=? ")
        + "ORDER BY name", () if tat_ca else (g,))
    hn: dict = {}
    for r in _db().query(
            "SELECT project_id pid, SUM(status='done') d, SUM(status='error') e "
            "FROM pipeline_files WHERE date(coalesce(done_at,taken_at),'localtime')"
            "=date('now','localtime') GROUP BY project_id"):
        hn[int(r["pid"])] = (int(r["d"] or 0), int(r["e"] or 0))
    kenh, tat, an = [], [], 0
    for r in rows:
        if r["pipe_hidden"]:
            an += 1
            continue
        if not r["pipe_on"]:
            tat.append(r["name"])
            continue
        d, e = hn.get(int(r["id"]), (0, 0))
        k = {"ten": r["name"], "cho": 0, "dang": 0, "tai": 0, "xong": d, "loi": e,
             "hong": ""}
        src = r["pipe_src"].strip() or r["export_dir"].strip()
        if not src and not (root or "").strip():
            k["hong"] = "chưa đặt thư mục"
        else:
            thu_muc = P.resolve_src_dir(root, r["name"], src)
            try:
                if not thu_muc.is_dir():
                    k["hong"] = "không thấy thư mục"
                else:
                    san, do_dang = P.scan_dir(thu_muc)
                    k["tai"] = len(do_dang)
                    for f in san:
                        try:
                            kh = os.path.normcase(os.path.abspath(str(f)))
                        except OSError:
                            kh = str(f)
                        if kh in dang_bay:
                            k["dang"] += 1
                        else:
                            k["cho"] += 1
            except OSError:
                k["hong"] = "không đọc được thư mục"
        kenh.append(k)
    return {"kenh": kenh, "tat": tat, "an": an,
            "cho": sum(k["cho"] for k in kenh), "dang": sum(k["dang"] for k in kenh),
            "tai": sum(k["tai"] for k in kenh),
            "kenh_co": sum(1 for k in kenh if k["cho"]),
            "xong": sum(k["xong"] for k in kenh), "loi": sum(k["loi"] for k in kenh)}


def bao_cao_xem_truoc(ten: str, x: dict, toi_da: int = 3600) -> str:
    """Tin xem trước: tổng + kênh có việc + kênh không có video + kênh lỗi/tắt."""
    kenh = x["kenh"]
    dong = [f"📋 <b>{_html(ten)}</b> — {len(kenh)} kênh bật"
            + (f", {len(x['tat'])} kênh tắt" if x["tat"] else "")]
    if x["cho"]:
        dong.append(f"➜ Sẽ cắt <b>{x['cho']} video</b> ở <b>{x['kenh_co']} kênh</b>")
    else:
        dong.append("➜ <b>KHÔNG có video mới nào chờ cắt</b> — chạy cũng chỉ quét rồi xong.")
    phu = []
    if x["dang"]:
        phu.append(f"{x['dang']} video đang chạy dở (không cắt lại)")
    if x["tai"]:
        phu.append(f"{x['tai']} file đang tải dở (chưa tính)")
    phu.append(f"hôm nay đã xong {x['xong']}" + (f", lỗi {x['loi']}" if x["loi"] else ""))
    dong.append("   " + " · ".join(phu))
    co = sorted([k for k in kenh if k["cho"] or k["dang"]],
                key=lambda k: (-k["cho"], -k["dang"], k["ten"]))
    if co:
        dong.append("\n🟢 <b>Kênh có video</b>")
        for k in co:
            t = f"• {_html(k['ten'])}: <b>{k['cho']}</b> chờ"
            if k["dang"]:
                t += f" · {k['dang']} đang chạy"
            if k["tai"]:
                t += f" · {k['tai']} đang tải"
            if k["xong"] or k["loi"]:
                t += f" · hôm nay xong {k['xong']}" + (f", lỗi {k['loi']}" if k["loi"] else "")
            dong.append(t)
    hong = [k for k in kenh if k["hong"]]
    if hong:
        dong.append("\n⚠ <b>Kênh không đọc được thư mục</b> (sẽ bị bỏ qua)")
        for k in hong:
            dong.append(f"• {_html(k['ten'])}: {k['hong']}")
    rong = [k for k in kenh if not k["cho"] and not k["dang"] and not k["hong"]]
    if rong:
        xong_rong = [k for k in rong if k["xong"]]
        chua = [k for k in rong if not k["xong"]]
        if xong_rong:
            dong.append(f"\n✅ <b>Đã làm hết hôm nay</b> ({len(xong_rong)}): "
                        + ", ".join(f"{_html(k['ten'])} ({k['xong']})" for k in xong_rong))
        if chua:
            dong.append(f"\n⚪ <b>Chưa có video mới</b> ({len(chua)}): "
                        + ", ".join(_html(k["ten"]) for k in chua))
    if x["tat"]:
        dong.append(f"\n⏹ <b>Kênh TẮT</b> (không chạy, {len(x['tat'])}): "
                    + ", ".join(_html(t) for t in x["tat"]))
    out = "\n".join(dong)
    if len(out) > toi_da:
        out = out[:toi_da].rsplit("\n", 1)[0] + "\n… (còn nữa — xem đủ ở hộp 🤖 Dây chuyền trên app)"
    return out


def bao_cao_kenh() -> str:
    nh = ds_nhom()
    if not nh:
        return "Chưa có kênh nào."
    dong = ["📁 <b>Nhóm kênh — hôm nay</b>"]
    for n in nh:
        dong.append(f"• <b>{_html(_ten_nhom(n['grp']))}</b>: {n['bat']}/{n['tong']} kênh bật · "
                    f"xong {n['xong']} video · chờ xem lại {n['loi']}")
    top = _db().query(
        "SELECT p.name, SUM(f.status='done') xong, SUM(f.status='error') loi "
        "FROM pipeline_files f JOIN projects p ON p.id=f.project_id WHERE "
        "date(coalesce(f.done_at,f.taken_at),'localtime')=date('now','localtime') "
        "GROUP BY p.id ORDER BY xong DESC LIMIT 10")
    if top:
        dong.append("\n🏆 <b>Kênh làm nhiều nhất hôm nay</b>")
        for r in top:
            dong.append(f"• {_html(r['name'] or '')}: {r['xong'] or 0} xong"
                        + (f" · {r['loi']} chờ xem lại" if r["loi"] else ""))
    return "\n".join(dong)


TRO_GIUP = ("🤖 <b>Bot quản lý dây chuyền</b> — bấm nút hoặc gõ lệnh\n"
            "/chay — chọn nhóm rồi CHẠY dây chuyền (giống nút ▶ Chạy)\n"
            "/theodoi — 1 tin tiến độ TỰ CẬP NHẬT (không spam tin mới)\n"
            "/tiendo — đang chạy gì, xong bao nhiêu, còn bao lâu\n"
            "/kenh — các nhóm kênh + kênh làm nhiều nhất hôm nay\n"
            "/loi — việc lỗi + video chờ xem lại\n"
            "/may — CPU, RAM, ổ đĩa, số luồng\n"
            "/tamdung — ngừng nhận việc MỚI (việc đang chạy vẫn chạy hết)\n"
            "/chaytiep — chạy lại sau khi tạm dừng\n"
            "/huy &lt;số&gt; — huỷ 1 việc (vd /huy 1234), video gốc giữ nguyên\n"
            "/moapp — app TẮT hoặc chưa đăng nhập: mở app + tự đăng nhập\n"
            "/dongapp — ĐÓNG app an toàn (hỏi xác nhận trước)\n"
            "Bot tự nhắn khi: có việc lỗi · việc kẹt quá "
            f"{KET_PHUT} phút · chạy hết hàng chờ · ổ đĩa dưới {O_TRONG_GB} GB · "
            "cơ sở dữ liệu hỏng.")

_PHIM = {"inline_keyboard": [
    [{"text": "▶ Chạy dây chuyền", "callback_data": "/chay"},
     {"text": "📡 Theo dõi", "callback_data": "/theodoi"}],
    [{"text": "Tiến độ", "callback_data": "/tiendo"},
     {"text": "Nhóm kênh", "callback_data": "/kenh"},
     {"text": "Lỗi", "callback_data": "/loi"}],
    [{"text": "Máy", "callback_data": "/may"},
     {"text": "⏸ Tạm dừng", "callback_data": "/tamdung"},
     {"text": "▶ Chạy tiếp", "callback_data": "/chaytiep"}]]}

# MENU LỆNH ("/" cạnh ô chat) — đăng ký bằng setMyCommands để anh Hùng khỏi
# phải nhớ/gõ lệnh. Dùng CHUNG cho bot chính + bot gác cổng.
LENH_MENU = [
    ("chay", "Chạy dây chuyền (chọn nhóm)"),
    ("theodoi", "Tiến độ tự cập nhật"),
    ("tiendo", "Đang chạy gì, còn bao lâu"),
    ("loi", "Việc lỗi + video chờ xem lại"),
    ("kenh", "Từng nhóm/kênh: video chờ, đang chạy, xong, lỗi"),
    ("may", "CPU, RAM, ổ đĩa"),
    ("tamdung", "Tạm dừng nhận việc mới"),
    ("chaytiep", "Chạy tiếp sau tạm dừng"),
    ("moapp", "Mở app + tự đăng nhập (khi app tắt)"),
    ("dongapp", "Đóng app an toàn (hỏi trước)"),
    ("trangthai", "App đang tắt / chờ đăng nhập / chạy"),
    ("start", "Hiện bảng nút + trợ giúp"),
]

# BÀN PHÍM NÚT cố định dưới ô chat: bấm = gửi đúng chữ trên nút -> đổi ra lệnh
NUT_DUOI = {
    "▶ Chạy": "/chay", "📡 Theo dõi": "/theodoi", "📊 Tiến độ": "/tiendo",
    "❗ Lỗi": "/loi", "🗂 Kênh": "/kenh", "🖥 Máy": "/may",
    "⏸ Tạm dừng": "/tamdung", "▶ Chạy tiếp": "/chaytiep",
    "🔓 Mở app": "/moapp", "⛔ Đóng app": "/dongapp", "ℹ Trạng thái": "/trangthai",
}
BAN_PHIM = {"keyboard": [
    [{"text": "▶ Chạy"}, {"text": "📡 Theo dõi"}, {"text": "📊 Tiến độ"}],
    [{"text": "❗ Lỗi"}, {"text": "🗂 Kênh"}, {"text": "🖥 Máy"}],
    [{"text": "⏸ Tạm dừng"}, {"text": "▶ Chạy tiếp"}],
    [{"text": "🔓 Mở app"}, {"text": "⛔ Đóng app"}, {"text": "ℹ Trạng thái"}]],
    "resize_keyboard": True, "is_persistent": True}


def doi_nut(text: str) -> str:
    """Chữ của nút bàn phím -> lệnh (không phải nút thì giữ nguyên)."""
    t = (text or "").strip()
    return NUT_DUOI.get(t, text)


def dang_ky_menu(goi) -> None:
    """Đăng ký menu lệnh "/" với Telegram. Lỗi thì thôi (chỉ là tiện ích)."""
    try:
        goi("setMyCommands", {"commands": [{"command": c, "description": d}
                                           for c, d in LENH_MENU]})
        goi("setChatMenuButton", {"menu_button": {"type": "commands"}})
    except Exception as e:  # noqa: BLE001
        _ghi_log(f"đăng ký menu lệnh lỗi: {str(e)[:120]}")


# lệnh trả lời NGAY ở luồng nghe (chỉ đọc RAM / ghi 1 cờ); còn lại -> ThreadPool
# (/chay KHÔNG nằm đây nữa: chọn nhóm giờ quét thư mục từng kênh để xem trước)
LENH_NHE = {"/moapp", "/dongapp","/dangnhap", "/mo", "/trangthai", "/tt", "/start", "/help", "/trogiup", "/tamdung", "/chaytiep", "/huy",
            "/huybo"}
# 429 ở các hàm này -> bỏ qua, KHÔNG chờ (tin sau sẽ sửa lại); send* -> chờ rồi gửi lại
_BO_QUA_429 = {"editMessageText", "editMessageReplyMarkup", "answerCallbackQuery",
               "deleteMessage"}
GIAN_GUI = 0.35             # giây tối thiểu giữa 2 lần send*
CHAM_LOG = 3.0              # lệnh xử lý lâu hơn số giây này -> ghi log
SONG_NHIP = 15              # giây giữa 2 lần sửa tin "theo dõi"
SONG_TOI_DA = 4 * 3600      # tin theo dõi tự dừng sau 4 giờ

# ---- IPv4 CHỈ CHO LUỒNG CỦA BOT ----
# Ép IPv4 bằng cách vá `allowed_gai_family` TOÀN CỤC sẽ đổi luôn cách gọi Groq,
# edge-tts, ElevenLabs của cả app. Nên vá có điều kiện: chỉ luồng nào đã đặt cờ
# `_LUONG.ipv4` (luồng của bot) mới bị ép, mọi luồng khác giữ hành vi cũ.
_LUONG = threading.local()
_VA_IPV4 = False


def _bat_ipv4() -> None:
    global _VA_IPV4
    if _VA_IPV4:
        return
    try:
        import urllib3.util.connection as uc
        goc = uc.allowed_gai_family

        def chon():
            return socket.AF_INET if getattr(_LUONG, "ipv4", False) else goc()
        uc.allowed_gai_family = chon
        _VA_IPV4 = True
    except Exception as e:  # noqa: BLE001
        _ghi_log(f"không ép được IPv4: {e!r}")


# ---- HÀNG ĐỢI LUỒNG GIAO DIỆN ----
# Bot KHÔNG được đụng Qt. Lệnh cần giao diện (chạy dây chuyền) được ĐẨY vào hàng
# này; main_window rút ra bằng QTimer ở luồng giao diện (`chay_hang_ui`).
_UI_Q: "queue.Queue" = queue.Queue()
_UI_FN: dict = {}


def dang_ky_ui(ten: str, fn) -> None:
    """Giao diện đăng ký 1 hàm bot được phép gọi (chạy ở LUỒNG GIAO DIỆN)."""
    _UI_FN[ten] = fn


def goi_ui(ten: str, *args, cho: float = 15.0):
    """Gọi hàm giao diện từ luồng bot; chờ kết quả tối đa `cho` giây.
    Không có giao diện / quá giờ -> {'ok': False, 'ly_do': ...} (không ném)."""
    if ten not in _UI_FN:
        return {"ok": False, "ly_do": "App chưa nối lệnh này với giao diện — app đang ở màn đăng nhập hoặc đang chạy BẢN CŨ. Tắt app, mở lại rồi đăng nhập."}
    xong = threading.Event()
    hop: dict = {}
    _UI_Q.put((ten, args, xong, hop))
    if not xong.wait(cho):
        return {"ok": False, "ly_do": "App đang bận, chưa nhận lệnh — thử lại sau ít phút."}
    return hop.get("kq", {"ok": False, "ly_do": hop.get("loi", "lỗi không rõ")})


def chay_hang_ui(toi_da: int = 5) -> int:
    """GỌI Ở LUỒNG GIAO DIỆN (QTimer). Rút tối đa `toi_da` lệnh. Không ném."""
    n = 0
    while n < toi_da:
        try:
            ten, args, xong, hop = _UI_Q.get_nowait()
        except queue.Empty:
            break
        n += 1
        try:
            hop["kq"] = _UI_FN[ten](*args)
        except Exception as e:  # noqa: BLE001
            hop["loi"] = f"{type(e).__name__}: {e}"[:200]
            _ghi_log(f"lệnh giao diện {ten} lỗi: {e!r}")
        finally:
            xong.set()
    return n


# ---- BỘ ĐỆM số liệu (đọc DB/đĩa) ----
_DEM: dict = {}
_DEM_KHOA = threading.Lock()


def dem(ten: str, ttl: float, fn):
    now = time.monotonic()
    with _DEM_KHOA:
        v = _DEM.get(ten)
        if v and now - v[0] < ttl:
            return v[1]
    kq = fn()
    with _DEM_KHOA:
        _DEM[ten] = (now, kq)
    return kq


def xoa_dem() -> None:
    with _DEM_KHOA:
        _DEM.clear()


# ------------------------------------------------------------------- bot --
class BotQuanLy:
    def __init__(self, token: str, cho_phep: set[int], pool=None, gui=None):
        self.token = token
        self.cho_phep = set(cho_phep)
        self.pool = pool
        self._dung = threading.Event()
        self._danh_thuc = threading.Event()   # đánh thức vòng soi NGAY khi có việc
        self._offset = 0
        self._gui_ngoai = gui                 # test thay hàm gửi
        self._tl = threading.local()          # mỗi luồng 1 requests.Session
        self._gui_khoa = threading.Lock()
        self._gui_luc = 0.0
        self._viec = ThreadPoolExecutor(max_workers=3, thread_name_prefix="tele-viec")
        self._khoa_doi_tuong: dict = {}
        self._khoa_doi_tuong_k = threading.Lock()
        self._nhom_map: dict[int, str] = {}
        self._truoc_khi_chay: dict[int, dict] = {}   # chat -> lượt xem trước /chay   # số trên nút -> tên nhóm (callback <=64 byte)
        self._song: dict[int, dict] = {}      # chat -> tin "theo dõi" đang sửa
        # trạng thái theo dõi
        self._da_bao_loi: set[int] = set()
        self._tien_do: dict[int, tuple[float, str, float]] = {}
        self._da_bao_ket: set[int] = set()
        self._co_viec = False
        self._bao_o = 0.0
        self._bao_db = False
        self._loi_cho: list[str] = []
        self._loi_tu = 0.0
        self._lan_dau = True

    # -- mạng --
    def _phien(self):
        s = getattr(self._tl, "s", None)
        if s is None:
            import requests
            s = self._tl.s = requests.Session()
        return s

    def _goi(self, method: str, data: dict, timeout: float = 20):
        import requests
        lan = 0
        while True:
            if method.startswith("send"):
                with self._gui_khoa:            # giãn 0,35s giữa các lần send*
                    cho = GIAN_GUI - (time.monotonic() - self._gui_luc)
                    if cho > 0:
                        time.sleep(cho)
                    self._gui_luc = time.monotonic()
            # ép IPv4 ĐÚNG trong lúc gọi Telegram rồi trả lại cờ cũ: luồng nào gọi
            # (kể cả luồng lạ) cũng không bị ép IPv4 cho Groq/edge-tts về sau.
            cu = getattr(_LUONG, "ipv4", False)
            _LUONG.ipv4 = True
            try:
                r = self._phien().post(API.format(tok=self.token, m=method), json=data,
                                       timeout=(5, timeout))
            except requests.RequestException as e:
                # lời lỗi của requests IN KÈM URL = token -> không cho lọt vào log
                raise RuntimeError(f"{method}: {type(e).__name__}") from None
            finally:
                _LUONG.ipv4 = cu
            try:
                j = r.json()
            except ValueError:
                j = {"ok": False, "description": r.text[:200]}
            if j.get("ok"):
                return j.get("result")
            if r.status_code == 429:
                if method in _BO_QUA_429:
                    return None                    # sửa/trả lời: bỏ qua, không chờ
                lan += 1
                sau = float((j.get("parameters") or {}).get("retry_after") or 1)
                if lan <= 3 and method.startswith("send"):
                    _ghi_log(f"{method} 429, chờ {sau:.0f}s rồi gửi lại")
                    time.sleep(min(sau, 30))
                    continue
            raise RuntimeError(f"{method} {r.status_code}: {j.get('description')}")

    def gui(self, chat_id: int, text: str, phim=False) -> Optional[int]:
        """Gửi tin -> message_id (None nếu lỗi). Không bao giờ ném."""
        if len(text) > 3900:
            text = text[:3900] + "\n…"
        if self._gui_ngoai:
            self._gui_ngoai(chat_id, text)
            return None
        data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                "disable_web_page_preview": True}
        if phim:
            data["reply_markup"] = _PHIM if phim is True else phim
        try:
            r = self._goi("sendMessage", data)
            return (r or {}).get("message_id")
        except Exception as e:  # noqa: BLE001
            _ghi_log(f"gửi lỗi: {str(e)[:200]}")
            return None

    def sua(self, chat_id: int, mid: int, text: str, phim=None) -> bool:
        """Sửa 1 tin đã gửi (tiến độ) thay vì gửi tin mới."""
        if len(text) > 3900:
            text = text[:3900] + "\n…"
        if self._gui_ngoai:
            self._gui_ngoai(chat_id, f"[sửa {mid}] " + text)
            return True
        data = {"chat_id": chat_id, "message_id": mid, "text": text,
                "parse_mode": "HTML", "disable_web_page_preview": True}
        if phim:
            data["reply_markup"] = phim
        try:
            self._goi("editMessageText", data)
            return True
        except Exception as e:  # noqa: BLE001
            if "not modified" in str(e):
                return True
            _ghi_log(f"sửa tin lỗi: {str(e)[:200]}")
            return False

    def bao_tat_ca(self, text: str) -> None:
        for cid in self.cho_phep:
            self.gui(cid, text)

    # -- điều phối lệnh --
    def _khoa_cho(self, khoa: str) -> threading.Lock:
        with self._khoa_doi_tuong_k:
            return self._khoa_doi_tuong.setdefault(khoa, threading.Lock())

    def nhan_lenh(self, chat_id: int, text: str, ma_nut: Optional[str] = None) -> None:
        """Cửa vào của MỌI lệnh từ luồng nghe. Nút bấm -> answerCallbackQuery
        ngay ở luồng nền; lệnh nhẹ làm ngay; lệnh nặng đẩy sang ThreadPool,
        cùng 1 lệnh của 1 chat thì làm lần lượt."""
        if ma_nut:
            def tra_loi():
                try:
                    self._goi("answerCallbackQuery",
                              {"callback_query_id": ma_nut, "text": "⏳ Đang làm..."})
                except Exception:  # noqa: BLE001
                    pass
            if self._gui_ngoai is None:
                self._viec.submit(tra_loi)
        text = doi_nut(text)
        lenh = (text or "").strip().split()[0].split("@")[0].lower() if (text or "").strip() else ""
        if lenh in LENH_NHE or chat_id not in self.cho_phep:
            self.xu_ly(chat_id, text)
            return
        khoa = self._khoa_cho(f"{chat_id}:{lenh}")

        def lam():
            with khoa:
                self.xu_ly(chat_id, text)
        self._viec.submit(lam)

    def xu_ly(self, chat_id: int, text: str) -> None:
        """Xử lý 1 lệnh. Không bao giờ ném lỗi ra ngoài."""
        t0 = time.monotonic()
        text = doi_nut((text or "").strip())
        lenh = text.split()[0].split("@")[0].lower() if text else ""
        if chat_id not in self.cho_phep:
            self.gui(chat_id, "🔒 Chat này CHƯA được phép điều khiển.\n"
                              f"Id của bạn: <code>{chat_id}</code>\n"
                              "Thêm dòng sau vào file .env của app rồi mở lại app:\n"
                              f"<code>TELEGRAM_CHAT_IDS={chat_id}</code>")
            _ghi_log(f"từ chối chat {chat_id}: {text[:40]}")
            return
        _ghi_log(f"chat {chat_id}: {text[:60]}")
        try:
            if lenh in ("/moapp", "/dangnhap", "/mo", "/trangthai", "/tt"):
                self.gui(chat_id, "🟢 App ĐANG CHẠY và đã đăng nhập.", phim=True)
            elif lenh in ("/start", "/help", "/trogiup", "/menu"):
                # bàn phím nút cố định dưới ô chat + bảng nút trong tin
                self.gui(chat_id, "⌨ Bảng nút đã hiện dưới ô chat — bấm là chạy, "
                                  "khỏi gõ. Hoặc bấm nút <b>/</b> (Menu) cạnh ô chat.",
                         phim=BAN_PHIM)
                self.gui(chat_id, TRO_GIUP, phim=True)
            elif lenh in ("/tiendo", "/tien_do"):
                self.gui(chat_id, dem("tiendo", 15, lambda: bao_cao_tien_do(self.pool)),
                         phim=True)
            elif lenh == "/theodoi":
                self._bat_theo_doi(chat_id)
            elif lenh == "/kenh":
                self.gui(chat_id, dem("kenh", 30, bao_cao_kenh))
                self._ds_nhom_nut(chat_id, "📋 Bấm 1 nhóm để xem TỪNG KÊNH: video chờ "
                                           "cắt · đang chạy · xong · lỗi", "/xemnhom")
            elif lenh == "/xemnhom":
                self._xem_nhom(chat_id, text)
            elif lenh == "/loi":
                self.gui(chat_id, dem("loi", 15, bao_cao_loi))
            elif lenh == "/may":
                self.gui(chat_id, dem("may", 15, lambda: bao_cao_may(self.pool)))
            elif lenh == "/tamdung":
                if self.pool is None:
                    self.gui(chat_id, "Hàng đợi chưa khởi động.")
                    return
                self.pool.tam_dung(f"bot Telegram {datetime.now():%d/%m %H:%M}")
                xoa_dem()
                g, c, t = self.pool.dem_dang_chay()
                self.gui(chat_id, f"⏸ Đã TẠM DỪNG nhận việc mới. Còn {g + c + t} việc "
                                  "đang chạy sẽ chạy cho xong. Tắt app vẫn giữ trạng thái "
                                  "dừng. Gõ /chaytiep để chạy lại.")
                self._danh_thuc.set()
            elif lenh == "/chaytiep":
                if self.pool is None:
                    self.gui(chat_id, "Hàng đợi chưa khởi động.")
                    return
                self.pool.chay_tiep()
                xoa_dem()
                self.gui(chat_id, "▶ Đã CHẠY TIẾP — app nhận việc trở lại.")
                self._danh_thuc.set()
            elif lenh == "/huy":
                self._huy(chat_id, text)
            elif lenh == "/chay":
                self._chay(chat_id, text)
            elif lenh == "/chayok":
                self._chay_ok(chat_id, text)
            elif lenh == "/batnhom":
                self._bat_nhom(chat_id, text)
            elif lenh == "/dongapp":
                self._dong_app(chat_id)
            elif lenh == "/dongappok":
                self._dong_app_ok(chat_id, text)
            elif lenh == "/huybo":
                self.gui(chat_id, "Đã bỏ, không chạy gì.")
            else:
                self.gui(chat_id, TRO_GIUP, phim=True)
        except Exception as e:  # noqa: BLE001
            _ghi_log(f"lệnh {lenh} lỗi: {e!r}")
            self.gui(chat_id, f"⚠ Lệnh lỗi, dây chuyền KHÔNG bị ảnh hưởng: {_html(str(e)[:200])}")
        finally:
            dt = time.monotonic() - t0
            if dt > CHAM_LOG:
                _ghi_log(f"CHẬM: lệnh {lenh} mất {dt:.1f}s")

    def _huy(self, chat_id: int, text: str) -> None:
        p = text.split()
        if len(p) < 2 or not p[1].lstrip("#").isdigit():
            self.gui(chat_id, "Gõ /huy kèm số việc, vd <code>/huy 1234</code> "
                              "(số ở dòng ▶ #... trong /tiendo).")
            return
        jid = int(p[1].lstrip("#"))
        r = _db().query_one(_SQL_JOB + "WHERE j.id=?", (jid,))
        if not r:
            self.gui(chat_id, f"Không có việc #{jid}.")
            return
        if r["status"] not in ("pending", "running"):
            self.gui(chat_id, f"Việc #{jid} đã ở trạng thái '{r['status']}', không cần huỷ.")
            return
        if self.pool is None:
            self.gui(chat_id, "Hàng đợi chưa khởi động.")
            return
        self.pool.cancel(jid)
        xoa_dem()
        self.gui(chat_id, f"⏹ Đã huỷ #{jid} ({_html(_ten_job(r))}). Video gốc giữ nguyên.")

    # -- chạy dây chuyền (2 bước: chọn nhóm -> xác nhận) --
    def _chay(self, chat_id: int, text: str) -> None:
        p = text.split()
        if len(p) >= 2 and p[1].lstrip("#").isdigit():
            k = int(p[1].lstrip("#"))
            g = self._nhom_map.get(k)
            if g is None:
                self.gui(chat_id, "Danh sách nhóm đã cũ — bấm /chay để chọn lại.")
                return
            if self._nhom_chua_bat(chat_id, k, g):
                return
            ten = "Tất cả nhóm" if g == "__ALL__" else f"Nhóm «{_ten_nhom(g)}»"
            # XEM TRƯỚC từng kênh rồi mới hỏi: bấm xác nhận phải biết sẽ chạy
            # bao nhiêu video ở kênh nào (giống hộp xác nhận ▶ Chạy trên app)
            x = self._xem_truoc(g)
            self._truoc_khi_chay[chat_id] = x
            hoi = ("\n\n<b>Chạy?</b> Lúc bấm app quét lại thư mục (y như nút ▶ Chạy); "
                   "file đã làm sẽ được bỏ qua.")
            nut = "✅ Chạy " + (f"{x['cho']} video" if x["cho"] else "(chỉ quét)")
            self.gui(chat_id, bao_cao_xem_truoc(ten, x) + hoi,
                     phim={"inline_keyboard": [[
                         {"text": nut, "callback_data": f"/chayok {k}"},
                         {"text": "🔄 Đếm lại", "callback_data": f"/chay {k}"},
                         {"text": "Huỷ", "callback_data": "/huybo"}]]})
            return
        dung = self.pool is not None and self.pool.dang_tam_dung()
        self._ds_nhom_nut(chat_id, "▶ <b>Chọn nhóm để chạy dây chuyền</b>\n"
                          "Bấm nhóm -> xem từng kênh có bao nhiêu video -> mới xác nhận."
                          + ("\n⚠ App đang TẠM DỪNG — bấm /chaytiep trước." if dung else ""),
                          "/chay")

    def _chay_ok(self, chat_id: int, text: str) -> None:
        p = text.split()
        k = int(p[1]) if len(p) >= 2 and p[1].isdigit() else -1
        g = self._nhom_map.get(k)
        if g is None:
            self.gui(chat_id, "Danh sách nhóm đã cũ — bấm /chay để chọn lại.")
            return
        kq = goi_ui("chay_day_chuyen", g)
        if not kq.get("ok"):
            self.gui(chat_id, f"⚠ Chưa chạy: {_html(kq.get('ly_do', ''))}")
            return
        xoa_dem()
        ten = "TẤT CẢ nhóm" if g == "__ALL__" else f"nhóm «{_ten_nhom(g)}»"
        x = self._truoc_khi_chay.pop(chat_id, None)
        so = (f" — sẽ cắt <b>{x['cho']} video</b> ở {x['kenh_co']} kênh"
              if x and x["cho"] else (" — không có video mới, chỉ quét" if x else ""))
        self.gui(chat_id, f"✅ Đã bấm Chạy dây chuyền {_html(ten)} ({kq.get('kenh', 0)} "
                          f"kênh bật){so}. App đang nhận video ở nền; tin dưới tự cập nhật. "
                          "Bấm 📋 Kênh để xem từng kênh làm tới đâu.")
        self._bat_theo_doi(chat_id)

    def _xem_truoc(self, g) -> dict:
        """Xem trước nhóm: lấy thư mục gốc + video đang chạy dở từ GIAO DIỆN
        (đúng nguồn ▶ Chạy dùng), đếm ở luồng bot. Giao diện không trả lời ->
        đọc thư mục gốc từ cài đặt, coi như không có gì đang chạy dở."""
        nen = goi_ui("nen_xem_truoc", cho=8.0)
        if isinstance(nen, dict) and nen.get("ok"):
            root, bay = nen.get("root", ""), set(nen.get("dang_bay") or ())
        else:
            try:
                from app.ui.appsettings import app_settings
                root = str(app_settings().value("pipe_root", "") or "")
            except Exception:  # noqa: BLE001
                root = ""
            bay = set()
        return xem_truoc_nhom(g, root, bay)

    def _dong_app(self, chat_id: int) -> None:
        """Hỏi xác nhận trước khi đóng app: nói rõ việc đang chạy + mở lại được
        từ xa hay không. Nút mang MỐC GIỜ (xem `_dong_app_ok`)."""
        n = 0
        if self.pool is not None:
            try:
                n = sum(self.pool.dem_dang_chay())
            except Exception:  # noqa: BLE001
                n = 0
        try:
            from app.core import tele_gac
            gac = tele_gac.dang_chay()
        except Exception:  # noqa: BLE001
            gac = False
        dong = ["⛔ <b>Đóng app trên máy?</b>"]
        if n:
            dong.append(f"• Đang chạy <b>{n} việc</b> — sẽ DỪNG giữa chừng. Mở lại app "
                        "thì các việc đó TỰ CHẠY LẠI (dùng lại bước đã lưu, video gốc "
                        "không mất).")
        else:
            dong.append("• Không có việc nào đang chạy.")
        if gac:
            dong.append("• Mở lại từ điện thoại: bấm 🔓 Mở app.")
        else:
            dong.append("⚠ Bot gác cổng KHÔNG chạy trên máy -> đóng rồi sẽ KHÔNG mở "
                        "lại từ điện thoại được (phải bật app tại máy).")
        dong.append(f"Nút xác nhận chỉ có hiệu lực {DONG_HAN_GIAY // 60} phút.")
        self.gui(chat_id, "\n".join(dong), phim={"inline_keyboard": [[
            {"text": "✅ Đóng app", "callback_data": f"/dongappok {int(time.time())}"},
            {"text": "Huỷ", "callback_data": "/huybo"}]]})

    def _dong_app_ok(self, chat_id: int, text: str) -> None:
        """Đóng app thật. Chặn 2 kiểu ĐÓNG NHẦM: (1) nút quá hạn; (2) CÙNG một
        nút bị xử lý lần 2 — app tắt trước khi kịp xác nhận offset với Telegram,
        mở lại thì nhận lại đúng lệnh này -> tự đóng tiếp, mở mãi không được."""
        phan = text.split()
        try:
            ts = int(phan[1])
        except (IndexError, ValueError):
            ts = 0
        now = time.time()
        if not ts or now - ts > DONG_HAN_GIAY or ts - now > 60:
            self.gui(chat_id, "Nút xác nhận đã CŨ — KHÔNG đóng. Bấm ⛔ Đóng app lại "
                              "nếu vẫn muốn đóng.")
            return
        try:
            from app.core import tele_gac
            so = tele_gac.file_song().with_name("dong_app_da_dung.txt")
        except Exception:  # noqa: BLE001
            so = None
        if so is not None:
            try:
                if so.read_text(encoding="utf-8").strip() == str(ts):
                    _ghi_log(f"bỏ qua lệnh đóng app lặp lại ({ts})")
                    return
            except OSError:
                pass
            try:
                so.write_text(str(ts), encoding="utf-8")
            except OSError:
                pass
        kq = goi_ui("dong_app", cho=10.0)
        if not kq.get("ok"):
            self.gui(chat_id, f"⚠ Không đóng được app: {_html(str(kq.get('ly_do', '')))}")
            return
        _ghi_log(f"chat {chat_id}: đóng app từ Telegram")
        self.gui(chat_id, "⛔ Đang ĐÓNG app (khoảng 3 giây). Việc đang chạy sẽ tự chạy "
                          "lại khi mở app. Bấm 🔓 Mở app để mở lại.", phim=BAN_PHIM)

    def _xem_nhom(self, chat_id: int, text: str) -> None:
        """/xemnhom [số]: từng kênh trong nhóm có bao nhiêu video chờ/đang chạy/
        xong/lỗi — CHỈ XEM, không chạy."""
        p = text.split()
        if len(p) >= 2 and p[1].isdigit():
            g = self._nhom_map.get(int(p[1]))
            if g is None:
                self.gui(chat_id, "Danh sách nhóm đã cũ — bấm 📋 Kênh để chọn lại.")
                return
            ten = "Tất cả nhóm" if g == "__ALL__" else f"Nhóm «{_ten_nhom(g)}»"
            self.gui(chat_id, bao_cao_xem_truoc(ten, self._xem_truoc(g)),
                     phim={"inline_keyboard": [[
                         {"text": "▶ Chạy nhóm này", "callback_data": f"/chay {p[1]}"},
                         {"text": "🔄 Xem lại", "callback_data": f"/xemnhom {p[1]}"}]]})
            return
        self._ds_nhom_nut(chat_id, "📋 <b>Chọn nhóm để xem từng kênh</b>", "/xemnhom")

    def _ds_nhom_nut(self, chat_id: int, tieu_de: str, lenh: str) -> bool:
        """Nút chọn nhóm — hiện MỌI nhóm, kể cả nhóm chưa bật kênh nào và nhóm
        mới tạo còn rỗng. LỖI THẬT 02/11/2026: anh Hùng thêm nhóm "Mỹ BKT"
        (16 kênh, chưa tích "Bật") -> bản cũ chỉ liệt kê nhóm có kênh BẬT nên
        nhóm này BIẾN MẤT khỏi bot, không một lời giải thích, tắt/mở app vẫn
        không thấy. Nay nhóm nào cũng hiện, ghi rõ trạng thái."""
        nh = ds_nhom()
        co = {n["grp"] for n in nh}
        rong = goi_ui("nhom_rong", cho=3.0)
        for g in (rong if isinstance(rong, list) else []):
            if g not in co:
                nh.append({"grp": g, "bat": 0, "tong": 0, "xong": 0, "loi": 0})
        self._nhom_map = {}
        hang, tong = [], 0
        for i, n in enumerate(nh):
            self._nhom_map[i + 1] = n["grp"]
            tong += n["bat"]
            if n["bat"]:
                nhan = (f"{_ten_nhom(n['grp'])} ({n['bat']} kênh · xong "
                        f"{n['xong']} hôm nay)")
            elif n["tong"]:
                nhan = f"{_ten_nhom(n['grp'])} ({n['tong']} kênh · CHƯA BẬT)"
            else:
                nhan = f"{_ten_nhom(n['grp'])} (chưa có kênh)"
            hang.append([{"text": nhan, "callback_data": f"{lenh} {i + 1}"}])
        if not hang:
            self.gui(chat_id, "⚠ App chưa có nhóm/kênh nào.")
            return False
        self._nhom_map[0] = "__ALL__"
        hang.append([{"text": f"TẤT CẢ ({tong} kênh bật)",
                      "callback_data": f"{lenh} 0"}])
        self.gui(chat_id, tieu_de, phim={"inline_keyboard": hang})
        return True

    def _nhom_chua_bat(self, chat_id: int, k: int, g) -> bool:
        """Nhóm KHÔNG có kênh nào bật -> NÓI RÕ vì sao + nút bật cả nhóm.
        Trả True nếu đã xử lý (caller dừng)."""
        if g in (None, "__ALL__"):
            return False
        r = _db().query_one(
            "SELECT COUNT(*) tong, SUM(pipe_on=1 AND pipe_hidden=0) bat, "
            "SUM(pipe_hidden=0) hien FROM projects WHERE COALESCE(grp,'')=?",
            (g,))
        tong = int(r["tong"] or 0) if r else 0
        bat = int(r["bat"] or 0) if r else 0
        hien = int(r["hien"] or 0) if r else 0
        if bat:
            return False
        ten = _html(_ten_nhom(g))
        if not tong:
            self.gui(chat_id, f"Nhóm «{ten}» CHƯA CÓ KÊNH nào. Trên app: bấm "
                              "<b>Sửa nhóm</b> (cạnh ô Nhóm) -> chuyển kênh vào "
                              "nhóm này, hoặc thêm kênh mới vào nhóm.")
            return True
        if not hien:
            self.gui(chat_id, f"Nhóm «{ten}» có {tong} kênh nhưng đều đang ẨN "
                              "khỏi dây chuyền. Bỏ ẩn trong hộp Dây chuyền trên app.")
            return True
        self.gui(chat_id, f"Nhóm «{ten}» có <b>{hien} kênh</b> nhưng <b>CHƯA kênh "
                          "nào BẬT dây chuyền</b> (cột 'Bật' chưa tích) nên app "
                          "chưa chạy nhóm này.",
                 phim={"inline_keyboard": [[
                     {"text": f"✅ Bật {hien} kênh nhóm này", "callback_data":
                      f"/batnhom {k}"},
                     {"text": "Huỷ", "callback_data": "/huybo"}]]})
        return True

    def _bat_nhom(self, chat_id: int, text: str) -> None:
        p = text.split()
        k = int(p[1]) if len(p) >= 2 and p[1].isdigit() else -1
        g = self._nhom_map.get(k)
        if g is None or g == "__ALL__":
            self.gui(chat_id, "Danh sách nhóm đã cũ — bấm /chay để chọn lại.")
            return
        kq = goi_ui("bat_nhom", g)
        if not isinstance(kq, dict) or not kq.get("ok"):
            self.gui(chat_id, "⚠ Chưa bật được: "
                     + _html(str((kq or {}).get("ly_do", "app không trả lời"))))
            return
        xoa_dem()
        self.gui(chat_id, f"✅ Đã bật dây chuyền cho {kq.get('n', 0)} kênh nhóm "
                          f"«{_html(_ten_nhom(g))}».")
        self._chay(chat_id, f"/chay {k}")

    # -- tin tiến độ TỰ CẬP NHẬT (sửa 1 tin, không gửi tin mới) --
    def _bat_theo_doi(self, chat_id: int) -> None:
        mid = self.gui(chat_id, self._noi_dung_song(), phim=_PHIM_SONG)
        if mid or self._gui_ngoai:
            self._song[chat_id] = {"mid": mid, "tu": time.monotonic(), "cu": ""}
            self._danh_thuc.set()

    def _noi_dung_song(self) -> str:
        nhan = goi_dang_nhan()
        t = bao_cao_tien_do(self.pool)
        if nhan:
            t += f"\n📥 Còn {nhan} video đang chờ app NHẬN vào dây chuyền"
        return t + f"\n<i>tự cập nhật mỗi {SONG_NHIP}s</i>"

    def _sua_song(self, xong: bool = False) -> None:
        """Sửa tin theo dõi. Tự xét "đã hết việc" bằng CHÍNH số liệu của lần sửa
        này (không trông vào lượt soi: việc ngắn lọt giữa 2 lượt soi thì lượt
        soi không thấy, tin theo dõi sẽ chạy mãi)."""
        if not self._song:
            return
        try:
            d = tong_quan()
            viec = d["running"] + d["pending"] + goi_dang_nhan()
        except Exception:  # noqa: BLE001
            viec = 1
        for cid, st in list(self._song.items()):
            try:
                if viec:
                    st["thay"] = True
                het = xong or (st.get("thay") and not viec)
                # bật theo dõi lúc rảnh mà 10 phút vẫn không có việc -> thôi
                ranh_lau = (not st.get("thay") and not viec
                            and time.monotonic() - st["tu"] > 600)
                text = self._noi_dung_song()
                if het:
                    text = text.replace(f"<i>tự cập nhật mỗi {SONG_NHIP}s</i>",
                                        "<i>✅ đã chạy hết — ngừng cập nhật</i>")
                if text != st["cu"] and st["mid"]:
                    self.sua(cid, st["mid"], text, None if het else _PHIM_SONG)
                st["cu"] = text
                if het or ranh_lau or time.monotonic() - st["tu"] > SONG_TOI_DA:
                    self._song.pop(cid, None)
            except Exception as e:  # noqa: BLE001
                _ghi_log(f"sửa tin theo dõi lỗi: {e!r}")

    # -- vòng nghe getUpdates (1 luồng riêng) --
    def _vong_nhan(self) -> None:
        cho = 2.0
        while not self._dung.is_set():
            _nhip_song()
            try:
                kq = self._goi("getUpdates", {"offset": self._offset, "timeout": 25,
                                              "allowed_updates": ["message", "callback_query"]},
                               timeout=35)
                cho = 2.0
                for u in kq or []:
                    self._offset = max(self._offset, u["update_id"] + 1)
                    self._nhan_mot(u)
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                _ghi_log(f"nhận lệnh lỗi: {msg[:200]}")
                # 409 = máy khác đang dùng CÙNG token -> 2 máy giành nhau
                # (409 lúc vừa mở app thường là BOT GÁC CỔNG chưa kịp nhường:
                # nó nhường trong <= 6s nên chờ ngắn)
                from app.core import tele_gac
                self._dung.wait((8.0 if tele_gac.dang_chay() else 60.0)
                                if "409" in msg else cho)
                cho = min(60.0, cho * 2)

    def _nhan_mot(self, u: dict) -> None:
        try:
            if "callback_query" in u:
                cq = u["callback_query"]
                cid = cq["message"]["chat"]["id"]
                self.nhan_lenh(cid, cq.get("data") or "", ma_nut=cq.get("id"))
            elif "message" in u:
                m = u["message"]
                self.nhan_lenh(m["chat"]["id"], m.get("text") or "")
        except Exception as e:  # noqa: BLE001
            _ghi_log(f"update lỗi: {e!r}")

    # -- vòng theo dõi + tự báo --
    def soi_mot_lan(self, now: Optional[float] = None) -> list[str]:
        """1 lượt soi dây chuyền -> danh sách tin cần báo. Thuần (test gọi thẳng)."""
        now = now or time.time()
        tin: list[str] = []
        d = tong_quan()
        # lỗi mới (lượt đầu chỉ ghi nhận, không báo dồn lỗi cũ)
        for r in d["loi"]:
            if r["id"] in self._da_bao_loi:
                continue
            self._da_bao_loi.add(r["id"])
            if not self._lan_dau:
                self._loi_cho.append(f"#{r['id']} {_html(_ten_job(r))}\n    <i>"
                                     f"{_html((r['error'] or '')[:140])}</i>")
                self._loi_tu = self._loi_tu or now
        # LỖI MỨC DÂY CHUYỀN (rà soát 01/11/2026): video bị chuyển _Loi / file
        # hỏng / "chờ xem lại" chỉ nằm ở sổ pipeline_files, không phải job
        # failed -> trước đây bot im, anh Hùng chỉ biết khi tự gõ /loi.
        try:
            _db_ = _db()
            # Theo THỜI ĐIỂM ghi (done_at), không theo id: mark_error SỬA dòng
            # 'taken' cũ nên id không đổi. Mốc = giờ DB (UTC) của lượt soi trước.
            _mx = _db_.query_one("SELECT datetime('now') m")["m"]
            _cu = getattr(self, "_pf_moc", None)
            if _cu is not None and not self._lan_dau:
                for r in _db_.query(
                        "SELECT f.id, f.status, f.file_name, f.note, p.name AS chan "
                        "FROM pipeline_files f LEFT JOIN projects p ON p.id=f.project_id "
                        "WHERE f.status IN ('error','bad') AND f.done_at>? "
                        "ORDER BY f.id LIMIT 50", (_cu,)):
                    if ("pf", r["id"]) in self._da_bao_loi:
                        continue
                    self._da_bao_loi.add(("pf", r["id"]))
                    self._loi_cho.append(
                        f"📂 {_html(r['chan'] or '')}: {_html((r['file_name'] or '')[:60])}"
                        f"\n    <i>{_html((r['note'] or r['status'])[:140])}</i>")
                    self._loi_tu = self._loi_tu or now
            self._pf_moc = _mx
        except Exception:  # noqa: BLE001 - báo lỗi phụ không được làm hỏng lượt soi
            pass
        if self._loi_cho and now - self._loi_tu >= GOM_LOI_GIAY:
            tin.append(f"❌ <b>{len(self._loi_cho)} việc lỗi mới</b>\n" + "\n".join(self._loi_cho[:8]))
            self._loi_cho, self._loi_tu = [], 0.0
        # kẹt: chạy mà tiến độ + lời nhắn đứng im quá KET_PHUT
        con = set()
        for r in d["chay"]:
            jid = r["id"]
            con.add(jid)
            # BỎ CHỮ SỐ trước khi so (rà soát 01/11/2026): lời đếm ngược "đợi
            # 37s…" đổi mỗi 5 giây nên job kẹt vòng đợi lượt AI / lượt ffmpeg
            # trước đây KHÔNG BAO GIỜ bị coi là đứng im.
            k = (float(r["progress"] or 0), re.sub(r"\d+", "#", r["message"] or ""))
            cu = self._tien_do.get(jid)
            if cu is None or (cu[0], cu[1]) != k:
                self._tien_do[jid] = (k[0], k[1], now)
                self._da_bao_ket.discard(jid)
            elif now - cu[2] >= KET_PHUT * 60 and jid not in self._da_bao_ket:
                self._da_bao_ket.add(jid)
                _dau = "đợi lượt" if ("đợi" in k[1] or "hồi lượt" in k[1]) else "đứng im"
                tin.append(f"⏳ <b>Việc #{jid} {_dau} {_phut(now - cu[2])}</b>\n"
                           f"{_html(_ten_job(r))}\n<i>{_html((r['message'] or '')[:120])}</i>\n"
                           f"Muốn bỏ thì gõ /huy {jid}")
        for jid in list(self._tien_do):
            if jid not in con:
                self._tien_do.pop(jid, None)
        # chạy hết hàng chờ (kể cả hàng NHẬN của lượt chạy)
        co_viec = (d["running"] + d["pending"] + goi_dang_nhan()) > 0
        # "HẾT" chỉ báo khi KHÔNG có việc ở 2 lượt soi LIỀN NHAU (job xuất được
        # xếp vài giây SAU khi phân tích xong -> 1 lượt rỗng chưa chắc là hết),
        # và DB không hỏng (DB hỏng thì mọi truy vấn trả rỗng = "hết" GIẢ).
        self._rong_dem = 0 if co_viec else getattr(self, "_rong_dem", 0) + 1
        if not co_viec and (d["corrupt"] or self._rong_dem < 2):
            co_viec = self._co_viec
        if self._co_viec and not co_viec and not self._lan_dau:
            # "HẾT hàng chờ" chỉ là hết VIỆC ĐÃ NHẬN; thư mục kênh có thể còn
            # video chưa nhận -> nói thẳng ở dòng đầu, không để tưởng xong hết.
            c = dem_cho_nhan(ttl=0)
            if c.get("loi"):
                dau = ("⚠ <b>Hết việc đang chạy</b> — chưa đọc được hết thư mục kênh "
                       f"({c['loi']} kênh lỗi), có thể vẫn còn video chưa phân tích.")
            elif c["video"]:
                dau = (f"⚠ <b>Hết việc đang chạy, nhưng thư mục kênh còn {c['video']} "
                       "video CHƯA phân tích.</b>")
            else:
                dau = "✅ <b>Đã chạy HẾT hàng chờ.</b>"
            tin.append(dau + "\n" + bao_cao_tien_do(self.pool))
        self._co_viec = co_viec
        # ổ đĩa (báo tối đa 1 lần/3 giờ)
        try:
            o, free = _o_dia()
            if free < O_TRONG_GB and now - self._bao_o > 3 * 3600:
                self._bao_o = now
                tin.append(f"💾 <b>Ổ {o} chỉ còn {free:.0f} GB</b> — dọn bớt kẻo xuất lỗi / hỏng DB.")
        except Exception:  # noqa: BLE001
            pass
        if d["corrupt"] and not self._bao_db:
            self._bao_db = True
            tin.append("🛑 <b>Cơ sở dữ liệu báo hỏng</b> — app đã dừng đọc. Khởi động lại "
                       "app để tự chữa (sao lưu tự động vẫn còn).")
        # báo cáo nhóm của phiếu đợt: gộp vào tin HẾT hàng chờ nếu có (#28)
        bc = _lay_bao_cao_nhom()
        if bc:
            gop = "\n\n".join(t for t, _ in bc)
            i_het = next((i for i, t in enumerate(tin)
                          if "HẾT hàng chờ" in t or "Hết việc đang chạy" in t), None)
            if i_het is not None:
                tin[i_het] = tin[i_het] + "\n\n" + gop
            else:
                tin.append(gop)
            for _, fn in bc:
                try:
                    if fn:
                        fn()
                except Exception:  # noqa: BLE001
                    pass
        self._lan_dau = False
        return tin

    def _vong_soi(self) -> None:
        lan_soi = 0.0
        while not self._dung.is_set():
            # có tin theo dõi -> thức mỗi SONG_NHIP; không -> NHIP_THEO_DOI.
            # Lệnh (tạm dừng, chạy...) set _danh_thuc -> dậy NGAY, không ngủ cố định.
            self._danh_thuc.wait(SONG_NHIP if self._song else NHIP_THEO_DOI)
            self._danh_thuc.clear()
            if self._dung.is_set():
                break
            try:
                if time.monotonic() - lan_soi >= NHIP_THEO_DOI - 1:
                    lan_soi = time.monotonic()
                    tin = self.soi_mot_lan()
                    for t in tin:
                        self.bao_tat_ca(t)
                    het = any(("HẾT hàng chờ" in t) or ("Hết việc đang chạy" in t) for t in tin)
                else:
                    het = False
                if self._song:
                    self._sua_song(xong=het)
            except Exception as e:  # noqa: BLE001
                _ghi_log(f"soi lỗi: {e!r}")

    def bat_dau(self) -> None:
        _bat_ipv4()
        threading.Thread(target=self._vong_nhan, daemon=True, name="tele-nhan").start()
        threading.Thread(target=self._vong_soi, daemon=True, name="tele-soi").start()
        _ghi_log(f"bot bật, {len(self.cho_phep)} chat được phép")
        if self.cho_phep:
            dung = self.pool is not None and self.pool.dang_tam_dung()

            def chao():
                dang_ky_menu(self._goi)
                for cid in self.cho_phep:
                    self.gui(cid, f"🟢 App đã mở trên máy <b>{socket.gethostname()}</b>"
                             + (" — ⏸ đang TẠM DỪNG (bấm Chạy tiếp)" if dung else "")
                             + ".", phim=BAN_PHIM)
            self._viec.submit(chao)

    def dung(self) -> None:
        self._dung.set()
        try:                              # gác cổng nhận việc NGAY, khỏi chờ 75s
            from app.core import tele_gac
            tele_gac.file_song().unlink()
        except Exception:  # noqa: BLE001
            pass
        self._danh_thuc.set()
        try:
            self._viec.shutdown(wait=False, cancel_futures=True)
        except Exception:  # noqa: BLE001
            pass


_PHIM_SONG = {"inline_keyboard": [[
    {"text": "⏸ Tạm dừng", "callback_data": "/tamdung"},
    {"text": "▶ Chạy tiếp", "callback_data": "/chaytiep"},
    {"text": "Lỗi", "callback_data": "/loi"}]]}


# ---- BÁO CÁO NHÓM (phiếu đợt, INTEGRATION.md mục 11) ----
# Tự chạy đẩy vào đây khi CẢ 2 phiếu của 1 nhóm đã đóng. Lượt soi kế tiếp gửi
# nó GỘP vào tin "HẾT hàng chờ" nếu lượt đó có tin ấy (không báo trùng), không
# thì gửi riêng. `khi_gui()` đánh dấu phiếu cắt -> mở lại app không gửi lại.
_BAO_NHOM: list = []
_BAO_NHOM_KHOA = threading.Lock()


def them_bao_cao_nhom(text: str, khi_gui=None) -> None:
    with _BAO_NHOM_KHOA:
        _BAO_NHOM.append((text, khi_gui))


def _lay_bao_cao_nhom() -> list:
    with _BAO_NHOM_KHOA:
        ra = list(_BAO_NHOM)
        _BAO_NHOM.clear()
    return ra


def goi_dang_nhan() -> int:
    """Số video còn trong hàng NHẬN của lượt chạy dây chuyền (0 = không có
    giao diện / không chạy). Hàm giao diện chỉ đọc len -> gọi thẳng được."""
    fn = _UI_FN.get("dang_nhan")
    if fn is None:
        return 0
    try:
        return int(fn() or 0)
    except Exception:  # noqa: BLE001
        return 0


def _nhip_song() -> None:
    """Đánh dấu "bot chính đang nghe" cho bot gác cổng nhường (xem tele_gac)."""
    try:
        from app.core import tele_gac
        tele_gac.file_song().write_text(str(int(time.time())), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def khoi_dong(pool=None) -> Optional[BotQuanLy]:
    """Gọi 1 lần lúc app mở. Không có token -> im lặng không làm gì."""
    global _bot
    try:
        tok, ids = _cfg()
        if os.environ.get("BQ_TAT_BOT"):
            return None                  # test / người dùng tắt hẳn bot
        if not tok or _bot is not None:
            return _bot
        _bot = BotQuanLy(tok, ids, pool)
        _bot.bat_dau()
    except Exception as e:  # noqa: BLE001 - bot không bao giờ làm app chết
        _ghi_log(f"khởi động lỗi: {e!r}")
    return _bot


def tat() -> None:
    try:
        if _bot is not None:
            _bot.dung()
    except Exception:  # noqa: BLE001
        pass
