# -*- coding: utf-8 -*-
r"""CỔNG 48 — LỚP PHỦ ĐOÁN CẢNH BẰNG **LỜI THOẠI** (và không được đoán bừa).

    .venv\Scripts\python _test_lop_phu_loi.py

VÌ SAO CÓ (anh Hùng 09/08/2026): anh cắt clip trên v2.20.0 và **không thấy
tuyết/trái tim nào**. Nhật ký `logs/lop_phu_*.log` ghi *"không có vision_digest
cho clip này -> bỏ qua nhóm lớp phủ"*. Đúng thiết kế (không đoán bừa) nhưng
`VISION_CUT` mặc định TẮT (đo 219 giây/video) nên **46 kiểu lớp phủ gần như
không bao giờ xuất hiện**. Nay có đường thứ hai: đoán cảnh bằng **CHÉP LỜI** —
thứ mọi video đều có sẵn, 0 giây thêm, 0 lượt LLM thêm.

Đường này đọc **CHỮ** nên dính bẫy nặng hơn đường xem hình. Cổng kiểm KẾT QUẢ:

  CA 1  **BẪY BỎ DẤU** — 16 câu, KHÔNG câu nào được kích hoạt cảnh sai. Bắt
        buộc có ca *"video nói **tuyệt vời** KHÔNG được rơi tuyết"*. 9/16 ca là
        bẫy ĐO ĐƯỢC trên lời thật (`_do_lop_phu_loi.py`), 4 ca là bẫy CJK.
  CA 2  **KHÔNG SỬA QUÁ TAY** — 13 câu ĐÚNG NGHĨA (Nhật · Hàn · Anh · Việt)
        vẫn phải khớp. Cổng chỉ chặn thì viết `return []` là xong.
  CA 3  **CHỐT CHẶN GIỮ NGUYÊN**: `NGUONG_TIN` = 0,55 · nhóm PHỤ một mình trần
        0,52 (không bao giờ tự kích hoạt) · không khớp -> KHÔNG THÊM.
  CA 4  **XUẤT THẬT BẰNG ffmpeg** — file ra có/không lớp phủ, đếm điểm ảnh.
        Đây là ca duy nhất trả lời được "anh Hùng có thấy tuyết không".
  CA 5  **XEM HÌNH VẪN ƯU TIÊN** khi có digest.
  CA 6  **KHÔNG ĐẾM MỘT BẰNG CHỨNG HAI LẦN**: 1 câu nhắc tới cảnh -> CHƯA đủ.
  CA 7  **TIỀN ĐỊNH** + bất biến video KHÔNG LỜI đi y đường cũ.
  CA 8  **QUÉT TĨNH** bảng `_DAU_VN` (mọi dạng có dấu phải bỏ dấu ra ĐÚNG khoá)
        + `digest_tu_loi` phải gắn cờ `loi` + `_dem_tu` KHÔNG được bỏ dấu.

BẪY KHI VIẾT CỔNG NÀY (ghi lại để đừng lặp): nguồn `testsrc2` mặc định có sẵn
vạch màu, nên "bản có lớp phủ" và "bản không" luôn lệch vài phần trăm do NÉN.
Ngưỡng phải đặt theo số đo thật của cổng 46 (thấy được 8,16-36,12%), và bản
KHÔNG lớp phủ phải ra dưới 3% — khoảng cách đó mới là kết luận được.
"""
from __future__ import annotations

import inspect
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.gettempdir()) / f"test_lp_loi_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
os.environ.setdefault("BQ_TEST", "1")

import _test_guard  # noqa: E402,F401  (cổng 17: test KHÔNG được đụng máy user)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from app.core import hieu_ung as HU          # noqa: E402
from app.core import lop_phu as LP           # noqa: E402
from config import settings                  # noqa: E402

_NOWIN = 0x08000000 if os.name == "nt" else 0
FF, FP = settings.FFMPEG_PATH, settings.FFPROBE_PATH
_LOI: list[str] = []
_OK: list[str] = []


def bao(ten: str, ok: bool, so: str = "") -> None:
    (_OK if ok else _LOI).append(ten)
    print(f"  [{'OK ' if ok else 'FAIL'}] {ten}" + (f": {so}" if so else ""))


