# -*- coding: utf-8 -*-
"""ĐO ĐỘ KHỚP MỐC TỪNG CHỮ CỦA GIỌNG NGOÀI (OmniVoice) — 4 THỨ TIẾNG.

═══════════════════════════════════════════════════════════════════════════
PHÁT HIỆN CHẶN ĐƯỜNG, PHẢI ĐỌC TRƯỚC KHI ĐỌC SỐ
═══════════════════════════════════════════════════════════════════════════
Piper suy mốc từ ĐỘ DÀI WAV (không liên quan Groq) nên đo bằng Groq chép
ngược là **thước độc lập** — con số 59,1 ms có nghĩa.

**OmniVoice thì KHÔNG.** Nó không trả mốc, nên `giong_ngoai._lay_moc_groq`
lấy mốc **THẲNG TỪ GROQ**. Đo lại bằng Groq = **so nó với chính nó**.
Và đã kiểm: Groq **TIỀN ĐỊNH** — chép cùng một file hai lần ra mốc GIỐNG
TỪNG CHỮ SỐ. Tức phép đo đó sẽ ra **đúng 0,0 ms** và tự phát chứng nhận
"khớp hoàn hảo, tốt hơn edge-tts 43,6 ms". Đây đúng họ bẫy mà repo này đã
sập nhiều lần (`astats` cổng 53 · `startswith` cổng 44 · mốc `main` cổng
36/51/52): **phép đo hỏng nguy hiểm hơn không đo, vì nó phát chứng nhận.**

VÌ VẬY PHẢI CÓ THƯỚC ĐỘC LẬP — đúng cách cổng 67 đã chặn phép trừ 94 ms:

  T1 `groq`  Groq whisper-large-v3 chép ngược, so TỪNG TỪ.
             · EDGE: **thước thật** (mốc edge lấy từ WordBoundary của chính
               máy đọc, không dính Groq) -> số này so thẳng được với mốc
               43,6 ms đã ghi.
             · OV: **VÒNG TRÒN**, in ra để chứng minh nó ra ~0 chứ KHÔNG
               phải để khoe.
  T2 `fw`    faster-whisper **medium** chạy TRÊN MÁY (CTranslate2). Trọng số
             KHÁC (medium vs large-v3) và cách chạy KHÁC (local vs dịch vụ)
             -> **độc lập với CẢ HAI arm**. Đây là thước chấm điểm chính.
  T3 `im`    `silencedetect` (`thay_giong.do_le_im`) — KHÔNG dùng máy nghe
             nào: so mốc chữ ĐẦU với lúc THẬT SỰ phát ra tiếng. Đúng thước
             thứ ba mà cổng 67 dùng để chặn phép trừ sai.

═══════════════════════════════════════════════════════════════════════════
BẮT BUỘC TÁCH *LỆCH HỆ THỐNG* KHỎI *RUNG* — SỐ THÔ LÀ SỐ LỪA
═══════════════════════════════════════════════════════════════════════════
Đã sập 3 lần: hai lỗi NGƯỢC DẤU triệt tiêu nhau nên cột "TB" trông ngang
nhau trong khi một bên rung gấp rưỡi. Lệch HỆ THỐNG trừ được bằng một hằng
số; RUNG thì không — đó mới là chất lượng thật của bộ mốc.
Và **arm đối chứng edge-tts phải chạy lại trên CÙNG corpus, ĐAN XEN**: cổng
67 đã chứng minh **độ trễ của thước ĐỔI THEO GIỌNG** (và theo ngôn ngữ), nên
mốc 43,6 ms đo trên corpus khác không dùng để so trực tiếp được.

  .venv\\Scripts\\python -u _do_gn_moc.py
  BQ_SO_CAU=12 BQ_LUOT=2 BQ_NN=vi,en,zh,ja .venv\\Scripts\\python -u _do_gn_moc.py
"""
from __future__ import annotations

import asyncio
import json
import os
import statistics
import sys
import time
from difflib import SequenceMatcher
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # noqa: BLE001
        pass

SO_CAU = int(os.environ.get("BQ_SO_CAU", "12"))
SO_LUOT = int(os.environ.get("BQ_LUOT", "2"))
NN = [x for x in os.environ.get("BQ_NN", "vi,en,zh,ja").split(",") if x]
RA = REPO / os.environ.get("BQ_RA", "_do_gn_moc.json")
GIONG_OV = os.environ.get("BQ_GIONG_OV", "ov:nu_tre")
#: faster-whisper: `medium` là trọng số KHÁC large-v3 của Groq -> độc lập.
FW_MODEL = os.environ.get("BQ_FW", "medium")

