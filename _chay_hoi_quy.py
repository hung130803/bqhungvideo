# -*- coding: utf-8 -*-
"""CHẠY CẢ LƯỢT HỒI QUY, IN **MÃ THOÁT THẬT** CỦA TỪNG CỔNG.

BA CÁI BẪY FILE NÀY CỐ Ý TRÁNH (đều đã sập ít nhất một lần trong repo):
 1. **Nối `| tail` là NUỐT MÃ THOÁT** — mã thoát thấy được sẽ là của `tail`.
    Đây gọi `subprocess.run` rồi in `returncode` nguyên vẹn.
 2. **cp1252**: chạy hồi quy mà đổ ra file thì `print` tiếng Việt nổ
    `UnicodeEncodeError` -> cổng chết trong 0-1 giây, chạy tay lại xanh. Ép
    `PYTHONIOENCODING=utf-8` cho MỌI tiến trình con.
 3. **"xanh" vì chạy chưa tới chốt**: cổng chết sớm cũng có thể rc=0 nếu nó
    thoát trước phần kiểm. Nên in kèm **thời gian chạy** và **dòng tổng kết
    ĐẠT/HỎNG** dò được — rc=0 mà 0 giây / không có dòng tổng kết là ĐÁNG NGỜ.

    .venv\\Scripts\\python -u _chay_hoi_quy.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

PY = str(REPO / ".venv" / "Scripts" / "python.exe")

#: (nhãn, file, mốc ĐẠT mong đợi hoặc None)
CONG = [
    # 70, 69 và 68 PHẢI nằm trong danh sách này: cổng không được gọi thì nó chỉ
    # là một file .py nằm đó, và lượt hồi quy "xanh" mà không chạy cổng mới
    # chính là bẫy "ĐẠT OAN vì lượt chạy chưa tới chốt".
    #
    # Cổng 70 canh bản sửa CHẶN SẢN XUẤT (Groq khai tử `llama-3.3-70b-
    # versatile` -> 404 hàng loạt -> chết cả dây chuyền). Nó CÓ gọi Groq thật ở
    # mục 9 để chứng minh bảng phân loại lỗi khớp thân lỗi Groq trả về HÔM NAY;
    # muốn chạy offline thì đặt `BQ_BO_MANG=1`.
    # Cổng 72 canh nhóm GIỌNG NGOÀI (OmniVoice / IndexTTS). Nó KHÔNG đốt GPU
    # hay lượt Groq nào trong hồi quy (vá `_chay_ov` + `_lay_moc_groq`); ca
    # chạy THẬT bật bằng `BQ_GN_THAT=1`.
    # Mốc 40 -> 48 (18/08/2026): CA 7 thêm 5 mục canh NHÃN ĐỔI THEO MÁY (có bộ
    # gióng hàng thì con số PHỦ/RUNG trong nhãn phải khác hẳn lúc chưa có, và
    # phần GIẤY PHÉP CC-BY-NC giữ nguyên ở CẢ HAI) + 3 mục canh CHỖ ĐỂ ĐỒ
    # không nằm trong `%TEMP%` (môi trường 7,74 GB từng nằm ở đó: một lượt dọn
    # đĩa là giọng biến khỏi combo, đúng bệnh `_lib` cổng 58 CA5).
    # Cổng 74 canh bản sửa CHẶN SẢN XUẤT thứ HAI trong hai ngày: Groq áp trần
    # token đầu ra MẶC ĐỊNH (3072/2048) khi app không đặt `max_tokens`, làm JSON
    # bản dịch ĐỨT giữa chừng -> "LLM trả về không phải JSON hợp lệ". Nó nằm
    # ĐÂY vì đúng hôm qua cổng 70 vừa dính bẫy "cổng không ai gọi thì chỉ là
    # một file .py nằm đó". Không đốt lượt Groq đáng kể: chỉ CA 9 gọi thật
    # (30 câu, 1 lượt); `BQ_BO_MANG=1` để chạy hoàn toàn offline.
    ("74 JSON bao dung",    "_test_json_bao_dung.py",    69),
    ("72 giọng ngoài",      "_test_giong_ngoai.py",      48),
    # Cổng 73 canh chính `giong_hang.py`. Trước hôm nay nó chỉ được canh GIÁN
    # TIẾP qua cổng 72 — tức phần lấy mốc cho MỌI máy đọc không có cổng riêng.
    ("73 gióng hàng",       "_test_giong_hang.py",      None),
    ("71 tách giọng GPU",   "_test_demucs_gpu.py",       22),
    ("70 model Groq còn sống", "_test_groq_model.py",    42),
    ("69 viết tắt + mốc",   "_test_viet_tat.py",         95),
    # Mốc 43 -> 44: thêm mục 7a' TỰ KIỂM bản vá cách ly QSettings (18/08/2026,
    # cổng từng ĐỎ OAN vì đọc trúng registry thật của anh Hùng).
    ("68 kiểu chữ thay giọng", "_test_kieu_chu_tg.py",    44),
    ("67 Adam ElevenLabs",  "_test_eleven_tg.py",        35),
    ("66 độ to đường xuất", "_test_do_to_xuat.py",       50),
    ("65 độ to + nghe thử", "_test_do_to_nghe_thu.py",   47),
    # Mốc 47 -> 57: cổng đã mọc thêm mục từ lâu (đo 53) và 18/08 thêm CA 3g
    # (nút tải Piper phải KHOÁ khi máy thiếu Python 3, như nút Demucs). Để mốc
    # thấp hơn số thật là mất khả năng bắt "mục lặng lẽ biến mất".
    ("64 Piper",            "_test_piper.py",           57),
    ("63 biến thể giọng",   "_test_bien_the_giong.py",  24),
    ("62 quét cả khung",    "_test_toan_khung.py",      33),
    ("60 chữ theo lời",     "_test_chu_theo_loi.py",    42),
    ("59 đường dài",        "_test_duong_dai.py",       46),
    ("57 bảng tiến độ",     "_test_tg_bang_tiendo.py",  57),
    ("56 che chữ",          "_test_che_chu.py",        123),
    ("55 thay giọng UI",    "_test_thay_giong_ui.py",   48),
    ("54 dubbing CJK",      "_test_dubbing_cjk.py",     44),
    ("53 thay giọng",       "_test_thay_giong.py",      44),
    ("52 CJK vá",           "_test_cjk_va.py",          46),
    ("52b mảnh cuối",       "_test_manh_cuoi.py",     None),
    ("31 nút không cụt",    "_test_nut_khong_cut.py", None),
    ("và/lỡ phụ đề",        "_test_va_lo_sub.py",       16),
    ("không popup",         "_test_no_popup.py",      None),
    ("làn cắt đói",         "_test_lane_starve.py",   None),
    ("smoke",               "_test_app_smoke.py",     None),
]

#: Dòng tổng kết — mỗi cổng viết một kiểu, có cổng bỏ dấu tiếng Việt
#: ("DAT 42 · HONG 0"). Bắt hụt thì cột ĐẠT ra "?" và cổng bị gắn nhãn ĐÁNG
#: NGỜ oan; đã dính một lượt với cổng 60/63.
_RE_TK = re.compile(r"(?:ĐẠT|DAT|OK)\s+(\d+)\s*[·.]\s*"
                    r"(?:HỎNG|HONG|SAI)\s+(\d+)")

#: Mục cổng CỐ Ý KHÔNG CHẤM. Hiện chỉ cổng 56 có (CA17a/b/c đo THỜI GIAN, máy
#: bận thì `bo_qua()` — chấm ĐẠT là phát chứng nhận khống, chấm HỎNG là đỏ oan).
#: Không trừ phần này ra thì cổng 56 bị gắn nhãn "TỤT so mốc 123" MỖI LẦN máy
#: bận, và nhãn TỤT xuất hiện thường xuyên thì người ta thôi đọc nó — đúng cái
#: bẫy "cổng đỏ oan còn nguy hơn không có cổng" (bài học cổng 41 và 47).
_RE_BQ = re.compile(r"(?:BỎ QUA|BO QUA)\s+(\d+)")


def moi_truong() -> dict:
    e = dict(os.environ)
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONUTF8"] = "1"
    e["BQ_FFMPEG_SLOTS"] = "1"
    # KHÔNG dùng `main`: sau khi gộp thì mốc CHÍNH LÀ bản đang test -> cổng
    # đối chứng tự PASS OAN vĩnh viễn.
    #
    # VÌ SAO `v2.25.0` CHỨ KHÔNG `v2.26.0` (đã chạy nhầm một lượt, cổng bắt
    # được): mục CA23-3'' của cổng 56 đòi **bản mốc phải có TRƯỚC tính năng
    # che chữ** — không thì phép so "bật/tắt che chữ vẫn ra cùng dedup_key"
    # là so với chính tính năng đang test. Mà `che_chu` RA ĐỜI Ở v2.26.0
    # (`git show v2.25.0:app/services.py` có 0 dòng `che_chu`, v2.26.0 có 15).
    # Lấy v2.26.0 làm mốc -> CA23-3'' ĐỎ, và nó đỏ ĐÚNG: cổng đang báo mốc
    # không hợp lệ chứ không phải app hỏng. Mốc đúng = bản phát hành NGAY
    # TRƯỚC tính năng.
    e.setdefault("BQ_MOC_REF", "v2.25.0")
    return e


def main() -> int:
    env = moi_truong()
    print("=" * 78)
    print(f"HỒI QUY — {len(CONG)} cổng · BQ_MOC_REF={env['BQ_MOC_REF']}")
    print("=" * 78)
    kq = []
    for ten, f, moc in CONG:
        p = REPO / f
        if not p.exists():
            print(f"  {ten:<22} KHÔNG CÓ FILE {f}")
            kq.append((ten, f, -1, 0.0, None, None, moc, 0))
            continue
        t0 = time.time()
        r = subprocess.run([PY, "-u", str(p)], cwd=str(REPO), env=env,
                           capture_output=True, timeout=3600)
        gy = time.time() - t0
        out = (r.stdout or b"").decode("utf-8", "replace") + \
              (r.stderr or b"").decode("utf-8", "replace")
        (REPO / "_kq_hq").mkdir(exist_ok=True)
        (REPO / "_kq_hq" / f"{f}.txt").write_text(out, encoding="utf-8")
        m = None
        for m2 in _RE_TK.finditer(out):
            m = m2                            # lấy dòng tổng kết CUỐI CÙNG
        dat = int(m.group(1)) if m else None
        hong = int(m.group(2)) if m else None
        mbq = None
        for m3 in _RE_BQ.finditer(out):
            mbq = m3                          # dòng tổng kết CUỐI CÙNG
        bq = int(mbq.group(1)) if mbq else 0
        # So mốc theo ĐẠT + BỎ QUA: mục bỏ qua là mục KHÔNG CHẤM, không phải
        # mục mất đi. Vẫn in ra số bỏ qua để một lượt bỏ qua không bao giờ
        # trông giống một lượt chấm đủ.
        kq.append((ten, f, r.returncode, gy, dat, hong, moc, bq))
        co = "" if moc is None or dat is None else (
            "  (mốc %d)" % moc if dat + bq >= moc else "  << TỤT so mốc %d" % moc)
        if bq:
            co = f"  · BỎ QUA {bq}{co}"
        print(f"  {ten:<22} rc={r.returncode:<3} {gy:6.1f}s  "
              f"ĐẠT {dat if dat is not None else '?':>4} · "
              f"HỎNG {hong if hong is not None else '?':<4}{co}")

    print("=" * 78)
    do = [k for k in kq if k[2] != 0]
    ngo = [k for k in kq if k[2] == 0 and (k[4] is None or k[3] < 0.3)]
    print(f"ĐỎ: {len(do)} cổng" + (f" -> {[k[0] for k in do]}" if do else ""))
    if ngo:
        print(f"ĐÁNG NGỜ (rc=0 mà không thấy dòng tổng kết / chạy <0,3s): "
              f"{[k[0] for k in ngo]}")
    tut = [k[0] for k in kq
           if k[6] and k[4] is not None and k[4] + k[7] < k[6]]
    if tut:
        print(f"TỤT SỐ MỤC so với mốc: {tut}")
    bqua = [(k[0], k[7]) for k in kq if k[7]]
    if bqua:
        print(f"MỤC KHÔNG CHẤM (máy bận, không phải ĐẠT cũng không phải "
              f"HỎNG): {bqua}")
    return 1 if do else 0


if __name__ == "__main__":
    raise SystemExit(main())
