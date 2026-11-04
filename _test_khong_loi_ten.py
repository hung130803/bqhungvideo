# -*- coding: utf-8 -*-
"""CỔNG 109 — VIDEO KHÔNG LỜI: TÊN FILE / HASHTAG / PHỤ ĐỀ KHÔNG ĐƯỢC LẤY CHỮ BỊA.

03/11/2026 anh Hùng (kênh 2 nhóm mỹ bkt): "Part 1 Gå inn i bygget. #Rengar
#Meme #Random #AllRight" — video Mỹ quay công trường ra tên tiếng Na Uy.
Đo DB thật: 173 từ / 1.088 giây (0,16 từ/giây) -> Groq bịa chữ Na Uy/Hà
Lan/Nga. App đo được "không lời" nhưng dấu đó KHÔNG BAO GIỜ vào clip
(`_c["khong_loi"]` gắn vào dict tạm, signals dựng lại thiếu khoá) nên lúc xuất
vẫn đốt phụ đề bịa + tên file lấy câu bịa.

CA 1: ngon_ngu_video — khong_loi / ngon_ngu_ten / tieu_de_tu_ten.
CA 2: resolve_pub_title — video không lời: bỏ câu bịa, bỏ tiêu đề AI viết sai
      tiếng, lùi tên file gốc; tiêu đề AI viết ĐÚNG tiếng thì giữ.
CA 3: BẤT BIẾN — video có lời: kết quả GIỐNG HỆT bản không truyền ten_nguon.
CA 4: hashtag — không lời -> đầu vào là tên file, nguon='ten'; có lời y nguyên.
CA 5: quét tĩnh — signals của đường AI + đường cơ bản đều gắn khong_loi.
"""
import ast
import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
TMP = Path(tempfile.mkdtemp(prefix="bq_test_kl_ten_"))
os.environ["BQ_DATA_DIR"] = str(TMP)
os.environ["BQ_DB_PATH"] = str(TMP / "studio.db")

from app.ai import ngon_ngu_video as NV  # noqa: E402
from app.modules import m1_highlight as M1  # noqa: E402

DAT = HONG = 0


def ok(dk, ten, chi_tiet=""):
    global DAT, HONG
    if dk:
        DAT += 1
        print("  ĐẠT ", ten, chi_tiet)
    else:
        HONG += 1
        print("  HỎNG", ten, chi_tiet)


def tr_bia(dur=1088.0):
    """Chép lời BỊA thật (chép từ DB video 3625)."""
    cau = ["Hjulet.", "All right.", "Gå inn på denne sida.", "Gå inn på denne.",
           "Gå inn i bygget.", "Takk for watching All right", "Wacht even.",
           "ТРЕВОЖНАЯ МУЗЫКА", "Ik heb een koffie gekocht."]
    segs, words, t = [], [], 0.0
    for i in range(40):
        c = cau[i % len(cau)]
        segs.append({"start": t, "end": t + 2, "text": c})
        for w in c.split():
            words.append({"word": w, "start": t, "end": t + .3})
        t += dur / 40
    return {"language": "Norwegian Nynorsk", "duration": dur, "segments": segs,
            "words": words, "text": " ".join(s["text"] for s in segs)}


def tr_that(dur=120.0):
    cau = ("So today we are going to show you how the whole thing works and "
           "why it matters for everyone here")
    segs, words, t = [], [], 0.0
    while t < dur - 6:
        segs.append({"start": t, "end": t + 6, "text": cau})
        for k, w in enumerate(cau.split()):
            words.append({"word": w, "start": t + k * .3, "end": t + k * .3 + .25})
        t += 6
    return {"language": "en", "duration": dur, "segments": segs, "words": words,
            "text": " ".join(s["text"] for s in segs)}


TEN = r"D:\video ssmatool\mỹ bkt\kênh 2\WHAT MY DAY LOOKS LIKE ON A CONSTRUCTION SITE.mp4"

print("CA 1: ngon_ngu_video")
ok(NV.khong_loi(tr_bia()), "chép lời bịa 0,16 từ/giây -> không lời")
ok(not NV.khong_loi(tr_that()), "lời thật -> có lời")
ok(not NV.khong_loi({}), "không có chép lời -> False (giữ hành vi cũ)")
ok(NV.ngon_ngu_ten(TEN) == "en", "tên file Anh -> en", NV.ngon_ngu_ten(TEN))
ok(NV.ngon_ngu_ten("お姉ちゃんの部屋.mp4") == "ja", "tên file Nhật -> ja")
ok(NV.ngon_ngu_ten("Một ngày đi làm ở công trường.mp4") == "vi", "tên Việt -> vi")
ok(NV.ngon_ngu_ten("") == "", "tên rỗng -> ''")
ok(NV.tieu_de_tu_ten(TEN) == "WHAT MY DAY LOOKS LIKE ON A CONSTRUCTION SITE",
   "tiêu đề từ tên", NV.tieu_de_tu_ten(TEN))
ok(NV.tieu_de_tu_ten("clip #fyp #viral [abc123].mp4") == "clip", "bỏ #tag/[id]")
ok(NV.ngon_ngu(tr_bia(), TEN) == "en", "ngon_ngu không lời -> theo tên (en, KHÔNG Na Uy)")

print("CA 2: tiêu đề video không lời")
sig_cu = {"segments": [[0, 100]], "n_seg": 1, "title_en": "", "hook": ""}
t = M1.resolve_pub_title(tr_bia(), sig_cu, "Đỉnh cao giữa hành trình", 0, 120,
                         ten_nguon=TEN)