NHAN_NN = {"vi": "Việt", "en": "Anh", "zh": "Trung", "ja": "Nhật"}
GIONG_EDGE = {"vi": "vi-VN-HoaiMyNeural", "en": "en-US-AriaNeural",
              "zh": "zh-CN-XiaoxiaoNeural", "ja": "ja-JP-NanamiNeural"}


# ---------------------------------------------------------------------------
# CORPUS — CHỮ THẬT trên máy anh Hùng, KHÔNG bịa câu mẫu
# ---------------------------------------------------------------------------
def _tu_hook_cache(lang_ten: str) -> list[str]:
    d = json.loads((REPO / "_do_hook_cache.json").read_text(encoding="utf-8"))
    cau: set[str] = set()
    for v in d:
        if not isinstance(v, dict) or v.get("lang") != lang_ten:
            continue
        for s in (v.get("segments") or []):
            t = str((s or {}).get("text") or "").strip()
            if t:
                cau.add(t)
    return sorted(cau, key=lambda t: -len(t))


def nap_cau(nn: str) -> list[str]:
    """Câu THẬT của từng thứ tiếng. Câu mẫu ngắn/sạch làm số đẹp giả tạo."""
    if nn == "vi":
        d = json.loads((REPO / "_do_dich_soat.json").read_text(
            encoding="utf-8"))
        for luot in d:
            for ten in ("MỐC", "SOÁT"):
                bd = (luot.get(ten) or {}).get("ban_dich") or []
                if bd:
                    c = sorted({t.strip() for t in bd if t and t.strip()},
                               key=lambda t: -len(t.split()))
                    return [t for t in c if len(t.split()) >= 6][:SO_CAU]
    elif nn == "en":
        c = [t for t in _tu_hook_cache("English") if len(t.split()) >= 6]
        return c[:SO_CAU]
    elif nn == "ja":
        c = [t for t in _tu_hook_cache("Japanese") if len(t) >= 12]
        return c[:SO_CAU]
    elif nn == "zh":
        d = json.loads((REPO / "_do_dich_cache.json").read_text(
            encoding="utf-8"))
        c = sorted({str((x or {}).get("text") or "").strip()
                    for x in (d.get("cau") or [])}, key=lambda t: -len(t))
        return [t for t in c if len(t) >= 8][:SO_CAU]
    raise SystemExit(f"không có corpus cho {nn!r}")


# ---------------------------------------------------------------------------
# HAI ARM
# ---------------------------------------------------------------------------
def doc_edge(texts: list[str], nn: str, san: Path) -> tuple[list, list]:
    """Arm đối chứng — đi CHÍNH cửa `dubbing._synth_all_words` của app."""
    from app.core import dubbing
    san.mkdir(parents=True, exist_ok=True)
    paths = [str(san / f"c{i:03d}.wav") for i in range(len(texts))]
    ok, words = asyncio.run(dubbing._synth_all_words(
        texts, GIONG_EDGE[nn], paths, lang=nn, el_lui=False))
    return list(ok), [(p, w) for p, w in zip(paths, words)]


def doc_ov(texts: list[str], nn: str, san: Path) -> tuple[list, list]:
    """Arm OmniVoice — gọi `giong_ngoai.doc_loat`.

    GIAI ĐOẠN 2 sẽ nối hàm này vào `dubbing._synth_all_words` (cửa chung);
    lúc đó arm này đổi sang gọi cửa chung y như arm EDGE. Hôm nay chưa nối
    được (luồng khác đang giữ `dubbing.py`) nên gọi thẳng — hai đường cho ra
    CÙNG kết quả vì cửa chung chỉ ủy quyền xuống đây, không xử lý gì thêm.
    """
    from app.core import giong_ngoai as gn
    san.mkdir(parents=True, exist_ok=True)
    paths = [str(san / f"c{i:03d}.wav") for i in range(len(texts))]
    ok, words = gn.doc_loat(texts, paths, GIONG_OV, lang=nn)
    return list(ok), [(p, w) for p, w in zip(paths, words)]


ARM = {"EDGE": doc_edge, "OV": doc_ov}

# ---------------------------------------------------------------------------
# THƯỚC
# ---------------------------------------------------------------------------
_DAU = ".,!?;:\"'“”…()-–—[]{}「」『』、。，！？；：《》"


def _chuan(w: str) -> str:
    return str(w or "").strip().strip(_DAU).lower()


_FW = {}


def _fw_words(wav: str, nn: str) -> list:
    """faster-whisper LOCAL (`medium`) -> [(từ, đầu, cuối)]. THƯỚC ĐỘC LẬP."""
    from faster_whisper import WhisperModel
    if FW_MODEL not in _FW:
        _FW[FW_MODEL] = WhisperModel(FW_MODEL, device="cpu",
                                     compute_type="int8")
    segs, _ = _FW[FW_MODEL].transcribe(wav, language=nn,
                                       word_timestamps=True, vad_filter=False)
    ra = []
    for s in segs:
        for w in (s.words or []):
            t = _chuan(w.word)
            if t:
                ra.append((t, float(w.start), float(w.end)))
    return ra


