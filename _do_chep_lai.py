# -*- coding: utf-8 -*-
"""CHÉP LỜI LẠI BẢN THÀNH PHẨM — cách gần "NGHE" nhất mà máy làm được.

Mọi thước trước đây đo thứ app TỰ KHAI (độ dài file, tempo, mốc dự kiến). Cái
anh Hùng làm là MỞ FILE RA NGHE. Thước này bắt chước đúng chuyện đó: xuất một
video THẬT bằng chính `thay_giong_video`, rồi đưa file thành phẩm cho Groq
**chép lời lại**, xong so với bản dịch mà app ĐỊNH nói.

Trả lời 3 câu một lúc:
  (1) **NÓI ĐÚNG CHỮ KHÔNG** — sai bao nhiêu % từ (WER), câu nào sai. Cao =
      "nói không chuẩn" (lỗi 3).
  (2) **NÓI ĐÚNG LÚC KHÔNG** — mốc câu #i trong file thành phẩm so với mốc
      người GỐC nói câu đó. Đây là phép đo hướng (a) chưa ai làm: trước giờ chỉ
      đo "lệch đầu đoạn", chưa bao giờ hỏi từng câu có rơi đúng lúc không.
  (3) **edge-tts đọc nhanh có nuốt chữ không** — chính là (1), đo trên bản
      thành phẩm đã qua `rate`/`atempo`.

    .venv\\Scripts\\python _do_chep_lai.py [zh|zh2|en] [số lượt]
"""
from __future__ import annotations

import difflib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

import _do_kho_tg as KHO                       # noqa: E402
from app.core import thay_giong as tg          # noqa: E402

SAN = REPO / "_do_chep_san"
_TU = re.compile(r"[a-z0-9']+")


def tu(s: str) -> list[str]:
    """Tách từ + chuẩn hoá — so chữ thì bỏ hoa/thường và dấu câu."""
    return _TU.findall((s or "").lower())


