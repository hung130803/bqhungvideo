# -*- coding: utf-8 -*-
r"""CỔNG 49 — XEM LẠI BẢN GHÉP CÓ MẠCH LẠC KHÔNG (và KHÔNG ĐƯỢC LÀM HỎNG CLIP).

    .venv\Scripts\python _test_mach_lac.py

VÌ SAO CÓ (anh Hùng 09/08/2026): app chọn 3 đoạn hay rồi ghép, **chưa bao giờ
xem lại bản ghép**. Ba đoạn hay riêng lẻ vẫn có thể rời rạc (trong nhà -> ngoài
đường -> lại trong nhà).

CỔNG NÀY KIỂM **KẾT QUẢ**, KHÔNG KIỂM "CÓ GỌI HÀM":

  CA 1  **FAIL-SAFE — phần quan trọng nhất.** 10 kiểu hỏng (mạng chết, hết
        lượt, JSON rác, `thu_tu` thiếu số, `bo` ngoài phạm vi, model trả chuỗi
        rỗng, trả prose, trả `null`, trả hoán vị lặp, ném lỗi lạ) -> **CẢ 10
        phải trả về ĐÚNG danh sách đoạn ban đầu**.
  CA 2  **`LLMTooLarge` PHẢI NỔI LÊN NGUYÊN VẸN, KHÔNG PHẠT KEY** (cổng 28:
        1 yêu cầu quá to từng khoá cả 38 key 120 giây).
  CA 3  **CÓ TÁC DỤNG THẬT** — bản ghép lủng củng thì ĐỔI ĐÚNG thứ tự / bỏ
        đúng đoạn. Cổng chỉ kiểm fail-safe thì `return segs` là qua hết.
  CA 4  **CHỐT AN TOÀN**: không bao giờ còn < 2 đoạn · không bao giờ tụt dưới
        Min người dùng đặt · điểm mạch lạc cao thì KHÔNG ĐỘNG VÀO.
  CA 5  **LLM THẬT (Groq)** trên bản ghép dựng sẵn: 1 bản xuôi + 1 bản đảo lộn
        cố ý -> in ra điểm mạch lạc của cả hai. Không có key -> BỎ QUA, nói rõ.
  CA 6  **NỐI VÀO ĐƯỜNG THẬT**: `m1_highlight` gọi hậu kiểm TRƯỚC
        `_enforce_len` (nếu sau thì hậu kiểm phá luôn rào độ dài — bài học
        cổng 12) và có công tắc `HAU_KIEM_GHEP`.
  CA 7  **NHẬT KÝ** ghi cả lúc GIỮ NGUYÊN (khâu này im lặng theo thiết kế).
"""
from __future__ import annotations

import inspect
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.mkdtemp(prefix="mach_lac_"))
os.environ["BQ_DATA_DIR"] = str(_SB)
os.environ["BQ_DB_PATH"] = str(_SB / "studio.db")
os.environ["QT_QPA_PLATFORM"] = "offscreen"

_env_that = (Path(os.environ.get("LOCALAPPDATA") or Path.home())
             / "BQHungVideo" / ".env")
if _env_that.exists():
    for _ln in _env_that.read_text(encoding="utf-8",
                                   errors="replace").splitlines():
        _k, _, _v = _ln.partition("=")
        _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
        if _k in ("GROQ_API_KEYS", "GROQ_KEYS_FILE") and _v:
            os.environ.setdefault(_k, _v)

import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

_LOI: list[str] = []
_OK: list[str] = []
_BQ: list[str] = []


def bao(ten: str, ok: bool, so: str = "") -> None:
    (_OK if ok else _LOI).append(ten)
    print(f"  [{'OK ' if ok else 'FAIL'}] {ten}" + (f": {so}" if so else ""))


def bo_qua(ten: str, ly: str) -> None:
    _BQ.append(f"{ten} — {ly}")
    print(f"  [BỎ ] {ten}: {ly}")


