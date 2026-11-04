# -*- coding: utf-8 -*-
"""CỔNG 106 — NHẠC NỀN TỰ CHỌN THEO NỘI DUNG: NHỎ, NÉ LỜI, ĐÚNG KHÔNG KHÍ.

Anh Hùng 02/11/2026: *"tự chọn, âm lượng nhạc nền mức nhỏ thôi ... đang kịch
tính lại cho nhạc vui vẻ không được ... không to, không lỗi"*.

  CA 1  tâm trạng: bất biến SỐNG CÒN — có dấu hiệu nặng đủ điểm thì KHÔNG BAO
        GIỜ ra 'playful'/'bright' (quét 3.000 tổ hợp câu ngẫu nhiên) + ca mẫu
  CA 2  chọn bài: tiền định, lùi 'calm' (không lùi sang vui), kho đủ mỗi tâm trạng
  CA 3  kho: catalog() nạp được (đường dựng phóng sự KHÔNG vỡ), mọi file có
        thật + sha256 khớp + CC0 + có cột `lufs` ĐO THẬT
  CA 4  hệ số + né lời + bỏ qua (hàm thuần)
  CA 5  xuất THẬT bằng ffmpeg: nhạc nằm dưới lời đúng ~12 dB lúc im, hạ thêm
        lúc nói, không vượt trần đỉnh, độ dài đúng; nguồn nền to -> VẪN
        chèn; tắt chế độ -> lệnh ffmpeg y như cũ (không input nhạc)
  CA 6  không đụng khoá chống trùng; chuỗi đánh dấu chỉ đổi khoá khi BẬT
  CA 7  nối đúng chỗ: m1 truyền `bgm_tu_dong`, lỗi kho nhạc không giết clip
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_DATA_DIR", tempfile.mkdtemp(prefix="bq106_"))
os.environ.setdefault("BQ_DB_PATH",
                      os.path.join(os.environ["BQ_DATA_DIR"], "t.db"))

import time  # noqa: E402
import _test_guard  # noqa: E402,F401  (cổng 17: chặn loa / cửa sổ ngoài)
import app.queue.jobs  # noqa: E402,F401  (cv2 TRƯỚC Qt)
from app.core import ffmpeg_utils as F  # noqa: E402
from app.core import music_library as ML  # noqa: E402
from app.core import nhac_tu_dong as NT  # noqa: E402

DAT = HONG = 0
FF = str(REPO / "bin" / "ffmpeg.exe")
NW = 0x08000000 if os.name == "nt" else 0
#: hằng số CỦA CỔNG (không đọc lại từ module — so với chính nó là tự chấm)
DUOI_LOI_CHOT = 12.0   # 18 -> 12: anh Hùng nghe "bé quá" (02/11/2026)
SO_BAI_TOI_THIEU = 60


def ok(dk: bool, ten: str, chi_tiet: str = "") -> None:
    global DAT, HONG
    if dk:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))
    else:
        HONG += 1
        print(f"  HỎNG {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))


NANG = ["cảnh sát đang truy đuổi chiếc xe", "police arrested him",
        "anh ấy đã qua đời vì ung thư", "the funeral was held",
        "vụ mất tích bí ẩn đang được điều tra", "a haunted house ghost",
        "gun shooting 🚨", "đám tang của mẹ", "a robbery at the store"]
VUI = ["haha buồn cười quá", "this prank is hilarious 😂", "cảm ơn mọi người",
       "happy birthday", "lol funny joke", "tuyệt vời quá 😍"]
TRUNG = ["hôm nay tôi đi chợ mua rau", "we fixed the engine today",
         "cái bàn này giá bao nhiêu", "let's see what is inside the box"]


def ca1() -> None:
    print("\n[CA 1] TÂM TRẠNG — có dấu hiệu nặng thì KHÔNG BAO GIỜ ra nhạc vui")
    rng = random.Random(106)
    sai = []
    for _ in range(3000):
        cau = [rng.choice(NANG)] + rng.sample(VUI, rng.randint(1, 3)) + \
            rng.sample(TRUNG, rng.randint(0, 2))
        rng.shuffle(cau)
        tieu = rng.choice(["", rng.choice(VUI), rng.choice(TRUNG)])
        m, _l = NT.tam_trang(" . ".join(cau), tieu)
        if m in ("playful", "bright"):
            sai.append((cau, m))
    ok(not sai, "3.000 tổ hợp có câu nặng + câu vui -> 0 lần ra nhạc vui",
       f"{len(sai)} lần sai, vd {sai[:1]}")
    for txt, mong in (("cảnh sát bắt giữ nghi phạm", "tension"),
                      ("Police chase 🚨 haha lol", "tension"),
                      ("bà đã qua đời, cả nhà khóc", "emotional"),
                      ("a haunted house, ghost everywhere", "mystery"),
                      ("haha chết cười với con mèo", "playful"),
                      ("thank you so much, amazing", "bright"),
                      ("hôm nay tôi sửa xe", "calm"),
                      ("nhớ đăng ký kênh nhé", "calm"),
                      ("My Wallet's Crying after this deal", "calm"),
                      ("The deadline is tomorrow", "calm")):
        m, ly = NT.tam_trang(txt)
        ok(m == mong, f"«{txt}» -> {mong}", f"ra {m} ({ly})")
    m, _ = NT.tam_trang("crying", "funny prank")
    ok(m == "calm", "dấu hiệu nặng CHƯA đủ điểm + vui -> nhạc ÊM (không vui)",
       m)
    m, _ = NT.tam_trang("", "Police Arrest Him — Hilarious 😂")
    ok(m == "tension", "tiêu đề cảnh sát + 'hilarious' -> căng (không vui)", m)


def ca2() -> None:
    print("\n[CA 2] CHỌN BÀI")
    tr = list(ML.catalog())
    a = NT.chon_bai(tr, "tension", "v1|10.0")
    b = NT.chon_bai(tr, "tension", "v1|10.0")
    ok(a and a == b and a["mood"] == "tension", "tiền định + đúng tâm trạng",
       a and a["id"])
    khac = {NT.chon_bai(tr, "calm", f"v{i}|0")["id"] for i in range(30)}
    ok(len(khac) >= 4, "30 clip khác nhau -> nhiều bài khác nhau", str(len(khac)))
    gia = [t for t in tr if t["mood"] in ("bright", "playful", "calm")]
    x = NT.chon_bai(gia, "tension", "z")
    ok(x is not None and x["mood"] == "calm",
       "thiếu bài đúng tâm trạng -> lùi 'calm', KHÔNG lùi sang vui",
       x and x["mood"])
    ok(NT.chon_bai([], "calm", "z") is None, "kho rỗng -> None (không nổ)")


def ca3() -> None:
    print("\n[CA 3] KHO NHẠC")
    tr = ML.catalog()
    ok(len(tr) >= SO_BAI_TOI_THIEU, f"kho >= {SO_BAI_TOI_THIEU} bài",
       f"{len(tr)} bài")
    dem = {m: sum(1 for t in tr if t["mood"] == m) for m in ML.MOODS}
    ok(all(v >= 4 for v in dem.values()), "mỗi tâm trạng >= 4 bài", str(dem))
    thieu, lech, gp, lu = [], [], [], []
    for t in tr:
        p = ML.folder() / t["file"]
        if not p.is_file():
            thieu.append(t["file"])
            continue
        if hashlib.sha256(p.read_bytes()).hexdigest() != t["sha256"]:
            lech.append(t["file"])
        if t.get("license") != "CC0-1.0":
            gp.append(t["file"])
        if not isinstance(t.get("lufs"), (int, float)) or not (
                -40 < float(t["lufs"]) < -8):
            lu.append(t["file"])
    ok(not thieu, "mọi bài có file", str(thieu[:3]))
    ok(not lech, "sha256 khớp", str(lech[:3]))
    ok(not gp, "mọi bài CC0", str(gp[:3]))
    ok(not lu, "mọi bài có cột lufs đo thật", str(lu[:3]))
    tren_dia = {p.name for p in ML.folder().glob("*.opus")}
    ok(tren_dia == {t["file"] for t in tr}, "không có file mồ côi ngoài catalog",
       str(tren_dia ^ {t["file"] for t in tr}))
    md = (ML.folder() / "NGUON.md").read_text("utf-8")
    ok(all(t["title"] in md for t in tr), "NGUON.md ghi đủ từng bài")
    lic = (REPO / "LICENSES.txt").read_text("utf-8")
    ok("tai_nhac_cc0" in lic and "app/assets/music" in lic,
       "LICENSES.txt ghi nguồn kho nhạc")


def ca4() -> None:
    print("\n[CA 4] HỆ SỐ · NÉ LỜI · BỎ QUA (thuần)")
    g = NT.he_so_db(-14.0, -20.0)
    ok(abs((-20.0 + g) - (-14.0 - DUOI_LOI_CHOT)) < 1e-6,
       "nhạc nằm dưới lời đúng 12 dB", f"{g:+.1f} dB")
    ok(NT.he_so_db(0.0, -30.0) <= 6.0, "không bao giờ kéo nhạc to > +6 dB")
    ok(NT.he_so_db(None, -20.0) + -20.0 <= -30.0, "không đo được lời -> rất nhỏ")
    # anh Hùng 02/11/2026: "mặc định video nào cũng phải chèn nhạc" -> KHÔNG
    # bao giờ bỏ qua, kể cả nền gốc to ngang lời (nhạc vẫn bám dưới lời).
    ok(all(NT.bo_qua(-14.0, -14.0 - x) == "" for x in (-2.0, 0.0, 2.0, 5.4,
                                                         12.7, 30.0)),
       "MỌI mức nền gốc -> VẪN chèn (không bỏ qua video nào)")
    # chế độ của MẪU: 'off' cũ / thiếu = TỰ CHỌN; chỉ 'none' mới tắt
    ok(NT.che_do_mau("off") == "auto" and NT.che_do_mau(None) == "auto"
       and NT.che_do_mau("") == "auto" and NT.che_do_mau("none") == "none"
       and NT.che_do_mau("random") == "random"
       and NT.che_do_mau("fixed") == "fixed",
       "mẫu cũ 'off'/thiếu khoá -> TỰ CHỌN; 'Tắt hẳn' mới tắt")
    e = NT.bieu_thuc_ne([(1.0, 3.0), (3.3, 5.0), (8.0, 9.0)], 12.0)
    ok(e.startswith("volume='1-") and e.count("clip(") == 2,
       "2 câu sát nhau gộp 1 bướu, câu xa riêng bướu", e[:80])
    ok(NT.bieu_thuc_ne([], 12.0) == "", "không có câu -> không né")
    # đường bao giữ VỊ TRÍ thời gian (lỗi cũ: bỏ cửa sổ im -> lệch mốc)
    bao = [F._SAN_IM] * 20 + [-12.0] * 20 + [F._SAN_IM] * 20
    ok(F.muc_tai_moc(bao, 0.05, 1.5) == -12.0
       and F.muc_tai_moc(bao, 0.05, 0.3) == F._SAN_IM,
       "mức tại mốc đọc ĐÚNG chỗ khi có đoạn im tuyệt đối")
    ok(F.nen_tai_moc(bao, 0.05, 1.5) == -12.0,
       "nền cục bộ KHÔNG tính cửa sổ im (giữ nghĩa cũ cho tiếng động)")
    ok(F.nen_tai_moc([F._SAN_IM] * 30, 0.05, 0.7) is None,
       "chỉ toàn im -> nền None (không bịa số)")


def _sinh_nguon(p: str, nen_to: bool) -> None:
    """"Lời" = tông 300+900 Hz bật theo câu [1-4], [6-9] s; ngoài đó im (hoặc
    nền ồn TO nếu `nen_to`)."""
    loi = ("0.30*(sin(2*PI*300*t)+0.6*sin(2*PI*900*t))"
           "*(between(t,1,4)+between(t,6,9))")
    nen = "+0.55*sin(2*PI*150*t)" if nen_to else ""   # nền to ngang lời
    # BẪY ĐÃ SẬP 02/11/2026 — cổng đứng im > 10 phút: bộ mã hoá AAC của
    # ffmpeg (cả N-126207 lẫn bản trong bộ cài) TREO VĨNH VIỄN ở **192k** với
    # tiếng MONO có đoạn IM TUYỆT ĐỐI rồi vào ÂM THUẦN (đo: 192k treo, 160k /
    # 128k / stereo / thêm chút nhiễu / `-aac_coder fast` đều chạy). Dùng 160k
    # = đúng mức app xuất clip; kèm `timeout` để cổng không bao giờ treo.
    wav = p + ".wav"
    subprocess.run([FF, "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", f"aevalsrc='{loi}{nen}':s=48000:d=12",
                    wav], check=True, timeout=120,
                   creationflags=NW, stdin=subprocess.DEVNULL)
    subprocess.run([FF, "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "color=c=0x1E6F5C:s=540x960:r=25:d=12",
                    "-i", wav, "-shortest", "-c:v", "libx264", "-preset",
                    "ultrafast", "-c:a", "aac", "-b:a", "160k", p],
                   check=True, timeout=120, creationflags=NW,
                   stdin=subprocess.DEVNULL)


def _pcm(p: str):
    """Đọc tiếng về 16 kHz, trộn mono bằng TRUNG BÌNH 2 kênh (L+R)/2.

    BẪY ĐÃ SẬP 02/11/2026: `-ac 1` của ffmpeg cộng 2 kênh với hệ số 0,707 nên
    tiếng GIỐNG NHAU ở 2 kênh bị PHỒNG đúng +3 dB -> file thật đỉnh -2,98 dBFS
    (astats) đọc ra -0,05 và cổng báo "méo" OAN. Trung bình thì không bao giờ
    vượt đỉnh của kênh to nhất."""
    import numpy as np
    r = subprocess.run([FF, "-nostdin", "-v", "error", "-i", p, "-vn", "-ac", "2",
                        "-ar", "16000", "-f", "f32le", "-"], capture_output=True,
                       creationflags=NW, stdin=subprocess.DEVNULL, check=True)
    x = np.frombuffer(r.stdout, dtype="float32")
    return x.reshape(-1, 2).mean(axis=1)


def _db_cua_so(x, a, b, sr=16000):
    import numpy as np
    s = x[int(a * sr):int(b * sr)]
    return 20 * np.log10(max(1e-9, float(np.sqrt(np.mean(s * s)))))


def ca5() -> None:
    print("\n[CA 5] XUẤT THẬT bằng ffmpeg")
    import numpy as np
    d = tempfile.mkdtemp(prefix="bq106x_")
    src = os.path.join(d, "src.mp4")
    _sinh_nguon(src, False)
    tr = {"segments": [{"start": 1.0, "end": 4.0, "text": "câu một"},
                       {"start": 6.0, "end": 9.0, "text": "câu hai"}]}
    bai = next(t for t in ML.catalog() if t["mood"] == "calm")
    path = ML.resolve(ML.PREFIX + bai["id"])
    kw = dict(bg="blur", out_w=540, out_h=960, encoder="libx264",
              fx_whoosh=False, hieu_ung="tat", chuyen_canh="tat")
    co, khong = os.path.join(d, "co.mp4"), os.path.join(d, "khong.mp4")
    log: dict = {}
    F.export_canvas_clip(src, co, [(0.0, 12.0)], (0.5, 0.5, 1.0),
                         bgm_path=path, bgm_tu_dong={"lufs": bai["lufs"],
                                                     "transcript": tr,
                                                     "log": log}, **kw)
    F.export_canvas_clip(src, khong, [(0.0, 12.0)], (0.5, 0.5, 1.0), **kw)
    ok(not log.get("bo_qua") and "he_so_db" in log, "đã chèn nhạc",
       json.dumps(log, ensure_ascii=False))
    a, b = _pcm(co), _pcm(khong)
    n = min(len(a), len(b))
    nhac = a[:n] - b[:n]
    loi = _db_cua_so(b, 1.5, 3.5)
    im = _db_cua_so(nhac, 10.0, 10.4)         # sau câu 2, trước mờ ra
    trong_loi = _db_cua_so(nhac, 2.0, 3.0)
    print(f"      lời {loi:.1f} dB · nhạc lúc im {im:.1f} · nhạc lúc nói "
          f"{trong_loi:.1f}")
    ok(DUOI_LOI_CHOT - 3 <= loi - im <= DUOI_LOI_CHOT + 5,
       "lúc im: nhạc nằm dưới lời ~12 dB (nghe rõ mà vẫn là nền)",
       f"dưới lời {loi - im:.1f} dB")
    ok(im - trong_loi >= 3.0, "lúc nói: nhạc hạ thêm (né lời)",
       f"hạ thêm {im - trong_loi:.1f} dB")
    ok(_db_cua_so(nhac, 0.0, 0.3) < im - 3.0, "mờ vào ở đầu clip")
    ok(abs(float(F.probe(co).duration) - 12.0) < 0.2, "độ dài đúng")
    pk = 20 * np.log10(max(1e-9, float(np.max(np.abs(a)))))
    ok(pk <= -0.5, "đỉnh không chạm trần", f"{pk:.2f} dBFS")
    # nguồn đã có nền TO -> bỏ qua
    src2 = os.path.join(d, "src2.mp4")
    _sinh_nguon(src2, True)
    log2: dict = {}
    F.export_canvas_clip(src2, os.path.join(d, "co2.mp4"), [(0.0, 12.0)],
                         (0.5, 0.5, 1.0), bgm_path=path,
                         bgm_tu_dong={"lufs": bai["lufs"], "transcript": tr,
                                      "log": log2}, **kw)
    ok(not log2.get("bo_qua") and "he_so_db" in log2,
       "video gốc nền to ngang lời -> VẪN chèn (mặc định mọi video có nhạc)",
       str(log2))
    # nguồn này TỰ NÓ đã sát 0 dBFS -> luật đúng là "bản CÓ nhạc KHÔNG méo
    # hơn bản KHÔNG nhạc" (cùng luật tiếng động), không phải ngưỡng cứng.
    F.export_canvas_clip(src2, os.path.join(d, "k2.mp4"), [(0.0, 12.0)],
                         (0.5, 0.5, 1.0), **kw)

    def _dinh(x):
        return 20 * np.log10(max(1e-9, float(np.max(np.abs(x)))))
    pk_co = _dinh(_pcm(os.path.join(d, "co2.mp4")))
    pk_k = _dinh(_pcm(os.path.join(d, "k2.mp4")))
    ok(abs(float(F.probe(os.path.join(d, "co2.mp4")).duration) - 12.0) < 0.2
       and pk_co <= max(-0.5, pk_k + 0.1),
       "nền to + nhạc: độ dài đúng, KHÔNG méo hơn bản không nhạc",
       f"có nhạc {pk_co:.2f} dBFS · không nhạc {pk_k:.2f} dBFS")
    # chế độ tắt: không có input nhạc nào (đường cũ y nguyên)
    seen = []
    goc = F._run_with_fallback if hasattr(F, "_run_with_fallback") else None
    if goc is not None:
        def _spy(build, *a2, **k2):
            seen.append(build("libx264"))
            return goc(build, *a2, **k2)
        F._run_with_fallback = _spy
        try:
            F.export_canvas_clip(src, os.path.join(d, "tat.mp4"),
                                 [(0.0, 12.0)], (0.5, 0.5, 1.0), **kw)
        finally:
            F._run_with_fallback = goc
        ok(seen and not any(".opus" in str(x) for x in seen[0]),
           "không bật chế độ -> lệnh ffmpeg không có nhạc")


def _so_luong(p: str) -> dict:
    """Độ dài TỪNG LUỒNG (giây) — đo cả hình lẫn tiếng, không tin 'format'."""
    r = subprocess.run([str(REPO / "bin" / "ffprobe.exe"), "-v", "error",
                        "-show_entries", "stream=codec_type,duration",
                        "-of", "json", p], capture_output=True,
                       creationflags=NW, stdin=subprocess.DEVNULL, check=True)
    return {s["codec_type"]: float(s.get("duration") or 0)
            for s in json.loads(r.stdout)["streams"]}


def ca5b() -> None:
    print("\n[CA 5B] NHẠC DÀI HƠN / NGẮN HƠN VIDEO · VIDEO CÂM — độ dài phải KHỚP")
    import numpy as np
    d = tempfile.mkdtemp(prefix="bq106y_")
    kw = dict(bg="blur", out_w=540, out_h=960, encoder="libx264",
              fx_whoosh=False, hieu_ung="tat", chuyen_canh="tat")
    tr = {"segments": [{"start": 1.0, "end": 3.0, "text": "a"}]}
    dai = max(ML.catalog(), key=lambda t: t["duration"])
    ngan = min(ML.catalog(), key=lambda t: t["duration"])
    # (a) nhạc DÀI hơn clip 12 s -> phải CẮT đúng 12 s
    src = os.path.join(d, "s12.mp4")
    _sinh_nguon(src, False)
    o = os.path.join(d, "a.mp4")
    F.export_canvas_clip(src, o, [(0.0, 12.0)], (0.5, 0.5, 1.0),
                         bgm_path=ML.resolve(ML.PREFIX + dai["id"]),
                         bgm_tu_dong={"lufs": dai["lufs"], "transcript": tr,
                                      "log": {}}, **kw)
    sl = _so_luong(o)
    ok(dai["duration"] > 12 and abs(sl.get("audio", 0) - 12.0) < 0.15
       and abs(sl.get("video", 0) - 12.0) < 0.15,
       f"nhạc {dai['duration']:.0f} s > clip 12 s -> CẮT đúng", str(sl))
    # (b) nhạc NGẮN hơn clip -> LẶP, cuối clip vẫn còn nhạc (không câm)
    T = ngan["duration"] + 8.0
    src2 = os.path.join(d, "dai.mp4")
    subprocess.run([FF, "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", f"color=c=0x1E6F5C:s=540x960:r=25:d={T}",
                    "-f", "lavfi", "-i",
                    f"aevalsrc='0.3*sin(2*PI*300*t)*between(t,1,3)':s=48000:d={T}",
                    "-shortest", "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac", src2], check=True, creationflags=NW, stdin=subprocess.DEVNULL)
    o2, o2k = os.path.join(d, "b.mp4"), os.path.join(d, "bk.mp4")
    F.export_canvas_clip(src2, o2, [(0.0, T)], (0.5, 0.5, 1.0),
                         bgm_path=ML.resolve(ML.PREFIX + ngan["id"]),
                         bgm_tu_dong={"lufs": ngan["lufs"], "transcript": tr,
                                      "log": {}}, **kw)
    F.export_canvas_clip(src2, o2k, [(0.0, T)], (0.5, 0.5, 1.0), **kw)
    sl = _so_luong(o2)
    ok(abs(sl.get("audio", 0) - T) < 0.15 and abs(sl.get("video", 0) - T) < 0.15,
       f"nhạc {ngan['duration']:.0f} s < clip {T:.0f} s -> độ dài vẫn khớp",
       str(sl))
    a, b = _pcm(o2), _pcm(o2k)
    n = min(len(a), len(b))
    nh = a[:n] - b[:n]
    sau = _db_cua_so(nh, ngan["duration"] + 2.0, ngan["duration"] + 5.0)
    ok(sau > -60, "SAU khi hết bài, nhạc LẶP lại (không câm)",
       f"{sau:.1f} dBFS ở giây {ngan['duration'] + 2:.0f}-"
       f"{ngan['duration'] + 5:.0f}")
    # (b2) nguồn SẠCH có đoạn im + KHÔNG có lời chép -> PHẢI chèn (thử phá
    # 02/11/2026: phép "nền = bpv20 cửa sổ có tiếng" LỌT vì thiếu ca này)
    lg2: dict = {}
    F.export_canvas_clip(src, os.path.join(d, "b2.mp4"), [(0.0, 12.0)],
                         (0.5, 0.5, 1.0),
                         bgm_path=ML.resolve(ML.PREFIX + dai["id"]),
                         bgm_tu_dong={"lufs": dai["lufs"], "transcript": {},
                                      "log": lg2}, **kw)
    ok("he_so_db" in lg2 and not lg2.get("bo_qua"),
       "không có lời chép + nguồn sạch -> vẫn CHÈN (không bỏ oan)", str(lg2))
    ok(lg2.get("nen_khong_noi_db") is not None and lg2.get("loi_db") is not None
       and lg2["nen_khong_noi_db"] < lg2["loi_db"] - 20,
       "nhật ký ghi ĐÚNG nền lúc không nói (nguồn có đoạn im -> rất thấp)",
       str(lg2))
    # ĐO THẲNG hàm đo đường bao (dùng chung với TIẾNG ĐỘNG): nguồn có lời ở
    # [1-4] và [6-9] s, ngoài đó IM TUYỆT ĐỐI -> đường bao phải đủ 12 s và
    # mốc 5 s phải đọc ra IM (lỗi cũ: cửa sổ im bị bỏ -> lệch mốc)
    mc = F._do_muc_clip(["-i", src])
    bao = mc.get("bao") or []
    ok(abs(len(bao) * mc.get("buoc", 0.05) - 12.0) < 0.3,
       "đường bao giữ ĐỦ độ dài (không bỏ cửa sổ im)",
       f"{len(bao) * mc.get('buoc', 0.05):.2f} s")
    ok(F.muc_tai_moc(bao, mc["buoc"], 5.0) == F._SAN_IM
       and F.muc_tai_moc(bao, mc["buoc"], 2.5) > -30,
       "mức tại giây 5 (im) đọc ra IM, giây 2,5 (đang nói) đọc ra có lời",
       f"5s={F.muc_tai_moc(bao, mc['buoc'], 5.0)} · "
       f"2,5s={F.muc_tai_moc(bao, mc['buoc'], 2.5)}")
    # (c) video KHÔNG có luồng tiếng -> vẫn xuất được, có nhạc, độ dài khớp
    src3 = os.path.join(d, "cam.mp4")
    subprocess.run([FF, "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "color=c=0x1E6F5C:s=540x960:r=25:d=8",
                    "-c:v", "libx264", "-preset", "ultrafast", src3],
                   check=True, creationflags=NW, stdin=subprocess.DEVNULL)
    o3 = os.path.join(d, "c.mp4")
    lg: dict = {}
    F.export_canvas_clip(src3, o3, [(0.0, 8.0)], (0.5, 0.5, 1.0),
                         bgm_path=ML.resolve(ML.PREFIX + dai["id"]),
                         bgm_tu_dong={"lufs": dai["lufs"], "transcript": {},
                                      "log": lg}, **kw)
    sl = _so_luong(o3)
    pk = 20 * np.log10(max(1e-9, float(np.max(np.abs(_pcm(o3))))))
    ok(abs(sl.get("video", 0) - 8.0) < 0.15
       and abs(sl.get("audio", 0) - 8.0) < 0.15,
       "video câm + nhạc -> độ dài khớp", str(sl))
    ok(-60 < pk <= -6, "video câm: nhạc có mà NHỎ (đặt mức tuyệt đối thấp)",
       f"đỉnh {pk:.1f} dBFS · {lg}")


def ca6() -> None:
    print("\n[CA 6] KHOÁ CHỐNG TRÙNG")
    sv = (REPO / "app" / "services.py").read_text("utf-8")
    ok("nhac_tu_dong" not in sv and "bgm_tu_dong" not in sv,
       "services.py không đổi vì nhạc tự chọn (khoá cũ y nguyên)")
    ok("bgm_path" in sv and re.search(r"hook_first, bgm_path, bgm_vol", sv),
       "khoá vẫn băm bgm_path -> chuỗi đánh dấu đổi khoá CHỈ khi bật")
    ok(NT.MA_TU_DONG.startswith(ML.PREFIX + "auto:")
       and NT.MA_TU_DONG.split(":", 2)[2] not in ML.MOODS,
       "chuỗi đánh dấu không trùng tâm trạng phóng sự")


def ca8() -> None:
    print("\n[CA 8] TRANG CHÍNH: mặc định video nào cũng có nhạc")
    from app.ui.studio_page import StudioPage

    class _Gia:
        _MUSIC_EXT = StudioPage._MUSIC_EXT

    def pick(L):
        g = _Gia()
        g.layout_tpl = L
        return StudioPage._pick_bgm(g)
    ok(pick({}) == NT.MA_TU_DONG, "mẫu chưa đặt gì -> TỰ CHỌN")
    ok(pick({"bgm_mode": "off"}) == NT.MA_TU_DONG, "mẫu cũ 'Tắt' -> TỰ CHỌN")
    ok(pick({"bgm_mode": "none"}) == "", "'Tắt hẳn' -> không nhạc")
    ok(pick({"bgm_mode": "fixed", "bgm_file": "Z:/khong/co.mp3"})
       == NT.MA_TU_DONG, "bài cố định MẤT file -> lùi TỰ CHỌN (không im)")
    d = tempfile.mkdtemp(prefix="bq106m_")
    ok(pick({"bgm_mode": "random", "bgm_dir": d}) == NT.MA_TU_DONG,
       "thư mục nhạc RỖNG -> lùi TỰ CHỌN")
    f = os.path.join(d, "a.mp3")
    Path(f).write_bytes(b"x")
    ok(pick({"bgm_mode": "random", "bgm_dir": d}) == f,
       "thư mục có nhạc -> giữ nguyên lựa chọn của anh")
    ok(pick({"bgm_mode": "fixed", "bgm_file": f}) == f,
       "bài cố định còn file -> giữ nguyên")


def ca9() -> None:
    print("\n[CA 9] ĐỘ TO NHẠC DO ANH HÙNG CHỌN + NÚT NGHE THỬ")
    import numpy as np
    ok(NT.ma_tu_dong(12) == NT.MA_TU_DONG and NT.ma_tu_dong(None)
       == NT.MA_TU_DONG, "mức MẶC ĐỊNH -> chuỗi đánh dấu CŨ (khoá không đổi)")
    ok(NT.muc_tu_ma(NT.ma_tu_dong(9)) == 9.0 and NT.la_tu_dong(NT.ma_tu_dong(9)),
       "mức 'To' (9 dB) mã hoá + đọc lại đúng")
    ok(NT.muc_tu_ma(NT.ma_tu_dong(99)) == NT.DUOI_LOI_MAX
       and NT.muc_tu_ma(NT.MA_TU_DONG + "@abc") == NT.DUOI_LOI_DB,
       "mức ngoài dải bị kẹp; chuỗi hỏng -> mặc định (không nổ)")
    from app.ui.studio_page import StudioPage

    class _Gia:
        _MUSIC_EXT = StudioPage._MUSIC_EXT
    g = _Gia()
    g.layout_tpl = {"bgm_mode": "auto", "bgm_auto_db": 6}
    ok(StudioPage._pick_bgm(g) == NT.MA_TU_DONG + "@6",
       "mẫu chọn 'Rất to' -> trang chính gửi đúng mức xuống job")
    m1 = (REPO / "app" / "modules" / "m1_highlight.py").read_text("utf-8")
    ok('"duoi_loi_db": _duoi_bgm' in m1, "m1 chuyền mức user chọn xuống xuất")
    # XUẤT THẬT: 'Rất to' (6) vs 'Rất nhỏ' (20) -> nhạc lệch ~14 dB
    d = tempfile.mkdtemp(prefix="bq106z_")
    src = os.path.join(d, "s.mp4")
    _sinh_nguon(src, False)
    bai = next(t for t in ML.catalog() if t["mood"] == "calm")
    kw = dict(bg="blur", out_w=540, out_h=960, encoder="libx264",
              fx_whoosh=False, hieu_ung="tat", chuyen_canh="tat")
    lv = {}
    F.export_canvas_clip(src, os.path.join(d, "k.mp4"), [(0.0, 12.0)],
                         (0.5, 0.5, 1.0), **kw)
    k = _pcm(os.path.join(d, "k.mp4"))
    for duoi in (6, 20):
        o = os.path.join(d, f"o{duoi}.mp4")
        F.export_canvas_clip(src, o, [(0.0, 12.0)], (0.5, 0.5, 1.0),
                             bgm_path=ML.resolve(ML.PREFIX + bai["id"]),
                             bgm_tu_dong={"lufs": bai["lufs"], "transcript": {},
                                          "duoi_loi_db": duoi, "log": {}}, **kw)
        a = _pcm(o)
        n = min(len(a), len(k))
        lv[duoi] = _db_cua_so(a[:n] - k[:n], 10.0, 10.4)
    ok(10.0 <= lv[6] - lv[20] <= 16.0, "'Rất to' to hơn 'Rất nhỏ' ~14 dB",
       f"{lv[6] - lv[20]:.1f} dB")
    # HÀM NGHE THỬ
    w = os.path.join(d, "n.wav")
    r = NT.dung_nghe_thu(w, mood="bright", duoi_db=12)
    ok(r.get("ok") and r.get("tam_trang") == "bright" and not r.get("co_loi")
       and abs(float(F.probe(w).duration) - 20.0) < 0.3,
       "nghe thử chưa chọn video: nhạc riêng 20 s, đúng tâm trạng chọn", str(r))
    w2 = os.path.join(d, "n2.wav")
    r2 = NT.dung_nghe_thu(w2, src=src, transcript={"segments": [
        {"start": 1.0, "end": 4.0, "text": "a"}]}, t0=0.0, dai=10)
    ok(r2.get("ok") and r2.get("co_loi")
       and abs(float(F.probe(w2).duration) - 10.0) < 0.3,
       "nghe thử với video: có tiếng video + nhạc, đúng độ dài", str(r2))
    pk = 20 * np.log10(max(1e-9, float(np.max(np.abs(_pcm(w2))))))
    ok(pk <= -0.5, "file nghe thử không méo", f"{pk:.2f} dBFS")
    r3 = NT.dung_nghe_thu(os.path.join(d, "n3.wav"), src="Z:/khong/co.mp4")
    ok(r3.get("ok") and not r3.get("co_loi"),
       "video không tồn tại -> vẫn nghe được nhạc riêng (không nổ)", str(r3))
    r4 = NT.dung_nghe_thu(os.path.join(d, "khong", "co", "thu_muc", "x.wav"))
    ok(r4.get("ok") is False and r4.get("loi"),
       "ghi file lỗi -> trả lỗi êm (không ném)", str(r4)[:80])
    # GIAO DIỆN THẬT: Chỉnh mẫu nhớ mức, nút nghe thử chạy, loa bị chặn
    from PyQt6.QtWidgets import QApplication
    from app.ui import theme
    from app.ui.editor import EditorDialog
    qa = QApplication.instance() or QApplication(sys.argv)
    qa.setStyleSheet(theme.QSS)
    dlg = EditorDialog("", {"bgm_mode": "auto", "bgm_auto_db": 9})
    ok(dlg._bgm_auto_db() == 9 and dlg.bgm_auto_muc.isEnabled()
       and dlg.bgm_nghe_btn.isEnabled() and "To" in dlg.bgm_auto_lbl.text(),
       "mở mẫu 'To' -> thanh kéo đúng chỗ, nhãn 'To', nút nghe thử bật",
       dlg.bgm_auto_lbl.text())
    ok(dlg._collect_layout().get("bgm_auto_db") == 9, "lưu mẫu giữ mức 'To'")
    # KÉO THANH (anh Hùng: "không kéo chỉnh được à"): kéo phải = to hơn
    dlg.bgm_auto_muc.setValue(dlg.bgm_auto_muc.maximum())
    ok(dlg._collect_layout().get("bgm_auto_db") == 4
       and "Rất to" in dlg.bgm_auto_lbl.text(),
       "kéo hết bên PHẢI -> nhạc to nhất (dưới lời 4 dB)", dlg.bgm_auto_lbl.text())
    dlg.bgm_auto_muc.setValue(dlg.bgm_auto_muc.minimum())
    ok(dlg._collect_layout().get("bgm_auto_db") == 24
       and "Rất nhỏ" in dlg.bgm_auto_lbl.text(),
       "kéo hết bên TRÁI -> nhạc nhỏ nhất (dưới lời 24 dB)")
    ok(NT.muc_tu_ma(NT.ma_tu_dong(24)) == 24 and NT.muc_tu_ma(NT.ma_tu_dong(4))
       == 4, "hai đầu thanh nằm TRONG dải app chấp nhận (không bị kẹp lệch)")
    ok(not dlg.bgm_vol.isVisibleTo(dlg),
       "chế độ tự chọn -> ẨN thanh 'Âm lượng nhạc' (của nhạc riêng) cho khỏi nhầm")
    dlg._dat_bgm_auto_db(9)
    dlg.bgm_mode.setCurrentIndex(dlg.bgm_mode.findData("none"))
    ok(not dlg.bgm_nghe_btn.isEnabled() and not dlg.bgm_auto_muc.isEnabled(),
       "'Tắt hẳn' -> khoá ô độ to + nút nghe thử")
    dlg.bgm_mode.setCurrentIndex(dlg.bgm_mode.findData("auto"))
    trc = len(_test_guard.DA_CHAN)
    dlg.bgm_nghe_btn.click()
    t = time.time()
    while time.time() - t < 30 and "Đang phát" not in dlg.bgm_nghe_lbl.text() \
            and "lỗi" not in dlg.bgm_nghe_lbl.text():
        qa.processEvents()
        time.sleep(0.05)
    ok("Đang phát" in dlg.bgm_nghe_lbl.text(), "bấm Nghe thử -> dựng + phát",
       dlg.bgm_nghe_lbl.text())
    ok(any("winsound.PlaySound" in x for x in _test_guard.DA_CHAN[trc:]),
       "test KHÔNG phát ra loa máy anh Hùng (guard chặn PlaySound)")
    # ĐÚNG TÌNH HUỐNG ANH HÙNG (ảnh 02/11/2026): mẫu dùng THƯ MỤC NHẠC RIÊNG
    # -> nút Nghe thử phải BẬT và phát nhạc của anh ở đúng thanh âm lượng
    tm = os.path.join(d, "nhac_rieng")
    os.makedirs(tm)
    subprocess.run([FF, "-nostdin", "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", "sine=f=440:d=30", "-c:a", "libmp3lame",
                    os.path.join(tm, "bai.mp3")], check=True, timeout=60,
                   creationflags=NW, stdin=subprocess.DEVNULL)
    dlg2 = EditorDialog("", {"bgm_mode": "random", "bgm_dir": tm,
                             "bgm_vol": 0.13})
    ok(dlg2.bgm_nghe_btn.isEnabled() and not dlg2.bgm_nghe_mood.isEnabled()
       and not dlg2.bgm_auto_muc.isEnabled() and "NHẠC CỦA ANH"
       in dlg2.bgm_nghe_lbl.text(),
       "mẫu THƯ MỤC NHẠC RIÊNG -> nút Nghe thử BẬT + dòng hướng dẫn rõ",
       dlg2.bgm_nghe_lbl.text()[:60])
    ok(dlg2.bgm_vol.isVisibleTo(dlg2) and dlg2.bgm_vol.isEnabled(),
       "nhạc riêng -> thanh 'Âm lượng nhạc' HIỆN và kéo được",
       dlg2.bgm_nghe_lbl.text()[:60])
    dlg2.bgm_nghe_btn.click()
    t = time.time()
    while time.time() - t < 30 and "Đang phát" not in dlg2.bgm_nghe_lbl.text() \
            and "lỗi" not in dlg2.bgm_nghe_lbl.text():
        qa.processEvents()
        time.sleep(0.05)
    ok("Đang phát" in dlg2.bgm_nghe_lbl.text()
       and "bai.mp3" in dlg2.bgm_nghe_lbl.text(),
       "bấm Nghe thử -> phát ĐÚNG bài trong thư mục của anh",
       dlg2.bgm_nghe_lbl.text()[:90])
    dlg2.done(0)
    dlg3 = EditorDialog("", {"bgm_mode": "fixed", "bgm_file": "Z:/mat.mp3"})
    dlg3.bgm_nghe_btn.click()
    qa.processEvents()
    # báo NGAY, không qua luồng nền (bản đầu báo trễ -> mục này nhấp nháy 1/4)
    ok("Chưa có file nhạc" in dlg3.bgm_nghe_lbl.text(),
       "bài cố định mất file -> báo NGAY lập tức", dlg3.bgm_nghe_lbl.text()[:80])
    ok("Chưa có file nhạc" in dlg3.bgm_nghe_lbl.text()
       or "không thấy file" in dlg3.bgm_nghe_lbl.text()
       or "lỗi" in dlg3.bgm_nghe_lbl.text(),
       "bài cố định mất file -> báo rõ, không nổ", dlg3.bgm_nghe_lbl.text()[:80])
    dlg3.done(0)
    # mức nghe thử nhạc riêng = đúng thanh âm lượng (0,13 vs 0,52 -> ~12 dB)
    w5, w6 = os.path.join(d, "v13.wav"), os.path.join(d, "v52.wav")
    NT.dung_nghe_thu(w5, nhac_file=os.path.join(tm, "bai.mp3"), vol=0.13)
    NT.dung_nghe_thu(w6, nhac_file=os.path.join(tm, "bai.mp3"), vol=0.52)
    lech = _db_cua_so(_pcm(w6), 5, 10) - _db_cua_so(_pcm(w5), 5, 10)
    ok(abs(lech - 12.04) < 1.5, "nghe thử nhạc riêng theo ĐÚNG thanh âm lượng",
       f"0,52 to hơn 0,13: {lech:.1f} dB (lý thuyết 12,0)")
    nut = [b.text() for b in dlg.findChildren(type(dlg.bgm_nghe_btn))
           if b in (dlg.bgm_nghe_btn, dlg.bgm_dung_btn)]
    ok(all(not re.search(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", x)
           for x in nut), "nhãn nút mới KHÔNG emoji", str(nut))
    dlg.done(0)


def ca7() -> None:
    print("\n[CA 7] NỐI ĐÚNG CHỖ")
    m1 = (REPO / "app" / "modules" / "m1_highlight.py").read_text("utf-8")
    t = ast.parse(m1)
    goi = [n for n in ast.walk(t) if isinstance(n, ast.Call)
           and getattr(n.func, "id", "") == "export_canvas_clip"]
    kws = {k.arg: k.value for c in goi for k in c.keywords}
    ok("bgm_tu_dong" in kws and isinstance(kws["bgm_tu_dong"], ast.Name),
       "m1 truyền bgm_tu_dong là BIẾN (không hằng số)")
    ok(isinstance(kws.get("bgm_path"), ast.Name)
       and kws["bgm_path"].id == "_bgm_xuat",
       "bgm_path đi qua bước chọn (_bgm_xuat)")
    ok("except Exception as _e_bgm" in m1, "lỗi kho nhạc không giết clip")
    ed = (REPO / "app" / "ui" / "editor.py").read_text("utf-8")
    ok('"auto"' in ed and "Tự chọn theo nội dung" in ed,
       "Chỉnh mẫu có lựa chọn 'Tự chọn theo nội dung'")
    sp = (REPO / "app" / "ui" / "studio_page.py").read_text("utf-8")
    ok("MA_TU_DONG" in sp, "trang chính trả chuỗi đánh dấu khi chọn tự động")


if __name__ == "__main__":
    for ca in (ca1, ca2, ca3, ca4, ca5, ca5b, ca6, ca7, ca8, ca9):
        try:
            ca()
        except Exception as e:  # noqa: BLE001
            HONG += 1
            print(f"  HỎNG {ca.__name__} NỔ: {type(e).__name__}: {e}")
    print(f"\nCỔNG 106: ĐẠT {DAT} · HỎNG {HONG}")
    sys.exit(1 if HONG else 0)