def _groq_words(wav: str) -> list:
    from app.core import thay_giong as tg
    d = tg.chep_loi(wav)
    ra = []
    for w in (d.get("words") or []):
        t = _chuan(w.get("word") or "")
        if t:
            ra.append((t, float(w.get("start") or 0.0),
                       float(w.get("end") or 0.0)))
    return ra


def so_tung_tu(moc: list, that: list) -> list[float]:
    """Lệch (ms) của từng từ khớp được. DƯƠNG = mốc MUỘN hơn tiếng."""
    suy = [(_chuan(m[2]), float(m[0])) for m in moc]
    suy = [x for x in suy if x[0]]
    tt = [(x[0], x[1]) for x in that]
    if not suy or not tt:
        return []
    sm = SequenceMatcher(None, [x[0] for x in suy], [x[0] for x in tt],
                         autojunk=False)
    lech = []
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            lech.append((suy[a + k][1] - tt[b + k][1]) * 1000.0)
    return lech


def thong_ke(lech: list[float]) -> dict:
    """TÁCH LỆCH HỆ THỐNG KHỎI RUNG — hai thứ chữa bằng hai cách khác hẳn."""
    if not lech:
        return {"n": 0}
    ab = sorted(abs(x) for x in lech)
    goc = statistics.median(lech)
    rung = sorted(abs(x - goc) for x in lech)
    return {
        "n": len(lech),
        "tb": round(sum(ab) / len(ab), 1),
        "trung_vi": round(statistics.median(ab), 1),
        "p90": round(ab[min(len(ab) - 1, int(len(ab) * 0.9))], 1),
        "max": round(ab[-1], 1),
        "lech_he_thong": round(goc, 1),
        "rung_tb": round(sum(rung) / len(rung), 1),
        "rung_trung_vi": round(statistics.median(rung), 1),
        "rung_p90": round(rung[min(len(rung) - 1, int(len(rung) * 0.9))], 1),
        "muon_hon_50": sum(1 for x in lech if x > 50),
        "ty_muon": round(100.0 * sum(1 for x in lech if x > 50) / len(lech), 1),
        "trong_50ms_sau_tru": sum(1 for x in lech if abs(x - goc) <= 50),
    }


def do_mot_arm(ten: str, nn: str, texts: list[str], san: Path) -> dict:
    """Đọc + chấm bằng cả 3 thước. Trả số thô để gộp sau."""
    t0 = time.time()
    ok, cap = ARM[ten](texts, nn, san)
    giay = time.time() - t0
    lech_groq: list[float] = []
    lech_fw: list[float] = []
    lech_im: list[float] = []
    thua: list[float] = []
    bo = 0
    for i, (p, moc) in enumerate(cap):
        if not ok[i] or not moc or not Path(p).exists():
            bo += 1
            continue
        try:
            g = _groq_words(p)
        except Exception as e:                               # noqa: BLE001
            print(f"      ! groq hỏng câu {i}: {type(e).__name__}: {e}")
            g = []
        if g:
            lech_groq += so_tung_tu(moc, g)
            # BỊA CHỮ: số token máy nghe chép ra so với số token GỬI ĐI.
            from app.ai import recap
            n_goc = len([t for t in recap._word_tokens(texts[i]) if _chuan(t)])
            if n_goc:
                thua.append(100.0 * (len(g) - n_goc) / n_goc)
        try:
            f = _fw_words(p, nn)
        except Exception as e:                               # noqa: BLE001
            print(f"      ! fw hỏng câu {i}: {type(e).__name__}: {e}")
            f = []
        if f:
            lech_fw += so_tung_tu(moc, f)
        # T3 — mốc chữ ĐẦU so với lúc THẬT SỰ phát tiếng (không máy nghe nào)
        try:
            from app.core import thay_giong as tg
            dau, _cuoi, _t = tg.do_le_im(p)
            lech_im.append((float(moc[0][0]) - float(dau)) * 1000.0)
        except Exception:                                    # noqa: BLE001
            pass
    return {"giay": round(giay, 2), "bo": bo,
            "groq": lech_groq, "fw": lech_fw, "im": lech_im, "thua": thua}