# đoạn mẫu + lời thoại: 3 đoạn, đoạn [1] cố ý LẠC LÕNG
SEGS = [[10.0, 40.0], [100.0, 130.0], [50.0, 80.0]]
TR = {"segments": [
    {"start": 12, "end": 38,
     "text": "Hôm nay tôi sẽ kể chuyện tôi mua căn nhà cũ nát này thế nào."},
    {"start": 102, "end": 128,
     "text": "Còn đây là công thức nấu phở bò gia truyền của bà tôi."},
    {"start": 52, "end": 78,
     "text": "Sau ba tháng sửa, căn nhà đã lột xác hoàn toàn, ai cũng bất ngờ."},
]}


def _ct(tra):
    """Giả lập `complete_text`: `tra` là chuỗi trả về HOẶC lỗi để ném."""
    def f(prompt, model=""):
        if isinstance(tra, BaseException):
            raise tra
        return tra
    return f


def ca1_fail_safe(ML) -> None:
    print("\n[CA 1] FAIL-SAFE — 10 kiểu hỏng, CẢ 10 phải giữ nguyên lựa chọn")
    from app.ai import llm
    HONG = [
        ("mạng chết", llm.LLMError("Connection aborted")),
        ("hết lượt mọi key", llm.LLMError("rate_limit_exceeded: try again")),
        ("lỗi lạ (TypeError)", TypeError("bùm")),
        ("trả chuỗi RỖNG", ""),
        ("trả prose không JSON", "Theo tôi thì bản ghép này khá ổn bạn nhé."),
        ("JSON hỏng cú pháp", '{"mach_lac": 3, "thu_tu": [0,1,}'),
        ("thu_tu THIẾU một số", '{"mach_lac":2,"thu_tu":[0,1],"bo":null}'),
        ("thu_tu LẶP số", '{"mach_lac":2,"thu_tu":[0,0,2],"bo":null}'),
        ("bo NGOÀI phạm vi", '{"mach_lac":2,"thu_tu":null,"bo":9}'),
        ("trả null", "null"),
    ]
    xau = []
    for ten, tra in HONG:
        try:
            ra, ly = ML.hau_kiem(SEGS, TR, _ct(tra))
        except Exception as e:  # noqa: BLE001
            xau.append(f"{ten}: NÉM LỖI {type(e).__name__}")
            continue
        if ra != SEGS:
            xau.append(f"{ten}: đổi thành {ra}")
        elif "GIỮ NGUYÊN" not in ly and "giữ nguyên" not in ly.lower():
            xau.append(f"{ten}: lý do không nói giữ nguyên — {ly[:40]}")
    bao("10/10 kiểu hỏng -> GIỮ NGUYÊN đúng danh sách đoạn ban đầu",
        not xau, "; ".join(xau) or "0 ca sai")
    # và KHÔNG được sửa tại chỗ danh sách của caller
    goc = [list(x) for x in SEGS]
    ML.hau_kiem(SEGS, TR, _ct('{"mach_lac":1,"thu_tu":[2,1,0],"bo":null}'))
    bao("KHÔNG sửa tại chỗ danh sách của caller (trả list MỚI)",
        SEGS == goc, str(SEGS))


def ca2_413(ML) -> None:
    print("\n[CA 2] `LLMTooLarge` (413) phải NỔI LÊN, KHÔNG PHẠT KEY")
    from app.ai import llm
    from config import settings
    # KHÔNG viết key giả có tiền tố thật vào file: cửa chặn phát hành chạy
    # `git diff | grep gsk_` và phải ra 0 — một chuỗi mẫu cũng làm nó đỏ.
    keys = settings.groq_keys() or ["(khong-co-key)"]
    truoc = [llm.key_status("groq")]
    noi = False
    # LỜI LỖI THẬT của Groq (đúng nguyên văn đã gặp 06/08/2026): có "413" +
    # "too large" VÀ có "rate_limit_exceeded" — đúng cái làm app khoá cả 38 key.
    _LOI_413 = ("Error code: 413 - {'error': {'message': 'Request too large "
                "for model ... tokens per minute (TPM): Limit 8000, "
                "Requested 8632', 'code': 'rate_limit_exceeded'}}")
    try:
        ML.hau_kiem(SEGS, TR, _ct(llm.LLMTooLarge(_LOI_413)))
    except llm.LLMTooLarge:
        noi = True
    except Exception as e:  # noqa: BLE001
        bao("413 nổi lên đúng kiểu LLMTooLarge", False, type(e).__name__)
    bao("413 NỔI LÊN NGUYÊN VẸN (caller tự thu nhỏ, không nuốt)", noi)
    sau = llm.key_status("groq")
    n_lim = sum(1 for k in sau if k.get("state") == "limited")
    bao("413 KHÔNG khoá key nào (cổng 28: 1 yêu cầu to = đốt sạch 38 key)",
        n_lim == 0, f"{n_lim}/{len(keys)} key bị khoá · "
                    f"{len(truoc[0])} key theo dõi")
    # và lời lỗi của 413 CÓ chứa 'rate_limit_exceeded' -> phải không bị nhầm
    bao("lời lỗi 413 CÓ chứa 'rate_limit_exceeded' (đúng bẫy cổng 28) mà vẫn "
        "được nhận ra là 'yêu cầu quá to', không phải 'hết lượt'",
        llm.is_too_large_error(_LOI_413)
        and llm.is_rate_limit_error(_LOI_413))


