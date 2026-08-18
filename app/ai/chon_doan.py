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


def _num_luong() -> list[str]:
    """Núm luồng cho 2 LỆNH ĐO dưới đây (`-threads` TRƯỚC `-i` = luồng GIẢI MÃ).

    LỖI THẬT tìm ra khi TỔNG RÀ SOÁT 08/08/2026: lượt e2e cả dây chuyền đo được
    **203 luồng ffmpeg (8,46× số nhân)**, phá mốc anh Hùng chốt là "≤ 2× nhân".
    Truy ra thủ phạm: `chuyen_dong` gọi `subprocess.run` TRẦN, không núm nào —
    **một mình nó 70 luồng (2,92× nhân)** và ngốn ~13,5 nhân suốt lúc chạy, cướp
    CPU của làn XUẤT đang chạy song song. (`hieu_ung.do_nhip` đã siết từ trước;
    `nang_luong` 24 luồng.) 2 lệnh này **CỐ Ý không qua cửa chờ ffmpeg** (lệnh
    ĐO mà xin chỗ sẽ tự khoá lẫn với lệnh xuất đang giữ chỗ) nên cửa chờ không
    cứu được — phải siết núm tại chỗ.

    SỐ ĐO A/B (`_ra_ab_chuyen_dong.py`, nguồn Nhật thật 653s/60fps/263 MB, máy
    24 nhân, **đan xen** 3 vòng — dãy số khít, không nhiễu):
        HIỆN TẠI (không núm) : 17,06s · **229,3 CPU-giây** · **70 luồng (2,92×)** ❌
        giải mã 4            : 28,60s · **102,2 CPU-giây** · 22 luồng (0,92×) ✅
        giải mã 2            : 47,83s ·  89,3 CPU-giây · 14 luồng (0,58×) ✅
        giải mã 1            : 80,71s ·  83,4 CPU-giây ·  9 luồng (0,38×) ✅
        GPU cuda + giải mã 4 : 52,92s ·  **30,0 CPU-giây** · 25 luồng (1,04×)

    VÌ SAO CHỌN 4 chứ không phải "cứ để nhanh": đây là bước THUẦN GIẢI MÃ nên
    siết luồng ĐẮT THẬT về wall (+66%) — khác hẳn đường xuất (nút cổ chai là
    NVENC nên siết luồng gần như miễn phí). Nhưng ở quy mô 200-300 kênh thì
    **CPU-giây mới là thứ khan hiếm**: 229 CPU-giây/video × 300 video/ngày =
    19 giờ-nhân/ngày chỉ để đo chuyển động; hạ còn 8,4 giờ-nhân. Và trong lúc
    nó ăn 13,5 nhân thì làn XUẤT chạy song song bị đói CPU. Mức 4 cũng đúng
    bằng mức `decode_threads()` đã đo là "mức cuối cùng còn miễn phí" cho đường
    xuất, nên hai đường nhất quán với nhau.

    VÌ SAO **KHÔNG** dùng thẳng `decode_threads()` (nó hạ về 2 khi ECO_MODE bật,
    mà ECO_MODE **mặc định BẬT**): đo lại cả pha phân tích trên nguồn Nhật
    6.394s cho thấy mức 2 làm `chuyen_dong` **82,4s -> 198,1s (2,4×)**, trong
    khi phần luồng tiết kiệm thêm là KHÔNG ĐÁNG (0,92× -> 0,58× số nhân — cả
    hai đều đã nằm gọn trong ngân sách 2×). ECO_MODE có lý ở đường XUẤT (nút cổ
    chai là NVENC nên siết luồng gần như miễn phí) nhưng ở bước THUẦN GIẢI MÃ
    này thì nó chỉ đổi rất nhiều thời gian lấy rất ít luồng. Nên mức ở đây tính
    theo SỐ NHÂN, chặn trần 4: máy 24 nhân -> 4; máy nhân viên 4 nhân -> 2;
    máy 2 nhân -> 1 (không bao giờ quá 1× số nhân).

    HƯỚNG RẺ HƠN NỮA, ĐÃ ĐO NHƯNG CHƯA DÙNG: `-hwaccel cuda` cho **30,0
    CPU-giây (−87%)** — máy anh Hùng GPU chỉ 11,3% nên gần như miễn phí. Chưa
    bật vì cần đường lùi cho máy nhân viên KHÔNG có NVIDIA (`d3d11va` đo ra
    **tệ hơn cả bản gốc**: 146,7s · 158,4 CPU-giây), tức phải thêm cửa dò +
    fallback — việc riêng, đừng gộp vào lượt này.
    """
    n = str(min(4, max(1, (os.cpu_count() or 4) // 2)))
    return ["-threads", n, "-filter_threads", n]
#: mốc "đoạn căng": to hơn trung bình bao nhiêu lần (theo biên độ, không phải dB)
NGUONG_CANG = 1.6


def nang_luong(src: str, ffmpeg: str, tong_giay: float = 0.0) -> list[float]:
    """Đo mức âm THEO TỪNG GIÂY của video -> list biên độ RMS (0..1).

    Dùng `astats` metadata mỗi cửa sổ; 1 lần chạy ffmpeg cho cả video, không
    giải mã hình (`-vn`) nên rẻ. Lỗi -> [] (caller tự bỏ qua phần 'nghe')."""
    try:
        r = subprocess.run(
            [ffmpeg, "-hide_banner", "-nostats", *_num_luong(), "-i", src, "-vn",
             "-af", f"aresample=16000,asetnsamples=n={int(16000 * CUA_SO)},"
                    f"astats=metadata=1:reset=1,"
                    f"ametadata=print:key=lavfi.astats.Overall.RMS_level:"
                    f"file=-",
             "-f", "null", os.devnull],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
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
            [ffmpeg, "-hide_banner", "-nostats", *_num_luong(), "-i", src, "-an",
             "-vf", f"fps={fps},scale=160:-2,format=gray,"
                    f"tblend=all_mode=difference,signalstats,"
                    f"metadata=print:key=lavfi.signalstats.YAVG:file=-",
             "-f", "null", os.devnull],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
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


def _giay_trung(a_segs: list, b_segs: list) -> float:
    """Tổng số GIÂY mà 2 clip dùng CHUNG cùng một đoạn phim gốc. Hàm thuần."""
    tong = 0.0
    for a in a_segs or []:
        try:
            a0, a1 = float(a[0]), float(a[1])
        except (IndexError, TypeError, ValueError):
            continue
        for b in b_segs or []:
            try:
                b0, b1 = float(b[0]), float(b[1])
            except (IndexError, TypeError, ValueError):
                continue
            tong += max(0.0, min(a1, b1) - max(a0, b0))
    return tong


def bo_trung_nhau(clips: list, ty_le: float = 0.15) -> tuple:
    """BỎ clip TRÙNG ĐOẠN với clip ĐIỂM CAO HƠN. Trả (giữ, [(clip, lý do)]).

    LỖI THẬT (chính bộ đo `_do_chon_doan.py` của tôi phơi ra, anh Hùng 07/08/2026
    yêu cầu "cắt ghép các đoạn hợp lý với nhau nhưng k được trùng"): 1 video ra
    Part1 `173,0-259,9s` và Part2 `244,6-315,8s` -> **DÙNG CHUNG 15,3 GIÂY**.
    Người xem 2 Part liền nhau sẽ thấy y hệt một đoạn -> mất uy tín kênh.
    Vì sao lọt: chốt khử trùng cũ (`_dedupe_windows`) CHỈ áp cho cửa sổ ứng viên
    heuristic, mà còn cho phép trùng tới 55%; clip do AI chọn thì KHÔNG ai kiểm
    trùng lẫn nhau — chỉ có `used_ranges` chống trùng với LẦN CHẠY TRƯỚC.

    So theo TỪNG ĐOẠN (không phải khoảng đầu-cuối): clip ghép nhiều đoạn có thể
    trải rộng nhưng thực ra không chồng nhau. Giữ clip ĐIỂM CAO, bỏ clip điểm
    thấp nếu phần dùng chung > `ty_le` × độ dài clip NGẮN HƠN. Hàm thuần."""
    if not clips:
        return [], []

    def _dai(c):
        """Tổng độ dài THẬT của clip (cộng từng đoạn). Đoạn rác -> bỏ qua chứ
        KHÔNG nổ: dữ liệu tới đây từ JSON của AI nên phải chịu được mọi thứ."""
        t = 0.0
        for s in (c.get("segments") or []):
            if not isinstance(s, (list, tuple)) or len(s) < 2:
                continue
            try:
                t += max(0.0, float(s[1]) - float(s[0]))
            except (TypeError, ValueError):
                continue
        return t

    thu_tu = sorted(range(len(clips)),
                    key=lambda i: -float(clips[i].get("score", 0) or 0))
    giu_i: list = []
    bo: list = []
    for i in thu_tu:
        c = clips[i]
        cs, cd = c.get("segments") or [], _dai(c)
        va = None
        for j in giu_i:
            d = clips[j]
            tr = _giay_trung(cs, d.get("segments") or [])
            ngan = min(cd, _dai(d)) or 1.0
            if tr > ty_le * ngan:
                va = (tr, d, tr / ngan)
                break
        if va is None:
            giu_i.append(i)
        else:
            bo.append((c, f"trùng {va[0]:.0f}s ({va[2]*100:.0f}%) với clip "
                          f"«{str(va[1].get('title') or '')[:40]}» điểm cao hơn"))
    giu_i.sort()                     # trả lại THỨ TỰ THỜI GIAN như đầu vào
    return [clips[i] for i in giu_i], bo


def khoi_prompt_gu(gu: dict, max_chars: int = 900) -> str:
    """Khối "GU CHỦ KÊNH" cho prompt chọn đoạn, dựng từ 👍/👎 anh Hùng đã bấm.

    Vì sao (anh Hùng 06/08/2026: "nhiều đoạn nó lấy hài quá không cần thiết"):
    thang điểm chung mãi cho ra gu chung. Ví dụ THẬT của chính kênh đó là cách
    rẻ nhất để AI hiểu "hay" theo nghĩa của anh — không tốn thêm lượt API, chỉ
    dài prompt vài dòng.

    KHÔNG có đánh giá nào -> trả "" (prompt Y HỆT cũ, không đổi hành vi gì).
    Hàm thuần — unit test được."""
    if not isinstance(gu, dict):
        return ""
    th = [d for d in (gu.get("thich") or []) if isinstance(d, dict)]
    kh = [d for d in (gu.get("khong") or []) if isinstance(d, dict)]
    if not th and not kh:
        return ""

    def _dong(d: dict) -> str:
        t = " ".join(str(d.get("title") or "").split())[:80]
        m = " ".join(str(d.get("thoai") or "").split())[:90]
        dai = float(d.get("dai") or 0)
        ns = int(d.get("n_seg") or 0)
        p = f'  - "{t or "(không tiêu đề)"}"'
        if dai > 0:
            p += f" ({dai:.0f}s, {ns} đoạn)" if ns else f" ({dai:.0f}s)"
        if m:
            p += f" — {m}"
        return p

    out = ("\n\nGU CỦA CHỦ KÊNH (chính chủ đã tự tay đánh giá clip cũ của kênh "
           "NÀY — đây là tiêu chuẩn CAO NHẤT, quan trọng hơn cảm nhận chung "
           "của bạn):")
    if th:
        out += "\n✓ CHỦ KÊNH THÍCH kiểu đoạn như thế này — hãy tìm đoạn tương tự:"
        for d in th:
            out += "\n" + _dong(d)
    if kh:
        out += ("\n✗ CHỦ KÊNH KHÔNG THÍCH kiểu đoạn như thế này — TRÁNH, dù bạn "
                "thấy nó hay:")
        for d in kh:
            out += "\n" + _dong(d)
    return out[:max_chars]


#: câu Whisper HAY BỊA khi không có lời nói (các ngôn ngữ hay gặp)
RAC_BIA = (
    "thank you", "thanks for watching", "subscribe", "subtitles by",
    "amara.org", "please subscribe", "bye bye", "music", "applause",
    "字幕", "ご視聴", "チャンネル登録", "감사합니다", "구독",
    "cảm ơn", "đăng ký kênh", "phụ đề",
)


def co_loi_noi_that(transcript: dict, tong_giay: float,
                    tu_moi_giay: float = 0.5) -> tuple[bool, str, float]:
    """Video này CÓ LỜI NÓI THẬT không? -> (có/không, lý do, số từ mỗi giây).

    VÌ SAO (anh Hùng 06/08/2026: "video ASMR không nói gì mà nó tự phân tích ra
    tiếng gì, ngôn ngữ nào lạ, mô tả thì linh tinh"). ĐO THẬT: cho Groq nghe 40
    giây TIẾNG ỒN THUẦN -> trả về **"Thank you."** + gán ngôn ngữ **English**.
    Đây là lỗi kinh điển của Whisper: gặp im lặng/nhạc/tiếng động là BỊA CHỮ.
    Chữ bịa chảy tiếp vào: chọn đoạn · tiêu đề · hashtag · và ĐỐT LÊN VIDEO
    thành phụ đề rác.

    Nhận diện rẻ (không thêm lượt API): MẬT ĐỘ TỪ. Người nói thật ~2-3 từ/giây;
    ví dụ trên chỉ **0,075 từ/giây**. KHÔNG dùng "tổng thời lượng từ" vì mốc câu
    bịa trải rộng 30 giây nên trông như 38,9% có lời (sai hoàn toàn)."""
    segs = (transcript or {}).get("segments") or []
    words = (transcript or {}).get("words") or []
    if tong_giay <= 0:
        return True, "", 0.0
    mds = (len(words) / tong_giay) if words else 0.0
    chu = " ".join(str(s.get("text", "")) for s in segs).lower()
    sach = "".join(c if (c.isalnum() or c.isspace()) else " " for c in chu)
    sach = " ".join(sach.split())
    if not sach:
        return False, "chép lời RỖNG (không có chữ nào)", mds
    if mds < tu_moi_giay:
        return False, (f"mật độ từ chỉ {mds:.2f} từ/giây (người nói thật ~2-3) "
                       f"-> gần như chắc chắn KHÔNG có lời nói"), mds
    con = sach
    for r in RAC_BIA:
        con = con.replace(r, " ")
    # ĐẾM TỪ PHẢI CJK-AWARE — LỖI THẬT tìm được 08/08/2026 khi làm cổng 40.
    # `.split()` coi CẢ CÂU Nhật/Trung là 1 "từ" (không có dấu cách), nên video
    # Nhật có ÍT ĐOẠN (short 8-60s: whisper trả 1-2 đoạn) ra 1-2 token, rơi
    # thẳng vào ngưỡng `max(2, ...)` -> bị gán nhầm "chỉ gồm câu Whisper bịa".
    # Hậu quả trong app: `_khong_loi=True` -> BỎ transcript khỏi việc chọn đoạn,
    # ép đi đường XEM HÌNH (~3-4 phút/video) và **KHÔNG đốt phụ đề** -> clip
    # Nhật ngắn ra không có chữ. Đo trước khi sửa (mật độ 2,00 từ/giây = nói
    # rõ ràng): Nhật 1 đoạn -> False · Nhật 2 đoạn -> False · Trung 1 đoạn ->
    # False; trong khi Anh/Việt/Hàn 1 đoạn -> True. BẤT BIẾN: `_word_tokens`
    # trả Y HỆT `.split()` khi text không có ký tự CJK -> đường EN/VI/KO không
    # đổi một chút nào.
    from app.ai.recap import _word_tokens as _wt
    if len(_wt(con)) <= max(2, len(_wt(sach)) // 10):
        return False, "nội dung chỉ gồm câu Whisper hay bịa (thank you/…)", mds
    return True, "", mds


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


#: 3 GÓC NHÌN cho hội đồng trọng tài — mỗi ông chấm 1 kiểu khác nhau, lấy
#: TRUNG VỊ. Vì sao: 1 trọng tài duy nhất có video trả sai định dạng / chấm lệch
#: (đo 06/08/2026: cùng bộ clip, lượt này 42/50/60, lượt sau 90/90/92 do parse
#: hỏng). 3 góc nhìn + trung vị thì 1 ông lệch KHÔNG kéo được kết quả.
GOC_NHIN = (
    ("người xem lần đầu",
     "Bạn là NGƯỜI XEM BÌNH THƯỜNG đang lướt, chưa biết gì về video này."),
    ("biên tập khó tính",
     "Bạn là BIÊN TẬP KHÓ TÍNH của kênh video ngắn, đã xem hàng nghìn clip."),
    ("người chỉ xem 3 giây đầu",
     "Bạn CHỈ xem 3 GIÂY ĐẦU rồi quyết định lướt hay ở lại. Chấm gần như hoàn "
     "toàn theo sức níu của mở đầu."),
)


def _trung_vi(xs: list) -> float:
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return 0.0
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def cham_hoi_dong(clips: list, transcript: dict, complete_text,
                  model: str = "") -> dict[int, dict]:
    """HỘI ĐỒNG 3 TRỌNG TÀI chấm mù, lấy TRUNG VỊ điểm.

    `model`: tên model đè (dùng model BIẾT SUY LUẬN cho khâu chấm — prompt chấm
    NGẮN nên không bị lỗi 413 như prompt chọn đoạn; xem ghi chú `config.py` về
    gpt-oss-120b). Rỗng -> model mặc định.

    Ông nào lỗi/parse hỏng thì BỎ phiếu ông đó; còn >=1 phiếu vẫn ra kết quả;
    không ông nào trả được -> {} để caller giữ điểm cũ (không bao giờ vỡ)."""
    phieu: dict[int, list] = {}
    ly_do: dict[int, str] = {}
    for ten, vai in GOC_NHIN:
        r = cham_mu(clips, transcript, complete_text, vai_tro=vai, model=model)
        for i, v in r.items():
            phieu.setdefault(i, []).append(float(v["score"]))
            if v.get("vi_sao") and i not in ly_do:
                ly_do[i] = v["vi_sao"]
    if not phieu:
        return {}
    return {i: {"score": round(_trung_vi(ds), 1),
                "vi_sao": ly_do.get(i, ""),
                "so_phieu": len(ds)}
            for i, ds in phieu.items()}


def cham_mu(clips: list, transcript: dict, complete_text,
            vai_tro: str = "", model: str = "") -> dict[int, dict]:
    """TRỌNG TÀI: 1 lượt LLM chấm MÙ từng clip theo `THANG`.

    `complete_text(prompt) -> str` truyền từ ngoài (dùng đúng bộ xoay key của
    app). Trả {index: {"score":float,"vi_sao":str}}; lỗi -> {} (caller giữ điểm
    cũ). Trọng tài KHÔNG biết clip nào điểm cao trước đó -> không bị mồi."""
    tt = _tom_tat_clip(clips, transcript)
    if not tt:
        return {}
    pr = ((vai_tro or "Bạn là BIÊN TẬP KHÓ TÍNH của kênh video ngắn.")
          + " Dưới đây là các đoạn ứng viên (chỉ có LỜI THOẠI). " + THANG +
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
            _p2 = (pr if _lan == 1 else
                   pr + "\n\nCHÚ Ý: chỉ in DUY NHẤT mảng JSON, không thêm chữ "
                        "nào khác, không markdown.")
            # `model`: dùng model BIẾT SUY LUẬN cho khâu CHẤM (prompt chấm NGẮN
            # nên không bị lỗi 413 như prompt chọn đoạn — xem config.py).
            raw = (complete_text(_p2, model=model) if model
                   else complete_text(_p2)) or ""
        except Exception:  # noqa: BLE001
            continue
        # BỎ khối <think> TRƯỚC khi dò dấu ngoặc: model suy luận nháp đầy
        # '[' ']' nên regex dưới bắt nhầm bản nháp (đo 06/08/2026: chấm bằng
        # qwen3.6 hỏng parse 3/3 lượt dù model trả lời đúng).
        try:
            from app.ai.llm import bo_khoi_suy_nghi as _bks
            raw = _bks(raw)
        except Exception:  # noqa: BLE001 - không có hàm thì cứ parse như cũ
            pass
        m = re.search(r"\[.*\]", raw, re.S)
        if m:
            try:
                arr = json.loads(m.group(0))
                break
            except (ValueError, TypeError):
                arr = None
        # BỘ BÓC BAO DUNG (v2.35.0): khối markdown · chữ dẫn thừa · dấu phẩy
        # thừa · **JSON ĐỨT CUỐI vì model hết chỗ token**. Regex trên đòi có
        # dấu `]` ĐÓNG nên câu trả lời bị cắt là nó không khớp gì cả -> mất
        # trắng cả bảng chấm (rơi hết về điểm AI tự chấm). Đặt SAU đường cũ
        # nên JSON hợp lệ vẫn ra kết quả y hệt.
        try:
            from app.ai.llm import boc_json as _bj
            d = _bj(raw)
            if isinstance(d, list) and d:
                arr = d
                break
        except Exception:  # noqa: BLE001
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
