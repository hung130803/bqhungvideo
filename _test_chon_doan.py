# -*- coding: utf-8 -*-
"""CỔNG 24 — AI NGHE + XEM + TRỌNG TÀI CHẤM MÙ khi chọn đoạn.

ĐO THẬT 06/08/2026 trên 3 video của anh Hùng (`_do_chon_doan.py`):
  · AI **TỰ CHẤM** cho 9/9 clip **85-95 điểm** -> sàn cứng 55 loại được **0**.
    Trọng tài chấm mù cùng bộ clip đó: **40-60**. => 2 THANG KHÁC ĐƠN VỊ, dùng
    sàn số cứng cho điểm trọng tài là loại oan 7/9 clip (mỗi video còn 1 Part).
  · Clip đầu của 1 video bắt đầu ở **0,6 giây** = ăn nguyên intro.
  · Trọng tài THẤT THƯỜNG: có lượt trả sai JSON -> rơi hết về điểm tự chấm.

BẤT BIẾN CANH Ở ĐÂY:
  1. Nghe: `nang_luong` ra list biên độ; `cua_so_cang` bắt đúng khoảng ồn hơn
     hẳn và KHÔNG bao giờ trả khoảng khi audio phẳng.
  2. Xem: `chuyen_dong` ra list điểm động; `cua_so_dong_khong_loi` CHỈ trả
     khoảng KHÔNG trùng lời nói (đoạn đánh nhau/rượt không ai nói).
  3. Sàn TỰ THÍCH ỨNG: 3 đoạn ngang điểm -> giữ đủ 3; 1 đoạn trội -> bỏ đoạn
     kém hơn hẳn; MỌI trường hợp giữ >= 1 clip (không bao giờ trắng tay).
  4. Lọc intro/outro: bỏ clip NẰM HẲN trong vùng đầu/cuối, KHÔNG cắt oan clip
     vắt qua; nếu bỏ hết thì trả nguyên trạng.
  5. Trọng tài: lỗi mạng / trả rác / JSON hỏng -> trả {} để caller GIỮ điểm cũ,
     tuyệt đối không ném lỗi ra ngoài; có thử lại lượt 2.
  6. Hook theo tiếng: mốc hook luôn NẰM TRONG segments của clip.
  7. Video không tiếng / không hình -> mọi hàm trả rỗng, không nổ.
"""
import os
import subprocess
import sys
import tempfile

T = tempfile.mkdtemp(prefix="chondoan_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
REPO = r"D:\claude\ai-content-studio"
sys.path.insert(0, REPO)
import _test_guard  # noqa: E402,F401

from app.ai import chon_doan as CD  # noqa: E402

FF = os.path.join(REPO, "bin", "ffmpeg.exe")
FAIL: list[str] = []


def kiem(ok, nhan, ct=""):
    print(("  ✓ " if ok else "  ✗ ") + nhan + ("" if ok else f"  << {ct}"))
    if not ok:
        FAIL.append(nhan)


def clip(a, b, score=50.0):
    return {"segments": [[a, b]], "score": score}


print("\n══ 1. NGHE: đo năng lượng + bắt khoảng ồn ══")
# video 20s: im 0-8s, TIẾNG TO 8-12s, im 12-20s
src = os.path.join(T, "a.mp4")
subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                "color=c=black:s=320x240:d=20", "-f", "lavfi", "-i",
                "sine=f=440:d=20", "-af",
                "volume=0.02:enable='lt(t,8)+gt(t,12)',volume=1.0:"
                "enable='between(t,8,12)'",
                "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
                "-shortest", src], capture_output=True)
nl = CD.nang_luong(src, FF)
kiem(len(nl) >= 15, f"đo được {len(nl)} cửa sổ 1 giây")
kh = CD.cua_so_cang(nl)
kiem(bool(kh), f"bắt được {len(kh)} khoảng ồn hơn hẳn")
if kh:
    a, b, gap = sorted(kh)[0]
    kiem(6.0 <= a <= 10.0 and gap > 1.5,
         f"khoảng ồn đúng chỗ 8-12s (ra {a:.0f}-{b:.0f}s, gấp {gap:.1f}×)")