def ca3_co_tac_dung(ML) -> None:
    print("\n[CA 3] CÓ TÁC DỤNG THẬT — lủng củng thì phải SỬA ĐÚNG")
    ra, ly = ML.hau_kiem(
        SEGS, TR, _ct('{"mach_lac":3,"thu_tu":[0,2,1],"bo":null,'
                      '"vi_sao":"đoạn nấu phở lạc chủ đề"}'))
    bao("đổi THỨ TỰ: [0,2,1] -> đúng danh sách mới",
        ra == [SEGS[0], SEGS[2], SEGS[1]], str(ra))
    bao("lý do ghi rõ việc đã làm (tra lại được)",
        "đổi thứ tự" in ly and "0→2→1" in ly, ly[:80])
    ra2, ly2 = ML.hau_kiem(
        SEGS, TR, _ct('{"mach_lac":2,"thu_tu":null,"bo":1,'
                      '"vi_sao":"đoạn 1 lạc chủ đề"}'))
    bao("BỎ đoạn: bỏ đúng đoạn 1, giữ 0 và 2",
        ra2 == [SEGS[0], SEGS[2]], str(ra2))
    bao("lý do ghi rõ đã bỏ đoạn nào", "bỏ đoạn 1" in ly2, ly2[:80])
    # ĐỔI THỨ TỰ **RỒI** BỎ: chỉ số `bo` là của bản GỐC, không phải bản đã đảo
    ra3, ly3 = ML.hau_kiem(
        SEGS, TR, _ct('{"mach_lac":2,"thu_tu":[2,1,0],"bo":1}'))
    bao("vừa đổi thứ tự vừa bỏ: `bo` tính theo bản GỐC, không lệch đoạn",
        ra3 == [SEGS[2], SEGS[0]], f"{ra3} · {ly3[:50]}")


def ca4_chot_an_toan(ML) -> None:
    print("\n[CA 4] CHỐT AN TOÀN")
    hai = [[10.0, 40.0], [50.0, 80.0]]
    ra, ly = ML.hau_kiem(hai, TR, _ct('{"mach_lac":1,"thu_tu":null,"bo":0}'))
    bao(f"không bao giờ còn < {ML.DOAN_TOI_THIEU} đoạn (clip 2 đoạn -> KHÔNG bỏ)",
        ra == hai, ly[:90])
    ra2, ly2 = ML.hau_kiem(SEGS, TR,
                           _ct('{"mach_lac":1,"thu_tu":null,"bo":1}'),
                           min_giay=70.0)
    bao("không bao giờ tụt dưới Min người dùng đặt (60s còn lại < Min 70s)",
        ra2 == SEGS, ly2[:90])
    ra3, ly3 = ML.hau_kiem(SEGS, TR,
                           _ct('{"mach_lac":1,"thu_tu":null,"bo":1}'),
                           min_giay=55.0)
    bao("Min 55s thì ĐƯỢC bỏ (chốt chặn không siết quá tay)",
        ra3 == [SEGS[0], SEGS[2]], str(ra3))
    ra4, ly4 = ML.hau_kiem(
        SEGS, TR, _ct('{"mach_lac":9,"thu_tu":[2,1,0],"bo":0}'))
    bao(f"mạch lạc >= {ML.NGUONG_MACH_LAC:.0f}/10 -> KHÔNG ĐỘNG VÀO dù model "
        "vẫn đề nghị đổi", ra4 == SEGS, ly4[:90])
    ra5, ly5 = ML.hau_kiem([[1.0, 9.0]], TR, _ct("KHÔNG ĐƯỢC GỌI"))
    bao("clip 1 đoạn -> không gọi LLM, trả nguyên", ra5 == [[1.0, 9.0]],
        ly5[:60])
    # `doc_ket` là nơi duy nhất được phép tin/không tin model -> soi trực tiếp
    bao("`doc_ket` từ chối hoán vị không đầy đủ",
        ML.doc_ket('{"mach_lac":1,"thu_tu":[0,2]}', 3)["thu_tu"] is None)
    bao("`doc_ket` nhận hoán vị đầy đủ",
        ML.doc_ket('{"mach_lac":1,"thu_tu":[2,0,1]}', 3)["thu_tu"] == [2, 0, 1])


