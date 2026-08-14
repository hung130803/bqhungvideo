# -*- coding: utf-8 -*-
r"""CỔNG 52 — **3 LỖ HỔNG TIẾNG TRUNG (CJK) ĐÃ VÁ** (14/08/2026).

    .venv\Scripts\python _test_cjk_va.py

Luồng kiểm tiếng Trung end-to-end (7 commit b71603b..6a05bcb) đo ra 3 chỗ mà
app **im lặng bỏ rơi tiếng Trung**. Cổng này chốt cả 3 lại, và quan trọng hơn:
chốt **BẤT BIẾN** của 4 thứ tiếng còn lại — bản vá đụng vào đúng những hàm mà
mọi video của anh Hùng đều đi qua.

  VIỆC 1 `app/core/lop_phu.py` — bảng từ khoá chọn lớp phủ chỉ có Nhật/Hàn.
      1.122 từ khoá chỉ khớp **1** từ trên 1.230 ký tự lời Trung (`宝物`, trùng
      may). Kèm **BẪY CHÉO NGÔN NGỮ**: `料理` (Nhật = nấu ăn, **Trung = xử
      lý**) nằm trong danh sách CẤM của 5 cảnh -> một câu tiếng Trung nói "xử
      lý chuyện này" là **cấm oan 5 cảnh**; `手紙` (Nhật = lá thư, **Trung =
      giấy vệ sinh**) khớp `bui_phim`.
  VIỆC 2 `app/ai/recap.py` — `.split()` trên chữ chép lời. Câu CJK ra **1
      token** -> mọi tỉ lệ trùng ra 0.0 -> **bộ dò chống chép lời TẮT IM
      LẶNG**. Đây là lớp bảo vệ chống video bị gắn cờ chép lại.
  VIỆC 3 `app/ai/hook_to_mo.py` — `_HUA_HEN` 26 từ, **0 chữ Hán**.

=== NGUỒN SỐ LIỆU: THẬT HẾT, KHÔNG BỊA ===
  · `_tq_work/trung_transcript.json` — Groq THẬT trên video `我的观影报告…mp4`
    của anh Hùng (187,27 s · 99 câu · 1.132 ký tự).
  · `_tq_work/zh_narrate.json` — corpus ĐỐI KHÁNG do **Groq THẬT** sinh
    (`_do_cjk_calib.py`): 14 câu được YÊU CẦU kể lại lời nhân vật (phải BỊ
    BẮT) + 11 câu được YÊU CẦU bình luận góc ngoài (KHÔNG được bắt).
  · `_do_hook_cache.json` — **16 video THẬT, 4 thứ tiếng** (Nhật · Hàn · Anh ·
    Việt), chép lời Groq thật. Đây là corpus BẤT BIẾN.

=== CHỐNG PASS OAN (bài học cổng 36/41/47/51) ===
  · so với **BẢN MỐC** `git show <sha>:...` chứ không so với `main`; có chốt
    "bản mốc phải KHÁC bản đang test", và nếu TRÙNG thì phân biệt 2 nguyên
    nhân bằng "HEAD có phải TỔ TIÊN của mốc không" (trùng + là tổ tiên = mốc
    đã chứa commit của nhánh -> FAIL; trùng + không phải tổ tiên = nhánh không
    đụng file đó -> bất biến ĐÚNG DO XÂY DỰNG).
  · mỗi việc có ca **TỰ KIỂM BỘ DÒ**: bắt bản MỐC phải TRƯỢT đúng phép đo mà
    bản mới ĐẠT. Thiếu ca đó thì cổng chỉ là con dấu.
  · quét tĩnh `.split()` bằng `tokenize`/`ast` (KHÔNG dùng `in` chuỗi — chính
    dòng ghi chú "CẤM .split()" sẽ bị kể là vi phạm, đỏ oan y hệt cổng 47).
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
WORK = REPO / "_tq_work"
T = tempfile.mkdtemp(prefix="bq_cjk_")
os.environ["BQ_DATA_DIR"] = os.path.join(T, "data")
os.environ["BQ_DB_PATH"] = os.path.join(T, "data", "studio.db")
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "settings.ini")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_FFMPEG_SLOTS"] = "1"
import _test_guard  # noqa: E402,F401 - CẤM cổng đụng máy anh Hùng

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

#: Mốc đối chứng = commit NGAY TRƯỚC loạt vá CJK (bản anh Hùng đang chạy).
MOC = os.environ.get("BQ_MOC_CJK", "841c773")

_OK: list = []
_FAIL: list = []


def ok(dieu_kien, ten: str, chi_tiet: str = "") -> bool:
    (_OK if dieu_kien else _FAIL).append(ten)
    print(f"  [{'OK  ' if dieu_kien else 'FAIL'}] {ten}"
          + (f"   — {chi_tiet}" if chi_tiet else ""))
    return bool(dieu_kien)


def _git(*a) -> str:
    return subprocess.run(("git",) + a, cwd=str(REPO), capture_output=True,
                          text=True, encoding="utf-8",
                          errors="replace").stdout


def _la_to_tien(sha: str) -> bool:
    """HEAD có phải TỔ TIÊN của `sha` không (bài học cổng 36)."""
    return subprocess.run(("git", "merge-base", "--is-ancestor", "HEAD", sha),
                          cwd=str(REPO), capture_output=True).returncode == 0


def _nap_moc(duong: str, ten: str):
    """Nạp bản MỐC của một file mã nguồn thành module RIÊNG.

    Trả `(module, khac)` — `khac=False` nghĩa là bản mốc TRÙNG bản đang test.
    """
    src = _git("show", f"{MOC}:{duong}")
    if len(src) < 500:
        return None, False
    cur = (REPO / duong).read_text(encoding="utf-8")
    khac = src.replace("\r\n", "\n") != cur.replace("\r\n", "\n")
    p = os.path.join(T, ten + ".py")
    Path(p).write_text(src, encoding="utf-8")
    sp = importlib.util.spec_from_file_location(ten, p)
    m = importlib.util.module_from_spec(sp)
    # PHẢI đăng ký vào sys.modules TRƯỚC khi exec: `@dataclass` tra
    # `sys.modules[cls.__module__].__dict__`, thiếu là nổ AttributeError.
    sys.modules[ten] = m
    sp.loader.exec_module(m)
    return m, khac


def _chot_moc(khac: bool, nhan: str) -> bool:
    """Chốt chống 'so nó với chính nó'. Trả True = ĐƯỢC đo bất biến."""
    if khac:
        ok(True, f"{nhan} bản mốc {MOC} KHÁC bản đang test (đo được bất biến)")
        return True
    if _la_to_tien(MOC):
        ok(False, f"{nhan} bản mốc TRÙNG bản đang test VÀ HEAD là tổ tiên của "
                  f"{MOC} -> mốc đã chứa chính bản vá, phép đo VÔ NGHĨA")
        return False
    ok(True, f"{nhan} bản mốc TRÙNG nhưng HEAD KHÔNG phải tổ tiên -> nhánh này "
             "không đụng file đó, bất biến ĐÚNG DO XÂY DỰNG")
    return False


# ====================================================================== CORPUS
_tq = json.loads((WORK / "trung_transcript.json").read_text(encoding="utf-8")) \
    if (WORK / "trung_transcript.json").exists() else {}
ZH_CAU = [(float(s["start"]), float(s["end"]), str(s.get("text") or ""))
          for s in (_tq.get("segments") or []) if str(s.get("text") or "").strip()]
ZH_NAR = json.loads((WORK / "zh_narrate.json").read_text(encoding="utf-8")) \
    if (WORK / "zh_narrate.json").exists() else {}
_hc = REPO / "_do_hook_cache.json"
KHO4 = json.loads(_hc.read_text(encoding="utf-8")) if _hc.exists() else []
#: 16 video / 4 nhóm tiếng -> [(nhóm, nhãn Groq trả, [(a, b, text)…])]
#: LƯU Ý dữ liệu THẬT: Groq gán nhầm nhãn cho video HÀN (`Norwegian Nynorsk`).
#: Giữ nguyên, KHÔNG sửa tay — đó đúng là thứ app nhận được ở đời thật, và
#: `chuan_ngon_ngu` phải trả "" cho cả nhãn sai lẫn nhãn đúng.
BB = [(str(v.get("nhom") or ""), str(v.get("lang") or ""),
       [(float(s["start"]), float(s["end"]), str(s.get("text") or ""))
        for s in v.get("segments") or [] if str(s.get("text") or "").strip()])
      for v in KHO4]

print("=" * 74)
print(f"CỔNG 52 — 3 LỖ HỔNG CJK ĐÃ VÁ · mốc đối chứng {MOC}")
print(f"corpus: lời Trung {len(ZH_CAU)} câu · Groq kể-lại "
      f"{len(ZH_NAR.get('ke_lai') or [])} / sáng-tác "
      f"{len(ZH_NAR.get('sang_tac') or [])} · bất biến {len(BB)} video "
      f"{sorted({n for n, _l, _s in BB})}")
print("=" * 74)

from app.core import lop_phu as LP        # noqa: E402
from app.ai import recap as R             # noqa: E402
from app.ai import hook_to_mo as H        # noqa: E402

LP_MOC, _lp_khac = _nap_moc("app/core/lop_phu.py", "lp_moc")
R_MOC, _r_khac = _nap_moc("app/ai/recap.py", "recap_moc")
H_MOC, _h_khac = _nap_moc("app/ai/hook_to_mo.py", "hook_moc")

# ══════════════════════════════════════════════════════════════════════════
print("\n=== CA 1. VIỆC 1 — BẪY CHÉO NGÔN NGỮ: cùng chữ Hán, khác nghĩa ===")


def _canh_cam(tu: str, lang: str) -> list:
    return sorted(k for k, l in LP.LUAT.items()
                  if LP._co(tu, LP._mau_loi(l, lang)[2]))


def _canh_khop(tu: str, lang: str) -> list:
    return sorted(k for k, l in LP.LUAT.items()
                  if LP._co(tu, LP._mau_loi(l, lang)[0])
                  or LP._co(tu, LP._mau_loi(l, lang)[1]))


_cam_zh = _canh_cam("料理", "zh")
_cam_ja = _canh_cam("料理", "")
ok(not _cam_zh, "1a `料理` (Trung = XỬ LÝ) KHÔNG còn cấm oan cảnh nào",
   f"cấm: {_cam_zh or '—'}")
ok(len(_cam_ja) == 5,
   "1b `料理` (Nhật = NẤU ĂN) VẪN cấm đủ 5 cảnh ở bảng mặc định — không sửa "
   "quá tay", f"{_cam_ja}")
ok(not _canh_khop("手紙", "zh"),
   "1c `手紙` (Trung = GIẤY VỆ SINH) không khớp cảnh nào",
   f"khớp: {_canh_khop('手紙', 'zh') or '—'}")
ok(_canh_khop("手紙", "") == ["bui_phim"],
   "1d `手紙` (Nhật = LÁ THƯ) vẫn khớp bui_phim ở bảng mặc định")
ok(all(not LP._CO_CJK.search(t)
       for l in LP.LUAT.values()
       for o in ("manh", "phu", "cam")
       for t in LP._tu_loi(l, "zh", o)
       if t not in {x for v in LP._ZH.values() for vv in v.values() for x in vv}),
   "1e bảng tiếng Trung KHÔNG thừa hưởng MỘT từ khoá Nhật/Hàn nào "
   "(chỗ `料理`/`手紙` chui vào)")
ok(LP.chuan_ngon_ngu("Chinese") == "zh" and LP.chuan_ngon_ngu("zh") == "zh"
   and LP.chuan_ngon_ngu("zh-CN") == "zh" and LP.chuan_ngon_ngu("yue") == "zh",
   "1f nhận CẢ `zh` LẪN `Chinese` (Groq trả nhãn CHỮ trên video thật — thiếu "
   "dạng nào là bản vá không bao giờ chạy mà không một dòng báo)")
ok(LP.chuan_ngon_ngu("Japanese") == "" and LP.chuan_ngon_ngu("ko") == ""
   and LP.chuan_ngon_ngu("English") == "" and LP.chuan_ngon_ngu("") == "",
   "1g Nhật/Hàn/Anh/rỗng -> bảng MẶC ĐỊNH (cửa duy nhất của bất biến)")

# ══════════════════════════════════════════════════════════════════════════
print("\n=== CA 2. VIỆC 1 — LỜI TRUNG THẬT: từ khoá khớp + độ tin ===")
_loi_zh = "".join(t for _a, _b, t in ZH_CAU)


def _n_khop(lang: str) -> int:
    return sum(1 for l in LP.LUAT.values() for bo in LP._mau_loi(l, lang)
               for r in bo if LP._co(_loi_zh, [r]))


_n_zh, _n_md = _n_khop("zh"), _n_khop("")
ok(_n_zh >= 8, f"2a bảng tiếng Trung khớp {_n_zh} từ khoá trên {len(_loi_zh)} "
   f"ký tự lời Trung (bảng mặc định: {_n_md})")
ok(_n_md == 1, "2b bản MẶC ĐỊNH vẫn chỉ khớp 1 từ (`宝物`, trùng may) — "
   "chứng minh 2a là do bản vá, không phải corpus dễ")

_dg = LP.digest_tu_loi(_tq, [[0.0, float(_tq.get("duration") or 187.27)]])
ok(sum(1 for d in _dg if d.get("lang")) == len(_dg) and len(_dg) > 50,
   "2c nhãn ngôn ngữ đóng lên MỌI mốc lời (rơi nhãn = dò bằng bảng Nhật)",
   f"{sum(1 for d in _dg if d.get('lang'))}/{len(_dg)} mốc")


def _tin(lang: str) -> dict:
    ra = {}
    for k, l in LP.LUAT.items():
        d = LP._diem(l, _dg, "", lang)
        if d:
            ra[k] = d["tin"]
    return ra


_t_zh, _t_md = _tin("zh"), _tin("")
ok(_t_zh.get("duoi_nuoc", 0) >= LP.NGUONG_TIN,
   f"2d cảnh ĐÚNG của video (lặn biển) vượt ngưỡng {LP.NGUONG_TIN}",
   f"duoi_nuoc {_t_zh.get('duoi_nuoc', 0):.2f} (bảng mặc định: "
   f"{_t_md.get('duoi_nuoc', 0):.2f})")
ok(_t_md.get("duoi_nuoc", 0) < LP.NGUONG_TIN,
   "2e TỰ KIỂM BỘ DÒ: cùng lời đó, bảng MẶC ĐỊNH KHÔNG vượt ngưỡng (nếu chỗ "
   "này cũng vượt thì 2d chỉ là con dấu)")

_ra_zh, _ly_zh = LP.chon_lop_phu(LP.digest_tu_loi(_tq, [[0.0, 60.0]]), "", 60.0,
                                 ngon_ngu="Chinese")
ok(len(_ra_zh) == 1 and _ra_zh[0]["canh"] == "duoi_nuoc",
   "2f đoạn cắt THẬT 0-60s (cảnh lặn tìm đồng hồ) -> ĐẶT ĐƯỢC lớp phủ đúng "
   "cảnh", f"{[x['khoa'] for x in _ra_zh]} · {_ly_zh[:70]}")
_ra_md, _ly_md = LP.chon_lop_phu(
    [{k: v for k, v in d.items() if k != "lang"}
     for d in LP.digest_tu_loi(_tq, [[0.0, 60.0]])], "", 60.0, ngon_ngu="")
ok(not _ra_md,
   "2g TỰ KIỂM BỘ DÒ: đúng đoạn đó, bảng mặc định ra 0 lớp phủ (đây là hành "
   "vi anh Hùng đang gặp)", _ly_md[:80])
# chốt AN TOÀN: bảng mới KHÔNG được biến thành "bạ đâu cũng thêm"
_ra_x, _ly_x = LP.chon_lop_phu(
    LP.digest_tu_loi({"language": "Chinese", "segments": [
        {"start": i * 3.0, "end": i * 3.0 + 2.5,
         "text": "我们今天来聊一聊这个很普通的话题大家随便看看就好"}
        for i in range(12)]}, [[0.0, 40.0]]), "", 40.0, ngon_ngu="zh")
ok(not _ra_x, "2h lời Trung KHÔNG dính cảnh nào -> vẫn KHÔNG thêm gì "
   "(bất biến số 1: thà clip trần còn hơn thêm bừa)", _ly_x[:80])

# ══════════════════════════════════════════════════════════════════════════
print("\n=== CA 3. VIỆC 1 — BẤT BIẾN Nhật/Hàn/Anh/Việt (16 video thật) ===")
if LP_MOC is None or not BB:
    ok(False, "3a thiếu bản mốc hoặc corpus 16 video")
elif _chot_moc(_lp_khac, "3a"):
    _lech, _n = [], 0
    for nhom, lang, ss in BB:
        tr = {"language": lang,
              "segments": [{"start": a, "end": b, "text": t} for a, b, t in ss]}
        segs = [[0.0, max(b for _a, b, _t in ss) + 1.0]]
        loi = " ".join(t for _a, _b, t in ss)
        for nguon in ("loi", "hinh+loi"):
            if nguon == "loi":
                d_new, d_old, l_in = (LP.digest_tu_loi(tr, segs),
                                      LP_MOC.digest_tu_loi(tr, segs), "")
            else:
                # đường XEM HÌNH: mốc mô tả tiếng Anh + LỜI thật của video
                mh = [{"t": 5.0, "desc": "a snowy mountain at sunset",
                       "act": 7},
                      {"t": 9.0, "desc": "people celebrating with a cake",
                       "act": 6}]
                d_new = LP.loc_digest_theo_doan(mh, segs)
                d_old = LP_MOC.loc_digest_theo_doan(mh, segs)
                l_in = loi
            a = LP_MOC.chon_lop_phu(d_old, l_in, segs[0][1])
            b = LP.chon_lop_phu(d_new, l_in, segs[0][1], ngon_ngu=lang)
            _n += 1
            if a != b:
                _lech.append((lang, nguon, a[0], b[0]))
            for k, l in LP.LUAT.items():
                x = LP_MOC._diem(LP_MOC.LUAT[k], d_old, LP_MOC._ha(l_in))
                y = LP._diem(l, d_new, LP._ha(l_in), LP.chuan_ngon_ngu(lang))
                _n += 1
                gx = None if x is None else tuple(
                    x[f] for f in ("khoa", "ho", "tho", "tin", "dm", "dp",
                                   "tm", "tp"))
                gy = None if y is None else tuple(
                    y[f] for f in ("khoa", "ho", "tho", "tin", "dm", "dp",
                                   "tm", "tp"))
                if gx != gy:
                    _lech.append((lang, k, gx, gy))
    ok(not _lech, f"3b {_n} phép so trên {len(BB)} video 4 thứ tiếng: quyết "
       f"định lớp phủ + điểm từng cảnh GIỐNG HỆT bản mốc {MOC}",
       f"lệch {len(_lech)}: {_lech[:2]}")
    # TỰ KIỂM: cùng bộ so đó phải BẮT ĐƯỢC khác biệt khi đưa lời TRUNG vào
    _a = LP_MOC.chon_lop_phu(LP_MOC.digest_tu_loi(_tq, [[0.0, 60.0]]), "", 60.0)
    _b = LP.chon_lop_phu(LP.digest_tu_loi(_tq, [[0.0, 60.0]]), "", 60.0,
                         ngon_ngu="Chinese")
    ok(_a != _b, "3c TỰ KIỂM BỘ DÒ: đúng phép so đó, lời TRUNG cho ra kết quả "
       "KHÁC bản mốc (nếu bằng nhau thì 3b chỉ là con dấu)",
       f"mốc {len(_a[0])} lớp phủ · nay {len(_b[0])}")

# ══════════════════════════════════════════════════════════════════════════
print("\n=== CA 4. VIỆC 2 — lưới chống chép lời CHẠY THẬT với tiếng Trung ===")
_tn = " ".join(R._norm_for_copy(t) for _a, _b, t in ZH_CAU)
_cau4 = "".join(t for _a, _b, t in ZH_CAU[8:12])
ok(len(R._word_tokens(R._norm_for_copy(_cau4))) > 1,
   "4a câu Trung dài ra > 1 token",
   f"{len(_cau4.split())} (.split()) -> "
   f"{len(R._word_tokens(R._norm_for_copy(_cau4)))} (_word_tokens)")
ok(len(R._content_words(_cau4)) > 4 and len(R._content_seq(_cau4)) > 4
   and len(R._content_pron_set(_cau4)) > 4,
   "4b 3 hàm đếm TỪ-NỘI-DUNG không còn ra 1 phần tử (lọc `len>1` đã sửa)",
   f"{len(R._content_words(_cau4))}/{len(R._content_seq(_cau4))}/"
   f"{len(R._content_pron_set(_cau4))}")


def _bat(t: str, mod=R) -> bool:
    return bool(mod._is_transcript_copy(t, _tn)
                or mod._is_copy_narrate(t, ZH_CAU, 0.0, 60.0))


_nv = sum(1 for _a, _b, t in ZH_CAU if _bat(t))
_kl = sum(1 for t in (ZH_NAR.get("ke_lai") or []) if _bat(t))
_st = sum(1 for t in (ZH_NAR.get("sang_tac") or []) if _bat(t))
ok(_nv >= 85, f"4c CHÉP NGUYÊN VĂN bị bắt {_nv}/{len(ZH_CAU)} câu")
ok(_kl == len(ZH_NAR.get("ke_lai") or []) and _kl > 0,
   f"4d KỂ LẠI (Groq sinh, thành phần THẬT) bị bắt {_kl}/"
   f"{len(ZH_NAR.get('ke_lai') or [])}")
ok(_st == 0, f"4e SÁNG TÁC (Groq sinh) KHÔNG bị gut oan câu nào — 0/"
   f"{len(ZH_NAR.get('sang_tac') or [])}")
ok(R._is_transcript_copy(_cau4, _tn),
   "4f chép NGUYÊN 4 CÂU LIỀN bị bắt (transcript nối bằng dấu cách, LLM viết "
   "liền -> lưới cũ trượt)")

# ══════════════════════════════════════════════════════════════════════════
print("\n=== CA 5. VIỆC 2 — BẤT BIẾN Anh/Việt/Nhật/Hàn (16 video thật) ===")
if R_MOC is None or not BB:
    ok(False, "5a thiếu bản mốc hoặc corpus")
elif _chot_moc(_r_khac, "5a"):
    # Phân biệt HAI mức, đừng gộp — gộp là ĐỎ OAN:
    #   · QUYẾT ĐỊNH  = 3 hàm app THỰC SỰ hành động theo (`_is_transcript_copy`
    #     · `_is_copy_narrate` · `_is_relevant`) + cả `validate_parts` đầu-cuối.
    #     Đây mới là "app xử sự khác đi không". PHẢI y hệt ở CẢ 4 thứ tiếng.
    #   · TẬP TOKEN nội bộ (`_content_words`/`_content_pron_set`/`_content_seq`)
    #     — với Nhật/Hàn chúng CỐ Ý đổi (trước đây trả 1 phần tử = HỎNG), nhưng
    #     phải chứng minh đổi mà KHÔNG lật một quyết định nào.
    _qd, _tk, _n = [], [], 0
    for nhom, lang, ss in BB:
        tn = " ".join(R._norm_for_copy(t) for _a, _b, t in ss)
        thu = [t for _a, _b, t in ss] \
            + ["".join(t for _a, _b, t in ss[:3])] \
            + ["Gã này vừa mất cả gia tài chỉ vì một cú click chuột",
               "The moment he touches the valve a loud hiss is heard"]
        for t in thu:
            _n += 1
            if R._is_transcript_copy(t, tn) != R_MOC._is_transcript_copy(t, tn):
                _qd.append((nhom, "_is_transcript_copy", t[:24]))
            for f in ("_content_words", "_content_pron_set", "_content_seq",
                      "_word_tokens"):
                _n += 1
                x = getattr(R, f)(t if f != "_word_tokens"
                                  else R._norm_for_copy(t))
                y = getattr(R_MOC, f)(t if f != "_word_tokens"
                                      else R_MOC._norm_for_copy(t))
                if x != y:
                    _tk.append((nhom, f, t[:24]))
        for a, b, t in ss[:14]:
            _n += 1
            if R._is_copy_narrate(t, ss, a, b) \
                    != R_MOC._is_copy_narrate(t, ss, a, b):
                _qd.append((nhom, "_is_copy_narrate", t[:24]))
            _n += 1
            near = {w for w in R._window_words(ss, a - 6, b + 6)
                    if R._la_tu_noi_dung(w) and w not in R._STOPWORDS}
            near_o = {w for w in R_MOC._window_words(ss, a - 6, b + 6)
                      if len(w) > 1 and w not in R_MOC._STOPWORDS}
            if R._is_relevant(t, near) != R_MOC._is_relevant(t, near_o):
                _qd.append((nhom, "_is_relevant", t[:24]))
        # ĐẦU-CUỐI: cùng kịch bản part -> `validate_parts` phải ra Y HỆT
        _ps = [{"start": a, "end": b, "mode": "narrate", "text": t}
               for a, b, t in ss[:10]]
        _n += 1
        if R.validate_parts(_ps, ss[0][0], ss[min(9, len(ss) - 1)][1],
                            sentences=ss) \
                != R_MOC.validate_parts(_ps, ss[0][0],
                                        ss[min(9, len(ss) - 1)][1],
                                        sentences=ss):
            _qd.append((nhom, "validate_parts", ""))
    ok(not _qd, f"5b {_n} phép so trên {len(BB)} video 4 thứ tiếng: MỌI QUYẾT "
       f"ĐỊNH chống chép lời (+ `validate_parts` đầu-cuối) GIỐNG HỆT mốc {MOC}",
       f"lệch {len(_qd)}: {_qd[:3]}")
    _tk_env = [x for x in _tk if x[0] in ("anh", "viet")]
    ok(not _tk_env, "5c BẤT BIẾN EN/VI tới tận TẬP TOKEN nội bộ (non-CJK: "
       "`_word_tokens` == `.split()` và `_la_tu_noi_dung` == `len>1`)",
       f"lệch {len(_tk_env)}")
    ok(_tk and all(x[0] in ("nhat", "han") for x in _tk),
       "5d tập token nội bộ CHỈ đổi ở Nhật/Hàn — và đó là CỐ Ý (trước đây câu "
       "của họ cũng ra 1 phần tử = hỏng), quyết định thì không lật cái nào",
       f"{len(_tk)} chỗ đổi, tất cả thuộc {sorted({x[0] for x in _tk})}")
    _a = sum(1 for _x, _y, t in ZH_CAU if _bat(t, R_MOC))
    ok(_a < 20 and _nv >= 85,
       "5e TỰ KIỂM BỘ DÒ: cùng phép đo đó, bản mốc chỉ bắt được rất ít câu "
       "Trung (nếu nó cũng bắt được nhiều thì CA 4 chỉ là con dấu)",
       f"mốc {_a}/{len(ZH_CAU)} · nay {_nv}/{len(ZH_CAU)}")

print("\n=== CA 6. VIỆC 2 — quét tĩnh `.split()` (AST, bỏ hằng chuỗi) ===")
_src = (REPO / "app" / "ai" / "recap.py").read_text(encoding="utf-8")
_bien, _hang = [], []
for _nd in ast.walk(ast.parse(_src)):
    if (isinstance(_nd, ast.Call) and isinstance(_nd.func, ast.Attribute)
            and _nd.func.attr == "split" and not _nd.args):
        (_hang if isinstance(_nd.func.value, ast.Constant) else _bien) \
            .append(_nd.lineno)
ok(len(_bien) == 1, "6a chỉ còn ĐÚNG 1 chỗ `.split()` trên BIẾN — nằm trong "
   "chính `_word_tokens` (đường non-CJK, bất biến)", f"dòng {_bien}")
ok(_bien and 940 < _bien[0] < 990,
   "6b chỗ đó đúng là `_word_tokens`, không phải chỗ khác lọt lưới",
   f"dòng {_bien[0] if _bien else '?'}")
ok(len(_hang) == 3, "6c 3 chỗ `.split()` trên HẰNG CHUỖI (tách bảng stopword "
   f"vi/en/hi) ĐỂ YÊN — đúng, chúng không đếm chữ chép lời", f"dòng {_hang}")

# ══════════════════════════════════════════════════════════════════════════
print("\n=== CA 7. VIỆC 3 — `_HUA_HEN` bắt được câu hứa hẹn tiếng Trung ===")


def _han(tap) -> list:
    return [t for t in tap if any(0x4E00 <= ord(c) <= 0x9FFF for c in t)
            and not any(0x3040 <= ord(c) <= 0x30FF for c in t)]


ok(len(_han(H._HUA_HEN)) >= 8,
   f"7a `_HUA_HEN` có {len(_han(H._HUA_HEN))} từ chữ Hán (trước: 0)")
ok(all(len(t) >= 2 for t in _han(H._HUA_HEN)),
   "7b mọi từ khoá Trung >= 2 ký tự (luật sắt CJK không dấu cách)")
ok("你看" not in H._HUA_HEN,
   "7c KHÔNG nhận `你看` — tiếng đệm dày đặc, đúng lý do `一番`/`제일` bị loại")
_zh1, _ly1 = H.cham_cau("首先我们来看第一步该怎么做", 2.5)
_zh2, _ly2 = H.cham_cau("接下来我教你一个最简单的办法", 2.5)
_en2, _ = H.cham_cau("keep watching to the end of this", 2.5)
_vi2, _ = H.cham_cau("bước đầu tôi sẽ làm như thế này", 2.5)
ok(_zh1 >= H.NGUONG, f"7d câu Trung 2 dấu hiệu vượt ngưỡng {H.NGUONG}",
   f"{_zh1:.3f} — {_ly1}")
ok(abs(_zh2 - _en2) < 0.01 and abs(_zh2 - _vi2) < 0.01,
   "7e câu Trung 1 dấu hiệu «hứa hẹn» ăn ĐÚNG số điểm của câu Anh/Việt tương "
   "đương -> NGANG HÀNG các thứ tiếng khác (0,302 là ĐÚNG THIẾT KẾ: 1 dấu "
   "hiệu mờ nhạt thì không qua cửa 0,34, tiếng nào cũng vậy)",
   f"Trung {_zh2:.3f} · Anh {_en2:.3f} · Việt {_vi2:.3f}")
_zh2_moc = H_MOC.cham_cau("接下来我教你一个最简单的办法", 2.5)[0] \
    if H_MOC else -1
ok(_zh2_moc < _zh2, "7f TỰ KIỂM BỘ DÒ: bản mốc chấm câu đó THẤP HƠN",
   f"mốc {_zh2_moc:.3f} -> nay {_zh2:.3f}")

print("\n=== CA 8. VIỆC 3 — BẤT BIẾN cham_cau 4 thứ tiếng (16 video) ===")
if H_MOC is None or not BB:
    ok(False, "8a thiếu bản mốc hoặc corpus")
elif _chot_moc(_h_khac, "8a"):
    _lech, _n = [], 0
    for nhom, lang, ss in BB:
        for a, b, t in ss:
            _n += 1
            if H.cham_cau(t, b - a)[0] != H_MOC.cham_cau(t, b - a)[0]:
                _lech.append((lang, t[:28]))
    ok(not _lech, f"8b {_n} câu THẬT của 16 video 4 thứ tiếng: `cham_cau` ra "
       f"ĐIỂM Y HỆT bản mốc {MOC} — 9 từ khoá Trung mới KHÔNG khớp bừa vào "
       "chữ Hán của tiếng Nhật", f"lệch {len(_lech)}: {_lech[:3]}")
    # TỰ KIỂM phải dùng câu CÓ CHỨA từ khoá mới. (Bản đầu của cổng này lấy 99
    # câu transcript Trung — chúng nói về săn kho báu, không câu nào chứa từ
    # "hứa hẹn" nào, nên ra 0/99 và ca tự-kiểm ĐỎ OAN.)
    _CAU_HH = ("首先我们来做这件事情", "第一步要准备好工具",
               "第一个办法其实很简单", "接下来我们看下一段",
               "教你一个很好用的方法", "这样做就不会出错了",
               "看到最后你会明白的", "继续看下去就知道原因",
               "别急我马上就说到重点")
    _len = [(H.cham_cau(c, 2.5)[0], H_MOC.cham_cau(c, 2.5)[0])
            for c in _CAU_HH]
    ok(all(a > b for a, b in _len),
       f"8c TỰ KIỂM BỘ DÒ: cả {len(_CAU_HH)} từ khoá Trung mới đều LÀM TĂNG "
       "điểm so với bản mốc (nếu bằng nhau thì 8b chỉ là con dấu)",
       f"nay {[round(a, 3) for a, _b in _len]} vs mốc "
       f"{[round(b, 3) for _a, b in _len]}")

# ══════════════════════════════════════════════════════════════════════════
print("\n=== CA 9. NHẬT/HÀN — đường CŨ giữ nguyên, và nói thẳng LỖ CÒN LẠI ===")
# GHI THẲNG, KHÔNG BỊA: máy anh Hùng **không còn video tiếng HÀN** nào (thư mục
# `video hàn` đã bị xoá; 4 video tên Hàn trong `_do_hook_cache.json` được Groq
# chép ra tiếng ANH vì tiếng trong video là tiếng Anh thật). Nên corpus 16 video
# ở CA 3/5/8 phủ Nhật · Anh · Việt, KHÔNG phủ chữ Hàn. Câu tiếng Hàn dưới đây là
# TỰ DỰNG để chạy được nhánh hangul, và cổng chỉ dùng chúng cho phép so BẤT
# BIẾN (so bản mốc với bản mới) — không rút kết luận chất lượng nào từ chúng.
_KO = ("그런데 갑자기 눈보라가 몰아치기 시작했습니다",
       "결국 그는 아무 말도 하지 못하고 돌아섰어요",
       "이 사진 속에 숨겨진 비밀을 아무도 몰랐습니다")
_JA = ("ところがその瞬間、誰も予想しなかったことが起きました",
       "実は彼はずっと前から気づいていたのです")
ok(all(not R._la_chu_han(x) for x in _KO + _JA) and R._la_chu_han("他立刻辨认出这是古船"),
   "9a `_la_chu_han` tách đúng: Hàn/Nhật -> False (đi đường CŨ) · Trung -> True")
ok(all(R._is_copy_narrate(x, [(0.0, 3.0, x)], 0.0, 3.0) is False
       for x in _KO + _JA),
   "9b Nhật/Hàn vẫn BỎ QUA lưới fuzzy/n-gram y như trước — không bật mò khi "
   "chưa có corpus để hiệu chuẩn")
if R_MOC is not None and _r_khac:
    _ss_ko = [(i * 3.0, i * 3.0 + 2.8, t) for i, t in enumerate(_KO + _JA)]
    _tn_ko = " ".join(R._norm_for_copy(t) for _a, _b, t in _ss_ko)
    _l9 = [t for _a, _b, t in _ss_ko
           if R._is_transcript_copy(t, _tn_ko)
           != R_MOC._is_transcript_copy(t, _tn_ko)
           or R._is_copy_narrate(t, _ss_ko, 0.0, 9.0)
           != R_MOC._is_copy_narrate(t, _ss_ko, 0.0, 9.0)]
    ok(not _l9, "9c câu Hàn/Nhật tự dựng: mọi quyết định Y HỆT bản mốc",
       f"lệch {len(_l9)}")
    _l9b = [t for _a, _b, t in _ss_ko
            if H.cham_cau(t, 2.8)[0] != H_MOC.cham_cau(t, 2.8)[0]]
    ok(not _l9b, "9d `cham_cau` trên câu Hàn/Nhật tự dựng cũng Y HỆT bản mốc")
_ko_ngan = "그는 결국 포기했어요"          # 11 ký tự — dưới ngưỡng 15
ok(not R._is_transcript_copy(_ko_ngan, R._norm_for_copy(_ko_ngan)),
   "9e LỖ CÒN LẠI (ghi thẳng, KHÔNG vá bừa): câu Nhật/Hàn ngắn hơn 15 ký tự "
   "chép nguyên văn VẪN LỌT — ngưỡng ký tự chỉ hạ cho chữ Hán thuần vì chỉ "
   "tiếng Trung có corpus để đo. Có corpus lời dẫn Nhật/Hàn thì hạ tiếp.",
   f"«{_ko_ngan}» {len(_ko_ngan)} ký tự")

# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 74)
print(f"KẾT: ĐẠT {len(_OK)} · HỎNG {len(_FAIL)}")
for x in _FAIL:
    print("   HỎNG:", x)
sys.exit(1 if _FAIL else 0)