kiem(CD.cua_so_cang([]) == [], "audio rỗng -> không nổ, trả rỗng")
kiem(CD.cua_so_cang([0.5] * 30) == [], "audio PHẲNG -> không bịa khoảng ồn")
kiem("ÂM THANH" in CD.khoi_prompt_nghe(kh, 20.0), "dựng được khối prompt NGHE")
kiem(CD.khoi_prompt_nghe([], 20.0) == "", "không có khoảng -> khối rỗng")
kiem(CD.nang_luong(os.path.join(T, "khong-co.mp4"), FF) == [],
     "file không tồn tại -> trả rỗng, không nổ")

print("\n══ 2. XEM: đo chuyển động + đoạn KHÔNG LỜI mà động mạnh ══")
# video 20s: 0-10s hình TĨNH, 10-20s hình ĐỘNG mạnh
src2 = os.path.join(T, "b.mp4")
subprocess.run([FF, "-y", "-v", "error",
                "-f", "lavfi", "-i", "color=c=navy:s=320x240:d=10",
                "-f", "lavfi", "-i", "testsrc2=s=320x240:r=25:d=10",
                "-filter_complex", "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]",
                "-c:v", "libx264", "-preset", "ultrafast", src2],
               capture_output=True)
cd = CD.chuyen_dong(src2, FF)
kiem(len(cd) >= 15, f"đo được {len(cd)} giây độ động")
if len(cd) >= 15:
    tinh = sum(cd[1:9]) / 8
    dong = sum(cd[11:19]) / 8
    kiem(dong > tinh * 2, f"phân biệt được TĨNH ({tinh:.3f}) vs ĐỘNG ({dong:.3f})")
tr_rong = {"segments": []}
kh2 = CD.cua_so_dong_khong_loi(cd, tr_rong, 20.0)
kiem(bool(kh2), f"bắt được {len(kh2)} khoảng động-không-lời")
# có lời nói phủ 10-20s -> KHÔNG được coi là 'không lời'
tr_co = {"segments": [{"start": 9.0, "end": 20.0, "text": "nói suốt"}]}
kiem(CD.cua_so_dong_khong_loi(cd, tr_co, 20.0) == [],
     "vùng ĐÃ CÓ LỜI NÓI -> không tính là đoạn không-lời")
kiem(CD.cua_so_dong_khong_loi([], tr_rong, 20.0) == [], "không hình -> rỗng")
kiem("HÌNH ẢNH" in CD.khoi_prompt_hanh_dong(kh2), "dựng được khối prompt XEM")

print("\n══ 3. SÀN TỰ THÍCH ỨNG (2 thang điểm khác đơn vị) ══")
giu, bo = CD.san_thich_ung([clip(0, 60, 60), clip(100, 160, 58),
                            clip(200, 260, 55)])
kiem(len(giu) == 3 and not bo, f"3 đoạn NGANG điểm -> giữ đủ 3 (ra {len(giu)})")
giu, bo = CD.san_thich_ung([clip(0, 60, 80), clip(100, 160, 30)])
kiem(len(giu) == 1 and len(bo) == 1, "1 đoạn trội -> bỏ đoạn kém hơn hẳn")
giu, bo = CD.san_thich_ung([clip(0, 60, 5), clip(100, 160, 4)])
kiem(len(giu) >= 1, "toàn đoạn dở -> vẫn giữ >= 1 (không trắng tay)")
kiem(CD.san_thich_ung([])[0] == [], "danh sách rỗng -> không nổ")
giu, _ = CD.san_thich_ung([clip(0, 60, 0), clip(1, 2, 0)])
kiem(len(giu) == 2, "điểm toàn 0 -> giữ nguyên (không lọc bừa)")

