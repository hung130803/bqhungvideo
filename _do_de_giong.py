# -*- coding: utf-8 -*-
"""ĐÈ GIỌNG (không tách) so với THAY HẲN GIỌNG (tách nhạc) — ĐO GHÉP CẶP
(19/08/2026).

Anh Hùng đề xuất: *"thêm tính năng KHÔNG tách nhạc nền, chỉ GIẢM tiếng video
gốc rồi ĐÈ giọng lồng tiếng vào, để không bị mất mấy tiếng của video"*.

Mệnh đề phải chứng minh: **mất tiếng = 0,00 s THEO CẤU TẠO** — không bỏ đi gì
thì không có gì để mất. Đường cũ (`tach`) tách rồi BỎ giọng gốc nên mọi câu bộ
chép lời bỏ qua đều thành khoảng TRỐNG; đo ghép cặp hôm nay ra **14,75 s /
1,62%** kể cả sau khi có `bu_giong_goc`.

──────────────────────────────────────────────────────────────────────────
THIẾT KẾ: **GHÉP CẶP** — MỘT lượt dây chuyền, HAI arm tách ra ở CHỖ TRỘN
──────────────────────────────────────────────────────────────────────────
Đo rời hai lượt là **báo cáo ngược sự thật**: cùng một bản mã, cùng 4 video, hai
lượt xuất rời ra **82,35 s và 45,60 s = lệch 1,81 lần** (LLM không tiền định ->
mỗi lượt bỏ qua bộ câu khác nhau). Commit `4d738e8` đã tố giác đúng chuyện này
một lần (20,05 s vs 30,65 s trong khi bản vá nằm im).

Nên ở đây **một lượt `thay_giong_video` cho mỗi video**, và hai arm tách ra ở
ĐÚNG chỗ chế độ mới tác động — tham số `nhac_wav` của `tron_thay_giong`:
  · arm **TACH** = `tron_thay_giong(lớp nhạc Demucs, mảnh + mảnh bù, …)`  ← cũ
  · arm **DE**   = `tron_thay_giong(**goc_wav**,        mảnh,           …)`  ← mới
Cùng bản tách, cùng bản chép lời, cùng bản dịch, cùng FILE GIỌNG, cùng bước
khớp thời gian. Khác nhau ĐÚNG hai thứ (lớp nền · có mảnh bù hay không), và đó
CHÍNH LÀ định nghĩa của chế độ mới. Mọi nhiễu LLM bị triệt tiêu theo cấu tạo.

`goc_wav` lấy từ **kwarg `goc_wav=` mà `thay_giong_video` vẫn truyền sẵn** cho
bước bù dải cao — không phải đoán đường dẫn.

──────────────────────────────────────────────────────────────────────────
BỐN THƯỚC, MỖI THƯỚC MỘT LÝ DO
──────────────────────────────────────────────────────────────────────────
1. **MẤT TIẾNG** — `_do_mat_giong.khoang_mat`: tách CẢ HAI vế bằng Demucs rồi
   so LỚP GIỌNG với LỚP GIỌNG. KHÔNG so đường bao cả file: bản xuất vẫn có nhạc
   ở đúng đoạn mất tiếng nên thước đó ra "IM HẲN 0,0 s" = chứng nhận SẠCH cho
   thứ đang hỏng. Kèm **PHÂN BỐ ĐỘ DÀI KHOẢNG** (<0,5 · 0,5-1 · 1-2 · >=2 s) —
   con số tổng che mất chỗ đáng đọc: lớp ">=1 s" mới là "mất cả cụm/cả câu" mà
   tai nghe ra là *bị tắt tiếng*.
2. **GIỌNG LỒNG NỔI TRÊN TIẾNG GỐC bao nhiêu dB LÚC ĐANG NÓI** —
   `do_giong_tren_nhac`. Phải đo LÚC ĐANG NÓI, không lấy RMS cả track: track
   giọng ~30% là im lặng nên RMS toàn bài thấp giả tạo.
3. **ĐỘ TO — HAI THƯỚC ĐỘC LẬP** (`loudnorm` pha ĐO + `ebur128`). Lệch quá
   0,5 LU thì DỪNG: một thước một mình thì không ai bắt được nó hỏng.
4. **ĐỈNH THẬT + SỐ MẪU CHẠM TRẦN** — `astats`, chỉ số **`Abs_Peak_count`**
   (KHÔNG phải `Number_of_clipped_samples`: tên đó không tồn tại nên cả lệnh
   ffmpeg chết và hàm trả None IM LẶNG = ca "không méo" tự ĐẠT vĩnh viễn), và
   đọc bằng **`in`** chứ không `startswith` (mỗi dòng mở đầu `[Parsed_astats_0
   @ ...]`).

CHỐT CHỐNG-ĐẠT-OAN nằm trong chính phép đo: arm **TACH** phải ra MẤT TIẾNG > 0.
Nếu cả hai arm ra 0,00 s thì thước KHÔNG CÓ RĂNG trên bộ file này và số của arm
DE là vô nghĩa — bảng in thẳng dòng đó ra.

**KHÔNG ĐỤNG MỘT BYTE NÀO** của `Downloads/longtieng` (chỉ ĐỌC + copy sang hộp
cát); hộp cát dọn ở `finally`. File tiếng để anh Hùng TỰ NGHE xuất ra
`_NGHE_THU_ANH_HUNG/de_giong/`.

Chạy:  .venv\\Scripts\\python -u _do_de_giong.py
       .venv\\Scripts\\python -u _do_de_giong.py 1 2    (chỉ video 1 và 2)
Kết quả cộng dồn vào `_kq_de_giong.json` — chạy lại thì BỎ QUA video đã xong
(8 luồng phiên này chết giữa chừng vì hết hạn mức; mất số đo là mất cả tiếng máy).
"""
from __future__ import annotations

