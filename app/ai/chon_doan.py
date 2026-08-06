# -*- coding: utf-8 -*-
"""CHỌN ĐOẠN THÔNG MINH: cho AI **NGHE** + **TRỌNG TÀI CHẤM MÙ** + né intro/outro.

VÌ SAO (đo thật 06/08/2026 trên 3 video thật của anh Hùng — `_do_chon_doan.py`):
  1. AI **TỰ CHẤM CHÍNH MÌNH**: 9/9 clip nó tự cho **85-95 điểm** -> sàn chất
     lượng 55 (`m1_highlight._apply_quality_floor`) loại được **0 clip**. Sàn
     đang là hình thức. => cần TRỌNG TÀI riêng, chấm MÙ theo thang rõ.
  2. AI chọn khi **bịt tai**: các bước `audio`/`scenes`/vision đều bị
     `LIGHT_MODE=1` chặn (đo: cả 4 = 'skipped'). Đoạn "người ta gào khóc" và
     đoạn "đọc thủ tục đều đều" qua CHỮ nhìn y như nhau -> chọn đoạn nhạt.
     => lấy NĂNG LƯỢNG TIẾNG bằng ffmpeg `astats` (không cần librosa, không
     cần mở LIGHT_MODE) rồi đưa mốc "to gấp mấy lần trung bình" vào prompt.
  3. Lấy nguyên **intro**: video 1 clip đầu bắt đầu ở **0,6 giây**.
     => chặn theo TỈ LỆ đầu/cuối video + cho phép nới nếu đoạn đó thật sự căng.

Mọi hàm ở đây THUẦN (trừ `nang_luong` gọi ffmpeg) để test được, và MỌI hàm đều
fail-safe: lỗi/thiếu dữ liệu -> trả về nguyên trạng, KHÔNG chặn đường cắt.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

_NO_WIN = 0x08000000 if sys.platform == "win32" else 0
#: cửa sổ đo năng lượng (giây). 1,0s đủ mịn để bắt tiếng gào/đập mà rẻ.
CUA_SO = 1.0
#: mốc "đoạn căng": to hơn trung bình bao nhiêu lần (theo biên độ, không phải dB)
NGUONG_CANG = 1.6


def nang_luong(src: str, ffmpeg: str, tong_giay: float = 0.0) -> list[float]:
    """Đo mức âm THEO TỪNG GIÂY của video -> list biên độ RMS (0..1).

    Dùng `astats` metadata mỗi cửa sổ; 1 lần chạy ffmpeg cho cả video, không
    giải mã hình (`-vn`) nên rẻ. Lỗi -> [] (caller tự bỏ qua phần 'nghe')."""
    try:
        r = subprocess.run(
            [ffmpeg, "-hide_banner", "-nostats", "-i", src, "-vn",
             "-af", f"aresample=16000,asetnsamples=n={int(16000 * CUA_SO)},"
                    f"astats=metadata=1:reset=1,"
                    f"ametadata=print:key=lavfi.astats.Overall.RMS_level:"
                    f"file=-",
             "-f", "null", os.devnull],
            capture_output=True, text=True, errors="replace",
            creationflags=_NO_WIN, timeout=900)
    except Exception:  # noqa: BLE001
        return []
    ra = []
    for m in re.finditer(r"RMS_level=(-?[0-9.]+|-inf)", r.stdout or ""):
        v = m.group(1)
        if v == "-inf":
            ra.append(0.0)
            continue
        try:                       # dBFS -> biên độ tuyến tính
            ra.append(min(1.0, 10 ** (float(v) / 20.0)))
        except ValueError:
            ra.append(0.0)
    return ra


def cua_so_cang(nl: list[float], top: int = 12,
                nguong: float = NGUONG_CANG) -> list[tuple[float, float, float]]:
    """Các khoảng ỒN HƠN HẲN trung bình -> [(giây_đầu, giây_cuối, gấp mấy lần)].

    Gộp các giây liền nhau thành 1 khoảng; sắp theo 'gấp' giảm dần, lấy `top`."""
    if not nl:
        return []
    tb = sum(nl) / len(nl)
    if tb <= 0:
        return []
    cao, khoang, dau = [i for i, v in enumerate(nl) if v >= tb * nguong], [], None
    for i, gi in enumerate(cao):
        if dau is None:
            dau = gi
        if i + 1 >= len(cao) or cao[i + 1] != gi + 1:
            a, b = dau, gi + 1
            gap = (sum(nl[a:b]) / max(1, b - a)) / tb
            khoang.append((float(a) * CUA_SO, float(b) * CUA_SO, round(gap, 2)))
            dau = None
    khoang.sort(key=lambda x: -x[2])
    return khoang[:top]


def khoi_prompt_nghe(khoang: list, tong_giay: float) -> str:
    """Khối chữ mô tả 'AI nghe được gì' để chèn vào prompt chọn đoạn."""
    if not khoang:
        return ""
    d = []
    for a, b, gap in sorted(khoang)[:12]:
        d.append(f"{int(a)//60}:{int(a)%60:02d}-{int(b)//60}:{int(b)%60:02d} "
                 f"(to gấp {gap:.1f}×)")
    return ("\nÂM THANH — các khoảng ỒN/CĂNG HƠN HẲN phần còn lại (người gào, "
            "khóc, va chạm, đám đông): " + " · ".join(d) +
            "\n=> ƯU TIÊN chọn đoạn CHỨA các mốc này; đoạn không có mốc nào "
            "thường là nói đều đều/giải thích -> chỉ lấy nếu nội dung thật sốc.")


def chuyen_dong(src: str, ffmpeg: str, fps: float = 4.0) -> list[float]:
    """Đo ĐỘ ĐỘNG CỦA HÌNH theo từng giây -> list điểm 0..1 (1 = hình đổi rất
    nhiều).

    Vì sao cần (yêu cầu anh Hùng 06/08/2026): "mấy đoạn không nói gì nhưng hành
    động trong video hay thì vẫn giữ". Chỉ nghe tiếng + đọc chữ là bỏ mất mấy
    đoạn ĐÁNH NHAU/RƯỢT/TAI NẠN không ai nói câu nào.

    Cách rẻ: hạ còn `fps` khung/giây + thu nhỏ 160px rồi dùng `tblend=difference` + `signalstats`
    (mức sai khác giữa 2 khung liên tiếp = mức động) — KHÔNG cần model vision, không cần
    mediapipe. Lỗi -> [] (caller bỏ qua phần 'xem')."""
    try:
        r = subprocess.run(
            [ffmpeg, "-hide_banner", "-nostats", "-i", src, "-an",
             "-vf", f"fps={fps},scale=160:-2,format=gray,"
                    f"tblend=all_mode=difference,signalstats,"
                    f"metadata=print:key=lavfi.signalstats.YAVG:file=-",
             "-f", "null", os.devnull],
            capture_output=True, text=True, errors="replace",
            creationflags=_NO_WIN, timeout=1800)
    except Exception:  # noqa: BLE001
        return []
    # YAVG của KHUNG SAI KHÁC (tblend difference) = mức ĐỘNG thật.
    # BẢN ĐẦU DÙNG `scdet` VÀ ĐÃ SAI (cổng 24 bắt): scdet chỉ chấm điểm CẮT
    # CẢNH — testsrc2 chuyển động liên tục mà điểm chỉ 0,004-0,016, chỉ chỗ
    # cut mới 0,365 => không bắt được "hành động", chỉ bắt được chỗ ghép.
    diem = [min(1.0, float(m.group(1)) / 64.0)
            for m in re.finditer(r"signalstats\.YAVG=([0-9.]+)", r.stdout or "")]
    if not diem:
        return []
    # gộp về TỪNG GIÂY: lấy mức động CAO NHẤT trong giây đó (1 cú va chạm 0,25s
    # vẫn phải nổi lên, dùng trung bình là bị san phẳng mất)
    n = max(1, int(round(fps)))
    return [min(1.0, max(diem[i:i + n])) for i in range(0, len(diem), n)]


def cua_so_dong_khong_loi(cd: list[float], transcript: dict,
                          tong_giay: float, top: int = 8,
                          pha: float = 0.4,
                          it_nhat: float = 2.0) -> list[tuple[float, float, float]]:
    """Khoảng HÌNH ĐỘNG MẠNH mà KHÔNG CÓ LỜI NÓI -> [(a, b, gấp mấy lần)].

    Đây chính là loại đoạn app đang bỏ sót: đánh nhau, rượt, tai nạn, đám đông
    ồn ào không ai nói câu nào. Chỉ lấy khoảng dài >= `it_nhat` giây để không
    nhặt nhiễu nén (1-2 khung nhảy)."""
    if not cd:
        return []
    tb = sum(cd) / len(cd)
    if tb <= 0:
        return []
    # NGƯỠNG = điểm GIỮA mức "tĩnh" (p20) và mức "động mạnh" (p90).
    # KHÔNG dùng "gấp N lần trung bình" (bản đầu, cổng 24 bắt sai): video nửa
    # tĩnh nửa động thì trung bình bị chính phần động kéo lên -> ngưỡng vượt
    # luôn cả phần động, ra 0 khoảng. Cách này tách 2 cụm nên đúng cả khi video
    # động suốt (lúc đó p20≈p90 -> lấy phần động hơn).
    sx = sorted(cd)
    p20 = sx[max(0, int(len(sx) * 0.20) - 1)]
    p90 = sx[min(len(sx) - 1, int(len(sx) * 0.90))]
    nguong_ = p20 + pha * max(0.0, p90 - p20)
    if nguong_ <= 0:
        nguong_ = tb
    # giây nào CÓ lời nói (theo transcript) -> loại khỏi ứng viên
    co_loi = set()
    for s in (transcript or {}).get("segments") or []:
        try:
            for g in range(int(float(s["start"])), int(float(s["end"])) + 1):
                co_loi.add(g)
        except (KeyError, ValueError, TypeError):
            continue
    ra, dau = [], None
    for i in range(len(cd) + 1):
        manh = (i < len(cd) and cd[i] >= nguong_ and i not in co_loi)
        if manh and dau is None:
            dau = i
        elif not manh and dau is not None:
            if (i - dau) >= it_nhat:
                gap = (sum(cd[dau:i]) / max(1, i - dau)) / tb
                ra.append((float(dau), float(i), round(gap, 2)))
            dau = None
    ra.sort(key=lambda x: -x[2])
    return ra[:top]


def khoi_prompt_hanh_dong(khoang: list) -> str:
    """Khối chữ 'AI thấy hành động gì' — ép AI GIỮ đoạn hay dù không có thoại."""
    if not khoang:
        return ""
    d = [f"{int(a)//60}:{int(a)%60:02d}-{int(b)//60}:{int(b)%60:02d} "
         f"(động gấp {g:.1f}×)" for a, b, g in sorted(khoang)]
    return ("\nHÌNH ẢNH — các khoảng KHÔNG CÓ LỜI NÓI nhưng HÀNH ĐỘNG MẠNH "
            "(đánh nhau, rượt, va chạm, đám đông, thao tác gấp): "
            + " · ".join(d) +
            "\n=> ĐƯỢC PHÉP và NÊN đưa các khoảng này vào clip dù không có "
            "thoại — đừng bỏ chỉ vì im lặng. Nếu 1 khoảng như vậy nằm sát đoạn "
            "có thoại hay, hãy GỘP chúng thành 1 clip.")


def _pct(x: float, tong: float) -> float:
    return (x / tong) if tong > 0 else 0.0


def loc_intro_outro(clips: list, tong_giay: float, dau: float = 0.04,
                    cuoi: float = 0.03) -> tuple[list, list]:
    """Bỏ clip NẰM HẲN trong vùng intro (đầu video) / outro (cuối video).

    Đo thật: clip đầu của video 1 bắt đầu ở 0,6s -> ăn nguyên intro. Chỉ bỏ khi
    clip nằm HẲN trong vùng đó (không cắt oan clip vắt qua). Trả (giữ, bỏ)."""
    if not clips or tong_giay <= 0:
        return clips, []
    giu, bo = [], []
    for c in clips:
        segs = c.get("segments") or []
        if not segs:
            giu.append(c)
            continue
        a, b = float(segs[0][0]), float(segs[-1][1])
        if _pct(b, tong_giay) <= dau:
            bo.append((c, "nằm trong intro"))
        elif _pct(a, tong_giay) >= 1.0 - cuoi:
            bo.append((c, "nằm trong outro"))
        else:
            giu.append(c)
    if not giu:                      # đừng trắng tay
        return clips, []
    return giu, bo


def hook_theo_tieng(clip: dict, nl: list[float],
                    dai: float = 3.0) -> list | None:
    """Chọn lại HOOK = 2-4 giây ỒN NHẤT **nằm trong clip** (đỉnh cảm xúc thật).

    Trả [a,b] hoặc None nếu không đủ dữ liệu. Dùng để BẢO ĐẢM mấy giây đầu clip
    có cao trào — thay vì tin vào mốc AI đoán từ chữ."""
    segs = clip.get("segments") or []
    if not nl or not segs:
        return None
    tot, best = -1.0, None
    n = int(dai / CUA_SO) or 1
    for s, e in segs:
        i0, i1 = int(float(s) / CUA_SO), int(float(e) / CUA_SO)
        for i in range(i0, max(i0 + 1, i1 - n + 1)):
            if i + n > len(nl):
                break
            m = sum(nl[i:i + n]) / n
            if m > tot:
                tot, best = m, [round(i * CUA_SO, 2), round((i + n) * CUA_SO, 2)]
    return best


def san_thich_ung(clips: list, ty_le: float = 0.72, san_rac: float = 28.0,
                  giu_it_nhat: int = 1, so_part: int = 0) -> tuple[list, list]:
    """SÀN TỰ THÍCH ỨNG: giữ clip đủ tốt **so với clip hay nhất CÙNG video**.

    VÌ SAO KHÔNG DÙNG SÀN SỐ CỨNG (đo thật 06/08/2026): trọng tài chấm mù cho
    40-60 điểm (thang khó tính), còn sàn cũ là 55 theo thang AI-tự-chấm (85-95)
    -> 7/9 clip bị loại oan, mỗi video còn 1 Part. HAI THANG KHÔNG CÙNG ĐƠN VỊ.

    Nay lọc theo TƯƠNG QUAN: clip nào < `ty_le` × điểm-clip-đầu-bảng thì bỏ
    (kém hơn hẳn), cộng thêm 1 sàn rác tuyệt đối cho đoạn dở hẳn.

    ƯU TIÊN SỐ PART USER ĐẶT (anh Hùng 06/08/2026: "nếu 3 part thì phải 3 part,
    không hơn; video ngắn quá không đủ thì 1-2 cũng được"): `so_part` > 0 ->
    LUÔN giữ đủ `so_part` clip TỐT NHẤT nếu có sẵn, chỉ bỏ clip DỞ HẲN (dưới
    `san_rac`). Thiếu ứng viên (video ngắn) thì ra bao nhiêu giữ bấy nhiêu.
    Trả (giữ, [(clip, lý_do)])."""
    if not clips:
        return clips, []
    diem = [float(c.get("score", 0) or 0) for c in clips]
    top = max(diem) if diem else 0.0
    if top <= 0:
        return clips, []
    # user đặt SỐ PART -> chỉ lọc RÁC, không lọc tương quan (không được ra ít
    # Part hơn yêu cầu chỉ vì đoạn này hơi kém đoạn kia)
    nguong = san_rac if so_part > 0 else max(san_rac, top * ty_le)
    giu, bo = [], []
    for c, d in zip(clips, diem):
        if d >= nguong:
            giu.append(c)
        else:
            bo.append((c, f"điểm {d:.0f} < ngưỡng {nguong:.0f}"
                          + ("" if so_part > 0 else
                             f" (kém hơn hẳn đoạn hay nhất {top:.0f})")))
    if so_part > 0 and len(giu) > so_part:
        # giữ ĐÚNG so_part clip điểm cao nhất, phần dư ghi rõ lý do
        thu = sorted(zip(giu, [float(c.get("score", 0) or 0) for c in giu]),
                     key=lambda x: -x[1])
        du = [c for c, _ in thu[so_part:]]
        giu = [c for c, _ in thu[:so_part]]
        bo += [(c, f"vượt số Part đã đặt ({so_part})") for c in du]
    # KHÔNG nâng `giu_it_nhat` theo so_part: cứu-nguy sẽ KÉO LẠI cả đoạn RÁC
    # cho "đủ part" (cổng 24 bắt: đoạn 5 điểm bị lôi về khi đặt 3 part). Thiếu
    # part vì video không có đủ đoạn dùng được là ĐÚNG — thà 1-2 Part sạch.
    if len(giu) < giu_it_nhat:                      # đừng trắng tay
        thu = sorted(zip(clips, diem), key=lambda x: -x[1])[:giu_it_nhat]
        giu = [c for c, _ in thu]
        bo = [(c, ly) for c, ly in bo if c not in giu]
    return giu, bo


# ---------------- TRỌNG TÀI CHẤM MÙ ----------------
THANG = (
    "Cho điểm 0-100 theo 5 tiêu chí (mỗi cái 0-20):\n"
    "1. HOOK 3 giây đầu: có câu/hành động khiến người ta KHÔNG lướt qua?\n"
    "2. XUNG ĐỘT/LEO THANG: có căng thẳng, tranh cãi, nguy hiểm tăng dần?\n"
    "3. BƯỚC NGOẶT/TIẾT LỘ: có thông tin bất ngờ, lật kèo, sự thật phơi ra?\n"
    "4. CÂU CHỐT: kết đoạn có câu/hành động đóng lại thoả mãn (không lửng lơ)?\n"
    "5. TỰ ĐỦ NGHĨA: xem RIÊNG đoạn này vẫn hiểu, không cần xem trước đó?\n"
    "TRỪ ĐIỂM MẠNH nếu: nói đều đều/giải thích thủ tục, lời chào kênh, kêu gọi "
    "đăng ký, quảng cáo, im lặng dài, chỉ mô tả bối cảnh.\n"
    "KHÓ TÍNH: đoạn tầm tầm cho 40-55; chỉ đoạn thật sự cuốn mới >70."
)


def _tom_tat_clip(clips: list, transcript: dict, max_ky_tu: int = 900) -> list:
    """Tóm tắt từng clip bằng THOẠI THẬT (trọng tài không được biết ai chọn)."""
    segs = (transcript or {}).get("segments") or []
    ra = []
    for i, c in enumerate(clips):
        cs = c.get("segments") or []
        if not cs:
            ra.append({"index": i, "loi": ""})
            continue
        a, b = float(cs[0][0]), float(cs[-1][1])
        noi = []
        for s in segs:
            if float(s.get("start", 0)) >= a and float(s.get("end", 0)) <= b:
                noi.append(" ".join(str(s.get("text", "")).split()))
            if sum(len(x) for x in noi) > max_ky_tu:
                break
        ra.append({"index": i, "loi": " ".join(noi)[:max_ky_tu]})
    return ra


def cham_mu(clips: list, transcript: dict, complete_text) -> dict[int, dict]:
    """TRỌNG TÀI: 1 lượt LLM chấm MÙ từng clip theo `THANG`.

    `complete_text(prompt) -> str` truyền từ ngoài (dùng đúng bộ xoay key của
    app). Trả {index: {"score":float,"vi_sao":str}}; lỗi -> {} (caller giữ điểm
    cũ). Trọng tài KHÔNG biết clip nào điểm cao trước đó -> không bị mồi."""
    tt = _tom_tat_clip(clips, transcript)
    if not tt:
        return {}
    pr = ("Bạn là BIÊN TẬP KHÓ TÍNH của kênh video ngắn. Dưới đây là các đoạn "
          "ứng viên (chỉ có LỜI THOẠI). " + THANG +
          "\nTrả về DUY NHẤT JSON: "
          '[{"index":số,"score":0-100,"vi_sao":"1 câu ngắn tiếng Việt"}]\n\n' +
          "\n\n".join(f"[{d['index']}] {d['loi'] or '(không có thoại)'}"
                      for d in tt))
    # THỬ 2 LƯỢT: đo thật 06/08/2026 — lượt 1 có video trọng tài trả về không
    # đúng JSON nên rơi hết về điểm AI tự chấm (90/90/92) => chất lượng lọc
    # THẤT THƯỜNG giữa các video. Lượt 2 siết yêu cầu "CHỈ JSON".
    arr = None
    for _lan in (1, 2):
        try:
            raw = complete_text(pr if _lan == 1 else
                                pr + "\n\nCHÚ Ý: chỉ in DUY NHẤT mảng JSON, "
                                     "không thêm chữ nào khác, không markdown.")
            raw = raw or ""
        except Exception:  # noqa: BLE001
            continue
        m = re.search(r"\[.*\]", raw, re.S)
        if not m:
            continue
        try:
            arr = json.loads(m.group(0))
            break
        except (ValueError, TypeError):
            arr = None
    if arr is None:
        return {}
    ra = {}
    for r in arr if isinstance(arr, list) else []:
        try:
            _i = int(r["index"])
            if not (0 <= _i < len(clips)):     # index lạ -> bỏ, đừng để caller
                continue                       # ghi điểm vào clip không có thật
            ra[_i] = {"score": max(0.0, min(100.0, float(r["score"]))),
                      "vi_sao": str(r.get("vi_sao", ""))[:120]}
        except (KeyError, ValueError, TypeError):
            continue
    return ra