print("\n══ 3b. TUÂN THỦ SỐ PART USER ĐẶT (anh Hùng: đặt 3 thì phải ra 3) ══")
g, b = CD.san_thich_ung([clip(0, 60, 80), clip(100, 160, 45),
                         clip(200, 260, 40)], so_part=3)
kiem(len(g) == 3 and not b, f"đặt 3 part, điểm 80/45/40 -> ra ĐỦ 3 (ra {len(g)})")
g, b = CD.san_thich_ung([clip(0, 60, 50), clip(100, 160, 90),
                         clip(200, 260, 70), clip(300, 360, 60)], so_part=2)
kiem(len(g) == 2, f"đặt 2 part, có 4 ứng viên -> ra ĐÚNG 2 (ra {len(g)})")
kiem(sorted(float(c["score"]) for c in g) == [70.0, 90.0],
     "2 clip giữ lại là 2 clip ĐIỂM CAO NHẤT (90, 70)")
kiem(any("vượt số Part" in l for _c, l in b),
     "clip dư ghi rõ lý do 'vượt số Part'", str(b))
g, b = CD.san_thich_ung([clip(0, 60, 55)], so_part=3)
kiem(len(g) == 1, "video ngắn chỉ có 1 đoạn mà đặt 3 -> ra 1 (không nổ)")
g, b = CD.san_thich_ung([clip(0, 60, 70), clip(100, 160, 5)], so_part=3)
kiem(len(g) == 1 and len(b) == 1,
     "đoạn RÁC (5 điểm) vẫn bị bỏ dù chưa đủ số part")
g, _ = CD.san_thich_ung([clip(0, 60, 80), clip(100, 160, 40)])
kiem(len(g) == 1, "KHÔNG đặt số part -> vẫn lọc theo tương quan (như trước)")

print("\n══ 3c. VIDEO KHÔNG CÓ LỜI NÓI (ASMR — Whisper BỊA chữ) ══")
# ĐO THẬT 06/08/2026: 40s tiếng ồn thuần -> Groq trả "Thank you." + gán English
tr_bia = {"segments": [{"start": 0, "end": 30, "text": "Thank you."},
                       {"start": 30, "end": 40, "text": "."}],
          "words": [{"start": 0, "end": 1, "word": "Thank"},
                    {"start": 1, "end": 2, "word": "you"},
                    {"start": 30, "end": 30.2, "word": "."}]}
co, vs, mds = CD.co_loi_noi_that(tr_bia, 40.0)
kiem(not co, f"ca ASMR thật -> KHÔNG có lời nói ({mds:.2f} từ/giây)", vs[:50])
tr_that = {"segments": [{"start": 0, "end": 20,
                         "text": "she screamed at him and then walked away"}],
           "words": [{"start": i * 0.4, "end": i * 0.4 + 0.3, "word": f"w{i}"}
                     for i in range(48)]}
co2, _v2, mds2 = CD.co_loi_noi_that(tr_that, 20.0)
kiem(co2, f"người nói THẬT -> nhận đúng là CÓ lời ({mds2:.2f} từ/giây)")
kiem(not CD.co_loi_noi_that({"segments": [], "words": []}, 30.0)[0],
     "chép lời RỖNG -> không có lời nói")
kiem(not CD.co_loi_noi_that(
    {"segments": [{"start": 0, "end": 60,
                   "text": "Thanks for watching! Please subscribe"}],
     "words": [{"start": i, "end": i + 0.3, "word": "x"} for i in range(45)]},
    60.0)[0], "nội dung chỉ gồm câu Whisper hay BỊA -> không có lời nói")
kiem(CD.co_loi_noi_that(tr_that, 0.0)[0], "duration 0 -> coi như CÓ lời (an toàn)")

print("\n══ 4. LỌC INTRO / OUTRO ══")
giu, bo = CD.san_thich_ung([clip(0, 60, 70)])
giu2, bo2 = CD.loc_intro_outro([clip(1, 20), clip(300, 380), clip(980, 999)],
                               1000.0)