import json
import os
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
_HAU = os.environ.get("BQ_KQ", "").strip()
SB = REPO / f"bq_de_giong{_HAU}"
KQ = REPO / f"_kq_de_giong{_HAU}.json"
NGHE = REPO / "_NGHE_THU_ANH_HUNG" / "de_giong"

DICH = "vi"
GIONG = "vi-VN-NamMinhNeural"

#: **DÙNG ĐÚNG ffmpeg MÀ APP CHẠY**, không ghi cứng `bin/ffmpeg.exe`.
#: ĐO ĐƯỢC 19/08/2026 (và nó là một cái bẫy thật): `bin\ffmpeg.exe` sau lượt
#: phục hồi từ `dist/` là build **2023-01-12**, còn `config.FFMPEG_PATH` mặc
#: định là `"ffmpeg"` -> lấy bản trên PATH = **N-121186 (2025-09-23)**. Hai bản
#: lệch 2,5 năm, và build 2023 **KHÔNG CÓ chỉ số `Abs_Peak_count`**
#: (`Unable to parse option value`, rc=1) nên phép đo "chạm trần" sẽ CHẾT trên
#: `bin/` mà vẫn chạy trên đường app đi. Đo bằng ffmpeg khác ffmpeg sản xuất là
#: đo một thứ khác thứ anh Hùng nghe.
from config import settings as _st                          # noqa: E402
FFMPEG = str(_st.FFMPEG_PATH)

#: Đích độ to + trần đỉnh (đã đo, xem cổng 65). Trần phải trừ HAI lần: alimiter
#: chặn đỉnh MẪU nên đỉnh thật vọt +0,06 dB, rồi AAC vọt thêm tới +0,19 dB.
DICH_LUFS = -14.0
TRAN_TP = -1.0
#: Hai thước độ to lệch quá mức này thì DỪNG — không có thước thứ hai thì không
#: ai bắt được thước thứ nhất hỏng.
LECH_LU_MAX = 0.5

#: Bậc phân bố độ dài khoảng mất tiếng.
BAC = ((0.0, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 1e9))
TEN_BAC = ("<0,5s", "0,5-1s", "1-2s", ">=2s")


# ==================================================================
# THƯỚC ĐỘC LẬP — KHÔNG gọi hàm của app, để bắt được app đo sai
# ==================================================================
def _chay(args: list[str], mo_ta: str, timeout: int = 1800) -> str:
    """ffmpeg -> stderr (mọi bộ đo của ffmpeg in ra stderr)."""
    r = subprocess.run([FFMPEG, "-nostdin", "-v", "info", *args],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"{mo_ta}: rc={r.returncode} {(r.stderr or '')[-400:]}")
    return r.stderr or ""