def main() -> int:
    ten = sys.argv[1] if len(sys.argv) > 1 else "zh"
    so_luot = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    dich_sang = "vi" if ten == "en" else "en"
    SAN.mkdir(parents=True, exist_ok=True)

    k = KHO.chuan_bi(ten, can_nhac=False)
    cau = k["cau"]
    print(f"[{ten}] {k['tong']:.2f}s · {len(cau)} câu · dịch sang {dich_sang}\n")

    bang = []
    for lan in range(1, so_luot + 1):
        tam = SAN / f"{ten}_l{lan}"
        if tam.exists():
            shutil.rmtree(tam, ignore_errors=True)
        tam.mkdir(parents=True, exist_ok=True)
        print(f"--- LƯỢT {lan}/{so_luot} — chạy ĐỦ đường thay giọng ---")
        t0 = time.time()
        r = tg.thay_giong_video(k["video"], dich_sang=dich_sang,
                                thu_muc_lam=tam, giu_file_tam=True)
        if not r.get("ok"):
            print(f"  LỖI: {r.get('loi')}")
            continue
        ra = Path(r["ra"])
        print(f"  xuất xong {time.time() - t0:.1f}s · {ra.name}")

        # --- chép lời lại CHÍNH FILE THÀNH PHẨM (có cả nhạc nền, đúng thứ tai nghe)
        wav = tam / "thanhpham.wav"
        tg.tach_wav(ra, wav)
        cl = tg.chep_loi(wav)
        nghe_tu = [(str(w.get("word", "")).strip(), float(w.get("start", 0)))
                   for w in (cl.get("words") or [])]
        nghe = [tu(w)[0] if tu(w) else "" for w, _ in nghe_tu]
        nghe_t = [t for _, t in nghe_tu]
        # bỏ token rỗng nhưng GIỮ mốc tương ứng
        gi = [j for j, w in enumerate(nghe) if w]
        nghe = [nghe[j] for j in gi]
        nghe_t = [nghe_t[j] for j in gi]

        # --- bản app ĐỊNH nói: bản dịch CUỐI CÙNG (sau rút gọn/đọc nhanh)
        mong = r.get("loi_cuoi") or []
        # MỐC phải lấy từ CHÍNH lượt chạy này. `thay_giong_video` tự chép lời
        # lại trên lớp GIỌNG đã tách (Demucs), ra 35 câu, trong khi bản cache
        # của `_do_kho_tg` chép trên wav THÔ ra 37 câu — lấy nhầm là so câu #i
        # của bảng này với mốc câu #i của bảng KHÁC, số ra sai hoàn toàn mà
        # trông vẫn hợp lý (lượt đo đầu ra "lệch 3,2 giây", toàn bộ do lỗi này).
        moc = r.get("cau_moc") or []
        if not mong or len(moc) != len(mong):
            print(f"  (mong {len(mong)} câu · mốc {len(moc)} câu -> bỏ lượt)")
            continue
        if not mong:
            print("  (không lấy được bản dịch cuối -> bỏ lượt)")
            continue

        mong_tu: list[str] = []
        ranh: list[tuple[int, int]] = []      # (đầu, cuối) từ của câu i
        for s in mong:
            a = len(mong_tu)
            mong_tu += tu(s)
            ranh.append((a, len(mong_tu)))

        sm = difflib.SequenceMatcher(None, mong_tu, nghe, autojunk=False)
        khop = sum(b.size for b in sm.get_matching_blocks())
        wer = 1.0 - khop / max(1, len(mong_tu))

        # từ mong -> chỉ số từ nghe (chỉ với phần KHỚP)
        anh = {}
        for b in sm.get_matching_blocks():
            for o in range(b.size):
                anh[b.a + o] = b.b + o

        lech, sai_cau = [], []
        for i, (a, b) in enumerate(ranh):
            js = [anh[x] for x in range(a, b) if x in anh]
            n_tu = max(1, b - a)
            if len(js) < max(1, n_tu // 2):
                sai_cau.append(i)          # quá nửa số từ không nghe thấy
                continue
            lech.append(nghe_t[min(js)] - float(moc[i][0]))

        lech_abs = sorted(abs(x) for x in lech)
        def _tv(xs):
            return xs[len(xs) // 2] if xs else 0.0
        d = {
            "lan": lan, "wer": round(100 * wer, 1),
            "tu_mong": len(mong_tu), "tu_nghe": len(nghe), "khop": khop,
            "cau_mat": len(sai_cau), "so_cau": len(ranh),
            "lech_tv_ms": round(1000 * _tv(lech_abs), 0),
            "lech_max_ms": round(1000 * (lech_abs[-1] if lech_abs else 0), 0),
            "cau_lech_qua_1s": sum(1 for x in lech_abs if x > 1.0),
            "cau_do_duoc": len(lech),
        }
        bang.append(d)
        print(f"  SAI CHỮ (WER)   : {d['wer']}%  "
              f"({d['khop']}/{d['tu_mong']} từ nghe đúng)")
        print(f"  câu MẤT HẲN     : {d['cau_mat']}/{d['so_cau']}"
              f"  {sai_cau[:10]}")
        print(f"  LỆCH MỐC từng câu: trung vị {d['lech_tv_ms']:.0f} ms · "
              f"lớn nhất {d['lech_max_ms']:.0f} ms · "
              f"quá 1s: {d['cau_lech_qua_1s']}/{d['cau_do_duoc']}")
        print()

    if bang:
        print("===== TỔNG HỢP =====")
        print(f"{'lượt':>5} {'WER':>7} {'câu mất':>9} {'lệch tv':>9} "
              f"{'lệch max':>9} {'lệch >1s':>9}")
        for d in bang:
            print(f"{d['lan']:>5} {d['wer']:>6}% {d['cau_mat']:>4}/"
                  f"{d['so_cau']:<4} {d['lech_tv_ms']:>7.0f}ms "
                  f"{d['lech_max_ms']:>7.0f}ms "
                  f"{d['cau_lech_qua_1s']:>4}/{d['cau_do_duoc']:<4}")
        (SAN / f"kq_{ten}.json").write_text(
            json.dumps(bang, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