def _esc(p: str) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:")


def chay(cmd: list, tmo: int = 600) -> tuple:
    r = subprocess.run(cmd, capture_output=True, timeout=tmo,
                       creationflags=_NOWIN)
    return r.returncode, (r.stderr or b"").decode("utf-8", "replace")


def _tr(cau: list, buoc: float = 3.0) -> dict:
    """Bản chép lời giả lập: mỗi câu `buoc` giây, CÓ MỐC (bắt buộc)."""
    return {"segments": [{"start": i * buoc, "end": i * buoc + buoc - 0.1,
                          "text": t} for i, t in enumerate(cau)]}


# ══════════════════════════════════════════════════════════ CA 1: BẪY BỎ DẤU
#: (câu, cảnh KHÔNG được kích hoạt, ý nghĩa thật của từ khoá bị đụng)
BAY = [
    # 3 ca anh Hùng nêu đích danh — BẮT BUỘC PHẢI CÓ
    ("Tuyệt vời quá đi mất, tuyệt vời luôn", "tuyet_roi", "tuyết / tuyệt vời"),
    ("Mùa đông năm nay đến sớm, mùa đông lạnh", "mua_roi", "mưa / mùa đông"),
    ("Màu sắc rất đẹp, màu sắc hài hoà", "trai_tim", "máu / màu sắc"),
    # 9 bẫy ĐO ĐƯỢC trên lời thật (`_do_lop_phu_loi.py` 09/08/2026)
    ("Thế là rồi xong, vậy là rồi nhé", "la_roi", "lá rơi / là rồi"),
    ("Rất tiếc phải nói, thật đáng tiếc", "confetti", "tiệc / tiếc"),
    ("Anh cứ làm đi, anh cứ tự nhiên", "tia_sang", "ảnh cũ / anh cứ"),
    ("Anh nên nghỉ ngơi, anh nên đi khám", "dom_bokeh", "ánh nến / anh nên"),
    ("Nằm mơ thấy lạ lắm, nằm mơ suốt", "mua_roi", "nấm mồ / nằm mơ"),
    ("Có đâu mà lo, làm gì có đâu", "trai_tim", "cô dâu / có đâu"),
    ("Lịch sự lắm, ăn nói lịch sự", "bui_phim", "lịch sử / lịch sự"),
    ("Trời lạnh mà ấm áp, mà ấm lắm", "ma_quai", "ma ám / mà ấm"),
    ("Có điện rồi, nhà có điện chưa", "tia_sang", "cổ điển / có điện"),
    # 4 bẫy CJK — không có dấu cách nên từ ngắn khớp trong từ dài
    ("火曜日に行きます。火曜日ですよ", "tan_lua", "火 / 火曜日 (thứ Ba)"),
    ("그건 불가능하고 불편해요. 불편합니다", "tan_lua", "불 / 불편 (bất tiện)"),
    ("눈이 아파요. 눈이 너무 아파", "tuyet_roi", "눈 = tuyết VÀ mắt"),
    ("가격 비교를 해봤어요. 비교해보니", "mua_roi", "비 = mưa VÀ so sánh"),
]

#: (câu, cảnh PHẢI nhận ra) — chống sửa quá tay
THAT = [
    ("外は大雪が降っています", "tuyet_roi"), ("吹雪で電車が止まった", "tuyet_roi"),
    ("今日は結婚式で花嫁がとても綺麗", "trai_tim"),
    ("誕生日ケーキとパーティーの準備", "confetti"),
    ("눈보라가 심해서 스키장에 못 갔어요", "tuyet_roi"),
    ("오늘 결혼식 신부가 정말 예뻐요", "trai_tim"),
    ("생일 케이크 파티 축하합니다", "confetti"),
    ("It was snowing hard, a real blizzard", "tuyet_roi"),
    ("The bride and groom kissed at the wedding", "trai_tim"),
    ("ngoài trời tuyết rơi trắng xoá", "tuyet_roi"),
    ("hôm nay là đám cưới của cô dâu", "trai_tim"),
    ("chúc mừng sinh nhật, bánh kem đây", "confetti"),
    ("lá vàng rơi đầy sân mùa thu", "la_roi"),
]