def ca5_llm_that(ML) -> None:
    print("\n[CA 5] LLM THẬT (Groq) — chấm bản XUÔI và bản ĐẢO LỘN")
    from config import settings
    keys = settings.groq_keys()
    if not keys:
        bo_qua("CA 5 LLM thật", "0 key Groq")
        return
    from app.ai import llm
    XUOI = {"segments": [
        {"start": 0, "end": 20, "text": "Tôi vừa mua một căn nhà cũ nát, "
                                        "ai nhìn cũng bảo tôi bị điên."},
        {"start": 30, "end": 50, "text": "Tôi bắt đầu đập bỏ toàn bộ tường "
                                         "cũ và làm lại hệ thống điện nước."},
        {"start": 60, "end": 80, "text": "Và đây là kết quả sau ba tháng, "
                                         "căn nhà đã lột xác hoàn toàn."}]}
    sg = [[0.0, 20.0], [30.0, 50.0], [60.0, 80.0]]
    diem = {}
    for ten, seg in (("XUÔI (1-2-3)", sg),
                     ("ĐẢO LỘN (3-1-2)", [sg[2], sg[0], sg[1]])):
        try:
            pr = ML.khoi_prompt(seg, XUOI)
            raw = llm.complete_text(pr) or ""
            d = ML.doc_ket(raw, len(seg))
            diem[ten] = (d or {}).get("mach_lac")
            print(f"        {ten}: mạch lạc {diem[ten]}/10 · "
                  f"{(d or {}).get('vi_sao', '')[:60]}")
        except Exception as e:  # noqa: BLE001
            print(f"        {ten}: LỖI {type(e).__name__}: {str(e)[:60]}")
            diem[ten] = None
    co = [v for v in diem.values() if v is not None]
    bao("LLM thật đọc được prompt hậu kiểm và chấm ra điểm (2/2 lượt)",
        len(co) == 2, str(diem))
    if len(co) == 2:
        bao("bản XUÔI được chấm >= bản ĐẢO LỘN (thước có phân biệt được)",
            diem["XUÔI (1-2-3)"] >= diem["ĐẢO LỘN (3-1-2)"], str(diem))
    # và tới đầu ra: chạy hau_kiem THẬT trên bản đảo lộn, không được nổ
    try:
        ra, ly = ML.hau_kiem([sg[2], sg[0], sg[1]], XUOI, llm.complete_text,
                             min_giay=0.0)
        bao("hau_kiem chạy với LLM THẬT, ra danh sách hợp lệ",
            isinstance(ra, list) and len(ra) in (2, 3), f"{len(ra)} đoạn · "
                                                        f"{ly[:80]}")
    except Exception as e:  # noqa: BLE001
        bao("hau_kiem chạy với LLM THẬT", False, f"{type(e).__name__}: {e}")


