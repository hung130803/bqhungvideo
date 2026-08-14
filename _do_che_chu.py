# -*- coding: utf-8 -*-
"""ĐO `app/core/che_chu.py` trên VIDEO THẬT của anh Hùng.

Ba phép đo, chạy riêng được (`python _do_che_chu.py do|che|viet|tat`):
  do   — TỈ LỆ DÒ ĐÚNG trên nhiều MỐC THỜI GIAN + TỈ LỆ DÒ NHẦM trên video
         KHÔNG có chữ (ca sai nguy hiểm nhất: che nhầm = hỏng hình).
  che  — so 2 cách che (mờ / khối đặc / hạt to) : thời gian + chữ còn đọc được.
  viet — viết chữ MỚI (Việt + Trung) đè lên dải đã che.

BỘ ĐỐI CHỨNG — SỰ THẬT GHI THEO TỪNG CỬA SỔ 20 GIÂY, xác nhận BẰNG MẮT (ảnh
dải đáy ở giữa mỗi cửa sổ, xem `_do_che_chu/bang/cua_so/`). Nhãn P_/N_ chỉ là
TÊN, sự thật nằm ở bảng `SU_THAT` bên dưới.
  BẪY ĐÃ SẬP KHI LÀM VIỆC NÀY: nhãn ban đầu ghi "10 video Mỹ = KHÔNG CÓ CHỮ",
  soi kỹ thì 3 video có chữ cháy THẬT ở vài cửa sổ (`en4` end-card "CHECK OUT
  THIS VIDEO", `en9` một câu phụ đề, `en10` "6:00AM" + @handle). Lấy nhãn
  CẢ-VIDEO làm sự thật thì 3 lần dò ĐÚNG bị đếm thành "dò nhầm" — tức là tự
  bịa ra một con số xấu rồi đi chỉnh ngưỡng theo nó.

LUẬT: KHÔNG đụng video gốc trong Downloads\\Video (chỉ đọc / cắt ra sandbox).
Mỗi lượt chỉ 1 ffmpeg (BQ_FFMPEG_SLOTS=1) — máy anh Hùng đang chạy việc thật.
"""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

from app.core import che_chu as C            # noqa: E402

SAN = Path(os.environ.get("BQ_CHE_CHU_SAN", r"D:\claude\_do_che_chu"))
NGUON = SAN / "nguon"
RA = SAN / "ra"
KHUNG = SAN / "khung"
V = Path(r"C:\Users\Admin\Downloads\Video")
DY = V / "Kênh Douyin — 20 video"


def _bo() -> list:
    """[(nhãn, đường dẫn, CÓ CHỮ hay không)] — nhãn P_=có chữ, N_=không."""
    ds = [("P_zh_ep12", NGUON / "zh_ep12.mp4", True),
          ("P_zh_dongho", NGUON / "zh_dongho.mp4", True)]
    for i, f in enumerate(sorted(DY.glob("*.mp4")), 1):
        ds.append((f"P_dy{i}", f, True))
    am = ["DaddyOFive.mp4", "DaddyOFive Ryan Missed the Bus!!!.mp4",
          "Daddy O Five - The Purge Prank (Scary).mp4",
          "KID STARTS A FIRE DaddyOFive Re Upload.mp4",
          "DaddyOFive - KID STEALS BROTHER'S XBOX on (922016).mp4",
          "GOING BACK TO OUR OLD HOUSE.mp4",
          "DAD VS JAKE IN NERF WAR!!.mp4",
          "HILARIOUS FAMILY GYMNASTICS CHALLENGE!!!.mp4",
          "GETTING OUR GOLDEN RETRIEVER PUPPY.mp4",
          "Surprise Vacation (First Trip w Ava).mp4"]
    for i, n in enumerate(am, 1):
        ds.append((f"N_en{i}", V / n, False))
    return [(a, b, c) for a, b, c in ds if Path(b).exists()]


# ──────────────────────────── PHÉP ĐO 1 — DÒ ────────────────────────────────
SO_CUA = 8
DAI_CUA = 20.0