def _khop_manh(cau: str, canh: str) -> list:
    """Từ khoá MẠNH khớp câu, dò đúng như đường LỜI THOẠI (text CÒN DẤU)."""
    l = LP.LUAT[canh]
    t = LP._ha(cau)
    return [tu for rs, tu in zip(l._rd_manh, l.manh)
            if any(x.search(t) for x in rs)]


def ca1_bay() -> None:
    print("\n[CA 1] BẪY BỎ DẤU / CJK — không câu nào được kích hoạt cảnh sai")
    n_kw = n_bat = 0
    for cau, canh, y in BAY:
        kw = _khop_manh(cau, canh)
        n_kw += bool(kw)
        # và tới tận ĐẦU RA: dựng mốc từ chính câu đó rồi hỏi có lớp phủ không
        r, _ly = LP.chon_lop_phu(LP.digest_tu_loi(_tr([cau, cau]),
                                                  [(0.0, 30.0)]), "", 30.0)
        n_bat += bool(r)
    bao("16/16 câu bẫy KHÔNG khớp từ khoá mạnh của cảnh sai",
        n_kw == 0, f"{n_kw} câu còn khớp nhầm")
    bao("16/16 câu bẫy KHÔNG sinh ra lớp phủ nào ở ĐẦU RA",
        n_bat == 0, f"{n_bat} câu vẫn ra lớp phủ")
    # in riêng ca BẮT BUỘC để người đọc thấy tận mắt
    cau = BAY[0][0]
    r, ly = LP.chon_lop_phu(LP.digest_tu_loi(_tr([cau, cau]), [(0.0, 30.0)]),
                            "", 30.0)
    bao('CA BẮT BUỘC: video nói "TUYỆT VỜI" KHÔNG được rơi tuyết',
        not r, ly[:88])
    # ĐỐI CHỨNG BỘ DÒ: bảng BỎ DẤU (bản cũ) phải KÊU ở đúng những ca đó — nếu
    # không thì cổng này chỉ là con dấu, không chứng minh được đã chữa gì.
    cu = 0
    for cau, canh, _y in BAY:
        l = LP.LUAT[canh]
        t = LP._khong_dau(cau)
        if any(r.search(t) for r in l._re_manh):
            cu += 1
    bao("ĐỐI CHỨNG: bảng BỎ DẤU (cách cũ) VẪN nhầm — bộ dò có thật sự làm gì",
        cu >= 8, f"cách cũ nhầm {cu}/16 · cách nay 0/16")


def ca2_khong_qua_tay() -> None:
    print("\n[CA 2] KHÔNG SỬA QUÁ TAY — câu đúng nghĩa vẫn phải nhận ra")
    mat = [f"{c[:28]}->{k}" for c, k in THAT if not _khop_manh(c, k)]
    bao("13/13 câu đúng nghĩa (Nhật·Hàn·Anh·Việt) vẫn khớp từ khoá mạnh",
        not mat, "; ".join(mat) or "0 câu mất")
    # tới ĐẦU RA: 2 câu cùng cảnh -> phải RA lớp phủ đúng cảnh đó
    ra = []
    for canh, cs in (("tuyet_roi", ["外は大雪が降っています", "吹雪で電車が止まった"]),
                     ("tuyet_roi", ["눈보라가 심해서 스키장에 못 갔어요",
                                    "함박눈이 내렸어요"]),
                     ("trai_tim", ["hôm nay là đám cưới của cô dâu",
                                   "cô dâu chú rể hôn nhau"]),
                     ("confetti", ["The birthday cake is here",
                                   "a big party celebration tonight"])):
        r, ly = LP.chon_lop_phu(LP.digest_tu_loi(_tr(cs), [(0.0, 30.0)]), "",
                                30.0)
        ok = bool(r) and r[0]["canh"] == canh
        ra.append(ok)
        print(f"        {'✓' if ok else '✗'} {canh:10s} <- {cs[0][:34]} … "
              f"{(r[0]['khoa'] if r else ly)[:46]}")
    bao("4/4 nhóm ngôn ngữ: 2 câu đúng cảnh -> RA lớp phủ đúng cảnh",
        all(ra), f"{sum(ra)}/4")


