# -*- coding: utf-8 -*-
"""ĐO LỆCH CHỮ (phụ đề cháy sẵn trong hình) SO VỚI TIẾNG (giọng đã thay).

VÌ SAO PHẢI CÓ FILE NÀY — lỗ hổng của mọi thước đo cũ
=====================================================
`khop_thoi_gian` báo `lech_dau_ms = 0` vì nó GHI THẲNG `lech_dau.append(0.0)`
kèm chú thích "đặt ĐÚNG mốc gốc" — tức nó đo CHỖ ĐẶT FILE, không đo CHỖ PHÁT
RA TIẾNG. `_do_tempo_cau.py`/`_do_le_im.py` cũng chỉ so TIẾNG với TIẾNG.

Anh Hùng xem bản thành phẩm và tả: *"chữ dịch ở dưới vẫn chạy mà trên đáng lý
ra phải nói mà k có nói, 1 lúc sau nó lại tự nói"*. Cái "chữ" đó là PHỤ ĐỀ
CHÁY SẴN trong khung hình Douyin — nó nằm trong ĐIỂM ẢNH, đường thay tiếng
`-c:v copy` nên nó giữ NGUYÊN mốc gốc, trong khi giọng thì bị đặt lại.
Chưa thước nào so hai thứ đó. File này so.

BA TRỤC THỜI GIAN đo trên CÙNG một video (không tin metadata, không tin mã
thoát ffmpeg):
  1. CHỮ    — mốc đổi dòng phụ đề, dò bằng ĐIỂM ẢNH trong dải chữ
              (`che_chu.do_dai_chu` cho toạ độ dải, mặt nạ nét chữ `_mat_na`).
  2. TIẾNG GỐC — mốc người trong video bắt đầu nói (Demucs tách giọng khỏi
              nhạc -> `silencedetect`). Đây là ĐỐI CHỨNG: video gốc vốn khớp.
  3. TIẾNG MỚI — mốc giọng đã thay bắt đầu nói (Demucs trên bản thành phẩm ->
              `silencedetect`).

Lệch cần báo = (2) so (1) [đối chứng] và (3) so (1) [cái anh Hùng nghe].

CHẠY:
    python _do_chu_tieng.py --goc "<video nguồn>" --ra "<video thành phẩm>" \
        --lam D:\\work --ten v1
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core import che_chu as CC          # noqa: E402
from app.core import thay_giong as TG       # noqa: E402

_NW = 0x0800_0000 if os.name == "nt" else 0

#: Lấy mẫu khung hình cho trục CHỮ. 20 khung/giây = phân giải 50 ms — dưới
#: ngưỡng nghe được (150 ms) một bậc, đủ để kết luận không bị chính phép đo
#: làm nhiễu.
FPS_LAY = 20.0

#: Bề rộng thu nhỏ khi đọc dải chữ (khớp `che_chu.RONG_DO` — ngưỡng NGUONG_NET
#: đã hiệu chuẩn ở bề rộng này, đổi là sai ngưỡng).
RONG_DO = getattr(CC, "RONG_DO", 640)

#: Hai khung liên tiếp giống nhau dưới mức này (IoU mặt nạ nét) = ĐỔI DÒNG.
IOU_DOI_DONG = 0.35

#: Mật độ nét tối thiểu để coi khung "đang có chữ" — lấy THEO VIDEO (0,35 lần
#: bách phân vị 90) chứ không cứng: mỗi kênh một cỡ chữ.
TY_LE_NGUONG = 0.35


def _ff(ten: str = "ffmpeg") -> str:
    return CC._bin(ten)


# ─────────────────────────── TRỤC 1 — CHỮ (điểm ảnh) ────────────────────────
def doc_dai_theo_thoi_gian(src: str | Path, dai, fps: float = FPS_LAY,
                           ) -> tuple[np.ndarray, np.ndarray]:
    """Đọc DẢI CHỮ của cả video ở `fps` -> (mốc giây, mặt nạ nét [T,H,W]).

    MỘT lượt ffmpeg giải mã, crop sẵn dải nên dữ liệu về nhỏ (dải cao ~7% khung).
    """
    tt = CC.thong_tin(src)
    W, H = tt["rong"], tt["cao"]
    if not W or not H:
        return np.zeros(0), np.zeros((0, 0, 0), np.uint8)
    w = RONG_DO if RONG_DO % 2 == 0 else RONG_DO + 1
    h = int(round(H * w / W))
    h += h % 2
    # dải ở toạ độ khung GỐC -> quy về khung đã thu nhỏ
    k = w / float(W)
    y0 = max(0, int(dai.y0 * k))
    y1 = min(h, int(round(dai.y1 * k)))
    if y1 - y0 < 4:                       # dải mỏng quá -> nới cho đủ đọc
        y0 = max(0, y0 - 4)
        y1 = min(h, y0 + 12)
    bh = y1 - y0
    vf = f"scale={w}:{h},crop={w}:{bh}:0:{y0},fps={fps:g}"
    cmd = [_ff(), "-v", "error", "-i", str(src), "-an", "-vf", vf,
           "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         creationflags=_NW)
    n = w * bh
    khung: list = []
    try:
        while True:
            buf = p.stdout.read(n)
            if not buf or len(buf) < n:
                break
            khung.append(CC._mat_na(np.frombuffer(buf, np.uint8)
                                    .reshape(bh, w)))
    finally:
        try:
            p.stdout.close()
        except Exception:                                       # noqa: BLE001
            pass
        p.wait(timeout=60)
    if not khung:
        return np.zeros(0), np.zeros((0, 0, 0), np.uint8)
    M = np.stack(khung)
    t = np.arange(len(khung)) / float(fps)
    return t, M


def moc_doi_dong(t: np.ndarray, M: np.ndarray) -> tuple[list, dict]:
    """Mốc (giây) DÒNG CHỮ MỚI hiện ra + số liệu phụ.

    "Dòng mới" = (a) từ KHÔNG chữ sang CÓ chữ, hoặc (b) đang có chữ mà mặt nạ
    nét đổi hẳn (IoU < `IOU_DOI_DONG`). Cả hai đều là lúc người xem thấy CHỮ
    MỚI — đúng thứ anh Hùng lấy làm mốc khi nói "chữ chạy rồi mà chưa nói".
    """
    if M.size == 0:
        return [], {"ly_do": "không đọc được khung"}
    d = M.reshape(len(M), -1).mean(axis=1)
    nguong = max(0.004, TY_LE_NGUONG * float(np.percentile(d, 90)))
    co = d >= nguong
    moc: list = []
    for i in range(1, len(M)):
        if not co[i]:
            continue
        if not co[i - 1]:
            moc.append(float(t[i]))
            continue
        a, b = M[i - 1].astype(bool), M[i].astype(bool)
        hop = np.logical_or(a, b).sum()
        if hop <= 0:
            continue
        iou = float(np.logical_and(a, b).sum()) / float(hop)
        if iou < IOU_DOI_DONG:
            moc.append(float(t[i]))
    # gộp mốc dính nhau < 0,25 s (một lần đổi dòng có thể nhấp nháy 2-3 khung)
    gon: list = []
    for x in moc:
        if not gon or x - gon[-1] > 0.25:
            gon.append(round(x, 3))
    return gon, {"nguong_mat_do": round(nguong, 5),
                 "ty_le_khung_co_chu": round(float(co.mean()), 4),
                 "so_khung": int(len(M))}


# ────────────────────── TRỤC 2/3 — TIẾNG (Demucs + silencedetect) ───────────
def tach_giong_ra(video: str | Path, lam: Path, ten: str) -> str:
    """Rút audio -> Demucs -> trả đường dẫn lớp GIỌNG (vocals)."""
    lam.mkdir(parents=True, exist_ok=True)
    wav = lam / f"{ten}.wav"
    if not wav.exists():
        TG.tach_wav(video, wav)
    d = lam / f"{ten}_tach"
    v = d / "vocals.wav"
    if v.exists():
        return str(v)
    r = TG.tach_giong(wav, d, cach="demucs")
    return str(r.get("giong") or "")


def moc_noi(giong_wav: str | Path, nguong_db: float = -38.0,
            im_toi_thieu: float = 0.30) -> list:
    """Mốc BẮT ĐẦU NÓI trên lớp giọng — `silencedetect` THẬT, không metadata.

    Trả list giây. Khoảng im ngắn hơn `im_toi_thieu` không tính là ngắt (thở
    giữa câu), nếu không một câu ra 5 mốc.
    """
    cmd = [_ff(), "-hide_banner", "-i", str(giong_wav), "-af",
           f"silencedetect=n={nguong_db}dB:d={im_toi_thieu:g}",
           "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=_NW, timeout=600)
    tong = TG.probe_duration(giong_wav)
    khoang: list = []
    st = None
    for m in re.finditer(r"silence_(start|end): (-?[\d.]+)", r.stderr or ""):
        if m.group(1) == "start":
            st = float(m.group(2))
        elif st is not None:
            khoang.append((st, float(m.group(2))))
            st = None
    if st is not None:
        khoang.append((st, tong))
    # ĐOẠN CÓ TIẾNG = phần bù của các khoảng im
    noi: list = []
    cur = 0.0
    for a, b in khoang:
        if a - cur > 0.12:
            noi.append(round(cur, 3))
        cur = b
    if tong - cur > 0.12:
        noi.append(round(cur, 3))
    return noi


# ──────────────────────────────── GHÉP CẶP ──────────────────────────────────
def ghep(chu: list, tieng: list, cua_so: float = 4.0) -> list:
    """Ghép mỗi mốc CHỮ với mốc TIẾNG gần nhất trong `cua_so` giây.

    Ghép theo KHOẢNG CÁCH chứ không theo thứ tự cứng: số dòng chữ và số câu
    tiếng không bằng nhau (một câu chép lời có thể trải 2-3 dòng phụ đề), ép
    theo thứ tự là đẻ ra lệch giả hàng giây.
    """
    ra: list = []
    for c in chu:
        gan = [v for v in tieng if abs(v - c) <= cua_so]
        if not gan:
            ra.append({"chu": c, "tieng": None, "lech_ms": None})
            continue
        v = min(gan, key=lambda x: abs(x - c))
        ra.append({"chu": c, "tieng": v,
                   "lech_ms": round((v - c) * 1000.0, 1)})
    return ra


def tom_tat(cap: list) -> dict:
    xs = [c["lech_ms"] for c in cap if c["lech_ms"] is not None]
    if not xs:
        return {"n": 0}
    a = np.array(xs, float)
    return {
        "n": len(xs), "khong_ghep_duoc": sum(1 for c in cap
                                             if c["lech_ms"] is None),
        "trung_binh_ms": round(float(a.mean()), 1),
        "trung_vi_ms": round(float(np.median(a)), 1),
        "tuyet_doi_tb_ms": round(float(np.abs(a).mean()), 1),
        "tuyet_doi_max_ms": round(float(np.abs(a).max()), 1),
        "p90_tuyet_doi_ms": round(float(np.percentile(np.abs(a), 90)), 1),
        "vuot_150ms": int((np.abs(a) > 150).sum()),
        "vuot_150ms_ty_le": round(float((np.abs(a) > 150).mean()), 4),
        "vuot_500ms": int((np.abs(a) > 500).sum()),
    }


def tich_luy(cap: list, phan: int = 4) -> list:
    """Lệch trung bình theo TỪNG PHẦN video — trôi dần thì thấy ngay ở đây."""
    xs = [c for c in cap if c["lech_ms"] is not None]
    if not xs:
        return []
    n = len(xs)
    ra = []
    for k in range(phan):
        lo, hi = n * k // phan, n * (k + 1) // phan
        pha = xs[lo:hi]
        if not pha:
            continue
        a = np.array([p["lech_ms"] for p in pha], float)
        ra.append({"phan": f"{k + 1}/{phan}",
                   "tu_giay": round(pha[0]["chu"], 1),
                   "den_giay": round(pha[-1]["chu"], 1),
                   "so_moc": len(pha),
                   "lech_tb_ms": round(float(a.mean()), 1),
                   "lech_tuyet_doi_tb_ms": round(float(np.abs(a).mean()), 1)})
    return ra


def do_mot(goc: str, ra_video: str, lam: Path, ten: str) -> dict:
    lam.mkdir(parents=True, exist_ok=True)
    print(f"[{ten}] dò dải chữ...", flush=True)
    dai = CC.do_dai_chu(ra_video)
    print(f"[{ten}] dải: co_chu={dai.co_chu} y={dai.y0}..{dai.y1} "
          f"({dai.ly_do})", flush=True)
    if not dai.co_chu:
        dai = CC.dai_mac_dinh(dai.rong, dai.cao)
    print(f"[{ten}] đọc khung dải chữ ({FPS_LAY:g} fps)...", flush=True)
    t, M = doc_dai_theo_thoi_gian(ra_video, dai)
    chu, tt_chu = moc_doi_dong(t, M)
    print(f"[{ten}] mốc CHỮ: {len(chu)} — {tt_chu}", flush=True)

    print(f"[{ten}] Demucs bản GỐC...", flush=True)
    g_voc = tach_giong_ra(goc, lam, f"{ten}_goc")
    print(f"[{ten}] Demucs bản THÀNH PHẨM...", flush=True)
    r_voc = tach_giong_ra(ra_video, lam, f"{ten}_ra")
    tieng_goc = moc_noi(g_voc) if g_voc else []
    tieng_moi = moc_noi(r_voc) if r_voc else []
    print(f"[{ten}] mốc TIẾNG GỐC {len(tieng_goc)} · TIẾNG MỚI "
          f"{len(tieng_moi)}", flush=True)

    cap_goc = ghep(chu, tieng_goc)
    cap_moi = ghep(chu, tieng_moi)
    kq = {
        "ten": ten, "goc": goc, "ra": ra_video,
        "dai_chu": dai.dict(), "tt_chu": tt_chu,
        "moc_chu": chu, "moc_tieng_goc": tieng_goc,
        "moc_tieng_moi": tieng_moi,
        "doi_chung_goc": {"tom_tat": tom_tat(cap_goc),
                          "theo_phan": tich_luy(cap_goc)},
        "thanh_pham": {"tom_tat": tom_tat(cap_moi),
                       "theo_phan": tich_luy(cap_moi),
                       "bang": cap_moi},
        "bang_goc": cap_goc,
    }
    return kq


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--goc", required=True)
    ap.add_argument("--ra", required=True)
    ap.add_argument("--lam", default=r"D:\claude\_tgdo")
    ap.add_argument("--ten", default="v1")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    kq = do_mot(a.goc, a.ra, Path(a.lam), a.ten)
    out = a.json or str(Path(a.lam) / f"_ket_{a.ten}.json")
    Path(out).write_text(json.dumps(kq, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    print("\n=== ĐỐI CHỨNG (chữ so TIẾNG GỐC) ===", flush=True)
    print(json.dumps(kq["doi_chung_goc"], ensure_ascii=False), flush=True)
    print("\n=== THÀNH PHẨM (chữ so TIẾNG MỚI) ===", flush=True)
    print(json.dumps(kq["thanh_pham"]["tom_tat"], ensure_ascii=False),
          flush=True)
    print(json.dumps(kq["thanh_pham"]["theo_phan"], ensure_ascii=False),
          flush=True)
    print(f"\n-> {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