#: SỰ THẬT từng cửa sổ (8 cửa × 20 s, rải đều). 1 = dải đáy CÓ chữ cháy ở mốc
#: giữa cửa sổ, 0 = KHÔNG. Ghi bằng MẮT từ `bang/cua_so/<nhãn>.png`.
SU_THAT = {
    "P_zh_ep12":   "11111111",
    "P_zh_dongho": "11111111",
    "P_dy1":       "11111111",
    "P_dy2":       "11111111",
    "P_dy3":       "11111111",
    "N_en1":       "00000000",
    "N_en2":       "00000000",
    "N_en3":       "00000000",
    "N_en4":       "00000001",   # cửa 8: end-card "CHECK OUT THIS VIDEO"
    "N_en5":       "00000000",
    "N_en6":       "00000000",
    "N_en7":       "00000000",
    "N_en8":       "00000001",   # cửa 8: thanh "@cole.labrant @everleighrose…"
    "N_en9":       "00000000",   # "RUCKUS"/"HILFIGER" là chữ TRÊN ÁO, không
                                 # phải chữ cháy -> KHÔNG được che
    "N_en10":      "00000011",   # cửa 7-8: thanh "@JASMINE.JADE @JAS.AVA"
}


def _moc_cua(d: float, n: int = SO_CUA, dai: float = DAI_CUA) -> list:
    """n cửa sổ `dai` giây rải đều, không chạm 2 mép."""
    lo, hi = d * 0.03, d * 0.97 - dai
    if hi <= lo:
        return [(0.0, min(d, dai))]
    b = (hi - lo) / max(1, n - 1)
    return [(lo + i * b, lo + i * b + dai) for i in range(n)]


def do_do(so_khung: int = 12) -> dict:
    print(f"\n=== PHÉP ĐO 1 — DÒ DẢI CHỮ ({SO_CUA} cửa sổ x {DAI_CUA:.0f}s/"
          f"video, {so_khung} khung/cửa sổ) ===")
    print("  cột 'thật' = ghi bằng MẮT từ ảnh dải đáy giữa mỗi cửa sổ")
    dung = sai_bo_sot = sai_che_oan = 0
    co_that = khong_that = 0
    chi_tiet = []
    for nhan, p, _ in _bo():
        that = SU_THAT.get(nhan)
        if not that:
            continue
        tt = C.thong_tin(p)
        cua = _moc_cua(tt["do_dai"])
        ra, t0 = [], time.perf_counter()
        for (a, b) in cua:
            r = C.do_dai_chu(p, bat_dau=a, ket_thuc=b, so_khung=so_khung)
            ra.append(r.co_chu)
        gy = time.perf_counter() - t0
        chuoi = ""
        for i, co in enumerate(ra):
            t = that[i] == "1"
            co_that += t
            khong_that += (not t)
            if co == t:
                dung += 1
                chuoi += "."
            elif t and not co:
                sai_bo_sot += 1
                chuoi += "s"          # BỎ SÓT (có chữ mà không dò ra)
            else:
                sai_che_oan += 1
                chuoi += "!"          # CHE OAN (không chữ mà dò ra) — NGUY HIỂM
        print(f"  {nhan:14s} thật={that}  dò={''.join('1' if x else '0' for x in ra)}"
              f"  [{chuoi}]  {gy:5.1f}s")
        chi_tiet.append((nhan, that, "".join("1" if x else "0" for x in ra),
                         chuoi, gy))
    tong = dung + sai_bo_sot + sai_che_oan
    print("  " + "-" * 72)
    print(f"  TỔNG {tong} cửa sổ ({co_that} thật CÓ chữ · "
          f"{khong_that} thật KHÔNG chữ)")
    print(f"  ĐÚNG            : {dung}/{tong} = {dung/max(1,tong)*100:.1f}%")
    print(f"  BỎ SÓT (s)      : {sai_bo_sot}/{co_that} = "
          f"{sai_bo_sot/max(1,co_that)*100:.1f}%  (còn chữ Trung trên hình)")
    print(f"  CHE OAN (!)     : {sai_che_oan}/{khong_that} = "
          f"{sai_che_oan/max(1,khong_that)*100:.1f}%  <-- CA SAI NGUY HIỂM NHẤT")
    return {"chi_tiet": chi_tiet, "dung": dung, "bo_sot": sai_bo_sot,
            "che_oan": sai_che_oan, "co_that": co_that,
            "khong_that": khong_that}


