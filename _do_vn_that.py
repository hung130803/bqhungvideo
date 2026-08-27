"""ĐO TRÊN CHÍNH LƯỢT CHẠY THẬT CỦA ANH HÙNG — không dựng lại kịch bản.

App của anh Hùng (`BQHungVideo.exe`) để lại đủ dấu vết để đo mà **KHÔNG đụng
một byte nào**: `job.json` có ĐỦ danh sách câu, còn thư mục `raw/` có file WAV
kèm `mtime` = đúng lúc câu đó đọc xong. Hiệu hai `mtime` liền nhau = giây/câu
THẬT, trên máy THẬT, với mẫu THẬT, dưới đúng tải nền THẬT.

CHỈ ĐỌC `%LOCALAPPDATA%\\BQHungVideo` — luật repo.

Câu hỏi phép đo trả lời:
  1. giây/câu thật là bao nhiêu (repo đang ghi 5,2 — số đó ở đâu ra?)
  2. giá đi theo SỐ CHỮ hay theo SỐ LƯỢT GỌI? (quyết định bản vá nào đáng làm)
  3. một video có bao nhiêu câu?
"""
from __future__ import annotations

import glob
import json
import os
import statistics as st
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent

GOC = Path(os.environ.get(
    "BQ_VN_DATA",
    r"C:\Users\Admin\AppData\Local\BQHungVideo\_giong_vieneu"))
KQ = REPO / "_kq_vn_that.json"