def in_bang(tieu_de: str, kho: dict, khoa: str) -> None:
    print(f"\n  {tieu_de}")
    print(f"    {'arm':<5} {'n':>5} {'TB':>7} {'hệ thống':>9} {'RUNG':>7} "
          f"{'rung p90':>9} {'muộn>50ms':>10}")
    for arm in ("EDGE", "OV"):
        tk = thong_ke(kho.get(arm, {}).get(khoa) or [])
        if not tk.get("n"):
            print(f"    {arm:<5}     -  (không đo được)")
            continue
        print(f"    {arm:<5} {tk['n']:>5} {tk['tb']:>7.1f} "
              f"{tk['lech_he_thong']:>9.1f} {tk['rung_tb']:>7.1f} "
              f"{tk['rung_p90']:>9.1f} {tk['ty_muon']:>9.1f}%")


def main() -> int:
    from config import settings
    if not settings.groq_keys():
        print("KHÔNG có key Groq -> không đo được. Dừng.")
        return 2
    from app.core import giong_ngoai as gn
    if not gn.co_omnivoice():
        print(f"KHÔNG dùng được OmniVoice: {gn.tinh_trang_omnivoice()['thieu']}")
        return 2

    san_goc = REPO / "_do_gn_san"
    kho: dict = {}                      # kho[nn][arm][thước] = [lệch...]
    tho: dict = {}
    for luot in range(SO_LUOT):
        for nn in NN:
            texts = nap_cau(nn)
            kho.setdefault(nn, {})
            # ĐAN XEN + XOAY THỨ TỰ: chạy liền mạch một arm rồi arm kia là
            # đo cả phần "máy đã nóng"/"model đã nạp" — đã sai 3 lần trên
            # máy này (nhớ mục "Đo A/B phải đan xen").
            thu_tu = ["EDGE", "OV"] if luot % 2 == 0 else ["OV", "EDGE"]
            for arm in thu_tu:
                san = san_goc / f"l{luot}_{nn}_{arm}"
                print(f"  lượt {luot + 1} · {NHAN_NN.get(nn, nn)} · {arm} "
                      f"({len(texts)} câu)...")
                r = do_mot_arm(arm, nn, texts, san)
                d = kho[nn].setdefault(arm, {"groq": [], "fw": [], "im": [],
                                             "thua": []})
                for k in ("groq", "fw", "im", "thua"):
                    d[k] += r[k]
                tho.setdefault(f"{nn}/{arm}", []).append(
                    {"luot": luot, "giay": r["giay"], "bo": r["bo"],
                     "n_groq": len(r["groq"]), "n_fw": len(r["fw"])})

    print("\n" + "=" * 74)
    print("KẾT QUẢ — lệch tính bằng ms · DƯƠNG = mốc MUỘN hơn tiếng")
    print("=" * 74)
    gop: dict = {"EDGE": {"groq": [], "fw": [], "im": [], "thua": []},
                 "OV": {"groq": [], "fw": [], "im": [], "thua": []}}
    for nn in NN:
        print(f"\n### {NHAN_NN.get(nn, nn).upper()}")
        in_bang("T2 fw (faster-whisper medium, ĐỘC LẬP — thước chấm điểm)",
                kho[nn], "fw")
        in_bang("T1 groq (EDGE = thước thật · OV = VÒNG TRÒN, xem đầu file)",
                kho[nn], "groq")
        in_bang("T3 im (silencedetect, chữ ĐẦU vs lúc phát tiếng)",
                kho[nn], "im")
        for arm in ("EDGE", "OV"):
            th = kho[nn].get(arm, {}).get("thua") or []
            if th:
                print(f"    BỊA CHỮ {arm:<5}: thừa TB {sum(th)/len(th):+.1f}% "
                      f"· nhiều nhất {max(th):+.1f}%")
            for k in gop[arm]:
                gop[arm][k] += kho[nn].get(arm, {}).get(k) or []

    print("\n" + "=" * 74)
    print("GỘP 4 THỨ TIẾNG")
    print("=" * 74)
    in_bang("T2 fw (ĐỘC LẬP)", gop, "fw")
    in_bang("T1 groq", gop, "groq")
    in_bang("T3 im", gop, "im")
    for arm in ("EDGE", "OV"):
        th = gop[arm]["thua"]
        if th:
            print(f"  BỊA CHỮ {arm:<5}: thừa TB {sum(th)/len(th):+.1f}%")

    RA.write_text(json.dumps(
        {"so_cau": SO_CAU, "so_luot": SO_LUOT, "nn": NN, "giong_ov": GIONG_OV,
         "fw_model": FW_MODEL, "tho": tho,
         "tk": {nn: {arm: {k: thong_ke(v) if k != "thua" else v
                           for k, v in d.items()}
                     for arm, d in kho[nn].items()} for nn in NN},
         "gop": {arm: {k: thong_ke(v) for k, v in d.items() if k != "thua"}
                 for arm, d in gop.items()}},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nGhi {RA.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
