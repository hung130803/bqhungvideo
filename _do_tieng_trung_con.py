"""LỜI KÊU 2 — "vẫn DÍNH TIẾNG TRUNG âm thanh gốc": ĐẾM GIÂY, TRÊN CHÍNH 4 FILE
ANH HÙNG VỪA XUẤT SÁNG 28/08/2026.

**THƯỚC PHẢI LÀ ASR, KHÔNG PHẢI RMS.** RMS/đường bao mức không phân biệt được
"tiếng động nền" với "người đang nói tiếng Trung" — mà đó đúng là câu hỏi.

**LƯỢT ĐẦU CỦA CHÍNH SCRIPT NÀY ĐÃ RA SỐ SAI, GHI LẠI KẺO NGƯỜI SAU LẠI SẬP:**
thả `language=None` cho Groq tự nhận diện thì nó chấm nhãn **cho CẢ FILE**. Bản
trộn cuối phần lớn là giọng Việt -> nhãn "Vietnamese" -> whisper **không bao giờ
sinh ra một ký tự Hán nào**, kể cả ở đoạn đang có người nói tiếng Trung. Kết
quả: **0,00 giây / 4 video** — một chứng nhận SẠCH hoàn toàn giả. Đúng họ bẫy
"phép đo hỏng phát chứng nhận".

**THƯỚC ĐÚNG = 3 CỘT, và cột 3 mới là cột chốt:**
  (1) ÉP `language="zh"` khi chép bản THÀNH PHẨM -> mọi chỗ nghe ra tiếng Trung
      đều bung chữ Hán. Một mình cột này KHÔNG đọc được: ép tiếng Trung lên
      giọng Việt thì whisper **bịa** chữ Hán.
  (2) SÀN BỊA (đối chứng bắt buộc): ép `language="zh"` lên một file **CHỈ CÓ
      giọng Việt** (không một mảnh tiếng gốc nào). Bao nhiêu chữ Hán ra ở đây
      là bấy nhiêu chữ Hán BỊA — mọi số ở cột (1) phải trừ đi cái sàn này.
  (3) **ĐỐI CHIẾU VỚI SỰ THẬT:** chép bản GỐC (tiếng Trung, tự nhận diện) làm
      chuẩn, rồi hỏi từng đoạn Hán ở cột (1): chữ đó có TRÙNG với chữ mà người
      gốc nói ĐÚNG LÚC ĐÓ không (quy về trục gốc bằng `t / k`)? Trùng thì đó là
      tiếng gốc THẬT lọt vào; không trùng gì thì đó là whisper bịa.

**KẾT CỤC: CỘT (2) ĐÃ ĐO, VÀ NÓ GIẾT CẢ PHÉP ĐO NÀY — ĐỌC TRƯỚC KHI DÙNG LẠI
BẤT CỨ SỐ NÀO Ở ĐÂY.** `_do_thuoc_zh_san.py` dựng SÀN BỊA bằng cặp sạch nhất
có thể (cùng video, cùng lượt dựng, khác đúng một cờ `bu_giong_goc_bat`):

    · bản xuất **KHÔNG có một mẩu tiếng gốc nào**  -> ép zh ra **94,99%**
    · bản xuất **CÓ 25,57 giây tiếng Trung thật**  -> ép zh ra **99,53%**
    · CHÊNH chỉ **4,54 điểm phần trăm**

Tức ép `language="zh"` lên bản trộn thì whisper **bịa chữ Hán gần bằng lượng
thật**, và phép đối chiếu với lời gốc KHÔNG cứu được: bản Việt vốn LÀ bản dịch
của lời Trung nên chữ bịa vẫn "trùng" theo nghĩa. **Con số 85,72% mà script này
từng in ra là RÁC, đã gạch khỏi báo cáo.** Cả hai chiều đều hỏng: thả
`language=None` ra **0,00%** (chứng nhận sạch giả, vì nhãn cả file là
"Vietnamese"), ép `zh` ra **~99%** (báo động giả).

**THƯỚC ĐÚNG CHO CÂU HỎI NÀY NẰM Ở `_do_bu_goc_that.py`:** đừng đo trên bản
TRỘN, hãy tách RIÊNG vật liệu bù ra rồi chép. Ở đó không có một mẩu giọng Việt
nào lẫn vào nên whisper không có gì để bịa theo — và nó trả thẳng nhãn
`Chinese` với **131/140 ký tự Hán (93,6%)**. Bài học chung: **muốn biết một
thành phần là tiếng gì thì đo CHÍNH thành phần đó, đừng đo bản đã trộn.**

**KHÔNG ĐỤNG FILE ANH HÙNG.** Chỉ `ffmpeg -i` (mở đọc) rồi ghi WAV sang hộp cát.

    .venv\\Scripts\\python _do_tieng_trung_con.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ["WHISPER_PROVIDER"] = "groq"
os.environ.setdefault("BQ_FFMPEG_SLOTS", "2")
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                       # noqa: BLE001
        pass

XUAT = Path(r"C:\Users\Admin\Downloads\longtieng\xuất")
GOC = Path(r"C:\Users\Admin\Downloads\longtieng")
SB = Path(r"D:\claude\_hop_cat_4loi\m3")
KQ = REPO / "_kq_tieng_trung_con.json"

#: Hán tự: CJK Unified Ideographs + Extension A + dạng tương thích. Chữ Việt và
#: chữ Anh KHÔNG có ký tự nào trong dải này, nên phép thử này SẠCH.
_HAN = re.compile(r"[㐀-䶿一-鿿豈-﫿]")

#: Đoạn Hán ở bản thành phẩm được coi là TIẾNG GỐC THẬT khi có ít nhất chừng
#: này tỉ lệ ký tự Hán trùng với lời người gốc nói đúng lúc đó. Đặt thấp có
#: chủ ý: whisper nghe qua nhạc nền + đã bị `atempo` kéo giãn nên chép sai
#: nhiều; cái ta cần phân biệt là "trùng ĐÁNG KỂ" với "bịa ra từ hư không"
#: (bịa thì trùng gần như 0 — xem cột SÀN BỊA).
NGUONG_TRUNG = 0.30

#: Nới cửa sổ khi quy mốc bản thành phẩm về trục gốc: mốc segment của whisper
#: xê dịch, và `k` chỉ đúng tới 4 chữ số.
LE_MOC = 3.0


def han(s: str) -> str:
    return "".join(_HAN.findall(s or ""))


def rut_wav(video: Path, ra: Path) -> None:
    """ffmpeg CHỈ MỞ ĐỌC video nguồn, ghi WAV 16k mono sang hộp cát."""
    from app.core.thay_giong import _ffmpeg
    if ra.exists() and ra.stat().st_size > 1024:
        return
    _ffmpeg(["-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
             "-c:a", "pcm_s16le", str(ra)],
            f"rút tiếng {video.name}", timeout=900)


def chep(wav: Path, lang: str | None, cache: Path) -> dict:
    """Chép lời qua Groq. CÓ CACHE ra đĩa — lượt đo sau khỏi đốt lại hạn mức."""
    if cache.exists():
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except Exception:                                   # noqa: BLE001
            pass
    from app.core import transcribe as tr
    t0 = time.time()
    if lang:
        # Ép ngôn ngữ -> phải đi CỬA THẤP `_transcribe_groq`; `tr.transcribe`
        # cố tình luôn thả None (chống nhãn "en" cũ phá video tiếng khác).
        d = tr._transcribe_groq(str(wav), lang, None)       # noqa: SLF001
    else:
        d = tr.transcribe(str(wav))
    d["_giay"] = round(time.time() - t0, 1)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return d


def doan_han(d: dict) -> list[dict]:
    ra = []
    for s in (d.get("segments") or []):
        h = han(s.get("text") or "")
        if h:
            ra.append({"a": round(float(s["start"]), 2),
                       "b": round(float(s["end"]), 2),
                       "han": h, "text": (s.get("text") or "")[:100]})
    return ra


def trung_voi_goc(dh: list[dict], goc: dict, k: float) -> list[dict]:
    """Mỗi đoạn Hán ở bản XUẤT: có trùng lời GỐC đúng lúc đó không?

    Quy mốc bản xuất về trục gốc bằng `t / k` (chỉnh hình chỉ GIÃN ĐỀU) rồi gom
    mọi ký tự Hán người gốc nói trong cửa sổ đó, lấy tỉ lệ ký tự Hán của đoạn
    xuất **có mặt** trong cửa sổ gốc.
    """
    gs = [(float(s["start"]), float(s["end"]), han(s.get("text") or ""))
          for s in (goc.get("segments") or [])]
    for x in dh:
        a, b = x["a"] / k - LE_MOC, x["b"] / k + LE_MOC
        cua = "".join(t for (sa, sb, t) in gs if sb >= a and sa <= b)
        kho = set(cua)
        n = len(x["han"])
        x["trung"] = round(sum(1 for c in x["han"] if c in kho) / n, 3) if n else 0.0
        x["goc_cua_so"] = cua[:80]
        x["THAT"] = bool(x["trung"] >= NGUONG_TRUNG)
    return dh


def main() -> int:
    SB.mkdir(parents=True, exist_ok=True)
    from app.core.thay_giong import probe_duration
    ket: dict = {"moc": "4 bản anh Hùng xuất 28/08/2026",
                 "nguong_trung": NGUONG_TRUNG, "video": []}
    vids = sorted(XUAT.glob("*.mp4"))
    print(f"{len(vids)} bản xuất trong {XUAT}")

    for i, v in enumerate(vids, 1):
        lam = SB / f"x{i}"
        lam.mkdir(parents=True, exist_ok=True)
        src = GOC / v.name
        print(f"\n{'='*74}\n[{i}/{len(vids)}] {v.name}")
        try:
            wx = lam / "xuat.wav"
            rut_wav(v, wx)
            dx = probe_duration(v)
            # --- cột 1: ÉP tiếng Trung lên bản THÀNH PHẨM
            zx = chep(wx, "zh", lam / "xuat_zh.json")
            dh = doan_han(zx)
            # --- cột 3: SỰ THẬT — bản gốc, tự nhận diện
            if not src.exists():
                raise FileNotFoundError(f"không thấy bản gốc: {src}")
            wg = lam / "goc.wav"
            rut_wav(src, wg)
            dg = probe_duration(src)
            zg = chep(wg, None, lam / "goc_auto.json")
            k = (dx / dg) if dg > 0 else 1.0
            dh = trung_voi_goc(dh, zg, k)
            that = [x for x in dh if x["THAT"]]
            bia = [x for x in dh if not x["THAT"]]
            gt = sum(x["b"] - x["a"] for x in that)
            r = {
                "video": v.name,
                "giay_xuat": round(dx, 2), "giay_goc": round(dg, 2),
                "k_do_duoc": round(k, 4),
                "nhan_goc": zg.get("language"),
                "so_doan_han": len(dh),
                "so_doan_TIENG_GOC_THAT": len(that),
                "so_doan_whisper_BIA": len(bia),
                "GIAY_TIENG_TRUNG_THAT": round(gt, 2),
                "PHAN_TRAM": round(100.0 * gt / dx, 2) if dx else 0.0,
                "doan": dh,
            }
        except Exception as e:                              # noqa: BLE001
            print(f"  LỖI: {type(e).__name__}: {e}")
            r = {"video": v.name, "loi": f"{type(e).__name__}: {e}"[:300]}
        ket["video"].append(r)
        if "loi" not in r:
            print(f"  xuất {r['giay_xuat']}s / gốc {r['giay_goc']}s "
                  f"-> k = {r['k_do_duoc']} · nhãn gốc {r['nhan_goc']}")
            print(f"  đoạn có chữ Hán: {r['so_doan_han']}"
                  f"  (TIẾNG GỐC THẬT {r['so_doan_TIENG_GOC_THAT']}"
                  f" · whisper BỊA {r['so_doan_whisper_BIA']})")
            print(f"  >>> GIÂY TIẾNG TRUNG THẬT: "
                  f"{r['GIAY_TIENG_TRUNG_THAT']}s ({r['PHAN_TRAM']}%)")
            for x in [y for y in r["doan"] if y["THAT"]][:10]:
                print(f"      [{x['a']:>7.2f}-{x['b']:>7.2f}] trùng "
                      f"{x['trung']:.2f} | {x['han'][:40]}")
        KQ.write_text(json.dumps(ket, ensure_ascii=False, indent=1),
                      encoding="utf-8")

    ok = [r for r in ket["video"] if "loi" not in r]
    tg = sum(r["GIAY_TIENG_TRUNG_THAT"] for r in ok)
    td = sum(r["giay_xuat"] for r in ok)
    ket["tong"] = {"so_video": len(ok), "giay_video": round(td, 2),
                   "GIAY_TIENG_TRUNG": round(tg, 2),
                   "phan_tram": round(100.0 * tg / td, 2) if td else 0.0}
    KQ.write_text(json.dumps(ket, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"\n{'='*74}\nTỔNG {len(ok)} video · {td:.1f}s")
    print(f"  >>> TIẾNG TRUNG CÒN LẠI: {tg:.2f}s "
          f"({100.0*tg/td if td else 0:.2f}%)")
    print(f"=> {KQ}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
