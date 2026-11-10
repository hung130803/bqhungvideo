# -*- coding: utf-8 -*-
"""ĐO TỪNG BƯỚC CỦA KHÂU XUẤT 1 PART (10/11/2026).

Số liệu 2 ngày: 347 Part, xuất trung vị 258 s = 1,9 lần độ dài clip; app xả
~58 Part/giờ trong khi phân tích sinh ~90 -> Part chờ TB 43 phút. App không ghi
giờ từng bước nên chưa biết bước nào ăn nhiều nhất -> đo bằng CHÍNH hàm xuất
`m1_highlight.export_clip`, trong HỘP CÁT (DB tạm, file ra thư mục tạm; video
gốc chỉ ĐỌC), bấm giờ MỌI lệnh ffmpeg/ffprobe + các hàm lớn.

Chạy:  .venv\\Scripts\\python _do_xuat_buoc.py <clip_id> [<clip_id> ...]
In bảng: bước · số lệnh · giây · % tổng; ghi JSON ra _kq_xuat_buoc.json.
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
SB = Path(tempfile.mkdtemp(prefix="bq_do_xuat_"))
os.environ["BQ_DATA_DIR"] = str(SB)
os.environ["BQ_DB_PATH"] = str(SB / "studio.db")
sys.path.insert(0, str(REPO))

THAT = Path(os.environ["LOCALAPPDATA"]) / "BQHungVideo"
src = sqlite3.connect(f"file:{THAT / 'studio.db'}?mode=ro", uri=True)
src.row_factory = sqlite3.Row
# .env thật (key Groq/Gemini) không cần: xuất không gọi AI. Mẫu payload lấy từ
# job xuất GẦN NHẤT đã xong (đúng mẫu đang chạy sản xuất).
mau = json.loads(src.execute(
    "SELECT payload FROM jobs WHERE type='m1_export_clip' AND status='done' "
    "ORDER BY id DESC LIMIT 1").fetchone()[0])
# Đọc HẾT dữ liệu thật TRƯỚC khi nạp app rồi đóng kết nối: để kết nối chỉ-đọc
# vào DB 470 MB đang được app ghi mở song song với DB hộp cát thì tiến trình
# chết im lặng (mã 127) ngay câu SELECT kế tiếp (đo 10/11/2026).
DL = {}
for _cid in [int(x) for x in sys.argv[1:]] or [10259]:
    _cl = dict(src.execute("SELECT * FROM clips WHERE id=?", (_cid,)).fetchone())
    _v = dict(src.execute("SELECT * FROM videos WHERE id=?", (_cl["video_id"],)).fetchone())
    _pj = dict(src.execute("SELECT * FROM projects WHERE id=?", (_v["project_id"],)).fetchone())
    _an = [dict(a) for a in src.execute("SELECT * FROM analysis WHERE video_id=?", (_v["id"],))]
    DL[_cid] = (_cl, _v, _pj, _an)
src.close()

import app.queue.jobs  # noqa: E402,F401  (cv2 trước Qt)
# Vẽ lớp chữ (QPainterPath) cần QApplication; thiếu là Qt giết tiến trình
# IM LẶNG mã 127 (sập 1 lần khi viết phép đo này). App thật luôn có sẵn.
# nền "offscreen" không có phông hệ thống -> chữ ra ô vuông; dùng nền mặc định.
from PyQt6.QtWidgets import QApplication  # noqa: E402
_QAPP = QApplication.instance() or QApplication([])
from app.database import db  # noqa: E402
from app.modules import m1_highlight as M1  # noqa: E402
from app.core import ffmpeg_utils as FU  # noqa: E402


def chep(bang, row):
    cols = list(row.keys())
    db.execute(f"INSERT OR REPLACE INTO {bang}({','.join(cols)}) VALUES({','.join('?' * len(cols))})",
               tuple(row[k] for k in cols))


# ---------- bấm giờ ----------
NHAT = []          # (nhãn, giây)
LENH = []          # (giây, trong hàm, lệnh)
_dang = []         # ngăn xếp nhãn hàm lớn


GIU = os.environ.get("BQ_GIU_LENH", "")


def giu_lenh(cmd):
    """Chép MỌI file đầu vào của lượt dựng hình chính (kể cả các mảnh trong
    danh sách concat) ra thư mục GIU rồi ghi lệnh đã đổi đường dẫn -> đo lại
    được lượt đó một mình, nhiều biến thể, trên SSD."""
    d = Path(GIU)
    d.mkdir(parents=True, exist_ok=True)
    moi = []
    for i, a in enumerate(cmd):
        if i > 0 and cmd[i - 1] == "-i" and os.path.isfile(a):
            dst = d / f"in{i}_{Path(a).name}"
            if a.endswith("_list.txt"):
                dong = []
                for ln in Path(a).read_text(encoding="utf-8").splitlines():
                    if ln.startswith("file "):
                        f = ln[5:].strip().strip("'")
                        g = d / Path(f).name
                        shutil.copy2(f, g)
                        dong.append(f"file '{g.as_posix()}'")
                    else:
                        dong.append(ln)
                dst.write_text("\n".join(dong) + "\n", encoding="utf-8")
            else:
                shutil.copy2(a, dst)
            moi.append(str(dst))
        else:
            moi.append(a)
    # file .ass của phụ đề nằm TRONG chuỗi filter -> chép theo tên
    import re
    for i, a in enumerate(moi):
        for m in re.findall(r"subtitles='([^']+\.ass)'", a):
            goc = m.replace("\\:", ":")
            if os.path.isfile(goc):
                g = d / Path(goc).name
                shutil.copy2(goc, g)
                moi[i] = moi[i].replace(m, g.as_posix().replace(":", "\\:"))
    (d / "lenh.json").write_text(json.dumps(moi, ensure_ascii=False, indent=0), encoding="utf-8")


def nhan_lenh(cmd):
    s = " ".join(map(str, cmd))
    exe = os.path.basename(str(cmd[0])).lower()
    if "ffprobe" in exe:
        return "ffprobe"
    if "loudnorm" in s or "ebur128" in s:
        return "đo độ to"
    if "astats" in s and "-f null" in s.replace("  ", " "):
        return "đo mức tiếng"
    if "-c:v copy" in s and "-c:a" in s:
        return "mã lại TIẾNG (hình copy)"
    if "filter_complex" in s or "-vf" in s:
        return "dựng hình + mã hoá"
    if "-c copy" in s or "concat" in s:
        return "nối/copy"
    return "ffmpeg khác"


def boc_popen():
    goc = subprocess.Popen

    class P(goc):
        def __init__(self, cmd, *a, **k):
            self._t0 = time.monotonic()
            self._nhan = nhan_lenh(cmd) if isinstance(cmd, (list, tuple)) else "lệnh"
            self._cha = _dang[-1] if _dang else ""
            self._ghi = False
            self._cmd = " ".join(map(str, cmd)) if isinstance(cmd, (list, tuple)) else str(cmd)
            if GIU and isinstance(cmd, (list, tuple)) and "curve_" in self._cmd and "concat" in self._cmd:
                giu_lenh(list(map(str, cmd)))
            super().__init__(cmd, *a, **k)

        def _xong(self):
            if not self._ghi:
                self._ghi = True
                NHAT.append(("ffmpeg", self._nhan, self._cha, time.monotonic() - self._t0))
                LENH.append((round(time.monotonic() - self._t0, 1), self._cha, self._cmd[:900]))

        def wait(self, *a, **k):
            r = super().wait(*a, **k)
            self._xong()
            return r

        def communicate(self, *a, **k):
            r = super().communicate(*a, **k)
            self._xong()
            return r
    subprocess.Popen = P


def boc_ham(mod, ten, nhan):
    goc = getattr(mod, ten)

    def f(*a, **k):
        _dang.append(nhan)
        t0 = time.monotonic()
        try:
            return goc(*a, **k)
        finally:
            _dang.pop()
            NHAT.append(("ham", nhan, _dang[-1] if _dang else "", time.monotonic() - t0))
    setattr(mod, ten, f)


boc_popen()
for mod, ten, nhan in [
    (M1, "export_canvas_clip", "export_canvas_clip"),
    (FU, "export_canvas_clip", "export_canvas_clip"),
    (FU, "chuan_do_to_clip", "chuẩn hoá độ to"),
    (M1, "chuan_do_to_clip", "chuẩn hoá độ to"),
    (M1, "render_overlay_png", "vẽ lớp chữ PNG"),
]:
    if hasattr(mod, ten):
        boc_ham(mod, ten, nhan)
for ten in ("_do_muc_clip", "_build_seg", "_tach_va_noi_manh", "_noi_xfade",
            "do_nhip", "_chon_nhac_tu_dong", "build_ass"):
    for mod in (FU, M1):
        if hasattr(mod, ten) and callable(getattr(mod, ten)):
            boc_ham(mod, ten, ten)
            break


class Ctx:
    def __init__(self, jid):
        self.job_id = jid
        self.profile = {"encoder": os.environ.get("BQ_DO_ENC", "h264_nvenc")}

    def progress(self, *_a, **_k):
        pass

    def check_canceled(self):
        pass


def do_mot(cid):
    cl, v, pj, an = DL[cid]
    chep("projects", pj)
    chep("videos", v)
    chep("clips", cl)
    for a in an:
        chep("analysis", a)
    out = SB / f"ra_{cid}"
    out.mkdir(exist_ok=True)
    db.execute("UPDATE projects SET assets_dir=?, export_dir=? WHERE id=?",
               (str(SB / f"as_{pj['id']}"), str(out), pj["id"]))
    p = dict(mau)
    p.update(clip_id=cid, out_dir=str(out), out_name=f"Part 1 do {cid}", part_no=1,
             overlay_png=str(SB / f"_ovl_{cid}.png"))
    jid = db.insert("INSERT INTO jobs(type,payload,status,attempts,max_attempts) "
                    "VALUES('m1_export_clip',?, 'running',1,3)", (json.dumps(p),))
    NHAT.clear()
    LENH.clear()
    t0 = time.monotonic()
    kq = M1.export_clip(p, Ctx(jid))
    tong = time.monotonic() - t0
    dur = json.loads(cl["signals"]).get("dur")
    return tong, dur, list(NHAT), kq


def in_bang(cid, tong, dur, nhat):
    print(f"\n=== clip {cid} · dài {dur}s · XUẤT {tong:.1f}s = {tong / (dur or 1):.2f}x ===")
    gom = {}
    for loai, nhan, cha, s in nhat:
        k = (loai, nhan, cha)
        g = gom.setdefault(k, [0, 0.0])
        g[0] += 1
        g[1] += s
    for (loai, nhan, cha), (n, s) in sorted(gom.items(), key=lambda x: -x[1][1]):
        print(f"  {s:7.1f}s {100 * s / tong:5.1f}%  x{n:<3} {loai:6} {nhan}"
              + (f"  (trong {cha})" if cha else ""))


if __name__ == "__main__":
    ids = [int(x) for x in sys.argv[1:]] or [10259]
    ket = {}
    for cid in ids:
        tong, dur, nhat, kq = do_mot(cid)
        in_bang(cid, tong, dur, nhat)
        ket[cid] = {"tong": tong, "dur": dur, "buoc": nhat, "lenh": list(LENH),
                    "do_to": (kq or {}).get("do_to", {}).get("ly_do") if isinstance(kq, dict) else None}
    Path(REPO, "_kq_xuat_buoc.json").write_text(json.dumps(ket, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.rmtree(SB, ignore_errors=True)