def ca6_noi_vao_duong_that() -> None:
    print("\n[CA 6] ĐÃ NỐI VÀO ĐƯỜNG THẬT (không phải mã chết)")
    src = (REPO / "app" / "modules" / "m1_highlight.py").read_text(
        encoding="utf-8")
    bao("`m1_highlight` có gọi `mach_lac.hau_kiem`",
        "mach_lac" in src and "hau_kiem(" in src)
    i_hk = src.find("_ml_mod.hau_kiem(")
    i_en = src.find("segs, _note = _enforce_len(segs, _min, _max")
    bao("hậu kiểm chạy TRƯỚC `_enforce_len` (`_enforce_len` vẫn là người nói "
        "cuối về độ dài — bài học cổng 12)",
        0 < i_hk < i_en, f"vị trí {i_hk} < {i_en}")
    bao("có công tắc `HAU_KIEM_GHEP`", "HAU_KIEM_GHEP" in src)
    from config import settings
    bao("`settings.HAU_KIEM_GHEP` có thật và mặc định BẬT",
        getattr(settings, "HAU_KIEM_GHEP", None) is True,
        str(getattr(settings, "HAU_KIEM_GHEP", None)))
    bao("hậu kiểm KHÔNG tự bật AI xem hình (chỉ đọc cache `get_analysis`)",
        "build_vision_digest" not in
        src[max(0, i_hk - 2200):i_hk + 900])
    from app.ai import mach_lac as ML
    s2 = inspect.getsource(ML)
    bao("`mach_lac` KHÔNG gọi vision/ffmpeg (chỉ đọc chữ đã có)",
        "build_vision_digest" not in s2 and "subprocess" not in s2
        and "complete_vision" not in s2)


def ca7_nhat_ky(ML) -> None:
    print("\n[CA 7] NHẬT KÝ ghi cả lúc GIỮ NGUYÊN")
    ML.ghi_nhat_ky("bản ghép mạch lạc 8/10 -> giữ nguyên 3 đoạn", "video 1")
    ML.ghi_nhat_ky("bản ghép 3/10 -> đổi thứ tự -> 0→2→1", "video 2")
    lg = Path(os.environ["BQ_DATA_DIR"]) / "logs"
    txt = "".join(p.read_text(encoding="utf-8", errors="replace")
                  for p in sorted(lg.glob("mach_lac_*.log"))) if lg.is_dir() \
        else ""
    bao("ghi được cả dòng GIỮ NGUYÊN và dòng ĐÃ SỬA",
        "giữ nguyên 3 đoạn" in txt and "0→2→1" in txt,
        f"{len(txt.splitlines())} dòng")
    # KHÔNG BAO GIỜ ném lỗi kể cả khi thư mục hỏng
    # (đường dẫn KHÔNG được chứa byte 0 — chính `os.environ.__setitem__` ném
    # ValueError trước khi tới hàm, bản đầu của cổng này FAIL OAN vì thế.)
    _cu = os.environ["BQ_DATA_DIR"]
    try:
        os.environ["BQ_DATA_DIR"] = str(Path(_cu) / "tep_khong_phai_thu_muc")
        Path(os.environ["BQ_DATA_DIR"]).write_text("x", encoding="utf-8")
        ML.ghi_nhat_ky("thử", "x")
        bao("ghi nhật ký KHÔNG BAO GIỜ ném lỗi (đường dẫn hỏng)", True)
    except Exception as e:  # noqa: BLE001
        bao("ghi nhật ký KHÔNG BAO GIỜ ném lỗi (đường dẫn hỏng)", False,
            type(e).__name__)
    finally:
        os.environ["BQ_DATA_DIR"] = _cu


def main() -> int:
    import app.queue.jobs  # noqa: F401
    from app.ai import mach_lac as ML
    ca1_fail_safe(ML)
    ca2_413(ML)
    ca3_co_tac_dung(ML)
    ca4_chot_an_toan(ML)
    ca5_llm_that(ML)
    ca6_noi_vao_duong_that()
    ca7_nhat_ky(ML)
    print("\n" + "=" * 72)
    print(f"ĐẠT {len(_OK)} · HỎNG {len(_LOI)}"
          + (f" · BỎ QUA {len(_BQ)}" if _BQ else ""))
    for x in _BQ:
        print("   ·", x)
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
