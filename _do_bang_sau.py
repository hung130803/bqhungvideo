# -*- coding: utf-8 -*-
"""BẢNG SAU của lỗi "MẤT TIẾNG 82,35 s" — chạy ĐƯỜNG THẬT rồi đo lại
(19/08/2026).

Anh Hùng: *"mấy cái đoạn âm thanh gốc nói tiếng Anh nó không đọc phần đó thì
lại bị TẮT TIẾNG"* · *"cái nghe được cái không"*.

BẢNG TRƯỚC (đã có): 4 bản anh Hùng đã xuất, đo bằng `_do_mat_giong.py` ->
**MẤT 82,35 s / 1.209,35 s = 6,8%**, dồn vào 2/4 video (**31,05 s** và
**50,35 s**). Bản vá `bu_giong_goc` đã có và mặc định BẬT, nhưng lần hiệu
chuẩn `4d738e8` MỚI KIỂM Ở MỨC HÀM — chưa chạy end-to-end. File này chạy nốt.

──────────────────────────────────────────────────────────────────────────
THIẾT KẾ: **GHÉP CẶP**, KHÔNG PHẢI HAI LƯỢT RỜI — đây là phần đáng nói nhất.
──────────────────────────────────────────────────────────────────────────
`_do_bu_goc_ab.py` chạy `thay_giong_video` HAI LẦN (một lần mỗi arm). Chính
commit `4d738e8` đã tố giác cách đó: hai arm ra `MẤT 20,05 s` và `30,65 s`
trong khi bản vá **không bù một mảnh nào** — chênh lệch 10,6 s ấy hoàn toàn
là **LLM không tiền định** (lượt sau dịch khác, bỏ qua 5 câu thay vì 4). Đọc
thẳng cột "MẤT" của hai lượt rời là báo cáo NGƯỢC sự thật.

Nên ở đây **MỘT lượt chạy dây chuyền cho mỗi video**, và hai arm tách ra ở
ĐÚNG chỗ bản vá tác động: `manh_tron = kh["manh"] + bu["manh"]`.
  · arm **BẬT** = `manh_tron` (chính là thứ `thay_giong_video` trả về)
  · arm **TẮT** = `manh_tron` TRỪ đi các mảnh bù
Cùng bản tách, cùng bản chép lời, cùng bản dịch, cùng file giọng. Khác nhau
ĐÚNG một thứ. Mọi nhiễu LLM bị triệt tiêu theo cấu tạo.

THƯỚC: `_do_mat_giong.khoang_mat` — **CHÍNH hàm đã đo bảng TRƯỚC**, so LỚP
GIỌNG (Demucs) của bản gốc với LỚP GIỌNG của bản xuất. KHÔNG dùng
`_do_mat_tieng.py` (so đường bao CẢ FILE): bản xuất vẫn có nhạc nền ở đúng
đoạn mất tiếng nên nó đo ra "IM HẲN 0,0 s" = chứng nhận SẠCH cho thứ đang
hỏng.

CỘT `HÙNG` = đo LẠI chính 4 file anh Hùng đã xuất, TRONG CÙNG LƯỢT NÀY. Bắt
buộc phải có: Demucs không tiền định, và bảng TRƯỚC đo ở phiên khác. Không có
cột này thì không phân biệt được "bản vá ăn" với "hôm nay Demucs tách khác".

**KHÔNG ĐỤNG MỘT BYTE NÀO** của `Downloads\longtieng` — copy sang hộp cát rồi
làm trên bản sao; hộp cát dọn ở `finally`.

Chạy:  .venv\\Scripts\\python -u _do_bang_sau.py
       .venv\\Scripts\\python -u _do_bang_sau.py 1      (chỉ video số 1)
Kết quả cộng dồn vào `_kq_bang_sau.json` (chạy lại thì BỎ QUA video đã xong —
5 luồng đã chết giữa chừng vì hết hạn mức, mất số đo là mất cả tiếng máy).
"""
from __future__ import annotations

import json
import os
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
XUAT_HUNG = NGUON / "xuất"
#: Hộp cát + file kết quả tách theo `BQ_KQ` để chạy được NHIỀU BẢN SONG SONG
#: (máy này luôn có 3-4 luồng khác dùng chung edge-tts; chạy tuần tự 4 video
#: đo ra ~35 s/câu). Hai bản cùng ghi một file JSON là bản ghi sau NUỐT bản
#: trước — mất số đo còn tệ hơn chạy chậm.
#: `.strip()` KHÔNG phải cho đẹp: `set BQ_KQ=_v4 && ...` của cmd.exe nuốt
#: luôn khoảng trắng trước `&&` -> thư mục tên `bq_bang_sau_v4 ` (có dấu cách
#: cuối) — Windows tạo được cấp 1 rồi CHẾT ở cấp 2 với `WinError 3`.
_HAU = os.environ.get("BQ_KQ", "").strip()
SB = REPO / (f"bq_bang_sau{_HAU}")
KQ = REPO / f"_kq_bang_sau{_HAU}.json"
NGHE = REPO / "_NGHE_THU_ANH_HUNG" / "bang_sau"