kiem(len(giu2) == 1 and len(bo2) == 2,
     f"bỏ clip trong intro + outro, giữ clip giữa (giữ {len(giu2)})")
kiem(all(l in ("nằm trong intro", "nằm trong outro") for _c, l in bo2),
     "lý do bỏ ghi rõ intro/outro")
g3, b3 = CD.loc_intro_outro([clip(10, 200)], 1000.0)
kiem(len(g3) == 1 and not b3, "clip VẮT QUA vùng đầu -> KHÔNG bị cắt oan")
g4, b4 = CD.loc_intro_outro([clip(1, 20)], 1000.0)
kiem(len(g4) == 1, "chỉ có 1 clip nằm trong intro -> vẫn giữ (đừng trắng tay)")
kiem(CD.loc_intro_outro([], 100.0)[0] == [], "rỗng -> không nổ")
kiem(CD.loc_intro_outro([clip(1, 2)], 0.0)[0] != [], "duration 0 -> giữ nguyên")

print("\n══ 5. TRỌNG TÀI: lỗi kiểu gì cũng KHÔNG được làm vỡ lượt cắt ══")
tr = {"segments": [{"start": 0, "end": 60, "text": "she screamed at him"},
                   {"start": 100, "end": 160, "text": "he explained the rules"}]}
cl = [clip(0, 60, 90), clip(100, 160, 92)]
kiem(CD.cham_mu(cl, tr, lambda p: '[{"index":0,"score":80,"vi_sao":"căng"},'
                                  '{"index":1,"score":30,"vi_sao":"nhạt"}]')
     == {0: {"score": 80.0, "vi_sao": "căng"},
         1: {"score": 30.0, "vi_sao": "nhạt"}}, "chấm đúng -> trả điểm mới")


def _no(_p):
    raise RuntimeError("mạng chết")


kiem(CD.cham_mu(cl, tr, _no) == {}, "LLM lỗi -> {} (caller giữ điểm cũ)")
kiem(CD.cham_mu(cl, tr, lambda p: "xin chào, không có json") == {},
     "trả rác không JSON -> {}")
kiem(CD.cham_mu(cl, tr, lambda p: "[{bad json") == {}, "JSON hỏng -> {}")
kiem(CD.cham_mu(cl, tr, lambda p: None) == {}, "trả None -> {}")
_dem = {"n": 0}


def _lan2(p):
    _dem["n"] += 1
    return "loạn" if _dem["n"] == 1 else '[{"index":0,"score":70}]'


kiem(CD.cham_mu(cl, tr, _lan2).get(0, {}).get("score") == 70.0,
     f"lượt 1 hỏng -> THỬ LẠI lượt 2 và ăn (gọi {_dem['n']} lượt)")
kiem(CD.cham_mu(cl, tr, lambda p: '[{"index":9,"score":50}]') == {},
     "index lạ -> bỏ qua, không nổ")
kiem(CD.cham_mu([], tr, lambda p: "[]") == {}, "không clip -> {}")

print("\n══ 6. HOOK theo tiếng luôn NẰM TRONG clip ══")
nl2 = [0.1] * 100
nl2[70:73] = [0.9, 0.95, 0.9]      # đỉnh ở giây 70-73
c = {"segments": [[40.0, 60.0], [65.0, 80.0]]}
hs = CD.hook_theo_tieng(c, nl2)
kiem(hs and 65.0 <= hs[0] and hs[1] <= 80.5,
     f"hook lấy đúng đỉnh trong đoạn 2: {hs}")
kiem(CD.hook_theo_tieng(c, []) is None, "không có audio -> None")
kiem(CD.hook_theo_tieng({"segments": []}, nl2) is None, "clip rỗng -> None")

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    sys.stdout.flush()
    os._exit(1)
print("KẾT QUẢ: TẤT CẢ ĐẠT — AI nghe/xem đúng, trọng tài không bao giờ làm vỡ "
      "lượt cắt, sàn không trắng tay")
sys.stdout.flush()
os._exit(0)
