"""
Đăng ký các job handler vào worker pool.

  - "analyze" : chạy lõi phân tích (tiến trình con) cho 1 video.
  - "auto"    : phân tích (nếu chưa) + tìm highlight trong 1 job — nút chính của UI.
  - "auto_mixed" : phân tích (nếu chưa) + ghép khoảnh khắc hay nhất (Mixed-Cut).
  - "auto_recap" : phân tích (nếu chưa) + AI viết kịch bản 🎙 Reup thuyết minh.
  - "m1_export_clip": đăng ký trong m1_highlight.
"""
from __future__ import annotations

import os
import subprocess
import sys

from app.core.analysis import analysis_status
from config import ROOT_DIR
from .worker import CanceledError, JobContext, register_handler

_CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
# Ưu tiên IDLE cho tiến trình phân tích (whisper/mediapipe chạy dài, nặng):
# Windows LUÔN nhường app khác trước -> máy yếu cũng KHÔNG đơ khi phân tích.
_IDLE_PRIORITY = 0x00000040 if sys.platform == "win32" else 0


def _run_analyze(video_id: int, ctx: JobContext, force: bool,
                 base: float = 0.0, span: float = 1.0) -> None:
    """Chạy lõi phân tích trong tiến trình con; tiến độ trong khoảng base..base+span."""
    # Bản .exe (PyInstaller) KHÔNG chạy được "-m module" -> dùng cờ --analyze mà
    # main.py nhận diện. Bản dev (python) thì chạy module như cũ.
    if getattr(sys, "frozen", False):
        args = [sys.executable, "--analyze", str(video_id)]
    else:
        args = [sys.executable, "-m", "app.core.analysis_runner", str(video_id)]
    if force:
        args.append("force")
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    # NGÂN SÁCH LUỒNG cho lib native trong tiến trình phân tích (whisper/
    # mediapipe/numpy): không set thì OpenMP mở luồng = số nhân -> 1 job
    # phân tích ăn 50-100% CPU cả máy. (analysis_runner cũng tự set — đây là
    # lớp bảo hiểm cho bản .exe, nơi PyInstaller có thể nạp numpy sớm.)
    from config import settings as _st
    cores = os.cpu_count() or 4
    n = (max(2, min(4, cores // 4)) if getattr(_st, "ECO_MODE", True)
         else max(2, min(8, cores // 2)))
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
                "CT2_INTRA_THREADS"):
        env.setdefault(var, str(n))
    proc = subprocess.Popen(
        args, cwd=str(ROOT_DIR), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
        creationflags=_CREATE_NO_WINDOW | _IDLE_PRIORITY,
    )
    from app.core.ffmpeg_utils import register_proc, unregister_proc
    register_proc(proc)
    last_error = ""

    # Đọc stdout bằng THREAD RIÊNG + poll hủy mỗi 0.5s: nếu đọc trực tiếp,
    # lúc tiến trình con im lặng lâu (nạp model whisper, transcribe đoạn dài)
    # sẽ không có dòng nào -> nút Hủy bị lờ tới dòng PROGRESS kế tiếp.
    import queue as _q
    import threading
    lines: _q.Queue = _q.Queue()

    def _reader():
        try:
            for raw in proc.stdout:  # type: ignore[union-attr]
                lines.put(raw.rstrip("\n"))
        except Exception:  # noqa: BLE001
            pass
        finally:
            lines.put(None)          # hết stdout (tiến trình thoát)

    threading.Thread(target=_reader, daemon=True).start()
    try:
        while True:
            ctx.check_canceled()     # nhạy với nút Hủy kể cả pha im lặng
            try:
                line = lines.get(timeout=0.5)
            except _q.Empty:
                continue
            if line is None:
                break
            if line.startswith("PROGRESS\t"):
                parts = line.split("\t", 2)
                try:
                    p = float(parts[1])
                except (ValueError, IndexError):
                    p = 0.0
                ctx.progress(base + span * p, parts[2] if len(parts) > 2 else "")
            elif line.startswith("ERROR\t"):
                last_error = line.split("\t", 1)[1]
    except CanceledError:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        raise
    finally:
        unregister_proc(proc)
    code = proc.wait()
    if code != 0:
        if last_error:
            raise RuntimeError(f"Phân tích lỗi: {last_error}")
        raise RuntimeError(
            f"Tiến trình phân tích dừng đột ngột (mã {code}). Thường do whisper GPU "
            "thiếu cuDNN — bỏ trống WHISPER_DEVICE trong .env (chạy CPU) rồi thử lại.")


def _analyze(payload: dict, ctx: JobContext) -> dict:
    video_id = int(payload["video_id"])
    _run_analyze(video_id, ctx, payload.get("force", False))
    return {"video_id": video_id, "status": analysis_status(video_id)}


def _precompute_hashtags(video_id: int) -> None:
    """Sinh sẵn 3-4 hashtag tên file cho video NGAY TRONG WORKER (sau khi cắt
    clip xong) và cache vào bảng analysis (kind='hashtags').

    Trước đây hashtag chỉ sinh LÚC XUẤT, trên UI THREAD (studio_page.
    _video_hashtags gọi LLM mạng 1-10s) — đúng lúc tự-xuất kích hoạt từ timer
    -> app đơ. Giờ worker làm trước, UI chỉ đọc DB (tức thì). Cùng 1 lời gọi
    social.write_hashtags như cũ — KHÔNG đổi prompt/chất lượng. Lỗi/không key
    -> bỏ qua im lặng (UI tự lo fallback như trước)."""
    try:
        from app.ai import llm, social
        from app.ai.recap import resolve_lang
        if not llm.is_configured():
            return
        from app.core.analysis import _set, get_analysis
        from app.database import db as _db
        clips = _db.query(
            "SELECT title, transcript FROM clips WHERE video_id=? "
            "AND status<>'archived' "   # đừng lấy tiêu đề 'Clip' của lần cũ
            "ORDER BY start_sec", (video_id,))
        tr = get_analysis(video_id, "transcript") or {}
        title = next(((c["title"] or "").strip() for c in clips
                      if (c["title"] or "").strip()), "")
        text = " ".join((c["transcript"] or "").strip() for c in clips
                        if (c["transcript"] or "").strip())
        if not text.strip():
            text = " ".join(s.get("text", "") for s in tr.get("segments", []))
        # NHÃN whisper có thể đoán bừa ('mi' Māori cho video Anh) -> resolve
        # theo lời thoại TRƯỚC khi bảo AI viết (lỗi thật: hashtag Māori).
        lang = resolve_lang(tr.get("language", "") or "", text)
        pre = get_analysis(video_id, "hashtags") or {}
        if pre.get("tags"):
            # đã có VÀ sinh với ĐÚNG ngôn ngữ -> khỏi tốn LLM. Bản cũ không
            # lưu 'lang' / lang khác (video từng dán nhãn sai) -> SINH LẠI.
            if str(pre.get("lang") or "") == lang:
                return
        tags = social.write_hashtags(title, text, lang, max_tags=4)
        if tags:
            _set(video_id, "hashtags", "done", {"tags": tags, "lang": lang})
    except Exception:  # noqa: BLE001 - tiện ích phụ, không được làm hỏng job
        pass


def _auto(payload: dict, ctx: JobContext) -> dict:
    """Tạo clip tự động: phân tích (nếu chưa) -> tìm highlight, 1 thanh tiến trình."""
    from app.modules.m1_highlight import generate_highlights
    video_id = int(payload["video_id"])

    done = all(analysis_status(video_id).get(k) in ("done", "skipped")
               for k in ("transcript", "scenes", "audio", "faces"))
    if not done:
        _run_analyze(video_id, ctx, force=False, base=0.0, span=0.8)

    parent = ctx

    class _Sub:
        profile = parent.profile
        def progress(self, p, m=""):
            parent.progress(0.8 + 0.2 * p, m)
        def check_canceled(self):
            parent.check_canceled()

    res = generate_highlights(
        {"video_id": video_id, "preset": payload.get("preset")}, _Sub())
    # Hashtag tên file: sinh sẵn ở WORKER để UI không phải gọi LLM (đỡ đơ)
    _precompute_hashtags(video_id)
    return {"video_id": video_id, **res}


def _auto_mixed(payload: dict, ctx: JobContext) -> dict:
    """Mixed-Cut 1 nút: phân tích (nếu chưa) -> ghép khoảnh khắc hay nhất."""
    from app.modules.m1_highlight import generate_mixed_cut
    video_id = int(payload["video_id"])

    done = all(analysis_status(video_id).get(k) in ("done", "skipped")
               for k in ("transcript", "scenes", "audio", "faces"))
    if not done:
        _run_analyze(video_id, ctx, force=False, base=0.0, span=0.8)

    parent = ctx

    class _Sub:
        profile = parent.profile
        def progress(self, p, m=""):
            parent.progress(0.8 + 0.2 * p, m)
        def check_canceled(self):
            parent.check_canceled()

    res = generate_mixed_cut(
        {"video_id": video_id, "preset": payload.get("preset")}, _Sub())
    _precompute_hashtags(video_id)   # sinh sẵn hashtag ở worker (đỡ đơ UI)
    return {"video_id": video_id, **res}


def _auto_recap(payload: dict, ctx: JobContext) -> dict:
    """🎙 Reup thuyết minh 1 nút: phân tích (nếu chưa) -> AI viết kịch bản
    thuyết minh cho các đoạn hay (m2_recap)."""
    from app.modules.m2_recap import generate_recap
    video_id = int(payload["video_id"])

    done = all(analysis_status(video_id).get(k) in ("done", "skipped")
               for k in ("transcript", "scenes", "audio", "faces"))
    if not done:
        _run_analyze(video_id, ctx, force=False, base=0.0, span=0.8)

    parent = ctx

    class _Sub:
        profile = parent.profile
        def progress(self, p, m=""):
            parent.progress(0.8 + 0.2 * p, m)
        def check_canceled(self):
            parent.check_canceled()

    res = generate_recap(
        {"video_id": video_id, "preset": payload.get("preset")}, _Sub())
    _precompute_hashtags(video_id)   # sinh sẵn hashtag ở worker (đỡ đơ UI)
    return {"video_id": video_id, **res}


def _don_thu_muc_tam(payload: dict) -> None:
    """Dọn thư mục làm việc tạm của MỘT video thay giọng.

    Phải dọn CẢ khi lỗi: file wav/mp3 của một video 10 phút lên hàng trăm MB,
    300 kênh mà mỗi video lỗi bỏ lại một đống là đúng đường dẫn tới "ổ C đầy
    100%" đã xảy ra thật hôm 31/07. Không bao giờ ném lỗi.

    ═══ CỬA HỞ ĐÃ VÁ 19/08/2026 (cổng 80) ═══
    Bản cũ: ``lam = str(payload.get("thu_muc_lam") or "")`` rồi
    ``if lam and os.path.isdir(lam): rmtree(lam)``. Chuỗi `""` thì
    `os.path.isdir("")` là False nên ca đó may mà thoát — NHƯNG **`"."` thì
    `isdir` trả True** và `rmtree(".")` xoá sạch thư mục đang làm việc, y hệt
    tai nạn `Path("")` của `giong_ngoai._don` cùng ngày. Gốc ổ đĩa (`"D:\\"`)
    cũng lọt. Mà `thu_muc_lam` đến từ PAYLOAD trong DB — job cũ do bản app
    trước ghi vào có thể mang bất cứ chuỗi nào.
    """
    from app.core.xoa_an_toan import don_thu_muc

    don_thu_muc(payload.get("thu_muc_lam"))


def _thay_giong(payload: dict, ctx: JobContext) -> dict:
    """THAY GIỌNG NÓI cho MỘT video (làn riêng `LAN_TG`, xem worker.py).

    Mỗi video một job — cố ý, không gộp cả thư mục vào 1 job:
      · tắt app giữa chừng thì chỉ mất video đang dở, các video còn lại nằm
        trong DB và chạy tiếp khi mở lại (bài học "sổ chỉ ở RAM, phải hồi
        phục": 72 nhận / 4 xong).
      · bấm Huỷ được TỪNG video.
      · bảng tiến độ đọc thẳng bảng `jobs`, không phải sổ RAM riêng.

    **KHÔNG BAO GIỜ ĐỤNG VIDEO GỐC (v2.27.0).** Anh Hùng: *"cho tôi tự chọn
    thư mục ĐẦU VÀO thư mục ĐẦU RA đi, KHÔNG CẦN cái thùng rác phân tích thay
    giọng rồi tự xoá đâu nhé"*. Vì vậy handler **ép `thay_goc=False`** rồi tự
    chuyển bản mới sang THƯ MỤC ĐÍCH — đường `delete_or_recycle` biến mất khỏi
    luồng này. Ép ở ĐÂY (không chỉ ở UI) là cố ý: job cũ nằm sẵn trong DB từ
    bản trước mang `thay_goc=True`, không ép thì mở app lên nó vẫn dọn gốc.

    Sổ trạng thái (`tg_so`) được ghi Ở ĐÂY chứ không chỉ ở UI: đóng hộp/tắt
    app rồi mở lại vẫn phải biết video nào đã xong.
    """
    import shutil

    from app.core import thay_giong as tg
    from app.core import tg_so

    duong = str(payload.get("video") or "")
    if not duong or not os.path.exists(duong):
        raise RuntimeError(f"Không thấy video: {duong}")

    # CHẶN TRƯỚC: máy nhân viên KHÔNG có Demucs -> KHÔNG được lui 'cách nhẹ'
    # (đo: rò rỉ lời 100% zh / 86,3% en = giọng cũ còn nguyên chồng lên giọng
    # mới, ffmpeg vẫn trả mã 0). Thà job đỏ còn hơn 300 kênh hỏng im lặng.
    tg.chot_co_bo_tach_giong(payload.get("cach_tach") or "auto")

    goc = os.path.abspath(duong)
    thu_muc_ra = str(payload.get("thu_muc_ra") or "").strip() or \
        tg_so.thu_muc_dich_mac_dinh(os.path.dirname(goc))
    # CHỐT SỐNG CÒN: đích trùng nguồn = ghi đè MẤT GỐC. Chặn ở đây nữa (UI đã
    # cảnh báo) vì job có thể tới từ payload cũ/đường gọi khác.
    if tg_so.trung_thu_muc(os.path.dirname(goc), thu_muc_ra):
        raise RuntimeError(
            "Thư mục đích TRÙNG thư mục nguồn — sẽ ghi đè mất video gốc")
    os.makedirs(thu_muc_ra, exist_ok=True)
    dich = tg_so.duong_ra(goc, thu_muc_ra)

    def _prog(p: float, m: str) -> None:
        # ctx.progress tự kiểm cờ Huỷ -> đổi sang HuyBo để `thay_giong_video`
        # KHÔNG nuốt nó thành "video lỗi" rồi tự thử lại.
        try:
            ctx.progress(max(0.0, min(0.999, p)), m[:160])
        except CanceledError as e:
            raise tg.HuyBo() from e

    try:
        r = tg.thay_giong_mot_video(
            duong,
            dich_sang=str(payload.get("dich_sang") or "en"),
            voice=str(payload.get("voice") or ""),
            cach_tach=str(payload.get("cach_tach") or "auto"),
            thay_goc=False,          # ÉP: video gốc GIỮ NGUYÊN, xem docstring
            kenh=str(payload.get("kenh") or ""),
            thung_rac="",
            thu_muc_lam=str(payload.get("thu_muc_lam") or ""),
            # CHE CHỮ CHÁY SẴN: job cũ trong DB KHÔNG mang khoá này -> `False`,
            # tức hành vi y hệt bản trước. Mức mờ qua `chuan_muc_mo` (SÀN CỨNG
            # 0,60 — dưới đó mắt vẫn đọc được chữ, đã đo ở cổng 56).
            che_chu=bool(payload.get("che_chu")),
            che_chu_cach=str(payload.get("che_chu_cach") or "mo"),
            che_chu_muc=float(payload.get("che_chu_muc") or 1.0),
            # VIẾT LẠI BẢN DỊCH THEO MỐC GIỌNG sau khi che. Job cũ trong DB
            # KHÔNG mang khoá này -> `False` = y hệt bản trước (chỉ che, không
            # viết). Chỉ có tác dụng khi `che_chu` bật.
            viet_chu=bool(payload.get("viet_chu")),
            # KIỂU CHỮ (cỡ · phông · đậm · nghiêng · màu · viền · vị trí) do
            # user đặt trong hộp Thay giọng. Job cũ trong DB KHÔNG mang khoá
            # này -> None = kiểu chữ mặc định, .ass giống TỪNG BYTE bản trước.
            # Chỉ có tác dụng khi `viet_chu` bật (không viết chữ thì không có
            # chữ nào để tạo kiểu).
            kieu_chu=payload.get("kieu_chu") or None,
            # CHỈNH VIDEO THEO GIỌNG (làm chậm HÌNH cho khớp tiếng, thay vì ép
            # tiếng vừa khung câu gốc). Job cũ trong DB KHÔNG mang khoá này ->
            # `False` = ép giọng y hệt bản trước. ĐỘC LẬP với `che_chu`.
            hinh_theo_giong=bool(payload.get("hinh_theo_giong")),
            # ĐÈ GIỌNG, KHÔNG TÁCH: giữ NGUYÊN tiếng gốc làm nền, chỉ hạ xuống
            # rồi đè giọng lồng lên. Job cũ trong DB KHÔNG mang khoá này ->
            # `False` = vẫn tách nhạc y hệt bản trước. ĐỘC LẬP với mọi cờ khác;
            # nó bỏ hẳn bước Demucs nên là đường DUY NHẤT chạy được trên máy
            # không có torch (xem `thay_giong.chot_co_bo_tach_giong`).
            de_giong=bool(payload.get("de_giong")),
            on_progress=_prog,
        )
    except tg.HuyBo as e:
        # HUỶ ≠ LỖI: KHÔNG ghi sổ (lượt sau vẫn phải chạy lại video này) và
        # KHÔNG dọn thư mục tạm (file có thể còn bị tiến trình con giữ).
        raise CanceledError() from e
    except Exception as e:           # noqa: BLE001 - ghi sổ rồi ném tiếp
        tg_so.ghi(goc, tg_so.LOI, loi=f"{type(e).__name__}: {e}"[:300])
        _don_thu_muc_tam(payload)
        raise
    if not r.get("ok"):
        loi = str(r.get("loi") or "Thay giọng lỗi không rõ")
        tg_so.ghi(goc, tg_so.LOI, loi=loi[:300])
        _don_thu_muc_tam(payload)
        raise RuntimeError(loi)

    # --- ĐẶT BẢN MỚI VÀO THƯ MỤC ĐÍCH (giữ NGUYÊN tên file gốc) ---
    try:
        if os.path.exists(dich):     # lần chạy lại -> thay bản cũ trong đích
            os.remove(dich)
        shutil.move(str(r["ra"]), dich)
    except OSError as e:
        tg_so.ghi(goc, tg_so.LOI, loi=f"không đặt được file vào đích: {e}")
        raise RuntimeError(
            f"Không đặt được video mới vào thư mục đích: {e}") from e
    r["ra"] = dich

    _don_thu_muc_tam(payload)
    tg_so.ghi(goc, tg_so.XONG, ra=dich, giay=r.get("giay_tong"),
              dich_sang=str(payload.get("dich_sang") or ""))
    # gọn lại cho cột `result` của bảng jobs (bỏ mảng câu/đường dẫn tạm)
    return {
        "vao": r.get("vao"), "ra": dich,
        "do_dai": r.get("do_dai"), "giay": r.get("giay_tong"),
        "kiem": r.get("kiem"), "tach": (r.get("tach") or {}).get("cach"),
        # CÁCH TRỘN phải nằm trong nhật ký: hai cách ra file tiếng KHÁC HẲN
        # nhau, nên đọc lại một job cũ mà không biết nó chạy cách nào là không
        # đối chiếu được gì (bài học `mẫu «(mẫu đã chốt lúc xếp job)»`, cổng 25b).
        "cach_tron": r.get("cach_tron"),
        "che_chu": r.get("che_chu"),
        "chu_theo_giong": r.get("chu_theo_giong"),
        "da_thay_goc": False, "goc_o": goc,
        "vi_sao": "giữ nguyên video gốc, bản mới nằm ở thư mục đích",
        "khop": r.get("khop"), "dich": r.get("dich"),
    }


register_handler("analyze", _analyze)
register_handler("auto", _auto)
register_handler("auto_mixed", _auto_mixed)
register_handler("auto_recap", _auto_recap)
register_handler("thay_giong", _thay_giong)

# Nạp handler của Module 1 (tự register khi import)
from app.modules import m1_highlight  # noqa: E402,F401
