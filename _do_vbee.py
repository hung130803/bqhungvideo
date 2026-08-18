# -*- coding: utf-8 -*-
"""ĐO giong_vbee.py — KHÔNG gọi API thật, KHÔNG tốn một điểm nào của anh Hùng.

Chứng minh 5 điều trước khi tin module:
  1. CHƯA CÓ KEY -> lùi edge-tts ÊM (ok toàn False), KHÔNG ném.
  2. Phân loại lỗi ĐÚNG BẢNG (401 phạt key · 413/429/500-credit KHÔNG phạt).
  3. HẾT ĐIỂM giữa mẻ -> bỏ CẢ video (không lẫn hai giọng) + ghi ĐÍCH DANH.
  4. KEY KHÔNG BAO GIỜ lọt ra log/nhãn/kết quả.
  5. Nhãn tiếng Việt, KHÔNG EMOJI.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
_SB = Path(tempfile.mkdtemp(prefix="bq_vbee_"))
os.environ["BQ_DATA_DIR"] = str(_SB)
os.environ.pop("VBEE_APP_ID", None)
os.environ.pop("VBEE_TOKEN", None)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core import giong_vbee as gv  # noqa: E402

DAT = HONG = 0


def ok(dieu: str, tot: bool, ghi: str = "") -> None:
    global DAT, HONG
    if tot:
        DAT += 1
        print(f"  DAT   {dieu}" + (f"  [{ghi}]" if ghi else ""))
    else:
        HONG += 1
        print(f"  HONG  {dieu}" + (f"  [{ghi}]" if ghi else ""))


KEY_GIA_ID = "appid-gia-1234567890"
KEY_GIA_TOKEN = "eyJhbGciOiJIUzI1NiJ9.GIA-KHONG-CO-THAT.abcdef123456"


def wav_that(giay: float = 0.4) -> bytes:
    """WAV THẬT (im lặng) để giả lập byte Vbee trả về.

    BẪY ĐÃ SẬP 1 LẦN khi viết chính file này: bản đầu trả `b"\\x00"*4000` —
    ffmpeg từ chối ĐÚNG LUẬT nên lượt đọc chết ở bước GHI FILE, không bao giờ
    đi tới nhánh `het_diem` đang cần đo. Mục 3 khi đó vẫn "ok[] toàn False" nên
    trông như ĐẠT, nhưng nó ĐẠT VÌ LÝ DO KHÁC HẲN — đúng họ bẫy "phép đo phát
    chứng nhận cho thứ chưa hề được kiểm".
    """
    import io
    import wave as _w
    buf = io.BytesIO()
    with _w.open(buf, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(24000)
        f.writeframes(b"\x00\x00" * int(24000 * giay))
    return buf.getvalue()


def doc_log() -> str:
    p = _SB / "logs"
    if not p.is_dir():
        return ""
    return "\n".join(f.read_text(encoding="utf-8", errors="replace")
                     for f in p.glob("giong_vbee_*.log"))


print("\n=== 1. CHUA CO KEY -> LUI EM ===")
ok("co_key() = False khi chua dat gi", gv.co_key() is False)
tt = gv.tinh_trang_vbee()
ok("tinh_trang bao thieu ca 2 thu", len(tt["thieu"]) == 2, str(tt["thieu"]))
gv.xoa_so_lui()
try:
    okk, words = gv.doc_loat(["Xin chao anh Hung.", "Cau thu hai."],
                             [str(_SB / "a.wav"), str(_SB / "b.wav")],
                             "vbee:ngochuyen", nhan_video="video_thu.mp4")
    nem = False
except Exception as e:  # noqa: BLE001
    okk, words, nem = [], [], True
    print(f"    (da nem: {type(e).__name__}: {e})")
ok("doc_loat KHONG nem khi thieu key", not nem)
ok("ok[] toan False -> caller lui edge", okk == [False, False], str(okk))
ok("words[] toan rong", words == [[], []])
ok("so_lui ghi DICH DANH ten video",
   len(gv.so_lui()) == 1 and gv.so_lui()[0][0] == "video_thu.mp4",
   str(gv.so_lui()))
ok("bao_cao_lui co chu 'edge-tts'", "edge-tts" in gv.bao_cao_lui())
ok("nhan giong noi ro CAN KEY", gv.CAN_KEY in gv.nhan_giong("vbee:ngochuyen"),
   gv.nhan_giong("vbee:ngochuyen"))

print("\n=== 2. PHAN LOAI LOI (bang o VbeeError) ===")
BANG = [
    (401, "unauthorized", "key_sai", True),
    (403, "forbidden", "key_sai", True),
    (413, "Request too large", "qua_to", False),
    (429, "TTS_CCR_MAX_LIMIT_REACHED", "qua_tai", False),
    (500, "TTS_SPEND_CREDITS_FAILED", "het_diem", False),
    (400, "webhookUrl must be defined", "loi_app", False),
    (503, "service unavailable", "khac", False),
]
for code, than, mong, phat in BANG:
    e = gv._phan_loai(code, than)
    ok(f"HTTP {code} -> kind={mong}, phat_key={phat}",
       e.kind == mong and e.phat_key is phat, f"ra kind={e.kind}")

print("\n=== 3. HET DIEM GIUA ME -> BO CA VIDEO ===")
os.environ["VBEE_APP_ID"] = KEY_GIA_ID
os.environ["VBEE_TOKEN"] = KEY_GIA_TOKEN
ok("co_key() = True khi da dat ca 2", gv.co_key() is True)

_that = gv._doc_mot
_dem = {"n": 0}


def _gia_het_diem(text, voice_code, speed, timeout):
    _dem["n"] += 1
    if _dem["n"] <= 2:
        return wav_that()          # 2 cau dau "doc duoc"
    raise gv.VbeeError("het_diem", "Tai khoan Vbee het diem: "
                                   "TTS_SPEND_CREDITS_FAILED")


gv._doc_mot = _gia_het_diem
gv.xoa_so_lui()
okk2, w2 = gv.doc_loat(["Cau mot.", "Cau hai.", "Cau ba.", "Cau bon."],
                       [str(_SB / f"h{i}.wav") for i in range(4)],
                       "vbee:ngochuyen", lay_moc=False,
                       nhan_video="video_het_diem.mp4")
gv._doc_mot = _that
ok("het diem -> ok[] TOAN False (khong lan 2 giong)",
   okk2 == [False] * 4, str(okk2))
ok("ghi DICH DANH video bi lui",
   len(gv.so_lui()) == 1 and gv.so_lui()[0][0] == "video_het_diem.mp4",
   str(gv.so_lui()))
ok("ly do noi ro HET DIEM", "HẾT ĐIỂM" in gv.so_lui()[0][1],
   gv.so_lui()[0][1])
ok("ly do noi ro KHONG khoa key", "KHÔNG bị khoá" in gv.so_lui()[0][1])

print("\n=== 3b. KEY SAI -> bao dung benh ===")


def _gia_key_sai(text, voice_code, speed, timeout):
    # Server doi khi DOI LAI chinh chuoi minh gui len -> bay ro key.
    raise gv.VbeeError("key_sai", f"Vbee tu choi key (HTTP 401): "
                                  f"Bearer {KEY_GIA_TOKEN} invalid")


gv._doc_mot = _gia_key_sai
gv.xoa_so_lui()
okk3, _ = gv.doc_loat(["Cau mot."], [str(_SB / "k.wav")], "vbee:ngochuyen",
                      lay_moc=False, nhan_video="video_key_sai.mp4")
gv._doc_mot = _that
ok("key sai -> lui em, ok[] False", okk3 == [False])
ok("ly do noi 'KEY SAI'", "KEY SAI" in gv.so_lui()[0][1], gv.so_lui()[0][1])

print("\n=== 4. KEY KHONG BAO GIO LOT RA ===")
log = doc_log()
ok("log KHONG chua token that", KEY_GIA_TOKEN not in log)
ok("log KHONG chua app_id that", KEY_GIA_ID not in log)
ok("log co ban CHE (dau sao)", "*" in log)
ok("so_lui KHONG chua token", all(KEY_GIA_TOKEN not in x for _n, x in
                                  gv.so_lui()))
ok("tinh_trang KHONG tra token nguyen van",
   KEY_GIA_TOKEN not in str(gv.tinh_trang_vbee()))
ok("che_key giu 4 ky tu cuoi", gv.che_key(KEY_GIA_TOKEN).endswith(
    KEY_GIA_TOKEN[-4:]) and KEY_GIA_TOKEN[:20] not in gv.che_key(KEY_GIA_TOKEN),
   gv.che_key(KEY_GIA_TOKEN))
ok("che_key chuoi ngan -> che HET", set(gv.che_key("abc123")) == {"*"})
ok("_loc_bi_mat va duoc key lot vao chuoi la",
   KEY_GIA_TOKEN not in gv._loc_bi_mat(f"loi: Bearer {KEY_GIA_TOKEN}"),
   gv._loc_bi_mat(f"loi: Bearer {KEY_GIA_TOKEN}"))

print("\n=== 5. NHAN: TIENG VIET, KHONG EMOJI ===")


def co_emoji(s: str) -> bool:
    return any(ord(c) > 0x2100 for c in s)


for ma, nhan in gv.danh_sach_giong():
    ok(f"nhan {ma} khong emoji", not co_emoji(nhan), nhan[:70])
ok("3 nhan canh bao khong emoji",
   not any(co_emoji(x) for x in (gv.CANH_BAO_MOC, gv.CANH_BAO_TIEN,
                                 gv.CANH_BAO_FREE)))
ok("canh bao FREE noi 'KHONG noi ro' (khong phan bua)",
   "KHÔNG nói rõ" in gv.CANH_BAO_FREE)

print("\n=== 6. DEM KY TU / DIEM TRUOC KHI CHAY ===")
cau = ["Xin chao cac ban.", "Hom nay troi dep."]
mong = sum(len(" ".join(c.split())) for c in cau)
ok("uoc_ky_tu dem dung chuoi SE GUI", gv.uoc_ky_tu(cau) == mong,
   f"{gv.uoc_ky_tu(cau)} vs {mong}")
ok("uoc_ky_tu bo xuong dong/khoang trang thua",
   gv.uoc_ky_tu(["a  \n  b"]) == 3, str(gv.uoc_ky_tu(["a  \n  b"])))
ok("uoc_diem = ky tu (1 diem/1 ky tu)", gv.uoc_diem(cau) == gv.uoc_ky_tu(cau))
cb = gv.canh_bao_truoc_me(cau, so_video=200)
ok("canh bao truoc me co so ky tu", str(mong) in cb.replace(".", ""), cb[:80])
ok("canh bao NOI THANG la khong biet so du",
   "không biết trước" in cb)
ok("canh bao rong khi khong co chu", gv.canh_bao_truoc_me([]) == "")

print("\n=== 7. TOC DO: dung num speed cua Vbee, kep dung dai ===")
ok("+0% -> 1.0", abs(gv._speed_tu_rate("+0%") - 1.0) < 1e-9)
ok("+25% -> 1.25", abs(gv._speed_tu_rate("+25%") - 1.25) < 1e-9)
ok("+200% kep ve tran 1.9", abs(gv._speed_tu_rate("+200%") - 1.9) < 1e-9)
ok("-90% kep ve san 0.25", abs(gv._speed_tu_rate("-90%") - 0.25) < 1e-9)
ok("rac -> 1.0 (khong nem)", abs(gv._speed_tu_rate("xyz") - 1.0) < 1e-9)

print("\n=== 8. 3 GIONG ANH HUNG NEU ===")
ma_vc = {m: vc for m, vc, _ in gv.GIONG_VBEE}
ok("co Ngoc Huyen", ma_vc.get("vbee:ngochuyen") ==
   "hn_female_ngochuyen_full_48k-fhg")
ok("co Anh Khoi (2 kieu)",
   sum(1 for m in ma_vc if m.startswith("vbee:anhkhoi")) == 2)
ok("Minh Quan KHONG bi bia ma",
   not any("minhquan" in m or "minhquan" in v for m, v in ma_vc.items()))
ok("Minh Quan duoc ghi la CHUA THAY",
   any("Minh Quân" in x for x in gv.GIONG_CHUA_THAY))
ok("giong la -> lui em", gv.doc_loat(["a"], [str(_SB / "x.wav")],
                                     "vbee:khong-co-that",
                                     lay_moc=False)[0] == [False])
ok("goi nham giong edge -> lui em",
   gv.doc_loat(["a"], [str(_SB / "y.wav")], "vi-VN-NamMinhNeural",
               lay_moc=False)[0] == [False])

print("\n=== 9. TU KIEM BO DO (go chot ra thi PHAI do) ===")
_luu = gv.TY_LE_TOI_THIEU
_dem["n"] = 0


def _gia_1_cau_hong(text, voice_code, speed, timeout):
    _dem["n"] += 1
    if _dem["n"] == 2:
        raise gv.VbeeError("khac", "gia vo cau 2 hong")
    return wav_that()


gv._doc_mot = _gia_1_cau_hong
gv.xoa_so_lui()
r_chot, _ = gv.doc_loat(["m", "h", "b"], [str(_SB / f"z{i}.wav")
                                          for i in range(3)],
                        "vbee:ngochuyen", lay_moc=False, nhan_video="v.mp4")
gv._doc_mot = _that
ok("1 cau hong -> BO CA LOAT (chong lan 2 giong)", r_chot == [False] * 3,
   str(r_chot))

print("\n" + "=" * 62)
print(f"DAT {DAT} · HONG {HONG}")
print(f"(log sandbox: {_SB})")
sys.exit(1 if HONG else 0)