def do_do_ca_video() -> dict:
    """Dò 1 LƯỢT trên CẢ video (đúng cách app sẽ gọi) — 16 khung rải đều."""
    print("\n=== PHÉP ĐO 1b — DÒ 1 LƯỢT CẢ VIDEO (16 khung rải đều) ===")
    ok = 0
    ds = _bo()
    for nhan, p, that in ds:
        t0 = time.perf_counter()
        r = C.do_dai_chu(p)
        gy = time.perf_counter() - t0
        dung = r.co_chu == that
        ok += dung
        print(f"  {'ĐÚNG' if dung else 'SAI '} {nhan:14s} "
              f"dò={'CÓ ' if r.co_chu else 'KHÔNG'} "
              f"y={r.y0}..{r.y1} tlk={r.ty_le_khung:.2f} "
              f"tỉ-số-nền={r.ty_so_nen:5.2f} {gy:4.1f}s | {r.ly_do[:52]}")
    print(f"  -> {ok}/{len(ds)} video đúng")
    return {"dung": ok, "tong": len(ds)}


# ──────────────────────────── PHÉP ĐO 2 — CHE ───────────────────────────────
def _cat(src, dst, bd: float, dai: float) -> None:
    subprocess.run([C._bin("ffmpeg"), "-y", "-v", "error", "-ss", f"{bd:.3f}",
                    "-i", str(src), "-t", f"{dai:.3f}", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", str(dst)], check=True,
                   creationflags=C._CREATE_NO_WINDOW)


def _cpu_giay(cmd: list) -> tuple:
    """(wall, CPU-giây) của MỘT lệnh ffmpeg — CPU-giây qua psutil (GetProcess
    Times trên Windows), không đoán theo wall."""
    import psutil
    t0 = time.perf_counter()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         creationflags=C._CREATE_NO_WINDOW)
    pp = psutil.Process(p.pid)
    cpu = 0.0
    while p.poll() is None:
        try:
            c = pp.cpu_times()
            cpu = c.user + c.system
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            break
        time.sleep(0.05)
    out, err = p.communicate()
    return time.perf_counter() - t0, cpu, p.returncode, err.decode("u8", "replace")