def ca3_chot_chan() -> None:
    print("\n[CA 3] CHỐT CHẶN GIỮ NGUYÊN (không được nới để lớp phủ hay hiện)")
    bao("NGUONG_TIN vẫn = 0,55", abs(LP.NGUONG_TIN - 0.55) < 1e-9,
        str(LP.NGUONG_TIN))
    bao("CACH_BIET vẫn = 0,12", abs(LP.CACH_BIET - 0.12) < 1e-9,
        str(LP.CACH_BIET))
    bao("LOP_PHU_MAX vẫn = 1", LP.LOP_PHU_MAX == 1, str(LP.LOP_PHU_MAX))
    # nhóm PHỤ một mình: 5 câu toàn từ BỐI CẢNH -> trần 0,52 < 0,55, KHÔNG bật
    phu = ["trời rất lạnh", "mùa đông tới rồi", "phải quàng khăn quàng",
           "đeo găng tay vào", "gió lạnh quá"]
    r, ly = LP.chon_lop_phu(LP.digest_tu_loi(_tr(phu), [(0.0, 30.0)]), "", 30.0)
    bao("nhóm từ khoá PHỤ một mình KHÔNG BAO GIỜ tự kích hoạt được",
        not r, ly[:96])
    # đo đúng con số trần 0,52
    l = LP.LUAT["tuyet_roi"]
    d = LP._diem(l, LP.digest_tu_loi(_tr(phu * 3), [(0.0, 60.0)]), "")
    bao("trần riêng của nhóm PHỤ đo được <= 0,52",
        d is not None and d["tin"] <= 0.52 + 1e-9,
        f"{d['tin']:.4f} (dm={d['dm']} dp={d['dp']})" if d else "None")
    # danh sách CẤM vẫn chặn: nói tuyết trong video NẤU ĂN
    r2, ly2 = LP.chon_lop_phu(
        LP.digest_tu_loi(_tr(["ngoài trời tuyết rơi trắng xoá",
                              "tuyết rơi dày lắm",
                              "giờ mình vào căn bếp nấu ăn thôi"]),
                         [(0.0, 30.0)]), "", 30.0)
    bao("từ khoá CẤM vẫn loại thẳng: nói tuyết trong video NẤU ĂN -> không thêm",
        not r2, ly2[:96])
    # nội dung KHÔNG dính cảnh nào -> không thêm
    r3, ly3 = LP.chon_lop_phu(
        LP.digest_tu_loi(_tr(["hôm nay mình sẽ nói về cách quản lý thời gian",
                              "các bạn nhớ ghi chép lại nhé"]),
                         [(0.0, 30.0)]), "", 30.0)
    bao("nội dung không dính cảnh nào -> KHÔNG thêm gì", not r3, ly3[:80])


