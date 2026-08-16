# -*- coding: utf-8 -*-
"""ĐO CÁCH LẤY MỐC TỪNG CHỮ CỦA PIPER — chọn giữa 2 cách đặt tên file.

VÌ SAO CÓ FILE NÀY: lượt đo trước (`_do_piper_moc.py`) ra **44 WAV cho 48 từ**
mà vẫn `zip()` ghép bừa -> mốc gán SAI TỪ, rc=0, không một dòng báo. Đúng họ
bẫy repo này đang chống. Gốc nằm ở `piper/__main__.py` dòng 206:

    wav_path = output_dir / f"{time.monotonic_ns()}.wav"

`time.monotonic` trên Windows nhảy **15,625 ms** (đo được, Python 3.12), nên
hai từ NGẮN đọc liền nhau nhận CÙNG một tên -> file sau GHI ĐÈ file trước.

Cách thay thế: `--output-dir-naming text` (tên file = chính chữ đó). Hết va
chạm thời gian, nhưng đẻ ra 2 va chạm KHÁC phải đo chứ không được đoán:
  (a) chữ TRÙNG NHAU trong câu ("tôi" xuất hiện 3 lần)
  (b) Windows KHÔNG PHÂN BIỆT HOA/THƯỜNG -> "Tôi" và "tôi" chung một file
  (c) `sanitize_filename` bỏ ký tự cấm -> 2 chữ khác nhau ra cùng tên

    .venv\\Scripts\\python -u _do_piper_moc2.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import wave
from pathlib import Path

# KHÔNG ghi cứng đường repo, và phải là `.parent` của CHÍNH file này — chạy
# phép đo từ một worktree khác mà trỏ về repo chính là đo BẢN MÃ KHÁC.
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

LIB = REPO / "_piper"
MODEL = LIB / "voices" / "vi_VN-vais1000-medium.onnx"
WORK = REPO / "_do_piper" / "work2"
PY = str(REPO / ".venv" / "Scripts" / "python.exe")
NO_WIN = 0x08000000 if os.name == "nt" else 0

# Câu thử CỐ Ý có chữ lặp ("tôi" 3 lần, "con" 2 lần) và chữ hoa/thường lẫn
# nhau — nếu không có mấy chỗ đó thì phép đo tự tránh mất đúng cái bẫy nó cần
# bắt.
CAU = ("Hôm nay tôi sẽ chia sẻ với các bạn một câu chuyện rất thú vị "
       "mà tôi đã gặp cách đây ba phút, khi đang đi bộ trên con đường quen thuộc "
       "gần nhà mình, và điều đó làm tôi suy nghĩ mãi cho tới tận bây giờ.")


def env_piper() -> dict:
    e = dict(os.environ)
    e["PYTHONPATH"] = str(LIB)
    e["PYTHONIOENCODING"] = "utf-8"
    return e


def chay(args: list[str], vao: str = "", han: int = 300):
    t0 = time.time()
    r = subprocess.run([PY, "-m", "piper", "-m", str(MODEL), *args],
                       input=vao.encode("utf-8"),
                       capture_output=True, env=env_piper(),
                       creationflags=NO_WIN, timeout=han)
    return (r.returncode, r.stderr.decode("utf-8", "replace")[-300:],
            round(time.time() - t0, 3))


def dai_wav(p) -> float:
    try:
        with wave.open(str(p), "rb") as w:
            return w.getnframes() / float(w.getframerate() or 1)
    except Exception:  # noqa: BLE001
        return 0.0


def don(d: Path) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("*.wav"):
        f.unlink()
    return d


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    print("=" * 74)
    print("ĐO CÁCH LẤY MỐC TỪNG CHỮ CỦA PIPER")
    print("=" * 74)
    print(f"phân giải `time.monotonic` máy này: "
          f"{time.get_clock_info('monotonic').resolution * 1000:.3f} ms")
    tu = CAU.split()
    print(f"câu thử: {len(CAU)} ký tự · {len(tu)} từ")
    thuong = [t.lower() for t in tu]
    print(f"  chữ khác nhau (phân biệt hoa/thường): {len(set(tu))}")
    print(f"  chữ khác nhau (KHÔNG phân biệt)     : {len(set(thuong))}"
          "   << Windows dùng số này")

    # ---------- mốc: cả câu ----------
    f_cau = WORK / "ca_cau.wav"
    rc, err, gy = chay(["-f", str(f_cau)], vao=CAU)
    d_cau = dai_wav(f_cau)
    print(f"\ncả câu: rc={rc} · tiếng={d_cau:.3f}s · wall={gy}s "
          f"· nhanh gấp {d_cau / max(gy, 1e-9):.2f}× thời gian thật")
    if rc != 0:
        print("stderr:", err)
        return 1

    kq = {"d_cau": d_cau, "so_tu": len(tu)}

    # ---------- CÁCH A: timestamp (cách lượt trước dùng) ----------
    print("\n[A] --output-dir-naming timestamp  (mỗi TỪ một dòng)")
    dA = don(WORK / "A")
    rc, err, gyA = chay(["-d", str(dA), "--output-dir-naming", "timestamp"],
                        vao="\n".join(tu))
    wA = sorted(dA.glob("*.wav"), key=lambda p: int(p.stem))
    mat = len(tu) - len(wA)
    print(f"    rc={rc} · WAV ra={len(wA)} / từ={len(tu)} · MẤT {mat} file")
    print(f"    => {'HỎNG — mốc sẽ gán LỆCH TỪ' if mat else 'đủ'}")
    kq["A_so_wav"] = len(wA)

    # ---------- CÁCH B: text, có KHỬ TRÙNG ----------
    print("\n[B] --output-dir-naming text  (khử trùng theo chữ THƯỜNG)")
    # gửi mỗi chữ khác nhau ĐÚNG MỘT LẦN, giữ thứ tự xuất hiện
    rieng: list[str] = []
    for t in thuong:
        if t not in rieng:
            rieng.append(t)
    dB = don(WORK / "B")
    rc, err, gyB = chay(["-d", str(dB), "--output-dir-naming", "text"],
                        vao="\n".join(rieng))
    wB = list(dB.glob("*.wav"))
    print(f"    rc={rc} · gửi {len(rieng)} chữ khác nhau · WAV ra={len(wB)}")

    # TRA THEO TÊN, nhưng KHÔNG ĐOÁN tên: `pathvalidate` đổi tên theo luật
    # riêng của nó (đo được: `con` -> `con_.wav` vì CON là tên THIẾT BỊ của
    # Windows). Đoán sai tên -> tra hụt -> mốc gán lệch mà không ai báo. Nên
    # dò bằng bộ khớp NHIỀU DẠNG rồi ĐỐI SOÁT tiêu thụ hết file hay chưa.
    co_dia = {p.name.lower(): p for p in dB.glob("*.wav")}

    def tra(s: str):
        for ten in (f"{s}.wav", f"{s}_.wav"):
            p = co_dia.get(ten.lower())
            if p is not None:
                return p
        return None

    bang: dict[str, float] = {}
    thieu = []
    dung_roi = set()
    for t in rieng:
        p = tra(t)
        if p is None:
            thieu.append(t)
            continue
        bang[t] = dai_wav(p)
        dung_roi.add(p.name.lower())
    thua = [n for n in co_dia if n not in dung_roi]
    print(f"    tra được {len(bang)}/{len(rieng)} chữ · thiếu {thieu}")
    print(f"    file KHÔNG chữ nào nhận: {thua}   << thừa = có chữ tra nhầm")
    kq["B_gui"] = len(rieng)
    kq["B_so_wav"] = len(wB)
    kq["B_tra_duoc"] = len(bang)

    du = len(bang) == len(rieng) and not thieu
    print(f"    => {'ĐỦ — mốc gán ĐÚNG TỪ' if du else 'HỎNG'}")

    # ---------- ghép mốc + CO GIÃN về đúng độ dài câu thật ----------
    print("\n[C] ghép mốc rồi CO GIÃN về đúng độ dài câu THẬT")
    tho = [bang.get(t, 0.0) for t in thuong]
    tong_tho = sum(tho)
    print(f"    tổng độ dài từng chữ đọc RỜI = {tong_tho:.3f}s")
    print(f"    độ dài câu đọc LIỀN          = {d_cau:.3f}s")
    print(f"    CHÊNH = {tong_tho - d_cau:+.3f}s "
          f"({(tong_tho / max(d_cau, 1e-9) - 1) * 100:+.1f}%)  "
          "<< vì sao BẮT BUỘC phải co giãn")
    he = d_cau / max(tong_tho, 1e-9)
    moc, t = [], 0.0
    for chu, d in zip(tu, tho):
        d2 = d * he
        moc.append([round(t, 3), round(t + d2, 3), chu])
        t += d2
    print(f"    hệ số co giãn = {he:.4f} · mốc cuối = {moc[-1][1]:.3f}s "
          f"(câu {d_cau:.3f}s)")
    print("    5 mốc đầu:", moc[:5])
    kq["tong_tho"] = tong_tho
    kq["he_co_gian"] = he
    kq["moc"] = moc

    # ---------- chi phí ----------
    print("\n[D] chi phí lấy mốc")
    print(f"    đọc cả câu        : {gy}s")
    print(f"    đọc {len(rieng)} chữ rời   : {gyB}s")
    print(f"    => lấy mốc đắt thêm {gyB / max(gy, 1e-9):.2f}× lượt đọc câu")
    kq["giay_cau"] = gy
    kq["giay_moc"] = gyB

    # ---------- [E] length_scale bão hoà ----------
    # ĐO LẠI, KHÔNG CHÉP SỐ CŨ: bảng `length_scale` ghi trong
    # `_do_piper/work/ket_qua.json` ra **TOÀN 0,000 giây** — tức lượt đo đó
    # KHÔNG HỀ CHẠY ĐƯỢC, mà script cũ không kiểm `rc` ở vòng này nên nó vẫn
    # ghi ra file kết quả trông như thật. Đúng họ bẫy "phép đo hỏng phát
    # chứng nhận" (astats cổng 53 · startswith cổng 44).
    print("\n[E] `length_scale` — ép ngắn tới đâu thì DỪNG (đo lại, có kiểm rc)")
    print(f"    {'length_scale':>12} | {'rc':>3} | {'giây':>8} | {'so tự nhiên':>12}")
    bang_ls, hong = [], 0
    for ls in (1.0, 0.9, 0.8, 0.74, 0.7, 0.6, 0.5, 0.45, 0.3, 0.2):
        f = WORK / f"ls_{ls}.wav"
        if f.exists():
            f.unlink()
        rc2, err2, _g = chay(["-f", str(f), "--length-scale", str(ls)], vao=CAU)
        d = dai_wav(f)
        if rc2 != 0 or d <= 0:          # KHÔNG im lặng ghi 0 vào bảng
            hong += 1
            print(f"    {ls:>12} | {rc2:>3} |   HỎNG   | {err2[:60]}")
            continue
        ty = d / max(d_cau, 1e-9)
        bang_ls.append((ls, d, ty))
        print(f"    {ls:>12} | {rc2:>3} | {d:>8.3f} | {ty:>11.3f}×")
    if bang_ls:
        nho = min(t for _l, _d, t in bang_ls)
        san = min((l for l, _d, t in bang_ls if abs(t - nho) < 0.005),
                  default=None)
        print(f"    => NÉN SÂU NHẤT: {nho:.3f}× độ dài tự nhiên "
              f"(bão hoà từ length_scale ≈ {san})")
        kq["ls_nen_sau_nhat"] = nho
        kq["ls_bao_hoa_tu"] = san
    kq["ls"] = [[l, d, t] for l, d, t in bang_ls]
    kq["ls_hong"] = hong

    json.dump(kq, open(WORK / "ket_qua.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\nGhi: {WORK / 'ket_qua.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