def do_che(dai_clip: float = 20.0, so_luot: int = 3) -> dict:
    print(f"\n=== PHÉP ĐO 2 — CHE ({dai_clip:.0f}s/clip, {so_luot} lượt ĐAN "
          "XEN, lấy TRUNG VỊ) ===")
    RA.mkdir(parents=True, exist_ok=True)
    KHUNG.mkdir(parents=True, exist_ok=True)
    nguon = []
    for nhan, p, that in _bo():
        if that and len(nguon) < 2:
            c = RA / f"{nhan}_goc.mp4"
            if not c.exists():
                _cat(p, c, C.thong_tin(p)["do_dai"] * 0.30, dai_clip)
            nguon.append((nhan, c))
    kq = {}
    for nhan, clip in nguon:
        d = C.do_dai_chu(clip)
        tt = C.thong_tin(clip)
        print(f"\n  --- {nhan} ({tt['rong']}x{tt['cao']}, {tt['do_dai']:.1f}s) "
              f"dải y={d.y0}..{d.y1} x={d.x0}..{d.x1}")
        moc = [tt["do_dai"] * f for f in (0.15, 0.35, 0.55, 0.75, 0.92)]
        md0 = C.mat_do_vung(clip, d.y0, d.y1, moc, d.x0, d.x1)
        print(f"      mật độ nét TRONG DẢI, bản GỐC        : {md0:.4f}")
        ket = {c: {"wall": [], "cpu": []} for c in ("khong", "mo", "khoi", "hat")}
        for _ in range(so_luot):
            for cach in ("khong", "mo", "khoi", "hat"):
                out = RA / f"{nhan}_{cach}.mp4"
                loc = "null" if cach == "khong" else C.loc_che(d, cach=cach)
                cmd = [C._bin("ffmpeg"), "-y", "-hide_banner", "-loglevel",
                       "error", "-i", str(clip), "-filter_complex", loc,
                       "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                       "-pix_fmt", "yuv420p", "-c:a", "copy", str(out)]
                w, cpu, rc, err = _cpu_giay(cmd)
                if rc != 0:
                    raise RuntimeError(f"{cach} mã thoát {rc}: {err[-400:]}")
                ket[cach]["wall"].append(w)
                ket[cach]["cpu"].append(cpu)
        goc = statistics.median(ket["khong"]["wall"])
        print(f"      {'cách':6s} {'wall':>7s} {'CPU-giây':>9s} "
              f"{'so gốc':>7s} {'mật độ còn':>11s} {'giây/phút video':>16s}")
        for cach in ("khong", "mo", "khoi", "hat"):
            w = statistics.median(ket[cach]["wall"])
            cp = statistics.median(ket[cach]["cpu"])
            out = RA / f"{nhan}_{cach}.mp4"
            md = C.mat_do_vung(out, d.y0, d.y1, moc, d.x0, d.x1)
            them = (w - goc) / tt["do_dai"] * 60.0
            print(f"      {cach:6s} {w:6.2f}s {cp:8.2f}s {w/goc:6.2f}x "
                  f"{md:10.4f} {them:14.1f}s")
            ket[cach].update({"wall_tv": w, "cpu_tv": cp, "mat_do": md,
                              "them_moi_phut": them})
        ket["mat_do_goc"] = md0
        ket["dai"] = d.dict()
        kq[nhan] = ket
        # trích khung TRƯỚC / SAU để MẮT tự nhìn
        t = tt["do_dai"] * 0.35
        C.trich_khung(clip, t, KHUNG / f"{nhan}_TRUOC.png")
        for cach in ("mo", "khoi", "hat"):
            C.trich_khung(RA / f"{nhan}_{cach}.mp4", t,
                          KHUNG / f"{nhan}_SAU_{cach}.png")
    return kq


# ──────────────────────────── PHÉP ĐO 3 — VIẾT ──────────────────────────────
DONG_MAU = [
    (0.0, 3.0, "Người ta chỉ lặn xuống thôi"),
    (3.0, 6.5, "rồi mọi chuyện bắt đầu"),
    (6.5, 10.0, "Chiếc đồng hồ lộ ra bí mật lớn"),
    (10.0, 14.0, "男人只是在潜水时"),
    (14.0, 18.0, "Không ai ngờ tới kết cục này"),
]


def do_viet(dai_clip: float = 20.0) -> dict:
    print("\n=== PHÉP ĐO 3 — VIẾT CHỮ MỚI ĐÈ LÊN ===")
    RA.mkdir(parents=True, exist_ok=True)
    KHUNG.mkdir(parents=True, exist_ok=True)
    kq = {}
    for nhan, p, that in _bo():
        if not that:
            continue
        clip = RA / f"{nhan}_goc.mp4"
        if not clip.exists():
            _cat(p, clip, C.thong_tin(p)["do_dai"] * 0.30, dai_clip)
        d = C.do_dai_chu(clip)
        out = RA / f"{nhan}_CHE_VIET.mp4"
        t0 = time.perf_counter()
        bao = C.che_va_viet(clip, out, DONG_MAU, dai=d, cach="mo",
                            thu_muc_tam=RA)
        gy = time.perf_counter() - t0
        tt = C.thong_tin(clip)
        print(f"  {nhan}: mã thoát {bao['ma_thoat']} · che={bao['che']} · "
              f"{bao['so_dong']} dòng · {gy:.2f}s "
              f"({gy/tt['do_dai']*60:.1f}s/phút video)")
        print(f"      kiểm file ra: {bao['kiem']}")
        for i, (a, b, c) in enumerate(DONG_MAU):
            C.trich_khung(out, (a + b) / 2,
                          KHUNG / f"{nhan}_VIET_{i}.png")
        kq[nhan] = {"bao": {k: v for k, v in bao.items() if k != "cmd"},
                    "giay": gy}
        if len(kq) >= 2:
            break
    return kq


if __name__ == "__main__":
    viec = sys.argv[1] if len(sys.argv) > 1 else "tat"
    ra = {}
    if viec in ("do", "tat"):
        ra["do"] = do_do()
        ra["do_ca"] = do_do_ca_video()
    if viec in ("che", "tat"):
        ra["che"] = do_che()
    if viec in ("viet", "tat"):
        ra["viet"] = do_viet()
    (SAN / "ket_qua.json").write_text(
        json.dumps(ra, ensure_ascii=False, default=str, indent=1),
        encoding="utf-8")
    print(f"\n-> {SAN / 'ket_qua.json'}")