def do_to_loudnorm(path: str | Path) -> dict:
    """Thước 1: `loudnorm` PHA ĐO (`print_format=json`, chỉ giải mã)."""
    out = _chay(["-i", str(path), "-af",
                 "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json",
                 "-f", "null", "-"], "loudnorm đo")
    m = re.search(r"\{[^{}]*input_i[^{}]*\}", out, re.S)
    if not m:
        raise RuntimeError("loudnorm KHÔNG in JSON — phép đo hỏng, KHÔNG trả None")
    d = json.loads(m.group(0))
    return {"I": float(d["input_i"]), "TP": float(d["input_tp"]),
            "LRA": float(d["input_lra"])}


def do_to_ebur128(path: str | Path) -> dict:
    """Thước 2 ĐỘC LẬP: `ebur128` (bộ đo KHÁC, cùng chuẩn EBU R128)."""
    out = _chay(["-i", str(path), "-af", "ebur128=peak=true:framelog=quiet",
                 "-f", "null", "-"], "ebur128")
    # khối Summary in ở cuối: "  I:  -14.0 LUFS" / "  Peak: -1.4 dBFS"
    i = tp = lra = None
    for dong in out.splitlines():
        s = dong.strip()
        if s.startswith("I:") and "LUFS" in s:
            i = float(s.split()[1])
        elif s.startswith("LRA:") and "LU" in s:
            lra = float(s.split()[1])
        elif s.startswith("Peak:") and "dBFS" in s:
            tp = float(s.split()[1])
    if i is None:
        raise RuntimeError("ebur128 KHÔNG in Summary — phép đo hỏng")
    return {"I": i, "TP": tp, "LRA": lra}


