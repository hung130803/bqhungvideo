# -*- coding: utf-8 -*-
"""ĐO HAI Ô ÂM LƯỢNG của hộp Thay giọng nói (v2.42.0, 20/08/2026).

Anh Hùng: *"cái phần âm thanh gốc nó nói bé k tuỳ chỉnh âm thanh đc à chứ to
quá"*. Bộ đo này trả lời ba câu, bằng SỐ trên file ffmpeg xuất THẬT:

  1. **MẶC ĐỊNH có đổi tiếng không?** So bản đang test với BẢN MỐC lấy từ git
     (`--moc`, mặc định `v2.41.1` = bản NGAY TRƯỚC việc này) trên CÙNG một
     nguồn. Lệch 0,00 ở mọi cột thì mới được nói "không đổi".
  2. **Kéo ô có tác dụng thật không**, và theo đúng chiều nào.
  3. **Trần an toàn có giữ không** — đo `Abs_Peak_count` (số mẫu chạm trần),
     là thước DUY NHẤT bắt được "hạn đỉnh gọt trên tiếng nói". I và TP KHÔNG
     bắt được vì `chuan_do_to` chạy SAU nên chúng luôn đúng đích.

**DÙNG `settings.FFMPEG_PATH`, KHÔNG ghi cứng `bin/ffmpeg.exe`** — 21 file
`_test_*.py` đang ghi cứng nó và bản trong `bin/` từng là build 2023 THIẾU
`Abs_Peak_count`, tức đo một ffmpeg KHÁC ffmpeg sản xuất (cổng 86).
`kiem_ffmpeg()` TỰ KIỂM BỘ ĐO trước khi đo bất cứ gì.

**TÊN CHỈ SỐ vs DÒNG IN RA:** tham số là `Abs_Peak_count` (gạch dưới), dòng in
ra là `Abs Peak count:` (dấu cách). Và mỗi dòng `astats` mở đầu bằng
`[Parsed_astats_0 @ ...]` nên phải dùng `in`, **KHÔNG `startswith`**.

**LẶP LẠI ĐƯỢC TỚI ĐÂU — ĐO RỒI, ĐỌC CHO ĐÚNG.** Trong CÙNG một tiến trình:
3 lượt / cấu hình ra **trải 0,00** ở cả I · TP · mẫu chạm trần (đo 20/08/2026).
Nhưng QUA NHIỀU LƯỢT CHẠY KHÁC NHAU, cột `TP` của mấy cấu hình có kéo ô lệch
tới **0,44 dB** (nền +6 đo được −4,23 / −4,46 / −4,67) trong khi `I` chỉ nhích
0,01-0,02 LU — dạng lệch của **bộ nén AAC tự chọn số luồng theo tải máy**, nhắm
vào ĐỈNH chứ không vào độ to. Cấu hình **MẶC ĐỊNH thì đứng yên −4,91 ở MỌI
lượt** và khớp bản mốc 0,0000, nên bất biến số 1 không bị ảnh hưởng. Đừng đọc
0,2-0,4 dB TP giữa hai lượt là "hồi quy" (bài học *"đo A/B phải đan xen"*):
biên tới trần ở đây là ~3,7 dB, gấp 8 lần mức lệch đó.

Chạy: `.venv\\Scripts\\python _do_muc_am.py [--moc v2.41.1]`
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import types
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

# HỘP CÁT: đặt TRƯỚC khi nạp config, không thì ghi vào DATA_DIR THẬT của app.
os.environ["BQ_DATA_DIR"] = tempfile.mkdtemp(prefix="bq_docam_")

from config import settings                                    # noqa: E402

FF = settings.FFMPEG_PATH
_NW = 0x0800_0000 if os.name == "nt" else 0

# ---- nguồn tổng hợp (cùng khuôn cổng 86, cùng lý do) ----
#: Nguồn TỰ SINH bằng `lavfi` nên bộ đo KHÔNG phụ thuộc file trên máy (bài học
#: cổng 68: ghi cứng tên file làm cổng ĐỎ OAN vì KHO chứ không vì mã).
TONG = 40.0
#: Giọng gốc NGẮT NHỊP từng "từ" (0,35 s tiếng / 0,15 s nghỉ). BẮT BUỘC ngắt
#: nhịp: nguồn liên tục thì `_san_nhieu` (bách phân vị 20) rơi vào GIỮA tiếng
#: nói -> mọi bộ dò TỰ ĐẠT OAN (bẫy đã sập khi dựng cổng 86).
NHIP = "lt(mod(t,0.5),0.35)"
GOC_NOI = (1.0, 38.0)
LONG_DEN = 34.0
DAI_LO, DAI_HI = 300, 3400
BUOC = 0.05


def _ff(args: list[str], what: str) -> None:
    r = subprocess.run([FF, "-v", "error", "-nostdin", "-y", *args],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=_NW, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError(f"{what}: rc={r.returncode} {(r.stderr or '')[:300]}")


def kiem_ffmpeg() -> None:
    """TỰ KIỂM BỘ ĐO trước khi đo. 4 phép — checklist 5-filter cũ ĐẠT OAN."""
    r = subprocess.run([FF, "-version"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", creationflags=_NW)
    ban = (r.stdout or "").splitlines()[0] if r.stdout else "?"
    print(f"  ffmpeg = {ban}")
    print(f"  settings.FFMPEG_PATH = {FF!r}  (KHÔNG ghi cứng bin/ffmpeg.exe)")
    h = subprocess.run([FF, "-h", "filter=astats"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       creationflags=_NW)
    n = (h.stdout or "").count("Abs_Peak_count")
    print(f"  `Abs_Peak_count` trong -h filter=astats: {n} lần "
          f"{'OK' if n else 'THIẾU -> build cũ, DỪNG'}")
    if not n:
        raise SystemExit("ffmpeg này KHÔNG có Abs_Peak_count — đổi ffmpeg")
    for f in ("alimiter", "loudnorm", "sidechaincompress", "ebur128"):
        q = subprocess.run([FF, "-hide_banner", "-filters"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", creationflags=_NW)
        assert re.search(rf"\s{f}\s", q.stdout or ""), f"thiếu filter {f}"
    print("  4 filter alimiter · loudnorm · sidechaincompress · ebur128: đủ")


# ==================================================================
# BA THƯỚC ĐỘC LẬP
# ==================================================================
def do_loudnorm(path: str | Path) -> dict:
    """I · TP · LRA bằng **pha ĐO của `loudnorm`** (thước 1)."""
    r = subprocess.run(
        [FF, "-v", "info", "-nostdin", "-i", str(path), "-af",
         "loudnorm=print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=_NW, timeout=1800)
    m = re.findall(r"\{[^{}]*input_i[^{}]*\}", (r.stderr or ""), re.S)
    if not m:
        raise RuntimeError(f"loudnorm KHÔNG in JSON (rc={r.returncode}) — "
                           f"đây đúng họ bẫy 'ffmpeg mã 0 mà kết quả sai'")
    d = json.loads(m[-1])
    return {"I": float(d["input_i"]), "TP": float(d["input_tp"]),
            "LRA": float(d["input_lra"])}


def do_ebur128(path: str | Path) -> dict:
    """I bằng **`ebur128`** (thước 2 — bộ đo KHÁC HẲN, không dùng chung mã)."""
    r = subprocess.run(
        [FF, "-v", "info", "-nostdin", "-i", str(path), "-af",
         "ebur128=peak=true:framelog=quiet", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=_NW, timeout=1800)
    e = r.stderr or ""
    kq: dict = {}
    for ten, khoa in (("I", r"I:\s*(-?\d+\.?\d*)\s*LUFS"),
                      ("LRA", r"LRA:\s*(-?\d+\.?\d*)\s*LU")):
        m = re.findall(khoa, e)
        if m:
            kq[ten] = float(m[-1])
    return kq


def do_astats(path: str | Path) -> dict:
    """Đỉnh MẪU + **số mẫu CHẠM TRẦN** (`Abs_Peak_count`) — thước 3.

    BẪY (cổng 44/53/86): mỗi dòng mở đầu bằng `[Parsed_astats_0 @ ...]` nên
    phải dùng `in`, KHÔNG `startswith`. Và tên tham số `Abs_Peak_count` (gạch
    dưới) KHÁC dòng in ra `Abs Peak count:` (dấu cách) — dò sai dạng là kết
    luận oan "thiếu chỉ số" trên một ffmpeg CÓ ĐỦ.
    """
    r = subprocess.run(
        [FF, "-v", "info", "-nostdin", "-i", str(path), "-af",
         "astats=measure_overall=Peak_level+Abs_Peak_count+RMS_level:"
         "measure_perchannel=none", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=_NW, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError(f"astats rc={r.returncode} — build ffmpeg cũ? "
                           f"{(r.stderr or '')[:200]}")
    kq: dict = {}
    for dong in (r.stderr or "").splitlines():
        if "Peak level dB:" in dong:
            kq["dinh_dbfs"] = float(dong.rsplit(":", 1)[1])
        elif "Abs Peak count:" in dong:       # `in`, KHÔNG `startswith`
            kq["cham_tran"] = int(float(dong.rsplit(":", 1)[1]))
        elif "RMS level dB:" in dong:
            kq["rms_dbfs"] = float(dong.rsplit(":", 1)[1])
    if "cham_tran" not in kq:
        raise RuntimeError("KHÔNG thấy dòng `Abs Peak count:` — ffmpeg thiếu "
                           "chỉ số, mọi kết luận về vỡ tiếng sẽ là oan")
    return kq


def sang_aac(wav: str | Path, out: str | Path) -> str:
    """Nén AAC 192k — ĐÚNG codec/bitrate `thay_audio_video` dùng.

    Phải đo TRÊN BẢN NÉN: `alimiter` chặn đỉnh MẪU nên đỉnh THẬT vọt +0,06 dB,
    rồi **AAC vọt tiếp tới +0,19 dB** (cổng 65). Đo mỗi lớp wav là bỏ qua đúng
    cái đã làm bản e2e v2.30.0 ra +0,04 dBTP (vỡ tiếng).
    """
    _ff(["-i", str(wav), "-c:a", "aac", "-b:a", "192k", str(out)], "nén AAC")
    return str(out)


# ==================================================================
# NGUỒN
# ==================================================================
def dung_nguon(d: Path) -> dict:
    """'Video gốc' tổng hợp: nền dải trầm + giọng gốc ngắt nhịp + mảnh lồng.

    **`anoisesrc` BẮT BUỘC có `s=` (seed)** — không thì mỗi lượt một mẻ ồn khác
    nhau và bộ đo nhấp nháy, rồi mọi phép so "trước/sau" thành vô nghĩa.
    """
    d.mkdir(parents=True, exist_ok=True)
    nhac, giong, goc = d / "nhac.wav", d / "giong_goc.wav", d / "goc.wav"
    _ff(["-f", "lavfi", "-i", f"anoisesrc=d={TONG}:c=pink:a=0.6:s=12345",
         "-af", "lowpass=f=300,lowpass=f=300,volume=0.5,aresample=44100",
         "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(nhac)],
        "dựng lớp nhạc")
    a, b = GOC_NOI
    _ff(["-f", "lavfi", "-i", f"anoisesrc=d={TONG}:c=white:a=0.9:s=777",
         "-af", f"highpass=f={DAI_LO},lowpass=f={DAI_HI},"
                f"volume='if(between(t,{a},{b})*{NHIP},1.0,0)':eval=frame,"
                f"aresample=44100",
         "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(giong)],
        "dựng lớp giọng gốc")
    _ff(["-i", str(nhac), "-i", str(giong), "-filter_complex",
         "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[o]",
         "-map", "[o]", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le",
         str(goc)], "trộn audio gốc")
    manh = d / "long_0.wav"
    _ff(["-f", "lavfi", "-i",
         f"anoisesrc=d={LONG_DEN - a}:c=white:a=0.9:s=555",
         "-af", f"highpass=f={DAI_LO},lowpass=f={DAI_HI},"
                f"volume='if({NHIP},0.9,0)':eval=frame,aresample=44100",
         "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(manh)],
        "dựng mảnh giọng lồng")
    return {"nhac": str(nhac), "giong": str(giong), "goc": str(goc),
            "manh": [(a, str(manh))]}


# ==================================================================
# GIỌNG NỔI TRÊN NỀN — ĐO LÚC ĐANG NÓI, không phải RMS cả track
# ==================================================================
def noi_tren_nen(TG, kq: dict, nen_wav: str, d: Path, ten: str) -> dict:
    """Giọng cao hơn nền bao nhiêu dB **LÚC ĐANG NÓI**.

    **PHẢI ĐO LÚC ĐANG NÓI:** track giọng ~30% là im lặng nên RMS toàn bài thấp
    giả tạo (bài học 15/08 — cùng bẫy "nền đo bằng `mean_volume`").

    Cách đo: dựng lại HAI NHÁNH đúng như `tron_thay_giong` đưa vào `amix` (lớp
    giọng đã nén × `gain_giong_db`, lớp nền × `gain_nhac_db`) rồi đo bằng
    `do_giong_tren_nhac` — CÙNG một phép cho MỌI cấu hình nên số so được với
    nhau. Không tự chấm bằng `can_bang_giong_nhac` (hàm TÍNH hệ số tự chấm
    mình là tự cấp chứng chỉ).
    """
    gg = float(kq["gain_giong_db"])
    gn = float(kq["gain_nhac_db"])
    g_wav, n_wav = d / f"nh_g_{ten}.wav", d / f"nh_n_{ten}.wav"
    _ff(["-i", str(kq["giong_da_nen"]), "-af", f"volume={gg:.2f}dB",
         "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(g_wav)],
        "nhánh giọng")
    _ff(["-i", nen_wav, "-af", f"volume={gn:.2f}dB",
         "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(n_wav)],
        "nhánh nền")
    return TG.do_giong_tren_nhac(g_wav, n_wav)


def loi_tren_im(mix: str, d: Path, ten: str) -> float:
    """ĐỐI CHỨNG ĐỘC LẬP — không dùng một con số nào do hàm đo tự báo.

    Lọc bản trộn về DẢI LỜI rồi so mức ở cửa sổ **giọng lồng đang nói** với cửa
    sổ **giọng lồng đã hết** (sau `LONG_DEN`, chỗ chỉ còn nền). Kéo ô âm lượng
    làm số này đổi; nó là phép kiểm chéo cho cột `noi_tren_nen` ở trên.
    """
    from app.core import thay_giong as TG
    loc = d / f"loc_{ten}.wav"
    _ff(["-i", mix, "-af",
         f"highpass=f={DAI_LO},lowpass=f={DAI_HI},aresample=44100",
         "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(loc)],
        "lọc dải lời")
    bao = TG.duong_bao_muc(loc, buoc=BUOC)
    if not bao:
        return float("nan")
    n = len(bao)
    i_het = int(LONG_DEN / BUOC)
    noi = [x for x in bao[int(2.0 / BUOC):i_het] if x > -100]
    im = [x for x in bao[i_het + int(1.0 / BUOC):n - int(1.0 / BUOC)]
          if x > -100]
    if len(noi) < 5 or len(im) < 5:
        return float("nan")
    noi.sort()
    im.sort()
    return round(noi[len(noi) // 2] - im[len(im) // 2], 2)


# ==================================================================
def nap_moc(duong: str, ten: str, moc: str) -> types.ModuleType:
    """Nạp một file của BẢN MỐC thành module riêng (không đụng bản đang test)."""
    r = subprocess.run(["git", "show", f"{moc}:{duong}"], cwd=str(REPO),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    if r.returncode != 0 or not (r.stdout or "").strip():
        raise RuntimeError(f"không lấy được {moc}:{duong}: {r.stderr[:200]}")
    m = types.ModuleType(f"moc_{ten}")
    m.__dict__["__file__"] = str(REPO / duong)      # để `Path(__file__)` còn đúng
    m.__dict__["_NGUON_"] = r.stdout
    exec(compile(r.stdout, f"<{moc}:{duong}>", "exec"), m.__dict__)
    return m


def mot_luot(TG, nguon: dict, d: Path, ten: str, ma: str, nen_khoa: str,
             muc_nen: float = 0.0, muc_giong: float = 0.0) -> dict:
    """Một cấu hình: trộn THẬT -> nén AAC -> đo đủ 3 thước.

    `ten` = nhãn cho người đọc · `ma` = TÊN FILE. Tách hai thứ vì nhãn có `/`
    và dấu tiếng Việt, mà `/` trong tên file làm ffmpeg ném *"No such file or
    directory"* — rc=4294967294, không phải lỗi âm thanh nào (đã sập một lần).
    """
    d.mkdir(parents=True, exist_ok=True)
    ten = ten           # nhãn hiển thị
    out = d / f"tron_{ma}.wav"
    kw = {}
    if muc_nen or muc_giong:
        kw = {"muc_nhac_db": muc_nen, "muc_giong_db": muc_giong}
    kq = TG.tron_thay_giong(nguon[nen_khoa], nguon["manh"], TONG, out,
                            goc_wav=nguon["goc"], **kw)
    aac = sang_aac(out, d / f"tron_{ma}.m4a")
    ln, eb, st = do_loudnorm(aac), do_ebur128(aac), do_astats(aac)
    st_wav = do_astats(out)
    nn = noi_tren_nen(TG, kq, nguon[nen_khoa], d, ma)
    return {
        "ten": ten,
        "I_loudnorm": ln["I"], "I_ebur128": eb.get("I"),
        "lech_2_thuoc": round(abs(ln["I"] - eb["I"]), 2) if eb.get("I") else None,
        "TP": ln["TP"], "LRA": ln["LRA"],
        "dinh_wav": st_wav["dinh_dbfs"], "cham_tran_wav": st_wav["cham_tran"],
        "dinh_aac": st["dinh_dbfs"], "cham_tran_aac": st["cham_tran"],
        "gain_giong_db": kq["gain_giong_db"], "gain_nhac_db": kq["gain_nhac_db"],
        "muc_tay_nen": kq.get("muc_tay_nen_db"),
        "muc_tay_giong": kq.get("muc_tay_giong_db"),
        "kep": bool((kq.get("muc_tay_kep") or {}).get("bi_kep")),
        "kep_vi_sao": (kq.get("muc_tay_kep") or {}).get("vi_sao", ""),
        "noi_tren_nen_tb": nn.get("giong_tren_nhac_tb"),
        "ty_le_chim": nn.get("ty_le_chim"),
        "loi_tren_im": loi_tren_im(str(out), d, ma),
        "do_dai": kq["do_dai"],
    }


COT = [("I_loudnorm", "I loudnorm", "{:+.2f}"),
       ("I_ebur128", "I ebur128", "{:+.2f}"),
       ("lech_2_thuoc", "lệch 2 thước", "{:.2f}"),
       ("TP", "TP dBTP", "{:+.2f}"),
       ("dinh_aac", "đỉnh AAC dBFS", "{:+.3f}"),
       ("cham_tran_aac", "mẫu chạm trần AAC", "{:d}"),
       ("cham_tran_wav", "mẫu chạm trần WAV", "{:d}"),
       ("gain_nhac_db", "hệ số NỀN dB", "{:+.2f}"),
       ("gain_giong_db", "hệ số GIỌNG dB", "{:+.2f}"),
       ("noi_tren_nen_tb", "giọng NỔI trên nền dB", "{:+.2f}"),
       ("ty_le_chim", "% cửa sổ chìm", "{:.1f}"),
       ("loi_tren_im", "đối chứng: lời trên nền dB", "{:+.2f}"),
       ("LRA", "LRA", "{:.2f}"),
       ("do_dai", "độ dài s", "{:.3f}")]


def bang(ds: list[dict]) -> None:
    ten = [x["ten"] for x in ds]
    w = max(24, *[len(t) + 2 for t in ten])
    print("\n| " + "chỉ số".ljust(26) + " | "
          + " | ".join(t.rjust(w) for t in ten) + " |")
    print("|" + "-" * 28 + "|" + "|".join(["-" * (w + 2)] * len(ten)) + "|")
    for khoa, nhan, dang in COT:
        o = []
        for x in ds:
            v = x.get(khoa)
            o.append("—".rjust(w) if v is None
                     else dang.format(v).rjust(w))
        print("| " + nhan.ljust(26) + " | " + " | ".join(o) + " |")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--moc", default="v2.41.1",
                    help="tag bản MỐC (bản NGAY TRƯỚC việc này)")
    ap.add_argument("--giu", action="store_true", help="giữ hộp cát")
    a = ap.parse_args()

    print("=" * 78)
    print("ĐO HAI Ô ÂM LƯỢNG — hộp Thay giọng nói")
    print("=" * 78)
    print("\n[0] TỰ KIỂM BỘ ĐO")
    kiem_ffmpeg()

    hop = Path(tempfile.mkdtemp(prefix="bq_docam_hop_"))
    try:
        from app.core import thay_giong as TG
        print(f"\n[1] DỰNG NGUỒN (seed cố định, {TONG:.0f}s)")
        d0 = hop / "nguon"
        nguon = dung_nguon(d0)
        for k in ("nhac", "goc"):
            print(f"  {k}: {do_loudnorm(nguon[k])['I']:+.2f} LUFS")

        print(f"\n[2] BẢN MỐC {a.moc} — cấu hình MẶC ĐỊNH")
        moc = nap_moc("app/core/thay_giong.py", "tg", a.moc)
        assert moc.__dict__["_NGUON_"] != \
            (REPO / "app/core/thay_giong.py").read_text(encoding="utf-8"), \
            "bản mốc TRÙNG bản đang test — đây là cổng PASS OAN, DỪNG"
        assert "chuan_muc_db" not in moc.__dict__["_NGUON_"], \
            "bản mốc ĐÃ CÓ chuan_muc_db -> chọn sai mốc"
        print("  mốc KHÁC bản đang test: OK · KHÔNG có `chuan_muc_db`: OK")
        r_moc = mot_luot(moc, nguon, hop / "moc", f"MỐC {a.moc}", "moc",
                         "nhac")

        print("\n[3] BẢN ĐANG TEST — 4 cấu hình")
        ket = [r_moc]
        for ten, ma, mn, mg in (
                ("mặc định 0+0", "md", 0.0, 0.0),
                ("tăng NỀN +3", "nen3", 3.0, 0.0),
                ("tăng NỀN +6", "nen6", 6.0, 0.0),
                ("tăng GIỌNG +3", "gi3", 0.0, 3.0),
                ("tăng GIỌNG +6", "gi6", 0.0, 6.0),
                ("hạ cả hai -6", "ha6", -6.0, -6.0)):
            print(f"  ... {ten}")
            ket.append(mot_luot(TG, nguon, hop / "nay", ten, ma, "nhac",
                                mn, mg))

        bang(ket)
        print("\n  ĐỌC CỘT `LRA` CỦA BẢNG NÀY CHO ĐÚNG — ĐÂY LÀ SỐ LỪA:")
        print("  nguồn tổng hợp có ~6 s gần câm ở cuối. Cửa chặn TƯƠNG ĐỐI của")
        print("  BS.1770 (-20 LU dưới độ to chưa chặn) hoặc GIỮ hoặc BỎ cả khúc")
        print("  đó tuỳ mức giọng, nên LRA nhảy 17,50 -> 0,10 là do KHÚC IM")
        print("  lọt/không-lọt cửa chặn, **KHÔNG** phải 'nén dập dải động'.")
        print("  Cột đứng vững ở đây là I · TP · mẫu chạm trần · giọng nổi trên")
        print("  nền. Muốn đọc LRA thì phải đo trên nguồn THẬT không có khúc câm.")

        # ---- BẤT BIẾN 1: MẶC ĐỊNH KHÔNG ĐỔI TIẾNG ----
        print("\n" + "=" * 78)
        print("BẤT BIẾN 1 — MẶC ĐỊNH phải cho ra số GIỐNG BẢN MỐC")
        print("=" * 78)
        md = ket[1]
        xau = []
        for khoa, nhan, dang in COT:
            if khoa == "lech_2_thuoc":
                continue
            x, y = r_moc.get(khoa), md.get(khoa)
            if x is None or y is None:
                continue
            dl = abs(float(x) - float(y))
            if dl > 1e-9:
                xau.append(f"{nhan}: mốc {x} -> nay {y} (lệch {dl:+.4f})")
            print(f"  {nhan.ljust(26)} mốc {dang.format(x).rjust(10)}  ->  "
                  f"nay {dang.format(y).rjust(10)}   lệch {dl:.4f}"
                  f"{'   <-- KHÁC!' if dl > 1e-9 else ''}")
        print(f"\n  => {'ĐẠT: 0 cột lệch' if not xau else 'HỎNG: ' + '; '.join(xau)}")

        # ---- BẤT BIẾN 2: HAI THƯỚC ĐỘ TO ĐỒNG Ý ----
        print("\n" + "=" * 78)
        print("BẤT BIẾN 2 — HAI thước độ to độc lập, ngưỡng 0,5 LU")
        print("=" * 78)
        print("  ĐỌC ĐÚNG NGƯỠNG NÀY: hai thước chỉ chắc chắn đồng ý trong")
        print("  VÙNG HIỆU CHUẨN. Trên nguồn dải động RỘNG chúng lệch 0,5-1,3")
        print("  LU mà KHÔNG thước nào hỏng (cửa chặn TƯƠNG ĐỐI của BS.1770 làm")
        print("  khối 400 ms lật vào/ra khác nhau) — nới ngưỡng cho hết đỏ là")
        print("  đúng lúc mất khả năng bắt một thước hỏng thật.")
        te = []
        for x in ket:
            l = x.get("lech_2_thuoc")
            k = l is not None and l <= 0.5
            if not k:
                te.append(f"{x['ten']}: lệch {l}")
            print(f"  {x['ten'].ljust(20)} loudnorm {x['I_loudnorm']:+.2f} · "
                  f"ebur128 {x['I_ebur128']:+.2f} · lệch {l:.2f} LU  "
                  f"{'OK' if k else 'VƯỢT 0,5 -> DỪNG'}")
        print(f"\n  => {'ĐẠT' if not te else 'HỎNG: ' + '; '.join(te)}")

        # ---- BẤT BIẾN 3: TRẦN AN TOÀN ----
        print("\n" + "=" * 78)
        print("BẤT BIẾN 3 — TRẦN AN TOÀN: đỉnh + mẫu chạm trần")
        print("=" * 78)
        tran = TG.TRAN_DINH_THAT_DBTP
        print(f"  trần TP đích = {tran:+.2f} dBTP (biên trừ HAI LẦN: "
              f"alimiter {TG.TRAN_DINH_THAT_DBTP - TG.BIEN_DINH_THAT_DB:+.2f})")
        vuot = [x for x in ket if x["TP"] > tran]
        print(f"  bản vượt trần TP: {len(vuot)}/{len(ket)}"
              + (" -> " + ", ".join(f"{x['ten']} {x['TP']:+.2f}" for x in vuot)
                 if vuot else ""))
        print(f"  trần đỉnh lớp giọng cho phần TĂNG TAY = "
              f"{TG.DINH_GIONG_TAY_TOI_DA_DB:+.2f} dBFS")
        for x in ket:
            print(f"  {x['ten'].ljust(20)} chạm trần WAV {x['cham_tran_wav']:>6} · "
                  f"AAC {x['cham_tran_aac']:>6} · kẹp={x['kep']}"
                  + (f" ({x['kep_vi_sao'][:60]})" if x["kep"] else ""))

        # ---- THỬ PHÁ: trần có RĂNG hay chỉ để trang trí ----
        # Bản MỐC nhận `muc_giong_db` mà KHÔNG kẹp gì cả — nó chính là "thế
        # giới không có trần". Không có arm này thì mọi con số ở trên chỉ chứng
        # minh "trần không làm hỏng gì", KHÔNG chứng minh "trần có tác dụng"
        # (đúng bài học "cổng PASS OAN": chốt phải FAIL được).
        print("\n" + "=" * 78)
        print("THỬ PHÁ — GỠ TRẦN RA THÌ CÓ VỠ TIẾNG THẬT KHÔNG")
        print("=" * 78)
        pha = []
        for xin in (6.0, 9.0, 12.0):
            r = mot_luot(moc, nguon, hop / "pha", f"MỐC không trần +{xin:.0f}",
                         f"pha{xin:.0f}", "nhac", 0.0, xin)
            pha.append(r)
        r6 = [x for x in ket if x["ten"] == "tăng GIỌNG +6"][0]
        bang([md, r6] + pha)
        moc6 = pha[0]
        print("\n  cùng XIN +6 dB:")
        print(f"    CÓ trần (bản này) : hệ số THẬT {r6['gain_giong_db']:+.2f} dB "
              f"· chạm trần WAV {r6['cham_tran_wav']} · đỉnh AAC "
              f"{r6['dinh_aac']:+.3f} dBFS")
        print(f"    KHÔNG trần (mốc)  : hệ số THẬT {moc6['gain_giong_db']:+.2f} dB "
              f"· chạm trần WAV {moc6['cham_tran_wav']} · đỉnh AAC "
              f"{moc6['dinh_aac']:+.3f} dBFS")
        rang = max(x["cham_tran_wav"] for x in pha) > md["cham_tran_wav"]
        print(f"\n  => thước CÓ RĂNG: {rang} — gỡ trần ra thì số mẫu chạm trần "
              f"nhảy {md['cham_tran_wav']} -> "
              f"{max(x['cham_tran_wav'] for x in pha)}")
        if not rang:
            print("     (KHÔNG nhảy => thước này KHÔNG chứng minh được gì về "
                  "trần, đừng đọc nó là 'trần an toàn')")
        return 0 if (not xau and not te and not vuot) else 1
    finally:
        if not a.giu:
            import shutil
            shutil.rmtree(hop, ignore_errors=True)
            shutil.rmtree(os.environ["BQ_DATA_DIR"], ignore_errors=True)
        else:
            print(f"\nhộp cát GIỮ LẠI: {hop}")


if __name__ == "__main__":
    raise SystemExit(main())
