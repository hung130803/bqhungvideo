# -*- coding: utf-8 -*-
"""CỔNG 57 — BẢNG TIẾN ĐỘ SỐNG · THƯ MỤC VÀO/RA · NHỚ VIDEO ĐÃ XONG.

Anh Hùng dùng thật v2.26.0 và báo 4 lỗi (nguyên văn):
  · *"load file rồi ấn chạy thì nó chỉ hiện ở dưới cái thanh tiến trình, không
    hiện gì cả, xong hay gì cũng không báo, hay đang phân tích như nào cũng
    không thấy"*
  · *"cho tôi tự chọn thư mục ĐẦU VÀO thư mục ĐẦU RA đi, KHÔNG CẦN cái thùng
    rác phân tích thay giọng rồi tự xoá đâu nhé"*
  · *"nếu cái nào phân tích thay lỗi phải có mục CHẠY LẠI"*
  · *"ấn chạy chỉ chạy những video CHƯA chạy xong thôi"*

CỔNG NÀY ĐO 7 ĐIỀU:
  1. Bấm Chạy -> bảng hiện ĐỦ DÒNG NGAY (kể cả video chưa tới lượt), trạng
     thái đổi qua TỪNG BƯỚC THẬT — đo bằng cách BẮT TÍN HIỆU `doi_trang_thai`,
     không phải nhìn bằng mắt.
  2. Thư mục đích nhận file mới · thư mục nguồn KHÔNG mất file nào (đếm file +
     so MD5 từng byte).
  3. Nguồn trùng đích -> CẢNH BÁO + xếp 0 job (không im lặng ghi đè).
  4. Chạy lần 2 -> video ĐÃ XONG bị bỏ qua (0 job), video LỖI thì CHẠY LẠI.
  5. Chuột phải "Làm lại video này" -> xếp ĐÚNG 1 job cho ĐÚNG video đó.
  6. Sổ trạng thái SỐNG SÓT qua khởi động lại (đọc lại bằng TIẾN TRÌNH KHÁC).
  7. THỬ PHÁ: gỡ chốt "bỏ qua video đã xong" -> mục 4 PHẢI VỠ. Không vỡ thì
     cổng này chỉ là con dấu.

THÀNH PHẦN THẬT: `WorkerPool` thật · DB thật (sandbox) · Qt thật (offscreen) ·
`app/queue/jobs.py:_thay_giong` thật · `tg_so`/`tg_chay` thật.
Chỗ DUY NHẤT thay: `thay_giong.thay_giong_mot_video` (6 bước audio) — cổng 53
và 55 đã đo phần đó bằng Demucs + Groq + edge-tts THẬT, ở đây mà chạy lại thì
mỗi lượt hàng phút và ĐỎ OAN theo mạng. Bản giả **phát lại ĐÚNG các mốc tiến
trình đọc từ chính mã nguồn `thay_giong.py`** (xem `_buoc_that`), nên phép đo
"trạng thái đổi theo bước THẬT" không bị lệch khi mã đổi.

    .venv\\Scripts\\python _test_tg_bang_tiendo.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = str(Path(__file__).resolve().parent)   # KHÔNG ghi cứng đường repo
sys.path.insert(0, REPO)

T = Path(tempfile.mkdtemp(prefix="tgbang_"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_DB_PATH"] = str(T / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(T / "settings.ini")  # KHÔNG chạm registry
os.environ["BQ_FFMPEG_SLOTS"] = "1"       # máy anh Hùng đang chạy việc thật

import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát

# cv2 (app.queue.jobs -> app.core.analysis) phải nạp TRƯỚC Qt — bài học guard.
import app.queue.jobs as _JOBS  # noqa: E402,F401
from app.core import tg_chay, tg_so  # noqa: E402
from app.core import thay_giong as TG  # noqa: E402
from app.database import db  # noqa: E402
from app.queue.worker import WorkerPool  # noqa: E402

from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

CANH_BAO: list = []          # mọi QMessageBox.warning bị chặn
BAO_XONG: list = []          # mọi QMessageBox.information bị chặn


def _ghi_canh_bao(*a, **k):
    CANH_BAO.append(" | ".join(str(x)[:200] for x in a[1:3]))
    return 0


def _ghi_bao(*a, **k):
    BAO_XONG.append(" | ".join(str(x)[:400] for x in a[1:3]))
    return 0


QMessageBox.exec = lambda self: 0                       # type: ignore
QMessageBox.warning = staticmethod(_ghi_canh_bao)       # type: ignore
QMessageBox.information = staticmethod(_ghi_bao)        # type: ignore
QMessageBox.critical = staticmethod(lambda *a, **k: 0)  # type: ignore
QMessageBox.question = staticmethod(                    # "Làm lại tất cả" -> Có
    lambda *a, **k: QMessageBox.StandardButton.Yes)     # type: ignore

_app = QApplication.instance() or QApplication([])
from app.ui import theme  # noqa: E402
_app.setStyleSheet(theme.QSS)          # QSS THẬT (bài học cổng 9)
from app.ui.thay_giong_dialog import CHU_DA_XONG, ThayGiongDialog  # noqa: E402

OK: list[str] = []
FAIL: list[str] = []
SO: dict = {}


def dat(dieu: str, ok: bool, chi_tiet: str = "") -> None:
    (OK if ok else FAIL).append(f"{dieu} {chi_tiet}".strip())
    print(f"  [{'ĐẠT' if ok else 'HỎNG'}] {dieu}"
          + (f" — {chi_tiet}" if chi_tiet else ""))


def md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for k in iter(lambda: fh.read(1 << 20), b""):
            h.update(k)
    return h.hexdigest()


def anh_thu_muc(d: Path) -> dict:
    """{tên file: md5} của MỌI file trong thư mục (kể cả thư mục con)."""
    return {str(p.relative_to(d)): md5(p) for p in sorted(d.rglob("*"))
            if p.is_file()}


# ==================================================================
# BƯỚC THẬT — đọc thẳng từ mã nguồn `thay_giong_video`
# ==================================================================
def _buoc_that() -> list:
    """[(tiến trình, lời nhắn)] của 8 bước, LẤY TỪ CHÍNH `thay_giong.py`.

    Vì sao không chép tay: chép tay là cổng đo bản chữ CŨ — mã đổi lời nhắn
    thì bảng tiến độ ngoài đời hiện sai mà cổng vẫn xanh (đúng họ bẫy "phép đo
    phát chứng nhận cho thứ đang hỏng").
    """
    ma = Path(REPO, "app/core/thay_giong.py").read_text(encoding="utf-8")
    i = ma.index("def thay_giong_video(")
    j = ma.index("\ndef ", i + 10)
    than = ma[i:j]
    ra = []
    for p, m in re.findall(r'prog\((0\.\d+),\s*f?"([^"]*)"', than):
        # f-string kiểu "Dịch {len(cau)} câu..." -> thay ô ngoặc bằng số thật
        ra.append((float(p), re.sub(r"\{[^}]*\}", "12", m)))
    return ra


BUOC = _buoc_that()
NHIP = 0.30            # giây mỗi bước — đủ để nhịp bảng (0,04s) bắt được


# ==================================================================
# BẢN GIẢ CỦA 6 BƯỚC AUDIO (cổng 53/55 đã đo phần thật)
# ==================================================================
HONG: set = set()          # tên file phải LỖI ở bước cuối
DA_GOI: list = []          # ghi lại tham số handler truyền xuống


def gia_thay_giong(video_in, dich_sang="en", voice="", cach_tach="auto",
                   thay_goc=True, kenh="", thung_rac="", thu_muc_lam="",
                   on_progress=None):
    v = Path(video_in)
    DA_GOI.append({"video": str(v), "thay_goc": bool(thay_goc),
                   "thung_rac": str(thung_rac or ""),
                   "thu_muc_lam": str(thu_muc_lam or "")})
    tam = Path(thu_muc_lam) if thu_muc_lam else v.parent
    tam.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    for p, m in BUOC:
        if on_progress:
            on_progress(p, m)          # có thể ném HuyBo -> để nó nổi lên
        time.sleep(NHIP)
    if v.name in HONG:
        return {"ok": False, "vao": str(v),
                "loi": "RuntimeError: ffmpeg ra file 0 KiB",
                "giay_tong": round(time.time() - t0, 2)}
    ra = tam / f"{v.stem}__thaygiong{v.suffix}"
    ra.write_bytes(b"MOI" + os.urandom(20000))
    return {"ok": True, "vao": str(v), "ra": str(ra), "do_dai": 12.0,
            "giay_tong": round(time.time() - t0, 2),
            "kiem": {"khung": 300, "rms": 0.09},
            "tach": {"cach": "demucs"}, "khop": {}, "dich": {}}


TG.thay_giong_mot_video = gia_thay_giong          # type: ignore
TG.chot_co_bo_tach_giong = lambda *a, **k: None   # máy nào cũng chạy được cổng
TG.tinh_trang_demucs = lambda: {                  # type: ignore
    "co": True, "thieu": [], "lib": str(T / "_lib"), "thiet_bi": "",
    "cai_duoc": True, "loi_nhan": ""}


def video_gia(d: Path, ten: str) -> Path:
    p = d / ten
    p.write_bytes(b"GOC" + os.urandom(30000))
    return p


def cho_xong(dlg, han: float = 120.0) -> float:
    """Đợi mọi job của hộp kết thúc, VỪA ĐỢI VỪA chạy nhịp bảng như app thật."""
    t0 = time.time()
    while time.time() - t0 < han:
        _app.processEvents()
        dlg._nhip()
        ids = list(dlg._jobs.values())
        if not ids:
            break
        rows = db.query(
            "SELECT status FROM jobs WHERE id IN ({})".format(
                ",".join("?" * len(ids))), tuple(ids))
        tt = [str(r["status"]) for r in rows]
        if tt and all(s in ("done", "failed", "canceled") for s in tt):
            dlg._nhip()
            break
        time.sleep(0.04)
    return round(time.time() - t0, 2)


# ==================================================================
print("=== DỰNG SÂN: 3 video giả + bộ điều phối THẬT ===")
print(f"  {len(BUOC)} mốc tiến trình đọc từ thay_giong.py: "
      + " · ".join(f"{p:.2f} {m[:22]}" for p, m in BUOC[:4]) + " ...")
NGUON = T / "kho_video"
NGUON.mkdir(parents=True, exist_ok=True)
V1 = video_gia(NGUON, "video_1.mp4")
V2 = video_gia(NGUON, "video_2.mp4")
V3 = video_gia(NGUON, "video_3.mp4")
DICH = T / "da_thay_tieng"
ANH_NGUON = anh_thu_muc(NGUON)

db.execute("DELETE FROM jobs")
pool = WorkerPool({}, max_cpu=1, max_gpu=1, max_tg=2)
pool.start()

HONG.add("video_3.mp4")          # video 3 CỐ Ý lỗi ở lượt đầu

dlg = ThayGiongDialog(pool, None)
dlg.ed_thu_muc.setText(str(NGUON))
dlg.ed_thu_muc_ra.setText(str(DICH))

# bắt TÍN HIỆU thay cho nhìn bằng mắt
CHUOI: dict = {}
dlg.doi_trang_thai.connect(
    lambda d, tt, p: CHUOI.setdefault(d, []).append(tt))
TONG_KET: list = []
dlg.xong_ca_luot.connect(
    lambda a, b, c, e: TONG_KET.append((a, b, c, e)))


# ==================================================================
print("\n=== NHÃN KHÔNG EMOJI (máy anh Hùng thiếu font -> Ô ĐEN) ===")
# Chỉ soi NHÃN NÚT + tiêu đề cột + nhãn chữ (bài học cổng 27: soi cả file thì
# emoji trong dòng ghi chú cũng bị kể, FAIL OAN).
import unicodedata  # noqa: E402

from PyQt6.QtWidgets import QLabel, QPushButton  # noqa: E402


def _co_emoji(s: str) -> bool:
    return any(ord(c) > 0xFFFF or unicodedata.category(c) == "So"
               for c in s or "")


_nhan = [w.text() for w in dlg.findChildren(QPushButton)]
_nhan += [w.text() for w in dlg.findChildren(QLabel)]
_nhan += [dlg.bang.horizontalHeaderItem(c).text()
          for c in range(dlg.bang.columnCount())]
_xau = [x for x in _nhan if _co_emoji(x)]
dat(f"KHÔNG nhãn nào có emoji ({len(_nhan)} nhãn)", not _xau, str(_xau))
dat("có đủ 2 ô thư mục + 2 nút chọn",
    any("nguồn" in x.lower() for x in _nhan)
    and any("đích" in x.lower() for x in _nhan),
    str([x for x in _nhan if "thư mục" in x.lower()])[:120])


print("\n=== CỔNG 1: BẢNG HIỆN ĐỦ DÒNG NGAY + ĐỔI THEO TỪNG BƯỚC ===")
dat("bảng liệt kê đủ 3 video NGAY khi chọn thư mục (chưa bấm gì)",
    dlg.bang.rowCount() == 3, f"{dlg.bang.rowCount()} dòng")
so_job = dlg._chay()
dat("bấm Chạy xếp đúng 3 job", so_job == 3, f"{so_job} job")
_o = [dlg.bang.item(r, 1).text() for r in range(dlg.bang.rowCount())]
dat("NGAY sau khi bấm Chạy: đủ 3 dòng có trạng thái (không dòng nào trống)",
    len(_o) == 3 and all(x.strip() for x in _o), " · ".join(_o))
dat("video chưa tới lượt vẫn hiện 'Đang chờ' (không phải trống)",
    _o.count("Đang chờ") >= 1, " · ".join(_o))
_tt0 = [dlg.bang.item(r, 2).text() for r in range(dlg.bang.rowCount())]
dat("cột Tiến trình có % + bước NGAY từ đầu", all("%" in x for x in _tt0),
    " · ".join(_tt0))

giay = cho_xong(dlg)
SO["luot1_giay"] = giay
print(f"  lượt 1 xong sau {giay}s · {len(CHUOI)} video có chuỗi trạng thái")
for d, ds in CHUOI.items():
    print(f"    {Path(d).name}: " + " -> ".join(ds))

# Bảng tra bước phải nhận ĐÚNG 8 mốc thật, KHÔNG nhãn nào bị nuốt. Lỗi đã bắt
# được ở lượt đầu: lời nhắn bước 5 *"Đọc bản dịch..."* CHỨA chữ "dịch" nên bị
# gán thành "Đang dịch" -> bảng không bao giờ hiện "Đang đọc".
_nhan_moc = [tg_so.buoc_tu_tien_trinh(p, m) for p, m in BUOC]
_so_buoc = [b for _n, b, _t in _nhan_moc]
dat("8 mốc THẬT trong mã -> 8 bước ĐÚNG THỨ TỰ, không bước nào bị nuốt",
    _so_buoc == sorted(_so_buoc) and len(set(_so_buoc)) >= 8,
    " · ".join(f"{m[:16]}->{n}" for (n, _b, _t), (_p, m)
               in zip(_nhan_moc, BUOC)))

_can = ("Đang tách giọng", "Đang chép lời", "Đang dịch", "Đang đọc",
        "Đang ghép")
_tat = set()
for ds in CHUOI.values():
    _tat |= set(ds)
SO["so_trang_thai_bat_duoc"] = len(_tat)
dat("bắt được ĐỦ các bước THẬT qua tín hiệu (tách/chép/dịch/đọc/ghép)",
    all(x in _tat for x in _can),
    "thiếu: " + str([x for x in _can if x not in _tat]) or "đủ")
_c1 = CHUOI.get(str(V1), [])
dat("một video đi từ 'Đang chờ' -> nhiều bước -> 'Xong'",
    _c1[:1] == ["Đang chờ"] and _c1[-1:] == ["Xong"] and len(_c1) >= 5,
    " -> ".join(_c1))
dat("video LỖI có trạng thái 'Lỗi'", CHUOI.get(str(V3), [])[-1:] == ["Lỗi"],
    " -> ".join(CHUOI.get(str(V3), [])))
_ghi3 = dlg.bang.item(dlg._dong_theo_duong(str(V3)), 3).text()
dat("cột Ghi chú của video lỗi là LÝ DO ĐỌC HIỂU (không phải mã lỗi thô)",
    "ffmpeg" not in _ghi3.lower() or "RuntimeError" not in _ghi3, _ghi3)
dat("XONG CẢ LƯỢT có dòng tổng kết (tín hiệu xong_ca_luot)",
    TONG_KET == [(2, 1, 0, 0)], str(TONG_KET))
dat("dòng tổng kết ghi rõ mấy xong / mấy lỗi",
    "2 video xong" in dlg.lb_tt.text() and "1 lỗi" in dlg.lb_tt.text(),
    dlg.lb_tt.text())
dat("có hộp BÁO XONG cho anh Hùng (không im lặng)",
    any("XONG CẢ LƯỢT" in x for x in BAO_XONG),
    (BAO_XONG[-1][:90] if BAO_XONG else "không có"))


# ==================================================================
print("\n=== CỔNG 2: ĐÍCH NHẬN FILE MỚI · NGUỒN KHÔNG MẤT FILE NÀO ===")
anh_sau = anh_thu_muc(NGUON)
dat("thư mục NGUỒN: không mất/không đổi file nào (MD5 từng byte)",
    all(anh_sau.get(k) == v for k, v in ANH_NGUON.items()),
    f"{len(ANH_NGUON)} file gốc · còn "
    f"{sum(1 for k, v in ANH_NGUON.items() if anh_sau.get(k) == v)}")
dat("thư mục NGUỒN: không đẻ thêm file rác nào",
    set(anh_sau) == set(ANH_NGUON),
    "thêm: " + str(sorted(set(anh_sau) - set(ANH_NGUON))))
ra_moi = sorted(p.name for p in DICH.glob("*.mp4"))
dat("thư mục ĐÍCH nhận đúng 2 video mới, GIỮ NGUYÊN tên gốc",
    ra_moi == ["video_1.mp4", "video_2.mp4"], str(ra_moi))
dat("video ở đích là BẢN MỚI (khác gốc từng byte)",
    md5(DICH / "video_1.mp4") != ANH_NGUON["video_1.mp4"])
dat("KHÔNG job nào đi đường xoá gốc (thay_goc=False ở MỌI lượt gọi)",
    DA_GOI and all(g["thay_goc"] is False for g in DA_GOI),
    f"{len(DA_GOI)} lượt gọi")
dat("KHÔNG job nào được truyền Thùng rác",
    all(not g["thung_rac"] for g in DA_GOI))
dat("thư mục làm việc tạm nằm trong ĐÍCH, không nằm cạnh video gốc",
    all(str(DICH) in g["thu_muc_lam"] for g in DA_GOI),
    DA_GOI[0]["thu_muc_lam"][-60:])
dat("dọn sạch thư mục tạm sau khi xong",
    not (DICH / TG.TEN_THU_MUC_TAM / "video_1").exists(),
    str(list((DICH / TG.TEN_THU_MUC_TAM).glob("*"))[:3]))


# ==================================================================
print("\n=== CỔNG 3: NGUỒN TRÙNG ĐÍCH -> CẢNH BÁO, KHÔNG GHI ĐÈ ===")
_truoc = len(CANH_BAO)
_anh_truoc = anh_thu_muc(NGUON)
dlg.ed_thu_muc_ra.setText(str(NGUON))          # cố ý trỏ đích = nguồn
dat("hộp NHẬN RA hai thư mục trùng nhau", dlg.trung_thu_muc() is True)
dat("nhãn cảnh báo hiện ngay dưới ô (không đợi bấm Chạy)",
    "TRÙNG" in dlg.lb_dich.text(), dlg.lb_dich.text()[:80])
_n = dlg._chay()
dat("bấm Chạy khi trùng -> xếp 0 job", _n == 0, f"{_n} job")
dat("có CẢNH BÁO bật lên (không im lặng ghi đè)", len(CANH_BAO) > _truoc,
    CANH_BAO[-1][:90] if CANH_BAO else "không có")
dat("thư mục nguồn KHÔNG bị đụng khi trùng",
    anh_thu_muc(NGUON) == _anh_truoc)
# đích để TRỐNG -> phải tự lấy <nguồn>\_da_thay_tieng, và KHÔNG còn coi là trùng
dlg.ed_thu_muc_ra.setText("")
dat("để trống ô đích -> tự dùng <nguồn>\\_da_thay_tieng",
    dlg.thu_muc_dich() == tg_so.thu_muc_dich_mac_dinh(str(NGUON)),
    dlg.thu_muc_dich())
dat("mặc định đó KHÔNG bị coi là trùng nguồn", dlg.trung_thu_muc() is False)
dlg.ed_thu_muc_ra.setText(str(DICH))


# ==================================================================
print("\n=== CỔNG 4: CHẠY LẦN 2 -> XONG THÌ BỎ QUA, LỖI THÌ LÀM LẠI ===")
CHUOI.clear()
TONG_KET.clear()
HONG.clear()                                   # lần này video 3 chạy được
_n2 = dlg._chay()
SO["job_luot2"] = _n2
dat("chạy lần 2 chỉ xếp job cho video LỖI (1 job, không phải 3)",
    _n2 == 1, f"{_n2} job")
_xep = [dlg._duong_theo_job(j) for j in dlg._jobs.values()]
dat("job đó đúng là video_3 (video lỗi)", _xep == [str(V3)],
    str([Path(x).name for x in _xep]))
_bo = [dlg.bang.item(r, 1).text() for r in range(dlg.bang.rowCount())
       if dlg._duong_dong(r) in (str(V1), str(V2))]
dat("2 video đã xong hiện rõ 'Đã xong — bỏ qua' (không im lặng)",
    _bo == [CHU_DA_XONG, CHU_DA_XONG], " · ".join(_bo))
cho_xong(dlg)
dat("video lỗi chạy lại thành công -> đích có đủ 3 video",
    sorted(p.name for p in DICH.glob("*.mp4"))
    == ["video_1.mp4", "video_2.mp4", "video_3.mp4"],
    str(sorted(p.name for p in DICH.glob("*.mp4"))))
dat("tổng kết lượt 2 ghi rõ số bỏ qua", TONG_KET == [(1, 0, 0, 2)],
    str(TONG_KET))


# ==================================================================
print("\n=== CỔNG 5: CHUỘT PHẢI 'LÀM LẠI VIDEO NÀY' ===")
CHUOI.clear()
_n3 = dlg._lam_lai_mot(str(V1))
SO["job_lam_lai_mot"] = _n3
dat("làm lại 1 video -> xếp ĐÚNG 1 job", _n3 == 1, f"{_n3} job")
_xep3 = [dlg._duong_theo_job(j) for j in dlg._jobs.values()]
dat("job đó đúng là video_1 (video được chọn)", _xep3 == [str(V1)],
    str([Path(x).name for x in _xep3]))
_pl = db.query_one("SELECT payload FROM jobs WHERE id=?",
                   (list(dlg._jobs.values())[0],))
_p = json.loads(_pl["payload"])
dat("payload job trỏ ĐÚNG video + ĐÚNG thư mục đích",
    _p["video"].lower() == str(V1).lower()
    and Path(_p["thu_muc_ra"]) == DICH, f"{Path(_p['video']).name}")
cho_xong(dlg)
dat("làm lại xong: đích vẫn đủ 3 video (ghi đè bản cũ, không đẻ tên lạ)",
    sorted(p.name for p in DICH.glob("*.mp4"))
    == ["video_1.mp4", "video_2.mp4", "video_3.mp4"],
    str(sorted(p.name for p in DICH.glob("*.mp4"))))
dat("thư mục nguồn VẪN không mất file nào sau 3 lượt chạy",
    anh_thu_muc(NGUON) == ANH_NGUON,
    f"{len(ANH_NGUON)} file")

# chuột phải "Bỏ qua video này"
dlg._bo_qua_mot(str(V2))
_n4 = dlg._chay()
dat("'Bỏ qua video này' -> lượt Chạy sau xếp 0 job cho video đó", _n4 == 0,
    f"{_n4} job")
# Trả video_2 về đúng sự thật cho các mục sau: nó ĐÃ XONG ở lượt 1 và bản mới
# đang nằm trong thư mục đích. (Dùng `xoa` ở đây là biến nó thành "chưa chạy"
# -> mục 7 đo nhầm.)
tg_so.ghi(str(V2), tg_so.XONG, ra=str(DICH / "video_2.mp4"))


# ==================================================================
print("\n=== CỔNG 6: SỔ SỐNG SÓT QUA KHỞI ĐỘNG LẠI ===")
so_file = tg_so.duong_so()
dat("sổ được GHI RA ĐĨA (không chỉ nằm trong RAM)", so_file.exists(),
    str(so_file.name) + f" · {so_file.stat().st_size if so_file.exists() else 0} byte")
# (a) giả lập tắt app trong cùng tiến trình: xoá sạch bộ nhớ đệm rồi đọc lại
tg_so._NHO.clear()
tg_so._DA_NAP = False
tg_so._MTIME = -1.0
dat("(a) xoá sạch bộ nhớ đệm -> đọc lại đĩa vẫn nhớ video đã xong",
    tg_so.da_xong(str(V1)) and tg_so.da_xong(str(V3)))
# (b) TIẾN TRÌNH KHÁC HẲN (đúng cảnh tắt app / app tự cập nhật rồi mở lại)
_ma = (
    "import os,sys,json\n"
    f"sys.path.insert(0, r'{REPO}')\n"
    f"os.environ['BQ_DATA_DIR']=r'{T}'\n"
    f"os.environ['BQ_DB_PATH']=r'{T / 'studio.db'}'\n"
    "from app.core import tg_so\n"
    "print(json.dumps({'v1': tg_so.da_xong(r'''" + str(V1) + "'''),"
    " 'v3': tg_so.da_xong(r'''" + str(V3) + "'''),"
    " 'can_chay_v1': tg_so.can_chay(r'''" + str(V1) + "''')}))\n"
)
_r = subprocess.run([sys.executable, "-c", _ma], capture_output=True,
                    text=True, timeout=180)
_dong = [x for x in (_r.stdout or "").splitlines() if x.startswith("{")]
_kq = json.loads(_dong[-1]) if _dong else {}
dat("(b) TIẾN TRÌNH KHÁC mở sổ lên vẫn nhớ 'đã xong'",
    _kq.get("v1") is True and _kq.get("v3") is True,
    json.dumps(_kq, ensure_ascii=False) or (_r.stderr or "")[-200:])
dat("(b) tiến trình khác cũng kết luận KHÔNG cần chạy lại",
    _kq.get("can_chay_v1") is False, str(_kq.get("can_chay_v1")))
# Đổi FILE rồi tra lại -> phải coi là CHƯA LÀM. Làm trên video RIÊNG (không
# đụng V1/V3): đổi mtime của video trong bảng là làm hỏng phép đo của mục 7.
_KHAC = T / "kiem_khoa"
_KHAC.mkdir(parents=True, exist_ok=True)
VK = video_gia(_KHAC, "kiem_khoa.mp4")
tg_so.ghi(str(VK), tg_so.XONG, ra="giả")
dat("video vừa ghi 'xong' -> không cần chạy lại",
    tg_so.can_chay(str(VK)) is False)
VK.write_bytes(b"KHAC" + os.urandom(30000))
dat("thay file khác cùng tên vào -> sổ coi là CHƯA LÀM (khoá có cỡ+mtime)",
    tg_so.can_chay(str(VK)) is True)


# ==================================================================
print("\n=== CỔNG 7: THỬ PHÁ — gỡ chốt 'bỏ qua video đã xong' ===")
# Anh Hùng dặn: bỏ chốt thì mục 4 PHẢI VỠ (vẫn xanh = cổng 4 chỉ là con dấu).
# CÓ HAI LỚP CHẮN, và đó là SỐ ĐO chứ không phải lời hứa — nên đo cả hai:
#   7a. gỡ chốt ở UI  -> `tg_chay.xep_mot` vẫn chặn video đã xong (lớp 2).
#   7b. gỡ CẢ HAI     -> xếp lại đủ 3 job = bất biến VỠ đúng như phải vỡ.
def _dem_lai_job() -> int:
    CHUOI.clear()
    n = dlg._chay()
    for jid in list(dlg._jobs.values()):        # huỷ ngay, khỏi chạy thừa
        pool.cancel(int(jid))
    cho_xong(dlg, han=30)
    dlg._jobs.clear()
    return n


_ui = tg_chay.can_chay
tg_chay.can_chay = lambda duong, lam_lai=False: True     # type: ignore
try:
    _n7a = _dem_lai_job()
finally:
    tg_chay.can_chay = _ui
SO["job_go_1_chot"] = _n7a
dat("7a gỡ chốt ở UI -> lớp 2 (`tg_chay.xep_mot`) VẪN chặn video đã xong",
    _n7a == 0, f"{_n7a} job (2 lớp chắn: UI + cửa xếp job)")

_lop2 = tg_so.can_chay
tg_chay.can_chay = lambda duong, lam_lai=False: True     # type: ignore
tg_so.can_chay = lambda duong: True                      # type: ignore
try:
    _n7b = _dem_lai_job()
finally:
    tg_chay.can_chay = _ui
    tg_so.can_chay = _lop2
SO["job_go_ca_2_chot"] = _n7b
dat("7b gỡ CẢ HAI chốt -> xếp lại CẢ 3 job = mục 4 VỠ (nó đang đo thật)",
    _n7b == 3, f"{_n7b} job (nếu vẫn 0 thì mục 4 là con dấu)")

_that_lai = tg_chay.can_chay(str(V3))
dat("vá lại chốt -> video đã xong lại được bỏ qua như cũ",
    _that_lai is False, f"can_chay(video_3)={_that_lai}")
dat("vá lại chốt -> bấm Chạy xếp 0 job như trước khi phá",
    dlg._chay() == 0)


# ==================================================================
try:
    pool.stop(wait=False)
except Exception:  # noqa: BLE001
    pass
dlg.close()

print("\n" + "=" * 62)
print("SỐ ĐO:", json.dumps(SO, ensure_ascii=False))
print(f"ĐẠT {len(OK)} · HỎNG {len(FAIL)}")
for f in FAIL:
    print("  HỎNG:", f)
shutil.rmtree(T, ignore_errors=True)     # KHÔNG để rác trên máy anh Hùng
sys.exit(1 if FAIL else 0)
