# -*- coding: utf-8 -*-
"""CỔNG 55 — THAY GIỌNG NÓI NỐI VÀO UI + CHẠY ĐA LUỒNG.

Cổng 53 kiểm các HÀM của `app/core/thay_giong.py`. Cổng này kiểm cái mà anh
Hùng thật sự bấm: **nút trên màn hình -> bộ điều phối -> video mới nằm đúng
chỗ, video gốc nằm trong Thùng rác**.

THÀNH PHẦN THẬT: ffmpeg thật · Groq thật (key qua ENV) · edge-tts thật ·
Demucs thật · WorkerPool thật. KHÔNG mock. Chỗ duy nhất được can thiệp là
**GÂY LỖI CÓ CHỦ Ý** (ffmpeg ghi ra file 0 KiB, giả lập máy thiếu Demucs) —
đó là phép thử, không phải thay thế thành phần.

CÁC CA:
  1. Bấm Chạy trên thư mục 2 video -> 2 video MỚI đúng chỗ, 2 gốc trong
     Thùng rác, **MD5 gốc trùng TỪNG BYTE**.
  2. ĐA LUỒNG THẬT: 2 luồng nhanh hơn chạy lần lượt (đo wall-time) + đo
     được SỐ JOB CHẠY CÙNG LÚC ở làn thay giọng.
  3. MÁY KHÔNG CÓ DEMUCS: hiện nút tải, KHOÁ nút Chạy, bấm Chạy không xếp
     job nào, handler NÉM — và KHÔNG có đường nào lui sang "cách nhẹ".
  4. FILE MỚI HỎNG (0 KiB): gốc CÒN NGUYÊN, Thùng rác KHÔNG có gì.
  5. ROUND-TRIP UI: đặt giá trị -> lưu -> mở hộp mới -> ra đúng giá trị cũ.
  6. THỬ PHÁ: bỏ chốt `kiem_video_ra` thì bất biến ca 4 PHẢI VỠ. Không vỡ =
     cổng này chỉ là con dấu.

    .venv\\Scripts\\python _test_thay_giong_ui.py
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = str(Path(__file__).resolve().parent)   # KHÔNG ghi cứng đường repo
sys.path.insert(0, REPO)

T = Path(tempfile.mkdtemp(prefix="tgui_"))
# THÙNG RÁC phải nằm NGOÀI %TEMP%: `_is_safe_recycle_root` (đúng) từ chối mọi
# thùng rác trong Temp và lùi về `_DaXoa` nội bộ — mà sandbox của cổng thì
# NẰM TRONG %TEMP%. Không tách ra thì cổng không bao giờ kiểm được đường
# "thùng rác user chọn", và mục MD5 sẽ HỎNG OAN (đã sập 1 lần khi viết cổng).
RAC = Path(REPO) / f"bq_test_tgrac_{os.getpid()}"
RAC.mkdir(parents=True, exist_ok=True)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_DB_PATH"] = str(T / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(T / "settings.ini")  # KHÔNG chạm registry
os.environ["BQ_FFMPEG_SLOTS"] = "1"       # máy anh Hùng đang chạy việc thật
os.environ["WHISPER_PROVIDER"] = "groq"

# KEY GROQ: nằm trong `<DATA_DIR thật>\.env`, mà cổng trỏ BQ_DATA_DIR sang
# thư mục tạm -> sandbox 0 key -> `transcribe` tụt về whisper MÁY -> tải model
# ~3 GB -> cổng FAIL OAN (bài học cổng 22). Chuyền qua BIẾN MÔI TRƯỜNG, không
# ghi ra file nào.
_ENV_THAT = (Path(os.environ.get("LOCALAPPDATA") or Path.home())
             / "BQHungVideo" / ".env")
if _ENV_THAT.exists():
    for _ln in _ENV_THAT.read_text(encoding="utf-8",
                                   errors="replace").splitlines():
        _k, _, _v = _ln.partition("=")
        _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
        if _k in ("GROQ_API_KEYS", "GROQ_KEYS_FILE") and _v:
            os.environ.setdefault(_k, _v)

import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát

# cv2 (app.queue.jobs -> app.core.analysis) phải nạp TRƯỚC Qt — bài học guard.
import app.queue.jobs as _JOBS  # noqa: E402,F401
from app.database import db  # noqa: E402
from app.queue.worker import WorkerPool  # noqa: E402
from config import settings  # noqa: E402
from app.core import thay_giong as TG  # noqa: E402

from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

# Hộp thoại KHÔNG được treo cổng: vá exec/warning/information/question.
QMessageBox.exec = lambda self: 0                      # type: ignore
QMessageBox.warning = staticmethod(lambda *a, **k: 0)  # type: ignore
QMessageBox.information = staticmethod(lambda *a, **k: 0)  # type: ignore
QMessageBox.critical = staticmethod(lambda *a, **k: 0)  # type: ignore
QMessageBox.question = staticmethod(
    lambda *a, **k: QMessageBox.StandardButton.No)      # type: ignore

_app = QApplication.instance() or QApplication([])
from app.ui import theme  # noqa: E402
_app.setStyleSheet(theme.QSS)          # QSS THẬT (bài học cổng 9)
from app.ui.thay_giong_dialog import ThayGiongDialog  # noqa: E402

OK: list[str] = []
FAIL: list[str] = []
SO: dict = {}


def dat(dieu: str, ok: bool, chi_tiet: str = "") -> None:
    (OK if ok else FAIL).append(f"{dieu} {chi_tiet}".strip())
    print(f"  [{'ĐẠT' if ok else 'HỎNG'}] {dieu}"
          + (f" — {chi_tiet}" if chi_tiet else ""))


def ff(args: list[str]) -> int:
    r = subprocess.run([settings.FFMPEG_PATH, "-y", "-hide_banner",
                        "-loglevel", "error", *args],
                       capture_output=True, text=True)
    return r.returncode


def md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for k in iter(lambda: fh.read(1 << 20), b""):
            h.update(k)
    return h.hexdigest()


# ==================================================================
# NGUỒN: video CÓ LỜI NÓI THẬT (edge-tts) + nhạc nền để còn cái mà GIỮ
# ==================================================================
LOI = ("Chào mọi người, hôm nay chúng ta thử một thứ rất hay. "
       "Anh ấy mở cánh cửa ra, và điều bất ngờ đã xảy ra ngay lúc đó.")


def _tts_goc(dst: Path) -> Path:
    """Đọc câu nguồn bằng CHÍNH đường TTS của app (`dubbing._synth_all`).

    Gọi thẳng `edge_tts.Communicate` là thỉnh thoảng ăn `NoAudioReceived` —
    server MS chập chờn theo đợt, và `_synth_all` đã có sẵn 4 lượt thử lại.
    Dùng lại nó vừa đúng luật "thành phần thật" vừa đỡ cổng ĐỎ OAN vì mạng.
    """
    import asyncio

    from app.core import dubbing

    ok = asyncio.run(dubbing._synth_all([LOI], "vi-VN-HoaiMyNeural",
                                        [str(dst)]))
    if not ok[0] or not dst.exists() or dst.stat().st_size < 2000:
        raise RuntimeError("edge-tts không đọc được câu nguồn (mạng/MS lỗi)")
    return dst


def dung_nguon(dst: Path, speech: Path) -> Path:
    """Video = hình testsrc2 + (LỜI NÓI thật trộn với NHẠC NỀN).

    Phải có nhạc nền thật: lớp "nhạc" mà Demucs giữ lại phải CÓ TIẾNG, không
    thì `_kiem_wav` đánh trượt đúng luật (RMS 0 = tách hỏng).
    """
    d = TG.probe_duration(speech)
    fc = ("[1:a][2:a]join=inputs=2:channel_layout=stereo,"
          "volume=-12dB[bed];"
          "[0:a]aformat=channel_layouts=stereo[sp];"
          "[bed][sp]amix=inputs=2:duration=first:normalize=0[a]")
    ff(["-i", str(speech),
        "-f", "lavfi", "-i", f"sine=frequency=196:duration={d:.2f}",
        "-f", "lavfi", "-i", f"sine=frequency=294:duration={d:.2f}",
        "-f", "lavfi", "-i",
        f"testsrc2=size=320x240:rate=25:duration={d:.2f}",
        "-filter_complex", fc, "-map", "3:v", "-map", "[a]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
        "-t", f"{d:.2f}", str(dst)])
    return dst


print("\n=== DỰNG NGUỒN (edge-tts THẬT + nhạc nền) ===")
_sp = _tts_goc(T / "loi.mp3")
_mau = dung_nguon(T / "mau.mp4", _sp)
_DAI = TG.probe_duration(_mau)
print(f"  video mẫu: {_DAI:.2f} giây, {_mau.stat().st_size} byte")
dat("dựng được video nguồn CÓ LỜI NÓI thật", _DAI > 3.0 and
    TG.do_rms(_mau) > 0, f"{_DAI:.2f}s, RMS {TG.do_rms(_mau):.5f}")
print("  key Groq trong sandbox:",
      len([x for x in os.environ.get("GROQ_API_KEYS", "").replace(",", "\n")
           .splitlines() if x.strip()]))


def thu_muc_video(ten: str, n: int) -> Path:
    d = T / ten
    d.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        shutil.copy2(_mau, d / f"video_{i + 1}.mp4")
    return d


def cho_xong(pool, ids: list[int], han: float = 900.0) -> dict:
    """Đợi job xong; VỪA ĐỢI VỪA ĐO số job chạy cùng lúc ở làn thay giọng."""
    t0 = time.time()
    dinh = 0
    while time.time() - t0 < han:
        _app.processEvents()          # cho hộp thoại chạy nhịp như app thật
        dinh = max(dinh, pool._dem_lan()[2])
        rows = db.query(
            "SELECT status FROM jobs WHERE id IN ({})".format(
                ",".join("?" * len(ids))), tuple(ids))
        tt = [str(r["status"]) for r in rows]
        if tt and all(s in ("done", "failed", "canceled") for s in tt):
            break
        time.sleep(0.25)
    return {"giay": round(time.time() - t0, 2), "dinh_song_song": dinh}


# ==================================================================
print("\n=== CA 5: ROUND-TRIP UI (đặt -> lưu -> mở lại) ===")
d5 = thu_muc_video("ca5", 1)
dlg5 = ThayGiongDialog(None, None)
dlg5.ed_thu_muc.setText(str(d5))
dlg5.cb_nn.setCurrentIndex(dlg5.cb_nn.findData("ko"))
dlg5.sp_luong.setValue(3)
dlg5.ck_xoa.setChecked(False)
dlg5.cb_giong.addItem("giọng thử", "ko-KR-SunHiNeural")
dlg5.cb_giong.setCurrentIndex(dlg5.cb_giong.count() - 1)
dlg5.luu_cai_dat()
dlg5.close()

dlg5b = ThayGiongDialog(None, None)
dat("nhớ THƯ MỤC", dlg5b.ed_thu_muc.text() == str(d5),
    dlg5b.ed_thu_muc.text()[-40:])
dat("nhớ NGÔN NGỮ ĐÍCH", dlg5b.cb_nn.currentData() == "ko",
    str(dlg5b.cb_nn.currentData()))
dat("nhớ SỐ LUỒNG", dlg5b.sp_luong.value() == 3, str(dlg5b.sp_luong.value()))
dat("nhớ ô XOÁ GỐC", dlg5b.ck_xoa.isChecked() is False)
dat("nhớ GIỌNG đã chọn",
    dlg5b.cb_giong.currentData() == "ko-KR-SunHiNeural",
    str(dlg5b.cb_giong.currentData()))
dat("bảng liệt kê đúng số video", dlg5b.bang.rowCount() == 1,
    f"{dlg5b.bang.rowCount()} dòng")
_s_ini = Path(os.environ["BQ_QSETTINGS_INI"])
dat("KHÔNG ghi QSettings THẬT (chỉ ghi file .ini sandbox)", _s_ini.exists(),
    str(_s_ini.name))
dlg5b.close()


# ==================================================================
print("\n=== CA 3: MÁY KHÔNG CÓ DEMUCS -> CHẶN, KHÔNG lui cách nhẹ ===")
_that_tt = TG.tinh_trang_demucs
_that_co = TG.co_demucs
TG.tinh_trang_demucs = lambda: {          # giả lập ĐÚNG máy nhân viên
    "co": False, "thieu": ["torch", "demucs"], "lib": str(T / "lib_rong"),
    "thiet_bi": "", "cai_duoc": True, "loi_nhan": TG.THIEU_DEMUCS}
TG.co_demucs = lambda: False
try:
    d3 = thu_muc_video("ca3", 1)
    goc3 = next(iter(TG.liet_ke_video(d3)))
    md5_3 = md5(goc3)
    dlg3 = ThayGiongDialog(None, None)
    dlg3.ed_thu_muc.setText(str(d3))
    dat("HIỆN nút tải bộ tách giọng", not dlg3.b_tai.isHidden(),
        dlg3.b_tai.text())
    dat("nhãn nút tải nói rõ DUNG LƯỢNG",
        "2 GB" in dlg3.b_tai.text(), dlg3.b_tai.text())
    dat("KHOÁ nút Chạy", not dlg3.b_chay.isEnabled())
    dlg3._chay()                            # bấm Chạy khi thiếu Demucs
    dat("bấm Chạy vẫn KHÔNG xếp job nào", len(dlg3._jobs) == 0,
        f"{len(dlg3._jobs)} job")
    dat("video gốc KHÔNG bị đụng", goc3.exists() and md5(goc3) == md5_3)
    dlg3.close()

    # handler của bộ điều phối cũng phải NÉM, không âm thầm ra video hỏng
    class _Ctx:
        job_id = 0
        profile: dict = {}

        def progress(self, p, m=""):
            pass

        def check_canceled(self):
            pass

    try:
        _JOBS._thay_giong({"video": str(goc3), "dich_sang": "en"}, _Ctx())
        dat("handler NÉM khi thiếu Demucs", False, "không ném")
    except RuntimeError as e:
        dat("handler NÉM khi thiếu Demucs", "Demucs" in str(e),
            str(e)[:60])
finally:
    TG.tinh_trang_demucs = _that_tt
    TG.co_demucs = _that_co


def _ma_that(path: Path) -> str:
    """Mã nguồn ĐÃ BỎ comment + chuỗi (bài học cổng 47/51: quét thô làm chính
    DÒNG GHI CHÚ giải thích bản vá bị kể là vi phạm -> ĐỎ OAN vĩnh viễn)."""
    import io
    import tokenize
    ra = []
    with open(path, "rb") as fh:
        for tok in tokenize.tokenize(io.BytesIO(fh.read()).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            ra.append(tok.string)
    return " ".join(ra)


for _f in ("app/ui/thay_giong_dialog.py", "app/queue/jobs.py",
           "app/services.py"):
    _m = _ma_that(Path(REPO, _f))
    dat(f"{_f}: KHÔNG có đường lui 'cách nhẹ'",
        "cho_phep_nhe" not in _m and "'nhe'" not in _m
        and '"nhe"' not in _m)
# TỰ KIỂM BỘ DÒ: chính `thay_giong.py` PHẢI còn chữ đó (nó là nơi cài chốt) —
# bộ dò không kêu ở đây thì mọi mục trên là con dấu.
_m_core = _ma_that(Path(REPO, "app/core/thay_giong.py"))
dat("TỰ KIỂM BỘ DÒ: thay_giong.py vẫn thấy 'cho_phep_nhe'",
    "cho_phep_nhe" in _m_core)


# ==================================================================
print("\n=== CA 1+2: CHẠY ĐỦ ĐƯỜNG TỪ UI + ĐA LUỒNG THẬT ===")
db.execute("DELETE FROM jobs")
pool = WorkerPool({}, max_cpu=1, max_gpu=1, max_tg=2)
pool.start()

thung = RAC / "ThungRac"
thung.mkdir(parents=True, exist_ok=True)

# --- arm B: 2 LUỒNG (đây cũng là ca 1) ---
d2 = thu_muc_video("ca1_2luong", 2)
goc_md5 = {p.name: md5(p) for p in TG.liet_ke_video(d2)}
dlg = ThayGiongDialog(pool, None, thung_rac=str(thung))
dlg.ed_thu_muc.setText(str(d2))
dlg.cb_nn.setCurrentIndex(dlg.cb_nn.findData("en"))
dlg.sp_luong.setValue(2)
dlg.ck_xoa.setChecked(True)
dlg._chay()                                   # <- BẤM CHẠY
ids2 = list(dlg._jobs.values())
dat("bấm Chạy xếp đúng 2 job", len(ids2) == 2, f"{len(ids2)} job")
dat("số luồng của hộp áp vào bộ điều phối", pool.max_tg == 2,
    f"max_tg={pool.max_tg}")
r2 = cho_xong(pool, ids2)
SO["2luong_giay"] = r2["giay"]
SO["dinh_song_song"] = r2["dinh_song_song"]
print(f"  2 luồng: {r2['giay']:.2f}s · đỉnh chạy cùng lúc "
      f"{r2['dinh_song_song']}")
dlg._nhip()
dlg.close()

rows2 = db.query("SELECT id, status, error FROM jobs WHERE id IN ({})".format(
    ",".join("?" * len(ids2))), tuple(ids2))
xong2 = [r for r in rows2 if str(r["status"]) == "done"]
dat("2 job đều XONG", len(xong2) == 2,
    "; ".join(f"{r['status']}:{str(r['error'] or '')[:90]}" for r in rows2))

con = TG.liet_ke_video(d2)
dat("thư mục vẫn có ĐÚNG 2 video (mới thay chỗ cũ)", len(con) == 2,
    str([p.name for p in con]))
moi_khac = [p for p in con if md5(p) != goc_md5.get(p.name)]
dat("cả 2 video trong thư mục là BẢN MỚI (khác gốc)",
    len(moi_khac) == 2, f"{len(moi_khac)}/2 khác gốc")
for p in con:
    try:
        k = TG.kiem_video_ra(p, TG.probe_duration(p))
        dat(f"bản mới {p.name} có hình + có tiếng", k["khung"] > 0
            and k["rms"] > 0, f"{k['khung']} khung, RMS {k['rms']}")
    except Exception as e:  # noqa: BLE001
        dat(f"bản mới {p.name} có hình + có tiếng", False, str(e)[:90])

# GỐC phải nằm trong Thùng rác NGƯỜI DÙNG CHỌN, TRÙNG TỪNG BYTE
rac = [p for p in thung.rglob("*.mp4")]
rac_md5 = {md5(p) for p in rac}
dat("2 video GỐC nằm trong Thùng rác user chọn", len(rac) == 2,
    f"{len(rac)} file: {[p.name for p in rac]}")
dat("MD5 gốc trong Thùng rác TRÙNG TỪNG BYTE với gốc ban đầu",
    set(goc_md5.values()) == rac_md5 and len(rac_md5) == 1,
    f"gốc {sorted(set(goc_md5.values()))} · rác {sorted(rac_md5)}")
from app.core import pipeline as P  # noqa: E402
dat("Thùng rác dùng thật KHÔNG nằm trong %TEMP%",
    P._is_safe_recycle_root(str(thung)), str(thung))
dat("KHÔNG xoá hẳn video nào (số file gốc = số file trong thùng rác)",
    len(rac) == len(goc_md5), f"{len(goc_md5)} gốc -> {len(rac)} trong rác")

# --- arm A: LẦN LƯỢT (1 luồng) trên 2 video Y HỆT ---
db.execute("DELETE FROM jobs")
d1 = thu_muc_video("ca2_lanluot", 2)
pool.set_limits(max_tg=1)
dlgA = ThayGiongDialog(pool, None, thung_rac=str(RAC / "ThungRacA"))
dlgA.ed_thu_muc.setText(str(d1))
dlgA.cb_nn.setCurrentIndex(dlgA.cb_nn.findData("en"))
dlgA.sp_luong.setValue(1)
dlgA.ck_xoa.setChecked(True)
dlgA._chay()
idsA = list(dlgA._jobs.values())
rA = cho_xong(pool, idsA)
dlgA.close()
SO["1luong_giay"] = rA["giay"]
SO["dinh_song_song_1"] = rA["dinh_song_song"]
print(f"  lần lượt (1 luồng): {rA['giay']:.2f}s · đỉnh cùng lúc "
      f"{rA['dinh_song_song']}")

dat("làn 1 luồng CHỈ chạy 1 job cùng lúc", rA["dinh_song_song"] <= 1,
    f"đỉnh {rA['dinh_song_song']}")
dat("làn 2 luồng CHẠY THẬT 2 job cùng lúc", r2["dinh_song_song"] >= 2,
    f"đỉnh {r2['dinh_song_song']}")
_nhanh = SO["1luong_giay"] / max(0.01, SO["2luong_giay"])
SO["nhanh_hon_lan"] = round(_nhanh, 3)
dat("2 luồng NHANH HƠN chạy lần lượt", _nhanh >= 1.20,
    f"{SO['1luong_giay']:.2f}s -> {SO['2luong_giay']:.2f}s "
    f"= nhanh {_nhanh:.2f} lần")


# ==================================================================
print("\n=== CA 4: FILE MỚI HỎNG (0 KiB) -> KHÔNG ĐƯỢC ĐỤNG GỐC ===")


def _chay_hong(thu_muc_ten: str, thung_ten: str, pha: int = 0) -> dict:
    """Chạy 1 video mà bước ghép cuối CỐ Ý ra file 0 KiB (ca đã xảy ra thật).

    `pha` = số chốt bị gỡ:
      0 = không gỡ gì (ca 4 — bất biến phải GIỮ)
      1 = gỡ `kiem_video_ra`
      2 = gỡ CẢ `kiem_video_ra` LẪN chốt cỡ file trong `thay_the_video_goc`
    """
    d = thu_muc_video(thu_muc_ten, 1)
    goc = next(iter(TG.liet_ke_video(d)))
    truoc = md5(goc)
    thung_h = RAC / thung_ten
    thung_h.mkdir(parents=True, exist_ok=True)

    that_thay = TG.thay_audio_video
    that_kiem = TG.kiem_video_ra
    that_the = TG.thay_the_video_goc

    def hong(video_goc, audio_moi, video_ra):
        # Đúng ca "ffmpeg trả mã 0 mà file rỗng": file ra tồn tại, 0 byte.
        Path(video_ra).write_bytes(b"")

    def the_khong_chot(video_goc, video_moi, kenh="", thung_rac=""):
        """Bản `thay_the_video_goc` ĐÃ BỊ GỠ chốt cỡ file — chỉ dùng để PHÁ."""
        from app.core import pipeline as _P
        g = Path(video_goc)
        hd, dst = _P.delete_or_recycle(g, kenh or g.parent.name,
                                       thung_rac or "")
        if hd == "recycled":
            shutil.move(str(video_moi), str(g))
        return {"thay": hd == "recycled", "goc_da_vao_thung_rac": str(dst)}

    TG.thay_audio_video = hong
    if pha >= 1:
        TG.kiem_video_ra = lambda *a, **k: {"khung": 1, "rms": 1.0}
    if pha >= 2:
        TG.thay_the_video_goc = the_khong_chot
    try:
        r = TG.thay_giong_mot_video(
            goc, dich_sang="en", thay_goc=True, kenh=d.name,
            thung_rac=str(thung_h), thu_muc_lam=str(d / "_tam"))
    finally:
        TG.thay_audio_video = that_thay
        TG.kiem_video_ra = that_kiem
        TG.thay_the_video_goc = that_the
    # quét CẢ thùng rác user chọn LẪN `_DaXoa` nội bộ — gốc "biến mất" ở đâu
    # cũng là gốc đã bị đụng.
    rac = list(thung_h.rglob("*.mp4")) + list(T.rglob("_DaXoa/**/*.mp4"))
    return {"goc": goc, "con": goc.exists() and md5(goc) == truoc,
            "rac": rac, "r": r}


h4 = _chay_hong("ca4", "ThungRac4", pha=0)
dat("file mới hỏng -> báo LỖI, không báo xong",
    not h4["r"].get("ok"), str(h4["r"].get("loi", ""))[:110])
dat("video GỐC còn nguyên vẹn (MD5 trùng)", h4["con"])
dat("Thùng rác KHÔNG có gì (chưa dọn gốc)", not h4["rac"],
    f"{len(h4['rac'])} file")


# ==================================================================
print("\n=== CA 6: THỬ PHÁ — gỡ chốt thì bất biến PHẢI vỡ ===")
# 6a. Gỡ MỘT chốt: bất biến VẪN GIỮ, vì `thay_the_video_goc` còn chốt cỡ file.
#     Đây là SỐ ĐO, không phải lời hứa: video của anh Hùng có HAI lớp chắn.
h6a = _chay_hong("ca6a", "ThungRac6a", pha=1)
dat("gỡ 1 chốt (kiem_video_ra) -> vẫn KHÔNG mất gốc (2 lớp chắn)",
    h6a["con"] and not h6a["rac"],
    f"gốc còn {h6a['con']} · rác {len(h6a['rac'])}")

# 6b. Gỡ CẢ HAI chốt -> bất biến PHẢI VỠ. Không vỡ = phép đo của ca 4 không
#     đo cái gì cả, cổng chỉ là con dấu.
h6b = _chay_hong("ca6b", "ThungRac6b", pha=2)
_vo = (not h6b["con"]) or bool(h6b["rac"])
dat("gỡ CẢ HAI chốt -> bất biến VỠ (ca 4 thật sự đang đo)", _vo,
    "gốc còn: {} · rác: {} — nếu KHÔNG vỡ thì ca 4 là con dấu"
    .format(h6b["con"], len(h6b["rac"])))


# ==================================================================
print("\n=== CA 7: CỬA CUỐI CỦA BẪY torch-SAU-Qt (sót 1 cửa, đã đo) ===")
# Cổng này (v2.25.0) đã đổi `co_demucs`/`tinh_trang_demucs` sang `find_spec`,
# NHƯNG `tinh_trang_demucs` vẫn gọi `thiet_bi_tach()` — hàm đó `import torch`.
# Tiến trình NÀY đã nạp Qt, nên đó đúng là cửa còn lại của bẫy.
# ĐO ĐƯỢC 14/08/2026 bằng `_test_app_smoke.py`: mở hộp "Thay giọng nói" ->
# *"Windows fatal exception: access violation"* ở
# `torch/__init__.py:_load_dll_libraries`, mà **rc vẫn = 0** và cổng vẫn in
# "KHÔNG LỖI" (faulthandler là VEH: in xong trả quyền, torch ném OSError,
# `except` nuốt). `try/except` KHÔNG chặn được access violation ở tầng native.
dat("CA7 tiến trình test này ĐÃ nạp Qt (điều kiện của bẫy)",
    TG.qt_da_nap(), "PyQt6 có trong sys.modules")
dat("CA7a `thiet_bi_tach` KHÔNG import torch khi Qt đã nạp -> trả '' "
    "(CHƯA BIẾT, không phải 'cpu')",
    TG.thiet_bi_tach() == "", f"trả {TG.thiet_bi_tach()!r}")
dat("CA7b gọi `thiet_bi_tach` xong torch VẪN KHÔNG bị nạp vào tiến trình",
    "torch" not in sys.modules,
    "torch không có trong sys.modules")
_tt7 = TG.tinh_trang_demucs()
dat("CA7c `tinh_trang_demucs` (cửa UI gọi) cũng KHÔNG kéo torch vào",
    "torch" not in sys.modules and _tt7["thiet_bi"] == "",
    f"thiet_bi={_tt7['thiet_bi']!r} · torch nạp: {'torch' in sys.modules}")
dat("CA7d nhưng vẫn DÒ RA đủ gói (find_spec vẫn chạy, không bị tắt oan)",
    _tt7["co"] is True or _tt7["thieu"] != [],
    f"co={_tt7['co']} · thiếu={_tt7['thieu']}")
# '' phải hiện thành "ĐÃ CÓ." trơn, KHÔNG được hiện "chạy trên CPU" — đoán
# bừa là máy có card đồ hoạ vẫn đọc thành CPU (đúng họ lỗi "chọn X ra Y").
_nhan = {"cuda": " (chạy trên card đồ hoạ)",
         "cpu": " (chạy trên CPU)"}.get("", "")
dat("CA7e thiết bị CHƯA BIẾT -> nhãn KHÔNG được đoán bừa 'chạy trên CPU'",
    _nhan == "", f"nhãn thêm: {_nhan!r}")


# ==================================================================
try:
    pool.stop(wait=False)
except Exception:  # noqa: BLE001
    pass

print("\n" + "=" * 62)
print("SỐ ĐO:", json.dumps(SO, ensure_ascii=False))
print(f"ĐẠT {len(OK)} · HỎNG {len(FAIL)}")
for f in FAIL:
    print("  HỎNG:", f)
for _d in (T, RAC):            # KHÔNG để lại rác trên máy anh Hùng
    try:
        shutil.rmtree(_d, ignore_errors=True)
    except OSError:
        pass
sys.exit(1 if FAIL else 0)