def ca4_xuat_that(src: str, td: str) -> None:
    """ĐO TRÊN FILE XUẤT THẬT — câu trả lời cho 'anh Hùng có thấy tuyết không'."""
    print("\n[CA 4] XUẤT THẬT BẰNG ffmpeg — lớp phủ CÓ THẬT trong file hay không")
    from app.core.ffmpeg_utils import export_canvas_clip
    TUYET = ["ngoài trời tuyết rơi trắng xoá", "tuyết rơi dày lắm luôn"]
    TUYETVOI = ["tuyệt vời quá đi mất", "tuyệt vời luôn ấy"]

    # ĐỘ DÀI CLIP KHÔNG ĐƯỢC NGẮN: lớp phủ ăn chung ngân sách `TY_LE_MAX` 10%
    # thời lượng, mà kiểu ngắn nhất cũng `DAI_MIN` ~0,8 s -> clip 2,6 s chỉ có
    # 0,26 s ngân sách và MỌI lớp phủ đều bị "nhường hiệu ứng điểm nhấn".
    # Bản đầu của cổng này đo ra 0,00% ở CẢ HAI ca vì thế (suýt kết luận oan là
    # đường lời không chạy). 10 s -> ngân sách 1,0 s, vừa đủ, vẫn trong LUẬT 1.
    DAI = 10.0

    def xuat(ten: str, cau) -> str:
        dst = os.path.join(td, ten)
        # câu ở giây 1 và 3 — PHẢI nằm trong đoạn cắt, nếu không `digest_tu_loi`
        # bỏ đúng như luật "không lấy bằng chứng của chỗ khác".
        nd = {"digest": [], "loi": "",
              "transcript": {"segments": [
                  {"start": 1.0 + 2.0 * i, "end": 2.5 + 2.0 * i, "text": t}
                  for i, t in enumerate(cau)]}} if cau else None
        export_canvas_clip(src, dst, [(0.0, DAI)], (0.5, 0.5, 1.0),
                           bg="blur", out_w=540, out_h=960, encoder="libx264",
                           hieu_ung="vua", noi_dung=nd, fx_whoosh=False,
                           chuyen_canh="tat")
        return dst

    a = xuat("nen.mp4", None)             # KHÔNG nội dung -> chắc chắn 0 lớp phủ
    b = xuat("tuyet.mp4", TUYET)          # 2 câu tuyết  -> PHẢI có lớp phủ
    c = xuat("tuyetvoi.mp4", TUYETVOI)    # 2 câu "tuyệt vời" -> KHÔNG được có

    def khac(x: str, y: str) -> float:
        """% điểm ảnh |dY| > 12 giữa 2 file (thước của cổng 46)."""
        fo = os.path.join(td, "d.txt")
        rc, err = chay([FF, "-v", "error", "-i", x, "-i", y,
                        "-filter_complex",
                        "[0:v][1:v]blend=all_mode=difference,"
                        "lutyuv=y='if(gt(val,12),255,0)',signalstats,"
                        f"metadata=print:key=lavfi.signalstats.YAVG:"
                        f"file='{_esc(fo)}'[o]",
                        "-map", "[o]", "-f", "null", "-"])
        if rc != 0 or not os.path.exists(fo):
            return -1.0
        vs = [float(m.group(1)) for ln in
              open(fo, encoding="utf-8", errors="replace")
              for m in [re.search(r"YAVG=([\d.]+)", ln)] if m]
        return (max(vs) / 255.0 * 100.0) if vs else -1.0

    d_tuyet, d_voi = khac(a, b), khac(a, c)
    bao("clip nói TUYẾT RƠI -> lớp phủ THẤY ĐƯỢC trong file xuất (>= 6%)",
        d_tuyet >= 6.0, f"{d_tuyet:.2f}% điểm ảnh đổi so bản không nội dung")
    bao('clip nói "TUYỆT VỜI" -> file xuất KHÔNG có lớp phủ nào (< 3%)',
        0.0 <= d_voi < 3.0, f"{d_voi:.2f}%")
    bao("khoảng cách giữa hai ca đủ để kết luận (>= 3 lần)",
        d_voi >= 0 and d_tuyet >= max(3.0 * d_voi, 6.0),
        f"tuyết {d_tuyet:.2f}% vs tuyệt-vời {d_voi:.2f}%")
    # nhật ký phải nói được vì sao (nhóm này im lặng theo thiết kế)
    lg = Path(os.environ["BQ_DATA_DIR"]) / "logs"
    txt = "".join(p.read_text(encoding="utf-8", errors="replace")
                  for p in sorted(lg.glob("lop_phu_*.log"))) if lg.is_dir() \
        else ""
    bao("nhật ký lop_phu ghi rõ NGUỒN là LỜI THOẠI (tra lại được)",
        "LỜI THOẠI" in txt, [x for x in txt.splitlines()
                             if "LỜI THOẠI" in x][:1])


def ca5_hinh_uu_tien() -> None:
    print("\n[CA 5] XEM HÌNH VẪN ƯU TIÊN khi có vision_digest")
    src = inspect.getsource(
        __import__("app.core.ffmpeg_utils", fromlist=["x"]).export_canvas_clip)
    i_moc = src.find("_lp_moc = ")
    i_neu = src.find("if not _lp_moc:")
    bao("đường LỜI chỉ chạy KHI digest RỖNG (`if not _lp_moc`)",
        0 < i_moc < i_neu, f"vị trí {i_moc} < {i_neu}")
    bao("đường LỜI KHÔNG truyền thêm `loi` (chống đếm 2 lần)",
        '_lp_loi = ""' in src)
    # digest xem hình MẠNH + lời nói chuyện khác -> vẫn ra cảnh của DIGEST
    dg = [{"t": 1.0, "desc": "snow falling on a mountain", "act": 8},
          {"t": 4.0, "desc": "a snowman in heavy snowfall", "act": 7}]
    r, ly = LP.chon_lop_phu(dg, "hôm nay trời đẹp", 30.0)
    bao("digest xem hình đủ mạnh -> ra lớp phủ theo HÌNH",
        bool(r) and r[0]["canh"] == "tuyet_roi",
        f"{r[0]['khoa'] if r else '(không)'} · {ly[:44]}")
    bao("nhật ký ghi nguồn XEM HÌNH khi đi đường digest",
        "XEM HÌNH" in ly, ly[:70])