def kiem_ffmpeg() -> str:
    """TỰ KIỂM BỘ ĐO trước khi đo: ffmpeg này có `Abs_Peak_count` không.

    Không có phép kiểm này thì một build ffmpeg cũ làm `do_dinh` NÉM giữa lượt
    chạy (đã mất một lượt vì đúng chuyện đó), hoặc tệ hơn là ai đó "chữa" bằng
    cách bắt lỗi rồi trả None -> ca "không méo" tự ĐẠT vĩnh viễn.
    """
    r = subprocess.run([FFMPEG, "-hide_banner", "-h", "filter=astats"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    v = subprocess.run([FFMPEG, "-hide_banner", "-version"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120).stdout.splitlines()
    ban = (v[0] if v else "?").strip()
    if "Abs_Peak_count" not in (r.stdout or ""):
        raise RuntimeError(
            f"ffmpeg này KHÔNG có chỉ số `Abs_Peak_count` nên KHÔNG đo được "
            f"chạm trần: {ban}\n({FFMPEG})\nĐỔI sang build mới (bản app chạy là "
            f"N-121186) rồi đo lại — đừng bắt lỗi rồi trả None.")
    print(f"  ffmpeg đo: {ban}")
    return ban


def do_dinh(path: str | Path) -> dict:
    """Đỉnh thật + SỐ MẪU CHẠM TRẦN. `Abs_Peak_count`, đọc bằng `in`.

    Tên đúng là **`Abs_Peak_count`** — `Number_of_clipped_samples` KHÔNG tồn
    tại nên cả lệnh ffmpeg chết. Và đọc bằng **`in`**, KHÔNG `startswith`: mỗi
    dòng mở đầu `[Parsed_astats_0 @ ...]`.
    """
    out = _chay(["-i", str(path), "-af",
                 "astats=measure_perchannel=none:"
                 "measure_overall=Peak_level+Abs_Peak_count",
                 "-f", "null", "-"], "astats đỉnh")
    dinh = cham = None
    for dong in out.splitlines():
        if "Peak level dB:" in dong:
            try:
                dinh = float(dong.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif "Abs Peak count:" in dong:
            try:
                cham = int(float(dong.split(":", 1)[1].strip()))
            except ValueError:
                pass
    if dinh is None or cham is None:
        raise RuntimeError(
            "astats KHÔNG trả Peak level / Abs Peak count — tên chỉ số sai thì "
            "cả lệnh chết và ca 'không méo' tự ĐẠT vĩnh viễn")
    return {"dinh_dbfs": dinh, "cham_tran": cham}


def do_to_hai_thuoc(path: str | Path, nhan: str, nem: bool = True) -> dict:
    """Đo bằng CẢ HAI thước rồi đối chiếu. Lệch > 0,5 LU thì **cột I KHÔNG ĐỌC
    ĐƯỢC** — đánh dấu `dong_y=False`, và (mặc định) NÉM.

    **`nem=False` không phải là nới ngưỡng.** Nó đổi chỗ NÉM: một lượt dây
    chuyền thật tốn hàng phút Groq + Demucs, ném ở đây là vứt luôn cột MẤT TIẾNG
    (thứ chính phải đo) chỉ vì một cột phụ. Nên nơi gọi bắt lấy, ghi cờ
    `dong_y=False`, và `in_bang` in DÒNG DỪNG thật to — số vẫn bị coi là không
    đọc được, chỉ khác là phần còn lại của phép đo không mất theo.

    ĐO ĐƯỢC 19/08/2026, ghi để đừng ai đọc nhầm ngưỡng này: hai thước đồng ý
    **0,03-0,08 LU** trên nguồn THẬT của anh Hùng (LRA 2,1 — Douyin master nén
    sẵn) và trên nguồn LIÊN TỤC, nhưng lệch tới **0,5-1,2 LU** trên nguồn dải
    động RỘNG (LRA 10-14). Tức 0,5 LU là ngưỡng ĐÚNG cho nội dung app này xử lý;
    đem nó áp lên nguồn tổng hợp dải động rộng là áp ngoài vùng hiệu chuẩn.
    """
    a, b = do_to_loudnorm(path), do_to_ebur128(path)
    lech = abs(a["I"] - b["I"])
    if lech > LECH_LU_MAX and nem:
        raise RuntimeError(
            f"{nhan}: hai thước độ to lệch {lech:.2f} LU "
            f"(loudnorm {a['I']:.2f} · ebur128 {b['I']:.2f}) > {LECH_LU_MAX} "
            f"-> DỪNG, không đọc số của một thước hỏng")
    return {"I_loudnorm": round(a["I"], 2), "I_ebur128": round(b["I"], 2),
            "I": round((a["I"] + b["I"]) / 2, 2), "lech_LU": round(lech, 3),
            "dong_y": lech <= LECH_LU_MAX,
            "TP_loudnorm": round(a["TP"], 2),
            "TP_ebur128": None if b["TP"] is None else round(b["TP"], 2),
            "LRA": round(a["LRA"], 2), **do_dinh(path)}


def phan_bo(kh: list) -> dict:
    """Phân bố TỔNG GIÂY theo bậc độ dài khoảng — chỗ đáng đọc nhất của bảng."""
    ra = {t: 0.0 for t in TEN_BAC}
    for a, b in kh:
        d = float(b) - float(a)
        for (lo, hi), t in zip(BAC, TEN_BAC):
            if lo <= d < hi:
                ra[t] += d
                break
    return {k: round(v, 2) for k, v in ra.items()}


# ==================================================================
def bao_giong(video: Path, lam: Path, ten: str) -> list[float]:
    """Đường bao mức của LỚP GIỌNG (Demucs) — đơn vị đo của cột MẤT TIẾNG.

    Dùng Demucs cho CẢ HAI vế nên chỗ mất tiếng người hiện ra bất kể còn nhạc.
    """
    import _do_mat_giong as DM
    from app.core import thay_giong as TG
    wav = lam / f"w_{ten}.wav"
    DM.rut_wav(video, wav)
    t = TG.tach_giong(wav, lam / f"t_{ten}", cach="demucs")
    return TG.duong_bao_muc(t["giong"], buoc=DM.BUOC)


def _mux(video_nen: Path, wav: Path, ra: Path) -> None:
    """Ghép lớp tiếng của arm kia lên ĐÚNG luồng hình của arm BẬT.

    `-c:v copy` + `aac 192k` = y hệt `thay_audio_video`, nên hai arm đi qua CÙNG
    một đời nén AAC. Lệch một tham số ở đây là lệch cả phép so.
    """
    r = subprocess.run(
        [FFMPEG, "-y", "-v", "error", "-nostdin", "-i", str(video_nen),
         "-i", str(wav), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-shortest", str(ra)],
        capture_output=True, text=True, timeout=1800)
    if r.returncode != 0 or not ra.exists():
        raise RuntimeError(f"mux: rc={r.returncode} {(r.stderr or '')[:300]}")


def lam_mot(i: int, goc: Path) -> dict:
    import _do_mat_giong as DM
    from app.core import thay_giong as TG

    lam = SB / f"v{i}"
    shutil.rmtree(lam, ignore_errors=True)
    lam.mkdir(parents=True, exist_ok=True)
    vin = lam / "nguon.mp4"
    shutil.copy2(goc, vin)                      # làm trên BẢN SAO
    dai = TG.probe_duration(vin)
    print(f"  nguồn {dai:.2f}s · {goc.stat().st_size / 1048576:.0f} MB")

    # ---- HAI ARM TÁCH RA Ở ĐÚNG THAM SỐ `nhac_wav` ----
    goc_bu, goc_tron = TG.bu_giong_goc, TG.tron_thay_giong
    hop: dict = {"bu_manh": [], "wav": {}, "tron": {}, "giay": {}}

    def bu_ghi(*a, **k):
        r = goc_bu(*a, **k)
        hop["bu_manh"] = list(r.get("manh") or [])
        return r

    def tron_hai_arm(nhac_wav, manh, tong, out_wav, **k):
        # arm TACH = ĐÚNG thứ dây chuyền đang làm (lớp nhạc + mảnh đã bù)
        t0 = time.time()
        r_tach = goc_tron(nhac_wav, manh, tong, out_wav, **k)
        hop["giay"]["TACH"] = round(time.time() - t0, 2)
        hop["wav"]["TACH"] = str(out_wav)
        hop["tron"]["TACH"] = r_tach

        # arm DE = lớp nền là CHÍNH audio gốc, và KHÔNG có mảnh bù (giọng gốc
        # đã nằm sẵn trong nền -> bù là cộng cùng một tín hiệu hai lần).
        nen_goc = k.get("goc_wav") or ""
        if not nen_goc or not Path(nen_goc).exists():
            raise RuntimeError(
                "KHÔNG có `goc_wav` để làm lớp nền — arm DE không đo được. "
                "(`thay_giong_video` vẫn truyền kwarg này cho bước bù dải cao; "
                "thiếu nó thì đừng đoán đường dẫn.)")
        bu_set = {str(p) for _o, p in hop["bu_manh"]}
        manh_de = [m for m in manh if str(m[1]) not in bu_set]
        print(f"    [ghép cặp] mảnh TACH {len(manh)} · DE {len(manh_de)} "
              f"(bỏ {len(manh) - len(manh_de)} mảnh bù) · nền DE = audio GỐC")
        out_de = Path(out_wav).with_name("tieng_DE.wav")
        t0 = time.time()
        r_de = goc_tron(nen_goc, manh_de, tong, out_de, **k)
        hop["giay"]["DE"] = round(time.time() - t0, 2)
        hop["wav"]["DE"] = str(out_de)
        hop["tron"]["DE"] = r_de
        hop["nen_goc"] = str(nen_goc)
        hop["manh_de"] = [(o, str(p)) for o, p in manh_de]
        return r_tach                            # dây chuyền đi tiếp bằng arm cũ

    TG.bu_giong_goc = bu_ghi
    TG.tron_thay_giong = tron_hai_arm
    t0 = time.time()
    try:
        r = TG.thay_giong_video(
            vin, dich_sang=DICH, thu_muc_lam=lam, voice=GIONG,
            cach_tach="demucs", viet_chu=False,
            on_progress=lambda p, m: print(f"      {p * 100:5.1f}% {m}"))
    finally:
        TG.bu_giong_goc, TG.tron_thay_giong = goc_bu, goc_tron
    gy_chung = time.time() - t0
    if not r.get("ok"):
        print(f"  LỖI dây chuyền: {r.get('loi')}")
        return {"ten": goc.name, "ok": False, "loi": str(r.get("loi"))[:400]}

    v_tach = Path(r["ra"])
    v_de = lam / "arm_DE.mp4"
    _mux(v_tach, Path(hop["wav"]["DE"]), v_de)
    NGHE.mkdir(parents=True, exist_ok=True)
    shutil.copy2(v_tach, NGHE / f"TACH_{goc.name}")
    shutil.copy2(v_de, NGHE / f"DE_{goc.name}")

    # ---- THỜI GIAN: phần CHUNG + phần RIÊNG của từng arm ----
    # Cột đáng đọc là "arm DE bỏ được bao nhiêu giây": đó là bước TÁCH (Demucs)
    # + bước BÙ, cả hai đều nằm trong `kq["tach"]["giay"]` / `bu_goc`.
    gy_tach_buoc = float((r.get("tach") or {}).get("giay") or 0.0)
    gy_bu = float((r.get("bu_goc") or {}).get("giay") or 0.0)

    # ---- ĐO ----
    print("  Demucs lớp giọng: gốc...")
    b_goc = bao_giong(vin, lam, "goc")
    do: dict = {}
    for nhan, v in (("TACH", v_tach), ("DE", v_de)):
        print(f"  Demucs lớp giọng: {nhan}...")
        b = bao_giong(Path(v), lam, nhan)
        kh, tk = DM.khoang_mat(b_goc, b)
        tk["khoang"] = [[round(a, 2), round(bb, 2)] for a, bb in kh]
        tk["phan_bo"] = phan_bo(kh)
        tk["dai_nhat"] = round(max([b2 - a2 for a2, b2 in kh] or [0.0]), 2)
        # độ to / đỉnh đo trên CHÍNH FILE VIDEO (sau đời nén AAC — đúng thứ anh
        # Hùng nghe), không đo trên lớp wav trung gian.
        # `nem=False`: hai thước lệch quá thì cột I bị đánh dấu KHÔNG ĐỌC ĐƯỢC
        # (`dong_y=False`) và `in_bang` kêu to, nhưng KHÔNG vứt luôn cột MẤT
        # TIẾNG của một lượt dây chuyền tốn hàng phút Groq + Demucs.
        tk["do_to"] = do_to_hai_thuoc(v, nhan, nem=False)
        do[nhan] = tk
        print(f"    >>> {nhan}: MẤT {tk['giay_mat']}s / {tk['so_khoang']} khoảng"
              f"  ({100 * tk['giay_mat'] / max(1e-9, dai):.2f}% video)"
              f"  · phân bố {tk['phan_bo']}")
        print(f"        I {tk['do_to']['I']:+.2f} LUFS (lệch 2 thước "
              f"{tk['do_to']['lech_LU']:.3f} LU) · đỉnh "
              f"{tk['do_to']['dinh_dbfs']:+.2f} dBFS · chạm trần "
              f"{tk['do_to']['cham_tran']} mẫu · TP "
              f"{tk['do_to']['TP_loudnorm']:+.2f} dBTP")

    # ---- GIỌNG LỒNG NỔI TRÊN LỚP NỀN bao nhiêu dB LÚC ĐANG NÓI ----
    # Đo trên CHÍNH hai lớp đưa vào bộ trộn, sau khi đã áp hệ số — số này là
    # thứ trả lời "có nghe rõ lời không", khác hẳn RMS cả track.
    noi: dict = {}
    for nhan in ("TACH", "DE"):
        tr = hop["tron"].get(nhan) or {}
        cb = tr.get("can_bang") or {}
        noi[nhan] = {
            "giong_tren_nen_truoc_db": cb.get("giong_tren_nhac_truoc_db"),
            "gain_giong_db": tr.get("gain_giong_db"),
            "gain_nen_db": tr.get("gain_nhac_db"),
            "giong_tren_nen_tinh_db": tr.get("giong_tren_nhac_tinh_db"),
            "giong_tren_nen_ke_ne_db": tr.get("giong_tren_nhac_ke_ne_db"),
            "duck_db": tr.get("duck_db_du_kien"),
            "duck_ratio": tr.get("duck_ratio"),
            "muc_nen_luc_noi_db": cb.get("muc_nhac_luc_noi_db"),
            "muc_giong_luc_noi_db": cb.get("muc_giong_luc_noi_db"),
        }
        print(f"  {nhan}: giọng trên nền {noi[nhan]['giong_tren_nen_tinh_db']} dB"
              f" (kể ducking {noi[nhan]['giong_tren_nen_ke_ne_db']})"
              f" · nền bị hạ {noi[nhan]['gain_nen_db']} dB")

    return {
        "ten": goc.name, "ok": True, "dai": round(dai, 2),
        "giay_chung": round(gy_chung, 1),
        "giay_tron": hop["giay"],
        "giay_buoc_tach": round(gy_tach_buoc, 1),
        "giay_buoc_bu": round(gy_bu, 1),
        "thiet_bi_tach": (r.get("tach") or {}).get("thiet_bi"),
        "so_manh_tach": len(hop["bu_manh"]) + len(hop.get("manh_de") or []),
        "so_manh_bu": len(hop["bu_manh"]),
        "bu_goc": r.get("bu_goc"),
        "so_cau": len((r.get("khop") or {}).get("moc_tieng") or []) or None,
        "khop_bo_qua": (r.get("khop") or {}).get("bo_qua"),
        "noi": noi,
        "do": do,
    }


def in_bang(ket: dict) -> None:
    print(f"\n{'=' * 78}\nBẢNG GHÉP CẶP — MẤT TIẾNG (thước: lớp giọng vs lớp giọng)")
    print(f"{'video':<26}{'dài':>9}{'TACH (cũ)':>12}{'DE (mới)':>12}"
          f"{'bù':>5}{'câu':>5}")
    t = {"TACH": 0.0, "DE": 0.0}
    tv = 0.0
    pb = {a: {t2: 0.0 for t2 in TEN_BAC} for a in ("TACH", "DE")}
    for i in sorted(ket, key=int):
        k = ket[i]
        if not k.get("ok"):
            print(f"{k.get('ten', '?')[:24]:<26}  LỖI {str(k.get('loi'))[:40]}")
            continue
        tv += k["dai"]
        c = []
        for n in ("TACH", "DE"):
            v = (k["do"].get(n) or {}).get("giay_mat")
            c.append(f"{v:>11.2f}s" if v is not None else f"{'—':>12}")
            if v is not None:
                t[n] += v
            for t2 in TEN_BAC:
                pb[n][t2] += ((k["do"].get(n) or {}).get("phan_bo") or {}).get(t2, 0.0)
        print(f"{k['ten'][:24]:<26}{k['dai']:>8.1f}s{''.join(c)}"
              f"{k.get('so_manh_bu', 0):>5}{k.get('so_cau') or 0:>5}")
    print(f"{'TỔNG':<26}{tv:>8.1f}s{t['TACH']:>11.2f}s{t['DE']:>11.2f}s")
    if tv > 0:
        print(f"{'% thời lượng':<26}{'':>9}{100 * t['TACH'] / tv:>11.2f}%"
              f"{100 * t['DE'] / tv:>11.2f}%")

    print(f"\nPHÂN BỐ ĐỘ DÀI KHOẢNG MẤT TIẾNG (giây)")
    print(f"{'arm':<10}" + "".join(f"{x:>10}" for x in TEN_BAC) + f"{'tổng':>10}")
    for n in ("TACH", "DE"):
        print(f"{n:<10}" + "".join(f"{pb[n][x]:>10.2f}" for x in TEN_BAC)
              + f"{t[n]:>10.2f}")

    print(f"\nĐỘ TO · ĐỈNH · GIỌNG NỔI TRÊN NỀN")
    print(f"{'video':<22}{'arm':<6}{'I LUFS':>9}{'lệch2':>7}{'TP':>8}"
          f"{'đỉnh':>8}{'chạm':>6}{'giọng/nền':>11}{'kể né':>8}{'nền hạ':>8}")
    khong_dong_y: list[str] = []
    for i in sorted(ket, key=int):
        k = ket[i]
        if not k.get("ok"):
            continue
        for n in ("TACH", "DE"):
            d0 = (k["do"].get(n) or {}).get("do_to") or {}
            if d0 and d0.get("dong_y") is False:
                khong_dong_y.append(
                    f"{k['ten'][:20]}/{n}: lệch {d0['lech_LU']:.2f} LU "
                    f"(loudnorm {d0['I_loudnorm']:+.2f} · "
                    f"ebur128 {d0['I_ebur128']:+.2f})")
    for i in sorted(ket, key=int):
        k = ket[i]
        if not k.get("ok"):
            continue
        for n in ("TACH", "DE"):
            d = (k["do"].get(n) or {}).get("do_to") or {}
            g = (k.get("noi") or {}).get(n) or {}
            if not d:
                continue
            print(f"{k['ten'][:20]:<22}{n:<6}{d['I']:>9.2f}{d['lech_LU']:>7.3f}"
                  f"{d['TP_loudnorm']:>8.2f}{d['dinh_dbfs']:>8.2f}"
                  f"{d['cham_tran']:>6}"
                  f"{(g.get('giong_tren_nen_tinh_db') or 0):>11.2f}"
                  f"{(g.get('giong_tren_nen_ke_ne_db') or 0):>8.2f}"
                  f"{(g.get('gain_nen_db') or 0):>8.2f}")
    if khong_dong_y:
        print(f"\n!! DỪNG ĐỌC CỘT `I LUFS` — hai thước lệch quá {LECH_LU_MAX} LU "
              f"ở {len(khong_dong_y)} chỗ:")
        for x in khong_dong_y:
            print(f"     {x}")
    else:
        print(f"   (hai thước độ to đồng ý ở MỌI dòng, lệch <= {LECH_LU_MAX} LU"
              f" -> cột I đọc được)")

    print(f"\nTHỜI GIAN CHẠY (giây)")
    print(f"{'video':<26}{'cả lượt':>10}{'bước TÁCH':>11}{'bước BÙ':>9}"
          f"{'trộn TACH':>11}{'trộn DE':>9}{'DE bỏ được':>12}")
    tb = tbu = 0.0
    for i in sorted(ket, key=int):
        k = ket[i]
        if not k.get("ok"):
            continue
        bo = k.get("giay_buoc_tach", 0) + k.get("giay_buoc_bu", 0)
        tb += k.get("giay_buoc_tach", 0)
        tbu += k.get("giay_buoc_bu", 0)
        print(f"{k['ten'][:24]:<26}{k.get('giay_chung', 0):>9.1f}s"
              f"{k.get('giay_buoc_tach', 0):>10.1f}s"
              f"{k.get('giay_buoc_bu', 0):>8.1f}s"
              f"{(k.get('giay_tron') or {}).get('TACH', 0):>10.1f}s"
              f"{(k.get('giay_tron') or {}).get('DE', 0):>8.1f}s"
              f"{bo:>11.1f}s")
    print(f"{'TỔNG bỏ được':<26}{'':>10}{tb:>10.1f}s{tbu:>8.1f}s"
          f"{'':>11}{'':>9}{tb + tbu:>11.1f}s")

    print(f"\n{'=' * 78}")
    print(f"GHÉP CẶP:  TACH {t['TACH']:.2f}s  ->  DE {t['DE']:.2f}s"
          + (f"   (giảm {100 * (t['TACH'] - t['DE']) / t['TACH']:.1f}%)"
             if t["TACH"] > 0 else ""))
    print(f"ĐÍCH mất tiếng = 0,00 s  ->  arm DE ra {t['DE']:.2f}s"
          + ("  ĐẠT" if t["DE"] <= 0.0 else "  CHƯA ĐẠT"))
    # CHỐT CHỐNG-ĐẠT-OAN: thước phải CÓ RĂNG trên bộ file này.
    if t["TACH"] <= 0.0:
        print("!! CẢNH BÁO: arm TACH cũng ra 0,00s -> THƯỚC KHÔNG CÓ RĂNG trên "
              "bộ file này, số của arm DE VÔ NGHĨA. Đừng đọc bảng trên.")
    else:
        print(f"chốt chống-đạt-oan: arm TACH ra {t['TACH']:.2f}s > 0 "
              f"-> thước CÓ RĂNG, số của arm DE đọc được")
    print(f"=> {KQ.name} · file nghe thử: {NGHE}")


def main() -> int:
    from app.core import thay_giong as TG

    if not NGUON.is_dir():
        print(f"KHÔNG CÓ thư mục nguồn: {NGUON}")
        return 2
    vids = sorted(NGUON.glob("*.mp4"))
    chi = {int(x) for x in sys.argv[1:]} if sys.argv[1:] else None
    ket: dict = {}
    if KQ.exists():
        try:
            ket = json.loads(KQ.read_text(encoding="utf-8"))
        except Exception:                                   # noqa: BLE001
            ket = {}
    kiem_ffmpeg()
    print(f"{len(vids)} video · Demucs: {TG.tinh_trang_demucs().get('co')} "
          f"· thiết bị {TG.thiet_bi_tach()!r}")
    SB.mkdir(exist_ok=True)
    try:
        for i, g in enumerate(vids, 1):
            if chi and i not in chi:
                continue
            if ket.get(str(i), {}).get("ok"):
                print(f"\n[{i}/{len(vids)}] ĐÃ CÓ số đo, bỏ qua: {g.stem[:36]}")
                continue
            print(f"\n{'=' * 78}\n[{i}/{len(vids)}] {g.stem[:48]}")
            try:
                ket[str(i)] = lam_mot(i, g)
            except Exception as e:                          # noqa: BLE001
                import traceback
                traceback.print_exc()
                ket[str(i)] = {"ten": g.name, "ok": False,
                               "loi": f"{type(e).__name__}: {e}"[:400]}
            KQ.write_text(json.dumps(ket, ensure_ascii=False, indent=1),
                          encoding="utf-8")
            shutil.rmtree(SB / f"v{i}", ignore_errors=True)
    finally:
        shutil.rmtree(SB, ignore_errors=True)
    in_bang(ket)
    return 0


if __name__ == "__main__":
    sys.exit(main())
