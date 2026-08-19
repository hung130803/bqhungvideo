# -*- coding: utf-8 -*-
"""NHẠC NỀN BỊ DÌM −10,46 dB — CÓ CÁCH RẺ HƠN KHÔNG? (19/08/2026)

Bản vá "giọng chìm dưới nhạc" (15/08) trả giá bằng nhạc nền: `g_nhac` tĩnh
(trần `HA_NHAC_TOI_DA_DB` = 8 dB) CỘNG ducking (~3,28 dB lúc đang nói). Chưa
ai đo lại xem còn đường nào rẻ hơn. File này đo.

────────────────────────────────────────────────────────────────────────────
HAI Ý TƯỞNG ĐEM RA ĐO — cả hai đều CHƯA từng đo trong repo này
────────────────────────────────────────────────────────────────────────────
(1) **HẠ THEO DẢI TẦN.** Lời nghe rõ hay không là chuyện của dải 300-3400 Hz.
    Hạ CẢ DẢI là vứt luôn phần trầm và phần treble của nhạc — hai phần KHÔNG
    tranh chấp gì với lời. Hạ đúng dải lời thì SNR chỗ cần giữ nguyên mà nhạc
    nghe vẫn dày.
(2) **ÍT TĨNH — NÉ SÂU.** `g_nhac` tĩnh áp lên TOÀN BỘ phim, kể cả những
    đoạn KHÔNG AI NÓI (nhạc phim, cao trào). Ducking thì chỉ áp lúc đang nói.
    Dồn phần hạ sang ducking là nhạc chỗ không có lời được giữ nguyên hơn,
    mà chỗ có lời vẫn đủ chỗ cho giọng.

CẢ HAI PHẢI GIỮ NGUYÊN SNR DẢI LỜI LÚC ĐANG NÓI — không thì đó không phải
"rẻ hơn", đó là đi lùi về đúng lỗi 15/08 (*"chỗ có chỗ không nghe không
được"*).

────────────────────────────────────────────────────────────────────────────
THƯỚC — 3 cột, đọc nhầm cột là kết luận ngược
────────────────────────────────────────────────────────────────────────────
· `NÓI/dải`  = nhạc trong dải 300-3400 Hz LÚC ĐANG NÓI. Đây là thứ CHE LỜI.
               Arm nào cũng phải <= arm A, không thì lời bị che thêm.
· `IM`       = nhạc TOÀN DẢI lúc KHÔNG ai nói. Đây là thứ anh Hùng nghe ra
               là *"nhạc nền mất hết"* — chỗ nhạc lẽ ra phải còn nguyên.
· `I (LUFS)` = độ to tích phân của LỚP NHẠC ĐÃ XỬ LÝ so với lớp nhạc gốc.
               HAI THƯỚC ĐỘC LẬP (`loudnorm` pha đo + `ebur128`); lệch quá
               0,5 LU thì DỪNG, không tin số.

ARM D LÀ ĐỐI CHỨNG KIẾN TRÚC, KHÔNG PHẢI ỨNG VIÊN: cắt dải rồi cộng lại
NGUYÊN (gain 0). Nó phải ra GIỐNG lớp nhạc gốc; không giống thì mọi số của
arm B/C/F là số của phép cắt dải chứ không phải của ý tưởng.

KHÔNG DÙNG `asplit` — cắt dải ghi ra FILE RIÊNG rồi mở lại bằng `-i` riêng,
đúng bản vá 15/08 (`asplit` làm độ dài đầu ra KHÔNG TIỀN ĐỊNH, rc vẫn 0).

**KHÔNG ĐỤNG** `Downloads\\longtieng` — copy sang hộp cát.

Chạy:  .venv\\Scripts\\python -u _do_nhac_dai.py
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                           # noqa: BLE001
    pass

NGUON = Path(r"C:\Users\Admin\Downloads\longtieng")
SB = REPO / "bq_nhac_dai"
KQ = REPO / "_kq_nhac_dai.json"
FFMPEG = str(REPO / "bin" / "ffmpeg.exe")

#: video NGẮN NHẤT trong 4 bản của anh Hùng — phép đo này là về CHUỖI XỬ LÝ,
#: không phải về nội dung, nên lấy cái rẻ nhất chạy được dây chuyền thật.
TEN = "#强烈推荐 #原创 #高分电影 #我在抖音看电影 #好片推荐.mp4"
DICH, GIONG = "vi", "vi-VN-NamMinhNeural"

LO, HI = 300.0, 3400.0          # dải LỜI (chuẩn điện thoại/băng thoại)
BUOC = 0.20                     # = `thay_giong.BUOC_DO_MUC`
DUOI_DB = 18.0                  # = `thay_giong.DANG_NOI_DUOI_DB`

#: quét `ratio` cho ý tưởng (2). Bảng cũ (`DUCK_RATIO`) chỉ có tới 3,0 và đo
#: ở mức nhạc KHÁC — phải quét lại, không suy từ công thức (bài học
#: `_do_hieu_chuan_duck.py`: tính ratio từ công thức sai 6 dB).
QUET_RATIO = (1.3, 2.0, 3.0, 4.5, 6.0, 9.0)

#: **HỆ SỐ HẠ NHẠC ÉP CỨNG — LÝ DO PHẢI CÓ, ĐỌC TRƯỚC KHI ĐỔI.**
#: Lượt đo đầu chạy với hệ số THẬT của video này và ra `g_nhac = 0,00 dB`:
#: lớp nhạc Douyin sau khi tách ĐÃ nằm dưới giọng TTS **+9,28 dB** (video 1)
#: và **+13,43 dB** (video 4), tức cao hơn đích `DICH_GIONG_TREN_NHAC_DB` = 6
#: nên `can_bang_giong_nhac` KHÔNG hạ nhạc một dB nào. Con số **−10,46 dB**
#: ghi trong CLAUDE.md là của MỘT nguồn khác (nhạc CAO HƠN giọng 10,61 dB).
#: Muốn trả lời "có cách rẻ hơn không" thì phải đo ở đúng chỗ nó cắn: ép
#: `g_nhac` về TRẦN `HA_NHAC_TOI_DA_DB` (−8 dB) trên chính stem thật này.
G_NHAC_EP = -8.0

#: Cửa sổ "IM XA LỜI": cách mọi cửa sổ đang-nói ít nhất bấy nhiêu giây. Cột
#: `IM` trơn gồm cả đuôi `release=300ms` của ducking nên nó KHÔNG phân biệt
#: được "nhạc bị hạ TĨNH" với "nhạc còn đang hồi sau câu nói".
IM_XA_GIAY = 1.0


def ff(args: list[str], mo_ta: str, to: int = 1800, muc: str = "error") -> str:
    """`muc="info"` là BẮT BUỘC cho `loudnorm`/`ebur128`.

    **BẪY ĐÃ SẬP Ở LƯỢT ĐẦU:** cả hai bộ đo in kết quả ở mức **info**, nên
    `-v error` (dùng cho mọi lệnh khác để log gọn) làm chúng KHÔNG IN GÌ ->
    regex không khớp -> hàm trả `nan` -> bảng đầy `nan` mà `rc` vẫn 0. Đúng họ
    "phép đo hỏng phát chứng nhận" (`astats` cổng 53): nếu tôi đọc cột `dI`
    trống rồi bỏ qua thì mọi kết luận về ĐỘ TO là bịa.
    """
    r = subprocess.run([FFMPEG, "-y", "-v", muc, *args],
                       capture_output=True, text=True, timeout=to)
    if r.returncode != 0:
        raise RuntimeError(f"{mo_ta}: rc={r.returncode} "
                           f"{(r.stderr or '')[:400]}")
    return (r.stderr or "") + (r.stdout or "")


def bpv(x: list[float], q: float) -> float:
    y = sorted(x)
    return y[min(len(y) - 1, max(0, int(len(y) * q)))] if y else -120.0


def bao(p: Path) -> list[float]:
    from app.core import thay_giong as TG
    return TG.duong_bao_muc(p, buoc=BUOC)


def loc_dai(vao: Path, ra: Path) -> Path:
    """Chỉ giữ dải LỜI. Dùng để đo SNR ở đúng chỗ tai nghe ra lời."""
    ff(["-i", str(vao), "-af",
        f"highpass=f={LO:.0f}:poles=2,lowpass=f={HI:.0f}:poles=2",
        "-c:a", "pcm_s16le", str(ra)], f"lọc dải {vao.name}")
    return ra


def do_i(p: Path) -> tuple[float, float]:
    """(I theo `loudnorm` pha ĐO, I theo `ebur128`) — HAI thước độc lập."""
    s = ff(["-i", str(p), "-af",
            "loudnorm=I=-14:TP=-1:LRA=11:print_format=json",
            "-f", "null", "-"], f"loudnorm đo {p.name}", muc="info")
    m = re.findall(r'"input_i"\s*:\s*"?(-?[\d.]+|-inf)"?', s)
    i1 = float(m[-1]) if m and m[-1] != "-inf" else float("nan")
    s2 = ff(["-i", str(p), "-af", "ebur128=peak=true", "-f", "null", "-"],
            f"ebur128 {p.name}", muc="info")
    m2 = re.findall(r"I:\s*(-?[\d.]+)\s*LUFS", s2)
    i2 = float(m2[-1]) if m2 else float("nan")
    return i1, i2


def dinh_va_tran(p: Path) -> tuple[float, int]:
    """(đỉnh dBFS, số mẫu chạm trần). Tên chỉ số là `Abs_Peak_count` —
    `Number_of_clipped_samples` KHÔNG TỒN TẠI trong ffmpeg bản này và làm
    CHẾT cả lệnh (bẫy cổng 53). Mỗi dòng có tiền tố `[Parsed_astats_0 @ ...]`
    nên dùng `in`, KHÔNG `startswith` (bẫy cổng 44)."""
    s = ff(["-i", str(p), "-af",
            "astats=measure_perchannel=none:"
            "measure_overall=Peak_level+Abs_Peak_count",
            "-f", "null", "-"], f"astats {p.name}")
    d, c = float("nan"), -1
    for dong in s.splitlines():
        if "Peak level dB:" in dong:
            try:
                d = float(dong.split(":")[-1].strip())
            except ValueError:
                pass
        elif "Abs Peak count:" in dong:
            try:
                c = int(float(dong.split(":")[-1].strip()))
            except ValueError:
                pass
    return d, c


class Do:
    """Bộ đo bám theo MỘT lượt chạy: cửa sổ đang-nói lấy từ giọng, cố định
    cho MỌI arm — đổi cửa sổ giữa các arm là so hai thứ khác nhau."""

    def __init__(self, giong_g: Path, nhac0: Path, lam: Path) -> None:
        self.lam = lam
        self.giong_g = giong_g
        self.nhac0 = nhac0
        bg = bao(giong_g)
        self.bg = bg
        nguong = bpv(bg, 0.95) - DUOI_DB
        self.noi = [i for i, v in enumerate(bg) if v >= nguong and v > -70.0]
        _n = set(self.noi)
        self.im = [i for i in range(len(bg)) if i not in _n]
        _xa = int(round(IM_XA_GIAY / BUOC))
        self.im_xa = [i for i in self.im
                      if not any((i + d) in _n for d in range(-_xa, _xa + 1))]
        self.gm = bao(loc_dai(giong_g, lam / "giong_mid.wav"))
        print(f"  cửa sổ: NÓI {len(self.noi)} · IM {len(self.im)} · "
              f"IM XA LỜI {len(self.im_xa)} (bước {BUOC}s) · "
              f"ngưỡng nói {nguong:.2f} dBFS")

    def _med(self, b: list[float], idx: list[int]) -> float:
        v = [b[i] for i in idx if i < len(b)]
        return bpv(v, 0.5) if v else float("nan")

    def cham(self, ten: str, nhac: Path) -> dict:
        bn = bao(nhac)
        bnm = bao(loc_dai(nhac, self.lam / f"mid_{ten}.wav"))
        i1, i2 = do_i(nhac)
        i10, i20 = self.i0
        r = {
            "noi_db": round(self._med(bn, self.noi), 2),
            "im_db": round(self._med(bn, self.im), 2),
            "im_xa_db": round(self._med(bn, self.im_xa), 2),
            "noi_mid_db": round(self._med(bnm, self.noi), 2),
            "im_mid_db": round(self._med(bnm, self.im), 2),
            "I_loudnorm": round(i1, 2), "I_ebur": round(i2, 2),
            "lech_thuoc": round(abs(i1 - i2), 2),
            "dI_loudnorm": round(i1 - i10, 2), "dI_ebur": round(i2 - i20, 2),
        }
        r["snr_mid_db"] = round(self._med(self.gm, self.noi)
                                - r["noi_mid_db"], 2)
        return r

    def moc(self) -> dict:
        self.i0 = do_i(self.nhac0)
        r = self.cham("GOC", self.nhac0)
        self.g0 = r
        return r


def chay_pipeline(lam: Path) -> dict:
    """Chạy dây chuyền THẬT trên bản sao, giữ lại stem để làm phép đo."""
    from app.core import thay_giong as TG
    hop: dict = {}
    goc_tron = TG.tron_thay_giong

    def bat(nhac_wav, manh, tong, out_wav, **k):
        r = goc_tron(nhac_wav, manh, tong, out_wav, **k)
        hop.update({"nhac": str(nhac_wav), "tong": float(tong), "tron": r})
        return r

    TG.tron_thay_giong = bat
    try:
        vin = lam / "nguon.mp4"
        shutil.copy2(NGUON / TEN, vin)
        r = TG.thay_giong_video(vin, dich_sang=DICH, thu_muc_lam=lam,
                                voice=GIONG, cach_tach="demucs",
                                viet_chu=False, giu_file_tam=True,
                                on_progress=lambda p, m: None)
    finally:
        TG.tron_thay_giong = goc_tron
    if not r.get("ok"):
        raise RuntimeError(f"dây chuyền lỗi: {r.get('loi')}")
    hop["kq"] = r
    return hop


def main() -> int:
    from app.core import thay_giong as TG

    if not (NGUON / TEN).exists():
        print(f"KHÔNG CÓ video: {TEN}")
        return 2
    SB.mkdir(exist_ok=True)
    ket: dict = {}
    try:
        lam = SB / "lam"
        lam.mkdir(exist_ok=True)
        # STEM CẤT RIÊNG, NGOÀI hộp cát: lượt đầu tốn 23 phút dây chuyền rồi
        # `finally` dọn sạch, nên sửa một dòng bộ đo là phải chạy lại cả dây
        # chuyền. Có stem thì lượt sau chỉ còn ffmpeg.
        kho = REPO / "bq_nhac_dai_stem"
        ts = kho / "thong_so.json"
        if ts.exists():
            print(f"DÙNG LẠI stem đã cất ở {kho.name} (bỏ qua dây chuyền)")
            tso = json.loads(ts.read_text(encoding="utf-8"))
            nhac0, giong_nen = kho / "nhac.wav", kho / "giong_nen.wav"
            g_giong = float(tso["g_giong_db"])
            g_nhac_that = float(tso["g_nhac_db"])
            nguong_duck = float(tso["duck_nguong"])
            ratio0 = float(tso["duck_ratio"])
            tong = float(tso["tong"])
            can_bang = tso.get("can_bang")
        else:
            print(f"chạy dây chuyền thật trên bản sao ({TEN[:36]})...")
            t0 = time.time()
            hop = chay_pipeline(lam)
            tron = hop["tron"]
            g_giong = float(tron["gain_giong_db"])
            g_nhac_that = float(tron["gain_nhac_db"])
            nguong_duck = float(tron["duck_nguong"])
            ratio0 = float(tron["duck_ratio"])
            tong = hop["tong"]
            nhac0 = Path(hop["nhac"])
            giong_nen = Path(tron["giong_da_nen"])
            can_bang = tron.get("can_bang")
            print(f"  xong {time.time() - t0:.0f}s")
            kho.mkdir(exist_ok=True)
            shutil.copy2(nhac0, kho / "nhac.wav")
            shutil.copy2(giong_nen, kho / "giong_nen.wav")
            ts.write_text(json.dumps(
                {"g_giong_db": g_giong, "g_nhac_db": g_nhac_that,
                 "duck_nguong": nguong_duck, "duck_ratio": ratio0,
                 "tong": tong, "can_bang": can_bang},
                ensure_ascii=False, indent=1), encoding="utf-8")
            nhac0, giong_nen = kho / "nhac.wav", kho / "giong_nen.wav"

        # **HỆ SỐ THẬT CỦA VIDEO NÀY LÀ 0,00 dB — xem `G_NHAC_EP`.** Ép về
        # trần để đo đúng chỗ bản vá cắn; hệ số thật vẫn in ra để không ai
        # đọc nhầm bảng này thành "app đang hạ nhạc 8 dB".
        g_nhac = G_NHAC_EP
        # NGƯỠNG DUCK PHẢI TÍNH LẠI THEO MỨC NHẠC *SAU* KHI HẠ — nó bám mức
        # thật, không phải hằng số (xem `DUCK_TREN_NGUONG_DB`). Giữ ngưỡng của
        # lượt g_nhac=0 là đo một cấu hình app không bao giờ sinh ra.
        nguong_duck, _r = TG._tham_so_duck(
            float((can_bang or {}).get("muc_nhac_luc_noi_db") or -14.0)
            + g_nhac)
        print(f"  g_giọng {g_giong:+.2f} dB · g_nhạc THẬT của video này "
              f"{g_nhac_that:+.2f} dB -> ÉP {g_nhac:+.2f} dB (trần "
              f"HA_NHAC_TOI_DA_DB) · duck ngưỡng {nguong_duck:.5f} "
              f"ratio {ratio0:.2f}")
        ket["thong_so"] = {"g_giong_db": g_giong, "g_nhac_db_that": g_nhac_that,
                           "g_nhac_db_ep": g_nhac, "duck_nguong": nguong_duck,
                           "duck_ratio": ratio0, "tong": tong,
                           "can_bang": can_bang}

        # giọng SAU khi áp hệ số — mẫu số của mọi phép SNR
        giong_g = lam / "giong_g.wav"
        ff(["-i", str(giong_nen), "-af", f"volume={g_giong:.2f}dB",
            "-c:a", "pcm_s16le", str(giong_g)], "áp hệ số giọng")

        d = Do(giong_g, nhac0, lam)
        print("\n  ĐO LỚP NHẠC GỐC (mốc)...")
        ket["GOC"] = d.moc()
        print(f"    I {ket['GOC']['I_loudnorm']} / {ket['GOC']['I_ebur']} "
              f"LUFS (lệch {ket['GOC']['lech_thuoc']}) · "
              f"NÓI {ket['GOC']['noi_db']} · IM {ket['GOC']['im_db']} dBFS")
        if ket["GOC"]["lech_thuoc"] > 0.5:
            print("  DỪNG: hai thước độ to lệch quá 0,5 LU")
            return 3

        # ---- cắt dải MỘT LẦN, ghi ra 3 FILE (không `asplit`) ----
        b = [lam / f"b{i}.wav" for i in range(3)]
        ff(["-i", str(nhac0), "-filter_complex",
            f"[0:a]acrossover=split={LO:.0f} {HI:.0f}:order=4th[b0][b1][b2]",
            "-map", "[b0]", "-c:a", "pcm_s16le", str(b[0]),
            "-map", "[b1]", "-c:a", "pcm_s16le", str(b[1]),
            "-map", "[b2]", "-c:a", "pcm_s16le", str(b[2])], "cắt 3 dải")

        def gop(ten: str, gdb: tuple[float, float, float],
                duck_dai: int | None, ratio: float) -> Path:
            """Cộng 3 dải lại, mỗi dải một hệ số; `duck_dai` = dải được NÉ."""
            ra = lam / f"nhac_{ten}.wav"
            vao: list[str] = []
            fc: list[str] = []
            for i in range(3):
                vao += ["-i", str(b[i])]
                fc.append(f"[{i}:a]volume={gdb[i]:.2f}dB[n{i}]")
            lab = [f"[n{i}]" for i in range(3)]
            if duck_dai is not None:
                vao += ["-i", str(giong_g)]
                fc.append(
                    f"[n{duck_dai}][3:a]sidechaincompress="
                    f"threshold={nguong_duck:.5f}:ratio={ratio:.3f}"
                    f":attack=20:release=300:makeup=1:level_sc=1[nd]")
                lab[duck_dai] = "[nd]"
            fc.append(f"{''.join(lab)}amix=inputs=3:duration=first"
                      f":normalize=0[mx]")
            fc.append(f"[mx]apad,atrim=0:{tong:.3f},asetpts=N/SR/TB[out]")
            ff([*vao, "-filter_complex", ";".join(fc), "-map", "[out]",
                "-ac", "2", "-ar", str(TG.SR_TACH), "-c:a", "pcm_s16le",
                str(ra)], f"gộp dải {ten}")
            dd = TG.probe_duration(ra)
            if abs(dd - tong) > 0.05:
                raise RuntimeError(f"{ten}: dài {dd:.3f}s, phải {tong:.3f}s")
            return ra

        def ca_dai(ten: str, gdb: float, ratio: float) -> Path:
            """Chuỗi HIỆN TẠI: hạ CẢ DẢI rồi né CẢ DẢI (arm A và arm E)."""
            ra = lam / f"nhac_{ten}.wav"
            fc = [f"[0:a]volume={gdb:.2f}dB[n0]",
                  f"[n0][1:a]sidechaincompress=threshold={nguong_duck:.5f}"
                  f":ratio={ratio:.3f}:attack=20:release=300:makeup=1"
                  f":level_sc=1[nd]",
                  f"[nd]apad,atrim=0:{tong:.3f},asetpts=N/SR/TB[out]"]
            ff(["-i", str(nhac0), "-i", str(giong_g), "-filter_complex",
                ";".join(fc), "-map", "[out]", "-ac", "2",
                "-ar", str(TG.SR_TACH), "-c:a", "pcm_s16le", str(ra)],
               f"cả dải {ten}")
            return ra

        arm: dict[str, Path] = {}
        print("\n  dựng các arm...")
        arm["A"] = ca_dai("A", g_nhac, ratio0)                  # hiện tại
        arm["D"] = gop("D", (0.0, 0.0, 0.0), None, ratio0)      # đối chứng
        arm["B"] = gop("B", (0.0, g_nhac, 0.0), 1, ratio0)      # chỉ dải lời
        arm["C"] = gop("C", (g_nhac / 2, g_nhac, g_nhac / 2), 1, ratio0)
        for r_ in QUET_RATIO:                                   # ít tĩnh-né sâu
            arm[f"E{r_:g}"] = ca_dai(f"E{r_:g}", g_nhac / 2, r_)
            arm[f"F{r_:g}"] = gop(f"F{r_:g}", (0.0, g_nhac / 2, 0.0), 1, r_)

        print(f"\n  {'arm':<7}{'NÓI/dải':>9}{'SNR dải':>9}{'IM':>9}"
              f"{'IM xa':>9}{'I(ln)':>8}{'I(ebu)':>8}{'dI':>7}{'lệch':>6}")
        g0 = ket["GOC"]
        print(f"  {'GỐC':<7}{g0['noi_mid_db']:>9.2f}{g0['snr_mid_db']:>9.2f}"
              f"{g0['im_db']:>9.2f}{g0['im_xa_db']:>9.2f}"
              f"{g0['I_loudnorm']:>8.2f}"
              f"{g0['I_ebur']:>8.2f}{0.0:>7.2f}{g0['lech_thuoc']:>6.2f}")
        for ten, p in arm.items():
            r = d.cham(ten, p)
            ket[ten] = r
            print(f"  {ten:<7}{r['noi_mid_db']:>9.2f}{r['snr_mid_db']:>9.2f}"
                  f"{r['im_db']:>9.2f}{r['im_xa_db']:>9.2f}"
                  f"{r['I_loudnorm']:>8.2f}"
                  f"{r['I_ebur']:>8.2f}{r['dI_ebur']:>7.2f}"
                  f"{r['lech_thuoc']:>6.2f}")
            if r["lech_thuoc"] > 0.5:
                print(f"       !! HAI THƯỚC ĐỘ TO LỆCH {r['lech_thuoc']:.2f} LU "
                      f"> 0,5 — KHÔNG tin cột I của arm này")
            KQ.write_text(json.dumps(ket, ensure_ascii=False, indent=1),
                          encoding="utf-8")

        # ---- ĐỌC KẾT QUẢ: arm nào che lời KHÔNG hơn A mà giữ nhạc hơn A ----
        a = ket["A"]
        print(f"\n  ĐỐI CHỨNG KIẾN TRÚC (arm D — cắt dải rồi cộng nguyên):")
        dd = ket["D"]
        print(f"    dI {dd['dI_ebur']:+.2f} LU · NÓI/dải lệch "
              f"{dd['noi_mid_db'] - g0['noi_mid_db']:+.2f} dB · IM lệch "
              f"{dd['im_db'] - g0['im_db']:+.2f} dB "
              f"({'ĐẠT' if abs(dd['dI_ebur']) <= 0.5 else 'HỎNG'})")
        print(f"\n  ỨNG VIÊN (che lời KHÔNG hơn arm A trong dải lời VÀ giữ "
              f"nhạc hơn arm A ở CẢ HAI cột IM):")
        tot = []
        for ten, r in ket.items():
            if ten in ("GOC", "A", "D", "thong_so"):
                continue
            if (r["noi_mid_db"] <= a["noi_mid_db"] + 0.30
                    and r["im_db"] > a["im_db"] + 0.30
                    and r["im_xa_db"] > a["im_xa_db"] + 0.30):
                tot.append((r["im_xa_db"] - a["im_xa_db"], ten, r))
        for x, ten, r in sorted(tot, reverse=True):
            print(f"    {ten:<7} nhạc IM {r['im_db']:+.2f} "
                  f"(+{r['im_db'] - a['im_db']:.2f}) · IM xa "
                  f"{r['im_xa_db']:+.2f} (+{x:.2f}) · che lời "
                  f"{r['noi_mid_db'] - a['noi_mid_db']:+.2f} dB · "
                  f"I {r['I_ebur'] - a['I_ebur']:+.2f} LU so arm A")
        if not tot:
            print("    KHÔNG CÓ — đánh đổi bắt buộc, giữ nguyên arm A")
    finally:
        shutil.rmtree(SB, ignore_errors=True)
    print(f"\n=> {KQ.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
