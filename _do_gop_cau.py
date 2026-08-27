# -*- coding: utf-8 -*-
"""NGHI PHẠM 2 — "CÂU CẮT QUÁ NHỎ NÊN NHIỀU MỐI NỐI": ĐO CẢ HAI MẶT.

Đề bài (mục D): *thử gộp câu ngắn liền nhau (trần ký tự cao hơn) rồi đo lại số
mối nối*, và **đo cả mặt hại** — câu dài hơn thì `atempo` phải ép nhiều hơn.

**ĐIỀU PHẢI KIỂM TRƯỚC, VÀ NÓ LẬT ĐỀ BÀI:** `cau_tu_transcript(d, gop_toi_da)`
**KHÔNG BAO GIỜ GỘP** — đọc mã thì `gop_toi_da` là TRẦN để **CẮT NHỎ** segment
quá dài, không phải đích để gộp. Danh sách câu đi thẳng từ `segments` của Groq
whisper. Nên "nâng trần ký tự" là một phép **KHÔNG CÓ TÁC DỤNG GÌ** trên bộ câu
ngắn; muốn gộp thì phải VIẾT bước gộp mới. Script này đo cả hai:
  (1) nâng `gop_toi_da` đổi được bao nhiêu câu (dự kiến: 0),
  (2) NẾU viết bước gộp thì được/mất gì — mô phỏng trên SỐ ĐO THẬT.

Dữ liệu vào là số ĐO, không phải mô hình: lưới câu lấy từ bản chép lời Groq
THẬT (cache `_do_tg_cache.json`), độ dài TIẾNG lấy từ **chính file WAV mà lượt
đo B vừa ghi ra** (`arm_cu/khop/khop_XXXX.wav`), đo bằng `do_le_im` nên là
tiếng NÓI THẬT, không tính lề im (bẫy `probe_duration` của v2.27.0).

**MÔ PHỎNG CÓ MỘT CHỖ KHÔNG CHẮC, GHI THẲNG:** gộp thật thì LLM viết lại thành
một câu và máy đọc đọc LIỀN, độ dài có thể khác tổng các mảnh. Ở đây lấy TỔNG
độ dài tiếng của các câu thành phần = giả định **BẢO TOÀN**, hơi BI QUAN (đọc
liền thường bớt được phần lấy hơi giữa câu).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

from app.core import thay_giong as tg                  # noqa: E402

KQ = REPO / "_kq_lienmach"
CACHE = REPO / "_do_tg_cache.json"
KHOP = REPO / "_do_kv_tam" / "lt1" / "g_EDGE" / "arm_cu" / "khop"
KHOA = "chep|lt1|90.0"

TRAN_KY_TU = (0, 60, 80, 100, 140)     # 0 = KHÔNG gộp (hiện trạng)
K_DO = (1.0, 1.1988)                   # arm CŨ và arm chỉnh hình CHẠM TRẦN
BAC = (0.5, 1.0, 2.0)


def doc_cau() -> list[dict]:
    d = json.loads(CACHE.read_text(encoding="utf-8"))
    chep = d.get(KHOA)
    if not chep:
        raise SystemExit(f"cache thiếu khoá {KHOA}")
    return tg.cau_tu_transcript(chep)


def do_tieng(n: int) -> list[tuple[float, float, float]]:
    """(lề đầu, dài TIẾNG THẬT, dài file) của từng câu — ĐO trên WAV đã ghi."""
    ra = []
    for i in range(n):
        p = KHOP / f"khop_{i:04d}.wav"
        if not p.exists():
            ra.append((0.0, 0.0, 0.0))
            continue
        d = tg.probe_duration(p)
        le_d, le_c, _ = tg.do_le_im(p, nguong_db=tg.NGUONG_IM_MOC_DB)
        ra.append((le_d, max(0.0, d - le_d - le_c), d))
    return ra


def gop(cau: list[dict], tieng: list, tran: int) -> list[list[int]]:
    """Gom câu liền nhau thành khối, trần KÝ TỰ bản dịch. `tran=0` -> không gộp."""
    if tran <= 0:
        return [[i] for i in range(len(cau))]
    khoi: list[list[int]] = []
    cur: list[int] = []
    n_ky = 0
    for i, c in enumerate(cau):
        m = len(str(c.get("text", "")).strip())
        # CẮT TRƯỚC KHI VƯỢT, không phải sau — đúng bài học `cau_tu_transcript`
        # (gộp rồi mới kiểm thì khối luôn vượt trần đúng MỘT câu).
        if cur and n_ky + m > tran:
            khoi.append(cur)
            cur, n_ky = [], 0
        cur.append(i)
        n_ky += m
    if cur:
        khoi.append(cur)
    return khoi


def do_mot(cau: list[dict], tieng: list, khoi: list[list[int]],
           k: float, tong: float) -> dict:
    """Đặt từng KHỐI vào mốc gốc × k rồi đo im GIỮA KHỐI + sức ép `atempo`."""
    tong_ra = tong * k
    moc: list[tuple[float, float]] = []
    temps: list[float] = []
    for j, kh in enumerate(khoi):
        p, q = kh[0], kh[-1]
        a = float(cau[p]["start"]) * k
        ke = (float(cau[khoi[j + 1][0]]["start"]) * k
              if j + 1 < len(khoi) else tong_ra)
        khung = max(0.05, float(cau[q]["end"]) * k - a)
        # trần MƯỢN: y `khop_thoi_gian` — được kéo tới sát câu kế
        cho_phep = max(khung, ke - a - tg.CHUA_TRUOC_CAU_KE)
        d_noi = sum(tieng[i][1] for i in kh)
        le = tieng[p][0] if p < len(tieng) else 0.0
        t = 1.0 if d_noi <= cho_phep + 1e-3 else min(
            tg.TEMPO_TOI_DA, d_noi / max(0.05, cho_phep))
        temps.append(t)
        d_ra = d_noi / t
        moc.append((a + le, a + le + d_ra))
    kho: list[float] = []
    for (_a0, b0), (a1, _b1) in zip(moc, moc[1:]):
        if a1 - b0 > 0:
            kho.append(a1 - b0)
    noi = sum(b - a for a, b in moc)
    return {
        "so_khoi": len(khoi), "so_moi_noi": max(0, len(khoi) - 1),
        "im_tong": round(sum(kho), 2),
        "im_pt": round(100.0 * sum(kho) / max(0.001, tong_ra), 2),
        **{f"im_>={m}": sum(1 for g in kho if g >= m) for m in BAC},
        "im_dai_nhat": round(max(kho), 2) if kho else 0.0,
        "im_tb": round(sum(kho) / len(kho), 3) if kho else 0.0,
        "co_tieng_pt": round(100.0 * noi / max(0.001, tong_ra), 2),
        "tempo_max": round(max(temps), 3) if temps else 1.0,
        "tempo_tb": round(sum(temps) / len(temps), 3) if temps else 1.0,
        "so_ep_120": sum(1 for t in temps if t > 1.20),
        "so_ep_130": sum(1 for t in temps if t > 1.30),
        "so_cham_tran": sum(1 for t in temps if t >= tg.TEMPO_TOI_DA - 1e-6),
    }


def main() -> int:
    KQ.mkdir(parents=True, exist_ok=True)
    cau = doc_cau()
    tong = max(float(c["end"]) for c in cau)
    tieng = do_tieng(len(cau))
    ky = [len(str(c.get("text", "")).strip()) for c in cau]
    giay = [float(c["end"]) - float(c["start"]) for c in cau]

    L: list[str] = []
    L.append("BẢNG D — GỘP CÂU NGẮN: ĐƯỢC GÌ, MẤT GÌ")
    L.append("=" * 100)
    L.append(f"nguồn lt1 · {tong:.2f}s · {len(cau)} câu (bản chép lời Groq THẬT)")
    L.append(f"  ký tự/câu: TB {sum(ky)/len(ky):.1f} · nhỏ nhất {min(ky)}"
             f" · lớn nhất {max(ky)}")
    L.append(f"  giây/câu:  TB {sum(giay)/len(giay):.2f} · nhỏ nhất"
             f" {min(giay):.2f} · lớn nhất {max(giay):.2f}")

    # (1) NÂNG `gop_toi_da` ĐỔI ĐƯỢC GÌ — kiểm bằng GỌI THẬT, không đọc mã suông
    d = json.loads(CACHE.read_text(encoding="utf-8"))[KHOA]
    L.append("")
    L.append("(1) NÂNG TRẦN `gop_toi_da` CỦA `cau_tu_transcript` — GỌI THẬT:")
    for g in (8.0, 12.0, 20.0, 60.0):
        n = len(tg.cau_tu_transcript(d, gop_toi_da=g))
        L.append(f"    gop_toi_da = {g:5.1f}s  ->  {n} câu")
    qua = sum(1 for x in giay if x > 12.0)
    L.append(f"    số segment gốc DÀI HƠN 12s: {qua}"
             f"  -> trần đó {'KHÔNG' if qua == 0 else 'CÓ'} đụng tới bộ câu này."
             f"  **`cau_tu_transcript` chỉ CẮT NHỎ, KHÔNG GỘP.**")

    # ---- MỆNH ĐỀ TRUNG TÂM: BAO NHIÊU PHẦN IM LÀ CỦA NGUỒN, BAO NHIÊU APP ĐẺ
    # Tách làm BA tầng, mỗi tầng một nguyên nhân KHÁC HẲN nhau — gộp lại là
    # không nói được nên chữa ở đâu.
    im_nguon = sum(max(0.0, float(cau[i + 1]["start"]) - float(cau[i]["end"]))
                   for i in range(len(cau) - 1))
    r1 = do_mot(cau, tieng, gop(cau, tieng, 0), 1.0, tong)
    rk = do_mot(cau, tieng, gop(cau, tieng, K_DO[1]), K_DO[1], tong)
    im_dich = r1["im_tong"] - im_nguon
    im_hinh = rk["im_tong"] - r1["im_tong"]
    L.append("")
    L.append("(0) IM GIỮA CÂU ĐẾN TỪ ĐÂU — ba tầng, ba nguyên nhân khác nhau:")
    L.append(f"    (a) CỦA NGUỒN   : {im_nguon:6.2f}s"
             f" ({100*im_nguon/tong:5.2f}%) — khoảng giữa hai segment chép lời,"
             f" tức chính người dẫn Douyin nghỉ")
    L.append(f"    (b) BẢN DỊCH NGẮN HƠN CÂU GỐC: {im_dich:6.2f}s"
             f" ({100*im_dich/tong:5.2f}%) — đọc xong sớm hơn khung câu")
    L.append(f"    (c) **CHỈNH VIDEO THEO GIỌNG (k={K_DO[1]})**: {im_hinh:6.2f}s"
             f" ({100*im_hinh/tong:5.2f}%) — giãn ĐỀU nên giãn cả chỗ đang im")
    L.append(f"    -> TỔNG khi BẬT chỉnh hình: {rk['im_tong']:.2f}s"
             f" / {tong*K_DO[1]:.2f}s = {rk['im_pt']:.2f}% thời lượng")
    L.append(f"    ĐỐI CHIẾU: (k-1)x{tong:.2f} = {(K_DO[1]-1)*tong:.2f}s"
             f"  vs  phần im tăng thêm {im_hinh:.2f}s"
             f"  =  {100*im_hinh/max(0.001,(K_DO[1]-1)*tong):.1f}% phần video"
             f" dài thêm rơi VÀO KHOẢNG IM")

    # (2) MÔ PHỎNG BƯỚC GỘP MỚI
    ra: dict = {"im_nguon": round(im_nguon, 2), "im_dich": round(im_dich, 2),
                "im_hinh": round(im_hinh, 2)}
    for k in K_DO:
        L.append("")
        nhan = ("arm CŨ (k=1,000 · không chỉnh hình)" if k == 1.0
                else f"arm CHỈNH HÌNH (k={k:.4f} · CHẠM TRẦN, ĐÚNG cái anh "
                     f"Hùng đang bật)")
        L.append(f"(2) MÔ PHỎNG GỘP — {nhan}")
        L.append(f"    {'trần ký tự':<12}{'câu':>5}{'mối nối':>9}"
                 f"{'im tổng':>9}{'im %':>7}{'>=0,5':>7}{'>=1,0':>7}"
                 f"{'>=2,0':>7}{'dài nhất':>10}{'có tiếng%':>11}"
                 f"{'tempo max':>11}{'ép>1,2':>8}{'chạm 1,5':>10}")
        L.append("    " + "-" * 111)
        for tran in TRAN_KY_TU:
            r = do_mot(cau, tieng, gop(cau, tieng, tran), k, tong)
            ra[f"k{k}_t{tran}"] = r
            ten = "KHÔNG gộp" if tran == 0 else f"{tran} ký tự"
            L.append(f"    {ten:<12}{r['so_khoi']:>5d}{r['so_moi_noi']:>9d}"
                     f"{r['im_tong']:>9.2f}{r['im_pt']:>7.2f}"
                     f"{r['im_>=0.5']:>7d}{r['im_>=1.0']:>7d}"
                     f"{r['im_>=2.0']:>7d}{r['im_dai_nhat']:>10.2f}"
                     f"{r['co_tieng_pt']:>11.2f}{r['tempo_max']:>11.3f}"
                     f"{r['so_ep_120']:>8d}{r['so_cham_tran']:>10d}")
    txt = "\n".join(L)
    print(txt)
    (KQ / "D_gop_cau.txt").write_text(txt, encoding="utf-8")
    (KQ / "D_gop_cau.json").write_text(
        json.dumps(ra, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {KQ / 'D_gop_cau.txt'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