def ca6_khong_dem_hai_lan() -> None:
    print("\n[CA 6] KHÔNG ĐẾM MỘT BẰNG CHỨNG HAI LẦN")
    mot = ["ngoài trời tuyết rơi trắng xoá"]
    r1, ly1 = LP.chon_lop_phu(LP.digest_tu_loi(_tr(mot), [(0.0, 30.0)]), "",
                              30.0)
    bao("MỘT câu nhắc tới cảnh -> CHƯA đủ (một câu lướt qua không phải chủ đề)",
        not r1, ly1[:96])
    hai = mot + ["tuyết rơi dày lắm luôn"]
    r2, _l2 = LP.chon_lop_phu(LP.digest_tu_loi(_tr(hai), [(0.0, 30.0)]), "",
                              30.0)
    bao("HAI câu -> đủ (bậc thang đúng như 2 mốc hình mạnh)", bool(r2),
        f"{r2[0]['khoa'] if r2 else '(không)'}")
    # nếu caller LỠ truyền cả `loi` thì 1 câu đã qua ngưỡng -> chứng minh vì sao
    # ffmpeg_utils phải để `loi=""`
    r3, _l3 = LP.chon_lop_phu(LP.digest_tu_loi(_tr(mot), [(0.0, 30.0)]),
                              mot[0], 30.0)
    bao("chứng minh: truyền KÈM `loi` thì 1 câu đã qua ngưỡng -> phải để rỗng",
        bool(r3), "đúng như dự đoán -> ffmpeg_utils đặt _lp_loi = ''")


def ca7_tien_dinh() -> None:
    print("\n[CA 7] TIỀN ĐỊNH + bất biến video KHÔNG LỜI")
    cs = ["ngoài trời tuyết rơi trắng xoá", "tuyết rơi dày lắm luôn"]
    ds = LP.digest_tu_loi(_tr(cs), [(0.0, 30.0)])
    r = [LP.chon_lop_phu(ds, "", 30.0)[0] for _ in range(3)]
    bao("3 lượt ra CÙNG một kiểu, cùng giây (3 làn xuất song song)",
        all(x == r[0] for x in r), str(r[0][0]["khoa"] if r[0] else None))
    for ten, tr in (("transcript rỗng", {}), ("None", None),
                    ("segments rỗng", {"segments": []}),
                    ("câu KHÔNG MỐC",
                     {"segments": [{"text": "ngoài trời tuyết rơi trắng xoá"}]})):
        bao(f"{ten} -> digest_tu_loi trả [] (đi y đường cũ)",
            LP.digest_tu_loi(tr, [(0.0, 30.0)]) == [])
    # mốc rơi NGOÀI đoạn cắt phải bị bỏ (không thì câu ở phút 12 bật tuyết cho
    # clip cắt ở phút 2) — cùng luật `loc_digest_theo_doan`
    tr2 = _tr(["trong doan", "ngoài trời tuyết rơi trắng xoá"], 100.0)
    ds2 = LP.digest_tu_loi(tr2, [(0.0, 50.0)])
    bao("câu nằm NGOÀI đoạn cắt bị bỏ (không lấy bằng chứng của chỗ khác)",
        len(ds2) == 1 and "trong doan" in ds2[0]["desc"], str(ds2))
    # hook-first (đoạn NGƯỢC THỜI GIAN) vẫn đổi mốc đúng: đoạn (20,30) đứng
    # TRƯỚC nên câu ở giây 20 phải ra giây 0 của clip, còn câu ở giây 0 ra giây
    # 10. Cộng dồn phải theo ĐÚNG THỨ TỰ DANH SÁCH, không được sắp xếp lại.
    ds3 = LP.digest_tu_loi(_tr(["a", "b", "c"], 10.0), [(20.0, 30.0),
                                                       (0.0, 10.0)])
    bao("hook-first (đoạn ngược thời gian): mốc đổi theo ĐÚNG thứ tự danh sách",
        [(d["t"], d["desc"]) for d in ds3] == [(0.0, "c"), (10.0, "a"),
                                               (20.0, "b")],
        str([(d["t"], d["desc"]) for d in ds3]))