ok(t == NV.tieu_de_tu_ten(TEN), "clip cũ (không dấu) + tên file -> tên file, KHÔNG câu bịa", repr(t))
t_cu = M1.resolve_pub_title(tr_bia(), sig_cu, "Đỉnh cao", 0, 120)
ok("Gå" in t_cu or "Hjulet" in t_cu, "đối chứng: không truyền tên -> ra câu bịa (thước có răng)", repr(t_cu))
sig_no = dict(sig_cu, title_en="Torsdagsfilm med skremmande lyd – gå inn og opplev!")
t = M1.resolve_pub_title(tr_bia(), sig_no, "x", 0, 120, ten_nguon=TEN)
ok("Torsdag" not in t, "tiêu đề AI tiếng Na Uy (viết theo nhãn bịa) -> bỏ", repr(t))
t = M1.resolve_pub_title(tr_bia(), sig_no, sig_no["title_en"], 0, 120, ten_nguon=TEN)
ok(t == NV.tieu_de_tu_ten(TEN), "tên clip CŨ = tiêu đề Na Uy (đường _t_show) -> cũng bỏ", repr(t))
sig_moi = {"segments": [[0, 100]], "n_seg": 1, "khong_loi": True,
           "ten_nguon": os.path.basename(TEN), "lang_tieu_de": "en",
           "title_en": "A Day On The Job Site Gone Wild"}
t = M1.resolve_pub_title(tr_bia(), sig_moi, "Đỉnh cao", 0, 120)
ok(t == "A Day On The Job Site Gone Wild", "dấu trong signals + tiêu đề đúng tiếng -> giữ (không cần tham số)", repr(t))
sig_vi = dict(sig_moi, title_en="", lang_tieu_de="")
t = M1.resolve_pub_title(tr_bia(), sig_vi, "Đỉnh cao giữa hành trình", 0, 120)
ok(t == NV.tieu_de_tu_ten(TEN), "video Anh: không lấy tiêu đề Việt", repr(t))
sig_rc = dict(sig_cu, recap={"lang": "vi"}, title_en="Câu chuyện công trường")
t = M1.resolve_pub_title(tr_bia(), sig_rc, "x", 0, 120, ten_nguon=TEN)
t0 = M1.resolve_pub_title(tr_bia(), sig_rc, "x", 0, 120)
ok(t == t0, "clip RECAP không bị đụng (giống hệt bản cũ)", f"{t!r} == {t0!r}")

sig_en = dict(sig_cu, title_en="Our BIGGEST Job Ever! Toughest Challenge Yet!")
t = M1.resolve_pub_title(tr_bia(), sig_en, "x", 0, 120, ten_nguon=TEN)
ok(t == sig_en["title_en"], "clip cũ có tiêu đề AI tiếng ANH đúng chữ -> GIỮ (không sửa quá tay)", repr(t))
ok(not NV.hop_ngon_ngu("Gå inn i bygget.", "en") and NV.hop_ngon_ngu("All right!", "en"),
   "hop_ngon_ngu: Na Uy trượt, Anh đạt")
ok(NV.hop_ngon_ngu("お姉ちゃんの部屋", "ja") and not NV.hop_ngon_ngu("Room", "ja"), "hop_ngon_ngu: Nhật")

print("CA 3: bất biến video có lời")
for sig, vi in (({"title_en": "", "hook": ""}, "Tiêu đề Việt"),
                ({"title_en": "Big Reveal", "hook": ""}, "x"),
                ({"title_en": "", "hook": "Watch this"}, "")):
    a = M1.resolve_pub_title(tr_that(), sig, vi, 0, 60)
    b = M1.resolve_pub_title(tr_that(), sig, vi, 0, 60, ten_nguon=TEN)
    ok(a == b, "có lời -> giống hệt", f"{a!r} == {b!r}")

print("CA 4: hashtag")
r = NV.dau_vao_hashtag(tr_bia(), TEN, "t", "All right Gå inn", "Norwegian Nynorsk")
ok(r[2] == "en" and r[3] == "ten" and "Gå" not in r[1], "không lời -> tên file, en, nguon=ten", str(r))
r = NV.dau_vao_hashtag(tr_that(), TEN, "t", "lời", "en")
ok(r == ("t", "lời", "en", ""), "có lời -> y nguyên", str(r))
src_jobs = (REPO / "app/queue/jobs.py").read_text(encoding="utf-8")
src_sp = (REPO / "app/ui/studio_page.py").read_text(encoding="utf-8")
ok("dau_vao_hashtag" in src_jobs and 'pre.get("nguon")' in src_jobs,
   "jobs: hashtag sinh sẵn đi qua cửa chung + bộ đệm so 'nguon'")
ok("dau_vao_hashtag" in src_sp and 'pre.get("nguon")' in src_sp,
   "studio_page: hashtag đi qua cửa chung + bộ đệm so 'nguon'")
ok("ten_nguon=src_p" in src_sp, "đặt tên Part truyền tên file gốc")

print("CA 5: quét tĩnh dấu khong_loi vào signals")
src = (REPO / "app/modules/m1_highlight.py").read_text(encoding="utf-8")
cay = ast.parse(src)


def _gan_khoa(ham):
    for n in ast.walk(ham):
        if (isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Subscript)
                and isinstance(n.targets[0].value, ast.Name)
                and n.targets[0].value.id == "signals"
                and isinstance(n.targets[0].slice, ast.Constant)
                and n.targets[0].slice.value == "khong_loi"):
            return True
    return False


ham = {f.name: f for f in cay.body if isinstance(f, ast.FunctionDef)}
ok(_gan_khoa(ham["generate_highlights"]), "đường AI gắn signals['khong_loi']")
ok(_gan_khoa(ham["_generate_heuristic"]), "đường cắt cơ bản gắn signals['khong_loi']")

print(f"\nCỔNG 109: ĐẠT {DAT} · HỎNG {HONG}")
sys.exit(1 if HONG else 0)