def mot_job(jd: str) -> dict | None:
    jf = os.path.join(jd, "job.json")
    if not os.path.isfile(jf):
        return None
    try:
        J = json.load(open(jf, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    it = J.get("items") or []
    if not it:
        return None
    t_job = os.path.getmtime(jf)
    raw = os.path.dirname(it[0]["raw"])
    # Khớp file THEO ĐÚNG đường dẫn `job.json` khai, không glob bừa: hai job
    # có thể dùng chung thư mục cha.
    xong = []
    for x in it:
        p = x["raw"]
        if os.path.isfile(p):
            try:
                xong.append((os.path.getmtime(p), len(x["text"]), x["text"],
                             os.path.getsize(p)))
            except OSError:
                pass
    xong.sort()
    d: dict = {
        "job": os.path.basename(jd),
        "so_cau": len(it),
        "so_xong": len(xong),
        "nhan_ban": bool(J.get("ref_audio")),
        "mau": os.path.basename(J.get("ref_audio") or ""),
        "voice": J.get("voice") or "",
        "tao_luc": time.strftime("%d/%m %H:%M:%S", time.localtime(t_job)),
        "ky_tu_tb": round(sum(len(x["text"]) for x in it) / len(it), 1),
        "ky_tu_min": min(len(x["text"]) for x in it),
        "ky_tu_max": max(len(x["text"]) for x in it),
    }
    if len(xong) < 2:
        return d
    # GIÂY/CÂU = hiệu mtime giữa hai file liền nhau. Câu ĐẦU bị bỏ khỏi thống
    # kê: khoảng của nó tính từ lúc ghi `job.json`, tức GỒM CẢ phần nạp model.
    hieu = [(xong[k][0] - xong[k - 1][0], xong[k][1])
            for k in range(1, len(xong))]
    giay = [h for h, _ in hieu]
    d.update({
        "nap_model_uoc_s": round(xong[0][0] - t_job, 1),
        "giay_moi_cau_TB": round(st.mean(giay), 2),
        "giay_moi_cau_trung_vi": round(st.median(giay), 2),
        "giay_moi_cau_min": round(min(giay), 2),
        "giay_moi_cau_max": round(max(giay), 2),
        "tong_giay_da_doc": round(xong[-1][0] - xong[0][0], 1),
    })
    # GIÁ THEO CHỮ hay THEO LƯỢT GỌI? Chia câu làm hai nửa theo số ký tự rồi
    # so giây/câu. Cùng giá = giá nằm ở LƯỢT GỌI, không ở độ dài chữ.
    co_du = [(g, n) for g, n in hieu if n > 0]
    if len(co_du) >= 8:
        co_du.sort(key=lambda x: x[1])
        nua = len(co_du) // 2
        ngan = [g for g, _ in co_du[:nua]]
        dai = [g for g, _ in co_du[-nua:]]
        d.update({
            "nua_CAU_NGAN": {
                "ky_tu_tb": round(st.mean([n for _, n in co_du[:nua]]), 1),
                "giay_tb": round(st.mean(ngan), 2)},
            "nua_CAU_DAI": {
                "ky_tu_tb": round(st.mean([n for _, n in co_du[-nua:]]), 1),
                "giay_tb": round(st.mean(dai), 2)},
        })
        # Phí CỐ ĐỊNH mỗi lượt gọi, khớp `a + b*n` (hai điểm).
        n1 = st.mean([n for _, n in co_du[:nua]])
        n2 = st.mean([n for _, n in co_du[-nua:]])
        g1, g2 = st.mean(ngan), st.mean(dai)
        if n2 > n1:
            b = (g2 - g1) / (n2 - n1)
            a = g1 - b * n1
            d["phi_co_dinh_moi_cau_s"] = round(a, 2)
            d["giay_moi_ky_tu"] = round(b, 4)
            d["%_phi_co_dinh"] = round(
                100.0 * a / max(1e-9, st.mean(giay)), 1)
    return d


def main() -> int:
    if not GOC.is_dir():
        print(f"KHÔNG THẤY {GOC}")
        return 2
    ra = []
    for jd in sorted(glob.glob(str(GOC / "_job_*"))):
        d = mot_job(jd)
        if d:
            ra.append(d)
    ra.sort(key=lambda x: -x.get("so_xong", 0))

    print("=" * 78)
    print("LƯỢT CHẠY THẬT CỦA ANH HÙNG — giọng nhân bản `vnb:` đọc tiếng Anh")
    print("=" * 78)
    print(f"{'job':<22}{'câu':>5}{'xong':>6}{'s/câu':>8}{'trung vị':>10}"
          f"{'nạp':>7}  {'ký tự/câu':>10}")
    for d in ra:
        if "giay_moi_cau_TB" not in d:
            continue
        print(f"{d['job']:<22}{d['so_cau']:>5}{d['so_xong']:>6}"
              f"{d['giay_moi_cau_TB']:>8.1f}{d['giay_moi_cau_trung_vi']:>10.1f}"
              f"{d['nap_model_uoc_s']:>7.0f}  {d['ky_tu_tb']:>10.0f}")
    xong = [d for d in ra if "giay_moi_cau_TB" in d]
    if xong:
        gg = [d["giay_moi_cau_TB"] for d in xong]
        cc = [d["so_cau"] for d in xong]
        print("-" * 78)
        print(f"giây/câu: TB {st.mean(gg):.1f} · trải {min(gg):.1f}-{max(gg):.1f}")
        print(f"số câu/video: TB {st.mean(cc):.0f} · trải {min(cc)}-{max(cc)}")
        print(f"=> MỘT LƯỢT ĐỌC (bước 4a) cho video trung bình: "
              f"{st.mean(gg) * st.mean(cc) / 60:.0f} PHÚT")
        print()
        for d in xong:
            if "nua_CAU_NGAN" in d:
                print(f"{d['job']}: câu NGẮN {d['nua_CAU_NGAN']['ky_tu_tb']:.0f} "
                      f"ký tự -> {d['nua_CAU_NGAN']['giay_tb']:.1f}s · "
                      f"câu DÀI {d['nua_CAU_DAI']['ky_tu_tb']:.0f} ký tự -> "
                      f"{d['nua_CAU_DAI']['giay_tb']:.1f}s · phí CỐ ĐỊNH "
                      f"{d.get('phi_co_dinh_moi_cau_s', 0):.1f}s "
                      f"({d.get('%_phi_co_dinh', 0):.0f}% mỗi câu)")
    KQ.write_text(json.dumps(ra, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"\nGhi: {KQ}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