def ca8_quet_tinh() -> None:
    print("\n[CA 8] QUÉT TĨNH")
    sai = [(k, v) for k, vs in LP._DAU_VN.items() for v in vs
           if LP._khong_dau(v) != k]
    bao("mọi dạng CÓ DẤU trong `_DAU_VN` bỏ dấu ra ĐÚNG khoá (bắt lỗi gõ)",
        not sai, str(sai[:4]) if sai else f"{len(LP._DAU_VN)} khoá")
    src = inspect.getsource(LP.digest_tu_loi)
    bao("`digest_tu_loi` gắn cờ `loi` vào mốc (nếu không thì dò bằng bảng "
        "BỎ DẤU -> mở lại 9 bẫy)", '"loi": True' in src)
    src2 = inspect.getsource(LP._dem_tu)
    bao("`_dem_tu` KHÔNG bỏ dấu lời thoại", "_khong_dau" not in src2)
    src3 = inspect.getsource(LP.loc_digest_theo_doan)
    bao("`loc_digest_theo_doan` MANG THEO cờ `loi` (rơi cờ = mất bộ dò có dấu)",
        'x["loi"] = True' in src3)
    # bảng CJK: từ khoá 1 ký tự là bẫy "khớp trong từ dài"
    ngan = [(k, t) for k, b in LP._CJK.items()
            for g in ("manh", "phu", "cam") for t in b.get(g, ())
            if len(t.strip()) < 2]
    bao("mọi từ khoá CJK dài >= 2 ký tự (1 ký tự khớp bên trong từ dài)",
        not ngan, str(ngan[:5]) if ngan else f"{sum(len(b.get(g, ())) for b in LP._CJK.values() for g in ('manh', 'phu', 'cam'))} từ")
    # BẤT BIẾN cổng 46: không kiểu lớp phủ nào lọt vào bảng chọn theo SỐ ĐO
    lot = sorted(set(LP.moi_kieu()) & {k for v in HU._UV_THEO_LOAI.values()
                                       for k in v})
    bao("BẤT BIẾN: không kiểu lớp phủ nào có mặt trong `hieu_ung._UV_THEO_LOAI`",
        not lot, str(lot))


def main() -> int:
    td = str(_SB)
    src = os.path.join(td, "src.mp4")
    # nguồn TỰ SINH (không ghi cứng đường dẫn máy anh Hùng) — màu PHẲNG không
    # có vạch, để "bản không lớp phủ" đo ra sát 0% (bài học cổng 42 về testsrc2)
    rc, err = chay([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                    "color=c=0x1E6F5C:s=1080x1920:r=30:d=11", "-f", "lavfi",
                    "-i", "sine=f=300:r=48000:d=11", "-c:v", "libx264",
                    "-preset", "ultrafast", "-qp", "0", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-shortest", src])
    if rc != 0:
        print("KHÔNG dựng được nguồn:", err[:300])
        return 2
    ca1_bay()
    ca2_khong_qua_tay()
    ca3_chot_chan()
    ca4_xuat_that(src, td)
    ca5_hinh_uu_tien()
    ca6_khong_dem_hai_lan()
    ca7_tien_dinh()
    ca8_quet_tinh()
    print("\n" + "=" * 72)
    print(f"ĐẠT {len(_OK)} · HỎNG {len(_LOI)}")
    for x in _LOI:
        print("   ✗", x)
    return 1 if _LOI else 0


if __name__ == "__main__":
    try:
        _rc = main()
    finally:
        import shutil
        shutil.rmtree(_SB, ignore_errors=True)
    sys.exit(_rc)
