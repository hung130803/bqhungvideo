# -*- coding: utf-8 -*-
"""ĐỌC THẬT ĐƯỢC KHÔNG — kiểm TỪNG giọng edge-tts còn bị khoá.

**VIỆC NÀY TÁCH LÀM ĐÔI CÁI ĐANG BỊ GỘP.** Tới hôm nay, luật mở giọng là
*"có trong `nhan_nha.BANG` thì mở"*, tức tấm vé vào combo được cấp bởi **phép
đo NHẤN NHÁ**. Nhấn nhá lại cần bộ 4 câu đúng tiếng, mà bộ câu chỉ có cho 15
thứ tiếng -> **137 giọng của 60 thứ tiếng bị khoá vì một lý do chẳng liên quan
gì tới chúng**. File này trả lời riêng câu hỏi RẺ và BẮT BUỘC:

    giọng này đọc ra tiếng THẬT hay không?

Điều kiện ĐẠT (cả ba, đo trên file máy đọc trả về):

1. `_synth_all` trả `ok=True` **và** file tồn tại (chốt "không phải 0 byte");
2. **ĐỘ DÀI** >= `DAI_TOI_THIEU` giây — câu thử dài 5-9 từ, ra 0,2 giây là máy
   đọc trả về một mảnh cụt chứ không phải câu;
3. **RMS** >= `RMS_TOI_THIEU` dBFS — file đủ dài mà toàn im lặng thì vẫn hỏng.
   Đây là chốt bắt ca `ffmpeg mã 0 nhưng file rỗng` phiên bản TTS.

**ĐI ĐÚNG CỬA `dubbing._synth_all`** — cửa mà lượt xuất thật đi. Gọi thẳng
`edge_tts.Communicate` thì phép kiểm chứng nhận cho một con đường KHÁC con
đường anh Hùng sẽ chạy.

**KIỂM CÂU THỬ CÓ ĐÚNG TIẾNG KHÔNG (`--kiem-tieng`).** Bản thân tôi không đọc
được 60 thứ tiếng, nên câu trong `_cau_doc_thu.py` là câu tôi tự viết. Để nó
không thành lời tự khen, phép kiểm này cho **Groq whisper chép ngược chính file
tiếng vừa đọc** rồi so NHÃN NGÔN NGỮ máy nghe đoán được với mã ngôn ngữ của
giọng. Đây là bước TUỲ CHỌN và tách hẳn: nó tốn lượt Groq, và **nó chấm CÂU chứ
không chấm GIỌNG** — giọng đã đạt/không đạt ở ba chốt trên rồi.

Chạy:
    .venv\\Scripts\\python -u _do_doc_that.py                 (137 giọng còn khoá)
    .venv\\Scripts\\python -u _do_doc_that.py --tat-ca        (cả 322)
    .venv\\Scripts\\python -u _do_doc_that.py --kiem-tieng    (thêm bước Groq)
    .venv\\Scripts\\python -u _do_doc_that.py --in-bang       (in bảng dán vào mã)
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")

# Hộp cát: KHÔNG đụng `%LOCALAPPDATA%\BQHungVideo` của anh Hùng, và KHÔNG để
# rác ở `%TEMP%` (luật đã chốt ở cổng 17).
SAN = REPO / "_kq_doc_that"
SAN.mkdir(exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(SAN / "data"))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

FF = str(REPO / "bin" / "ffmpeg.exe")
FP = str(REPO / "bin" / "ffprobe.exe")
NOWIN = 0x08000000
KHO = REPO / "_kq_edge_voices.json"
KQ = SAN / "ket_qua.json"

#: Câu thử 5-9 từ, giọng nào cũng phải ra >= ngần này giây. Đặt THẤP có chủ ý
#: (câu ngắn nhất trong bảng — `uz`, `gl` — đo được ~1,7 giây): mục tiêu là bắt
#: ca "ra mảnh cụt / file rỗng", không phải chấm tốc độ đọc.
DAI_TOI_THIEU = 0.80
#: Trên ngưỡng này là CÓ TIẾNG. edge-tts trả mp3 chuẩn hoá quanh -18..-24 dBFS;
#: file im lặng đo ra -91 dBFS (sàn của phép đo 16-bit). Khoảng trống giữa hai
#: nhóm rất rộng nên ngưỡng đặt ở đâu trong đó cũng được — lấy -60 cho chắc.
RMS_TOI_THIEU = -60.0
#: Hạn chờ MỘT giọng. `_synth_all` tự thử lại 4 lần (mỗi lần cách 1,5-6 giây)
#: nên ca hỏng thật tốn ~25 giây; 90 giây là dư cho cả ca mạng chậm.
HAN_GIAY = 90.0


# ---------------------------------------------------------------------------
# ĐO FILE
# ---------------------------------------------------------------------------
def _chay(cmd: list[str], giay: float = 120.0) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                          creationflags=NOWIN, timeout=giay)


def do_dai(p: Path) -> float:
    """Độ dài giây (0.0 = không đọc được)."""
    r = _chay([FP, "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nw=1:nk=1", str(p)])
    try:
        return float((r.stdout or "").strip())
    except (TypeError, ValueError):
        return 0.0


#: `astats` in ra ``[Parsed_astats_0 @ 0x...] RMS level dB: -20.1`` — dòng có
#: TIỀN TỐ, nên `startswith` KHÔNG BAO GIỜ khớp và mọi file ra -99 dBFS, ca
#: "không có tiếng" tự ĐẠT vĩnh viễn. Đúng bẫy đã ghi ở cổng 44. Dùng `in`.
_RE_RMS = re.compile(r"RMS level dB:\s*(-?[\d.]+|-?inf)")


def do_rms(p: Path) -> float:
    """RMS toàn file (dBFS). File im lặng -> số rất âm, KHÔNG phải None."""
    r = _chay([FF, "-v", "info", "-i", str(p), "-af",
               "astats=measure_overall=RMS_level:measure_perchannel=none",
               "-f", "null", "-"])
    m = _RE_RMS.search((r.stderr or "") + (r.stdout or ""))
    if not m:
        raise RuntimeError("astats không in ra RMS level — phép đo hỏng, "
                           "KHÔNG được trả None âm thầm")
    v = m.group(1)
    return -99.0 if "inf" in v else float(v)


# ---------------------------------------------------------------------------
# ĐỌC MỘT GIỌNG
# ---------------------------------------------------------------------------
def doc_mot(voice: str, locale: str) -> dict:
    """Cho `voice` đọc 1 câu ĐÚNG TIẾNG qua `dubbing._synth_all`, rồi đo."""
    from _cau_doc_thu import cau_cho_locale
    from app.core import dubbing

    cau = cau_cho_locale(locale)
    if not cau:
        return {"ok": False, "vi_sao": "chưa có câu thử cho tiếng này"}
    tm = SAN / "wav" / voice
    tm.mkdir(parents=True, exist_ok=True)
    mp3 = tm / "c0.mp3"
    if mp3.exists():
        mp3.unlink()
    t0 = time.monotonic()
    try:
        ok = asyncio.run(asyncio.wait_for(
            dubbing._synth_all([cau], voice, [str(mp3)]), timeout=HAN_GIAY))
    except asyncio.TimeoutError:
        return {"ok": False, "vi_sao": f"quá {HAN_GIAY:.0f} giây không xong"}
    except Exception as e:                                     # noqa: BLE001
        return {"ok": False, "vi_sao": f"{type(e).__name__}: {e}"}
    giay = round(time.monotonic() - t0, 1)
    if not ok or not ok[0]:
        return {"ok": False, "giay": giay,
                "vi_sao": "_synth_all trả ok=False (thử lại 4 lần vẫn hỏng)"}
    if not mp3.exists():
        return {"ok": False, "giay": giay, "vi_sao": "không có file"}
    cỡ = mp3.stat().st_size
    if cỡ <= 0:
        return {"ok": False, "giay": giay, "vi_sao": "file 0 byte"}
    dai = do_dai(mp3)
    try:
        rms = do_rms(mp3)
    except RuntimeError as e:
        return {"ok": False, "giay": giay, "vi_sao": str(e)}
    d = {"giay": giay, "byte": cỡ, "dai": round(dai, 2), "rms": round(rms, 1),
         "cau": cau}
    if dai < DAI_TOI_THIEU:
        d.update(ok=False, vi_sao=f"quá ngắn {dai:.2f}s < {DAI_TOI_THIEU}s")
    elif rms < RMS_TOI_THIEU:
        d.update(ok=False, vi_sao=f"IM LẶNG {rms:.1f} dBFS < {RMS_TOI_THIEU}")
    else:
        d["ok"] = True
    return d


# ---------------------------------------------------------------------------
# DANH SÁCH
# ---------------------------------------------------------------------------
def danh_sach(tat_ca: bool = False) -> list[tuple[str, str]]:
    """[(ShortName, Locale)] — mặc định CHỈ giọng chưa có trong `nhan_nha`."""
    from app.core import nhan_nha
    v = json.loads(KHO.read_text(encoding="utf-8"))
    da = set(nhan_nha.BANG)
    ra = [(x["ShortName"], x["Locale"]) for x in v
          if tat_ca or x["ShortName"] not in da]
    return sorted(set(ra))


def _nap_key_groq() -> int:
    """Chuyền key Groq của `.env` THẬT vào tiến trình qua BIẾN MÔI TRƯỜNG.

    KHÔNG ghi ra file, KHÔNG in ra màn hình (41 key). Cùng cách `_test_pipe_e2e`
    đã chốt — hộp cát trỏ `BQ_DATA_DIR` sang thư mục tạm nên nó không tự thấy
    `.env`, và thiếu key thì `transcribe` lùi về whisper MÁY (tải 3 GB).
    """
    if os.environ.get("GROQ_API_KEYS"):
        return len(os.environ["GROQ_API_KEYS"].split(","))
    for env in (Path(os.environ.get("LOCALAPPDATA", "")) / "BQHungVideo" / ".env",
                REPO / ".env"):
        if not env.exists():
            continue
        for dong in env.read_text(encoding="utf-8", errors="replace").splitlines():
            if dong.strip().startswith("GROQ_API_KEYS"):
                gt = dong.split("=", 1)[1].strip().strip('"').strip("'")
                if gt:
                    os.environ["GROQ_API_KEYS"] = gt
                    return len(gt.split(","))
    return 0


def kiem_tieng(ra: dict) -> dict:
    """Cho Groq chép ngược file tiếng rồi so NHÃN NGÔN NGỮ với giọng.

    **Chấm CÂU, không chấm GIỌNG.** Nhãn lệch nghĩa là câu tôi viết có thể sai
    tiếng (hoặc máy nghe đoán nhầm) — giọng vẫn đọc ra tiếng thật.
    """
    from app.core import transcribe as TS
    so = _nap_key_groq()
    print(f"\n--- KIỂM CÂU CÓ ĐÚNG TIẾNG KHÔNG (Groq, {so} key) ---")
    if not so:
        print("KHÔNG có key Groq -> BỎ QUA (không lùi whisper máy: 3 GB)")
        return {}
    # Mỗi LOCALE chỉ kiểm MỘT giọng: câu là của locale, không phải của giọng.
    dai_dien: dict[str, str] = {}
    for v, d in ra.items():
        if d.get("ok") and d.get("loc") and d["loc"] not in dai_dien:
            dai_dien[d["loc"]] = v
    nh: dict[str, dict] = {}
    for i, (loc, v) in enumerate(sorted(dai_dien.items()), 1):
        p = SAN / "wav" / v / "c0.mp3"
        try:
            kq = TS.transcribe(str(p))
            nn = str(kq.get("language") or "")[:24]
        except Exception as e:                                 # noqa: BLE001
            nn = f"LỖI {type(e).__name__}"
        mong = loc.split("-")[0].lower()
        khop = nn.lower().startswith(mong) or nn.lower() == mong
        nh[loc] = {"may_nghe": nn, "mong": mong, "khop": bool(khop)}
        print(f"{i:3d}/{len(dai_dien)} {loc:12s} mong {mong:4s} · "
              f"máy nghe {nn:24s} {'KHỚP' if khop else 'LỆCH'}", flush=True)
    kh = sum(1 for d in nh.values() if d["khop"])
    print(f"--- KHỚP {kh}/{len(nh)} locale ---")
    return nh


# ---------------------------------------------------------------------------
def main() -> int:
    from _cau_doc_thu import IT_CHAC
    tat_ca = "--tat-ca" in sys.argv
    ds = danh_sach(tat_ca)
    ra: dict = {}
    if KQ.exists():
        try:
            ra = json.loads(KQ.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            ra = {}
    print("=" * 78)
    print(f"ĐỌC THẬT ĐƯỢC KHÔNG — {len(ds)} giọng, cửa dubbing._synth_all")
    print(f"ĐẠT = ok + dài >= {DAI_TOI_THIEU}s + RMS >= {RMS_TOI_THIEU} dBFS")
    print("=" * 78)
    t0 = time.monotonic()
    for i, (v, loc) in enumerate(ds, 1):
        if v in ra and ra[v].get("ok"):
            d = ra[v]
        else:
            d = doc_mot(v, loc)
            d["loc"] = loc
            ra[v] = d
            KQ.write_text(json.dumps(ra, ensure_ascii=False, indent=1),
                          encoding="utf-8")
        d.setdefault("loc", loc)
        if d.get("ok"):
            print(f"{i:3d}/{len(ds)} {v:34s} ĐẠT  {d['dai']:5.2f}s "
                  f"{d['rms']:6.1f}dB {d['byte']:7d}B", flush=True)
        else:
            print(f"{i:3d}/{len(ds)} {v:34s} HỎNG {d.get('vi_sao')}",
                  flush=True)
    dat = sorted(v for v, d in ra.items() if v in dict(ds) and d.get("ok"))
    hong = sorted((v, ra[v].get("vi_sao", "?")) for v, d in ra.items()
                  if v in dict(ds) and not d.get("ok"))
    print("-" * 78)
    print(f"ĐẠT {len(dat)}/{len(ds)} · HỎNG {len(hong)} · "
          f"{time.monotonic() - t0:.0f} giây")
    if hong:
        print("\nKHÔNG ĐỌC ĐƯỢC (tên + lý do):")
        for v, ly in hong:
            print(f"  {v:34s} {ly}")
    it = sorted({ra[v]["loc"].split("-")[0] for v in dat
                 if ra[v].get("loc", "").split("-")[0] in IT_CHAC})
    if it:
        print(f"\nTiếng tôi ÍT CHẮC về câu thử (đã khai trước khi đo): "
              f"{', '.join(it)}")
    if "--kiem-tieng" in sys.argv:
        nh = kiem_tieng(ra)
        (SAN / "kiem_tieng.json").write_text(
            json.dumps(nh, ensure_ascii=False, indent=1), encoding="utf-8")
    if "--in-bang" in sys.argv:
        print("\n--- dán vào giong_mo.DOC_DUOC ---")
        for v in dat:
            print(f'    "{v}",')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