DICH = "vi"
GIONG = "vi-VN-NamMinhNeural"
FFMPEG = str(REPO / "bin" / "ffmpeg.exe")


def _mux(video_bat: Path, wav: Path, ra: Path) -> None:
    """Ghép audio arm TẮT lên ĐÚNG luồng hình của arm BẬT.

    `-c:v copy` + `aac 192k` = y hệt `thay_audio_video`, nên hai arm đi qua
    CÙNG một đời nén. Lệch một tham số ở đây là lệch cả phép so.
    """
    r = subprocess.run(
        [FFMPEG, "-y", "-v", "error", "-i", str(video_bat), "-i", str(wav),
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-shortest", str(ra)],
        capture_output=True, text=True, timeout=1800)
    if r.returncode != 0 or not ra.exists():
        raise RuntimeError(f"mux TẮT: rc={r.returncode} {(r.stderr or '')[:300]}")


def bao_giong(video: Path, lam: Path, ten: str) -> list[float]:
    """Đường bao mức của LỚP GIỌNG (Demucs) — đơn vị đo của cả bảng."""
    import _do_mat_giong as DM
    from app.core import thay_giong as TG
    wav = lam / f"w_{ten}.wav"
    DM.rut_wav(video, wav)
    t = TG.tach_giong(wav, lam / f"t_{ten}", cach="demucs")
    return TG.duong_bao_muc(t["giong"], buoc=DM.BUOC)


def in_bang_giay(nhan: str, kh: list, tran: int = 60) -> None:
    print(f"    ── {nhan}: {len(kh)} khoảng ──")
    for a, b in kh[:tran]:
        print(f"       {a:8.2f} -> {b:8.2f}   ({b - a:5.2f}s)")
    if len(kh) > tran:
        print(f"       … còn {len(kh) - tran} khoảng, xem {KQ.name}")


def lam_mot(i: int, goc: Path, ket: dict) -> dict:
    import _do_mat_giong as DM
    from app.core import thay_giong as TG

    lam = SB / f"v{i}"
    if lam.exists():
        shutil.rmtree(lam, ignore_errors=True)
    lam.mkdir(parents=True, exist_ok=True)
    vin = lam / "nguon.mp4"
    shutil.copy2(goc, vin)                      # làm trên BẢN SAO
    dai = TG.probe_duration(vin)
    print(f"  nguồn {dai:.2f}s · {goc.stat().st_size / 1048576:.0f} MB")

    # ---- CHẶN HAI ARM TÁCH RA Ở ĐÚNG CHỖ BẢN VÁ TÁC ĐỘNG ----
    goc_bu, goc_tron = TG.bu_giong_goc, TG.tron_thay_giong
    hop: dict = {"bu_manh": [], "tat_wav": "", "tron_bat": {}, "tron_tat": {}}

    def bu_ghi(*a, **k):
        r = goc_bu(*a, **k)
        hop["bu_manh"] = list(r.get("manh") or [])
        return r

    def tron_hai_arm(nhac_wav, manh, tong, out_wav, **k):
        r_bat = goc_tron(nhac_wav, manh, tong, out_wav, **k)
        bu_set = {str(p) for _o, p in hop["bu_manh"]}
        manh_tat = [m for m in manh if str(m[1]) not in bu_set]
        print(f"    [ghép cặp] mảnh BẬT {len(manh)} · TẮT {len(manh_tat)} "
              f"(bù {len(manh) - len(manh_tat)})")
        out_tat = Path(out_wav).with_name("tieng_TAT.wav")
        r_tat = goc_tron(nhac_wav, manh_tat, tong, out_tat, **k)
        hop["tat_wav"] = str(out_tat)
        hop["tron_bat"], hop["tron_tat"] = r_bat, r_tat
        return r_bat

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
    gy = time.time() - t0
    if not r.get("ok"):
        print(f"  LỖI dây chuyền: {r.get('loi')}")
        return {"ten": goc.name, "ok": False, "loi": str(r.get("loi"))[:400]}

    v_bat = Path(r["ra"])
    v_tat = lam / "arm_TAT.mp4"
    _mux(v_bat, Path(hop["tat_wav"]), v_tat)
    NGHE.mkdir(parents=True, exist_ok=True)
    shutil.copy2(v_bat, NGHE / f"BAT_{goc.name}")
    print(f"  xuất xong {gy:.0f}s · bù {r.get('bu_goc', {}).get('so_bu')} mảnh"
          f" / {r.get('bu_goc', {}).get('giay_bu')}s")

    # ---- ĐO ----
    print("  Demucs lớp giọng: gốc...")
    b_goc = bao_giong(vin, lam, "goc")
    do: dict = {}
    for nhan, v in (("HUNG", XUAT_HUNG / goc.name), ("TAT", v_tat),
                    ("BAT", v_bat)):
        if not Path(v).exists():
            continue
        print(f"  Demucs lớp giọng: {nhan}...")
        b = bao_giong(Path(v), lam, nhan)
        kh, tk = DM.khoang_mat(b_goc, b)
        tk["khoang"] = [[round(a, 2), round(bb, 2)] for a, bb in kh]
        do[nhan] = tk
        print(f"    >>> {nhan}: MẤT {tk['giay_mat']}s / {tk['so_khoang']} "
              f"khoảng  ({100 * tk['giay_mat'] / max(1e-9, dai):.1f}% video)")
    for nhan in ("HUNG", "TAT", "BAT"):
        if nhan in do and do[nhan]["khoang"]:
            in_bang_giay(nhan, do[nhan]["khoang"])

    cb = (hop["tron_bat"] or {}).get("can_bang") or {}
    return {
        "ten": goc.name, "ok": True, "dai": round(dai, 2),
        "giay_chay": round(gy, 1),
        "bu_goc": r.get("bu_goc"),
        "khop_bo_qua": (r.get("khop") or {}).get("bo_qua"),
        "so_cau": len((r.get("khop") or {}).get("moc_tieng") or []) or None,
        "nhac": {
            "gain_nhac_db": (hop["tron_bat"] or {}).get("gain_nhac_db"),
            "gain_giong_db": (hop["tron_bat"] or {}).get("gain_giong_db"),
            "giong_tren_nhac_truoc_db": cb.get("giong_tren_nhac_truoc_db"),
            "can_bu_db": cb.get("can_bu_db"),
            "muc_nhac_luc_noi_db": cb.get("muc_nhac_luc_noi_db"),
            "muc_giong_luc_noi_db": cb.get("muc_giong_luc_noi_db"),
            "dinh_giong_db": cb.get("dinh_giong_db"),
            "giong_tren_nhac_tinh_db":
                (hop["tron_bat"] or {}).get("giong_tren_nhac_tinh_db"),
        },
        "do": do,
    }


def main() -> int:
    from app.core import thay_giong as TG

    if not NGUON.is_dir():
        print(f"KHÔNG CÓ thư mục nguồn: {NGUON}")
        return 2
    vids = sorted(NGUON.glob("*.mp4"))
    chi = sys.argv[1:] and {int(x) for x in sys.argv[1:]} or None
    ket: dict = {}
    if KQ.exists():
        try:
            ket = json.loads(KQ.read_text(encoding="utf-8"))
        except Exception:                                   # noqa: BLE001
            ket = {}
    print(f"{len(vids)} video · Demucs: {TG.tinh_trang_demucs()}")
    SB.mkdir(exist_ok=True)
    try:
        for i, g in enumerate(vids, 1):
            if chi and i not in chi:
                continue
            if ket.get(str(i), {}).get("ok"):
                print(f"\n[{i}/{len(vids)}] ĐÃ CÓ số đo, bỏ qua: {g.stem[:36]}")
                continue
            print(f"\n{'=' * 74}\n[{i}/{len(vids)}] {g.stem[:46]}")
            try:
                ket[str(i)] = lam_mot(i, g, ket)
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

    print(f"\n{'=' * 74}\nBẢNG MẤT TIẾNG — TRƯỚC / SAU  (thước: lớp giọng vs lớp giọng)")
    print(f"{'video':<30}{'dài':>9}{'HÙNG':>10}{'TẮT':>10}{'BẬT':>10}{'bù':>7}")
    t = {"HUNG": 0.0, "TAT": 0.0, "BAT": 0.0}
    tv = 0.0
    for i in sorted(ket, key=int):
        k = ket[i]
        if not k.get("ok"):
            print(f"{k.get('ten', '?')[:28]:<30}  LỖI {str(k.get('loi'))[:40]}")
            continue
        tv += k["dai"]
        c = []
        for n in ("HUNG", "TAT", "BAT"):
            v = (k["do"].get(n) or {}).get("giay_mat")
            c.append(f"{v:>9.2f}s" if v is not None else f"{'—':>10}")
            if v is not None:
                t[n] += v
        print(f"{k['ten'][:28]:<30}{k['dai']:>8.1f}s{''.join(c)}"
              f"{(k.get('bu_goc') or {}).get('so_bu', 0):>7}")
    print(f"{'TỔNG':<30}{tv:>8.1f}s"
          f"{t['HUNG']:>9.2f}s{t['TAT']:>9.2f}s{t['BAT']:>9.2f}s")
    if tv > 0:
        print(f"{'% video':<30}{'':>9}"
              f"{100 * t['HUNG'] / tv:>9.2f}%{100 * t['TAT'] / tv:>9.2f}%"
              f"{100 * t['BAT'] / tv:>9.2f}%")
    print(f"\n  GHÉP CẶP (cùng lượt chạy):  TẮT {t['TAT']:.2f}s -> "
          f"BẬT {t['BAT']:.2f}s   (giảm {t['TAT'] - t['BAT']:.2f}s)")
    print(f"  So bảng TRƯỚC 82,35s:       BẬT {t['BAT']:.2f}s")
    print(f"=> {KQ.name} · file nghe thử: {NGHE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
