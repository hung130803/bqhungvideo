"""LỜI KÊU 1 + 2 — BÙ GIỌNG GỐC CHÈN BAO NHIÊU GIÂY TIẾNG TRUNG VÀO VIDEO, VÀ
NÓ CÓ NẰM ĐÚNG CHỖ "ĐƯỢC ĐOẠN RỒI NGHỈ" KHÔNG (28/08/2026).

Chạy `thay_giong_video` THẬT trên **video gốc của chính anh Hùng**, với **đúng
cấu hình đọc từ QSettings** (`vnb:` nhân bản · `tach` · `hinh` · che chữ ·
nhấn nhá), rồi:

  (1) đọc thẳng `kq["bu_goc"]` — **MỘT lượt chạy cho SỐ CỦA CẢ HAI ARM**:
      `giay_bu` = số giây tiếng GỐC được chèn (arm BẬT, tức arm anh Hùng đang
      chạy) · `giay_trong` = số giây IM nếu TẮT bù. Hai cột này là hai nhánh
      của cùng một phép `khoang_khong_giong` nên chúng ghép cặp THEO CẤU TẠO,
      không cần chạy hai lượt để so.
  (2) **THƯỚC DỨT ĐIỂM:** ghép TẤT CẢ mảnh bù lại thành một file rồi đưa Groq
      chép lời **tự nhận diện**. Ở đây không có một mẩu giọng TTS nào lẫn vào
      nên whisper không có gì để mà "bịa theo ngữ cảnh Việt": ra chữ Hán là
      tiếng Trung THẬT, ra nhãn `Chinese` là xong chuyện.
      Đây là chỗ chữa cái bệnh của `_do_tieng_trung_con.py`: đo trên BẢN TRỘN
      thì giọng Việt lấn át, thả `language=None` ra nhãn "Vietnamese" và **0
      chữ Hán trên cả 4 video** (chứng nhận sạch GIẢ), còn ép `language="zh"`
      thì whisper bịa. Tách riêng vật liệu bù ra thì cả hai bệnh biến mất.
  (3) mảnh bù có rơi vào ĐÚNG khoảng im giữa câu không — nối lời kêu 1 với 2.

**KHÔNG ĐỤNG VIDEO GỐC:** chép sang hộp cát rồi làm trên bản sao.

    .venv\\Scripts\\python _do_bu_goc_that.py [BAT|TAT]
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ["WHISPER_PROVIDER"] = "groq"
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                       # noqa: BLE001
        pass

GOC = Path(r"C:\Users\Admin\Downloads\longtieng")
SB = Path(r"D:\claude\_hop_cat_4loi\m1")
NGHE = REPO / "_NGHE_THU_ANH_HUNG" / "bon_loi"

#: Video NGẮN NHẤT trong 4 bản anh Hùng vừa chạy (148,6 s gốc / 178,1 s xuất).
TEN = "#强烈推荐 #原创 #高分电影 #我在抖音看电影 #好片推荐.mp4"

# ---- ĐỌC THẲNG TỪ QSettings CỦA ANH HÙNG, KHÔNG ĐOÁN ----
#   tg_giong      = vnb:...\_mau_giong\test.wav
#   tg_ngon_ngu   = vi
#   tg_tron_cach  = tach      -> de_giong=False
#   tg_khop_cach  = hinh      -> hinh_theo_giong=True, doc_deu=False
#   tg_che_chu=1 · tg_viet_chu=1 · tg_nhan_nha=1
GIONG = r"vnb:C:\Users\Admin\AppData\Local\BQHungVideo\_mau_giong\test.wav"
DICH = "vi"

_HAN = re.compile(r"[㐀-䶿一-鿿豈-﫿]")


def han(s: str) -> str:
    return "".join(_HAN.findall(s or ""))


def ghep_manh_bu(khoang: list, tam: Path, ra: Path) -> int:
    """Nối MỌI mảnh bù thành một file để nghe/chép riêng. Trả số mảnh."""
    from app.core.thay_giong import _ffmpeg
    ds = sorted((tam / "bu_goc").glob("bu_*.wav"))
    if not ds:
        return 0
    lst = tam / "_bu_list.txt"
    lst.write_text(
        "".join(f"file '{p.as_posix()}'\n" for p in ds), encoding="utf-8")
    _ffmpeg(["-f", "concat", "-safe", "0", "-i", str(lst),
             "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(ra)],
            "ghép mảnh bù giọng gốc", timeout=600)
    return len(ds)


def chep(wav: Path) -> dict:
    from app.core import transcribe as tr
    return tr.transcribe(str(wav))


#: TÊN ARM -> (bu_giong_goc_bat, hinh_theo_giong, doc_deu).
#:   BAT/TAT = ô anh Hùng ĐANG dùng (mục 2), bật/tắt bù -> đo ĐÁNH ĐỔI.
#:   MUC1/MUC3 = hai ô CÒN LẠI trong combo, bù vẫn BẬT như mặc định -> trả lời
#:   câu "anh Hùng đổi Ô thì tiếng Trung bớt được bao nhiêu giây".
ARM = {
    "BAT":  (True,  True,  False),      # mục 2 — ĐÚNG ô anh Hùng đang chạy
    "TAT":  (False, True,  False),      # mục 2, tắt bù -> im lặng trở lại
    "MUC1": (True,  False, False),      # mục 1 — không chỉnh hình
    "MUC3": (True,  True,  True),       # mục 3 — chỉnh hình + đọc ĐỀU
}


def main() -> int:
    arm = (sys.argv[1] if len(sys.argv) > 1 else "BAT").upper()
    bat, hinh, deu = ARM[arm]
    from app.core import thay_giong as TG

    SB.mkdir(parents=True, exist_ok=True)
    NGHE.mkdir(parents=True, exist_ok=True)
    src = GOC / TEN
    if not src.exists():
        print(f"KHÔNG CÓ: {src}")
        return 2
    vin = SB / "nguon.mp4"
    if not vin.exists():
        shutil.copy2(src, vin)                  # làm trên BẢN SAO
    lam = SB / f"arm_{arm}"
    kqf = REPO / f"_kq_bu_goc_that_{arm}.json"

    print(f"ARM {arm} — bù={bat} · hinh_theo_giong={hinh} · doc_deu={deu}")
    print(f"video {TEN} ({TG.probe_duration(vin):.2f}s)")
    print(f"giọng {GIONG} · dịch sang {DICH} · tách+che chữ+nhấn nhá")

    t0 = time.time()
    r = TG.thay_giong_video(
        vin, dich_sang=DICH, thu_muc_lam=lam, voice=GIONG,
        cach_tach="demucs", giu_file_tam=True,
        che_chu=True, che_chu_cach="mo", che_chu_muc=1.0, viet_chu=True,
        hinh_theo_giong=hinh, doc_deu=deu,
        bu_giong_goc_bat=bat,
        de_giong=False,                             # cách trộn "tach"
        nhan_nha=True,
        on_progress=lambda p, m: print(f"   {p*100:5.1f}% {m}"))
    giay = time.time() - t0
    if not r.get("ok"):
        print(f"LỖI: {r.get('loi')}")
        kqf.write_text(json.dumps({"ok": False, "loi": str(r.get("loi"))[:500]},
                                  ensure_ascii=False, indent=1),
                       encoding="utf-8")
        return 1

    bu = r.get("bu_goc") or {}
    kh = r.get("khop") or {}
    hinh = r.get("hinh") or {}
    ket = {"arm": arm, "bat": bat, "video": TEN, "giay_chay": round(giay, 1),
           "bu_goc": bu, "hinh": hinh,
           "khop": {k: v for k, v in kh.items()
                    if k in ("tempo_max", "bo_qua", "so_cau")},
           "ra": r.get("ra")}

    print(f"\n{'='*74}\nXUẤT XONG {giay:.0f}s")
    print(f"  bù giọng gốc: {json.dumps(bu, ensure_ascii=False)[:600]}")

    # --- giữ bản nghe thử (chuẩn -14 LUFS đã do chính tron_thay_giong làm)
    ra = Path(r["ra"])
    giu = NGHE / f"BUGOC_{arm}_{ra.stem}{ra.suffix}"
    shutil.copy2(ra, giu)
    ket["nghe_thu"] = str(giu)
    print(f"  nghe thử -> {giu.name} ({giu.stat().st_size/1024/1024:.0f} MB)")

    # --- THƯỚC DỨT ĐIỂM: vật liệu bù, nghe RIÊNG, chép RIÊNG
    tam = lam / ra.parent.name if (lam / ra.parent.name).exists() else ra.parent
    if bat:
        bw = SB / f"chi_manh_bu_{arm}.wav"
        n = ghep_manh_bu(bu.get("khoang") or [], tam, bw)
        ket["so_manh_bu_tren_dia"] = n
        if n:
            shutil.copy2(bw, NGHE / f"CHI_MANH_BU_{n}manh.wav")
            d = chep(bw)
            txt = d.get("text") or ""
            h = han(txt)
            ket["chep_manh_bu"] = {
                "nhan_ngon_ngu": d.get("language"),
                "giay": round(float(d.get("duration") or 0), 2),
                "so_ky_tu": len(txt), "so_ky_tu_HAN": len(h),
                "ti_le_han": round(len(h) / len(txt), 3) if txt else 0.0,
                "trich": txt[:400],
            }
            print(f"\n  === CHÉP RIÊNG VẬT LIỆU BÙ ({n} mảnh) ===")
            print(f"  nhãn ngôn ngữ Groq: {d.get('language')}")
            print(f"  ký tự Hán: {len(h)}/{len(txt)}")
            print(f"  trích: {txt[:300]}")

    kqf.write_text(json.dumps(ket, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\n=> {kqf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
