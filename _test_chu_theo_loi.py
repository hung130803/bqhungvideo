# -*- coding: utf-8 -*-
"""CỔNG 60 — CHỮ CHẠY THEO LỜI · DỊCH KHÔNG SÓT CHỮ GỐC · CÂN MỨC GIỌNG-NHẠC.

Canh đúng 3 lỗi anh Hùng báo 15/08/2026 trên đường THAY GIỌNG:

  LỖI 1 *"nói đến đâu chữ hiện đến đó chứ không hiện hàng loạt ra chữ như thế
          kia"* -> `dong_chu_theo_giong` phải cắt câu thành CỤM, mốc lấy từ
          WordBoundary, KHÔNG hở KHÔNG chồng.
  LỖI 2 *"âm thanh sau khi tách lỗi hết, chỗ có chỗ không nghe không được"*
          -> giọng mới bị nhạc nền dìm 9,3 dB; `can_bang_giong_nhac` phải ĐO
          rồi tính hệ số, và fail-safe khi đo hỏng.
  LỖI 3 *"dịch còn lỗi, còn có cả tiếng Trung không hiểu"* -> `con_chu_goc`
          phải bắt chữ Hán sót VÀ không báo động giả khi đích LÀ tiếng Trung.

Toàn HÀM THUẦN + ffmpeg (không mạng, không Groq) nên chạy nhanh và không nhấp
nháy. Cổng nào cần thành phần thật thì đã có cổng 53/55/57.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core import thay_giong as tg          # noqa: E402

DAT = FAIL = 0


def dat(ten: str, ok: bool, ghi: str = "") -> None:
    global DAT, FAIL
    if ok:
        DAT += 1
        print(f"  DAT  {ten}" + (f"  ({ghi})" if ghi else ""))
    else:
        FAIL += 1
        print(f"  HONG {ten}" + (f"  ({ghi})" if ghi else ""))


# ==================================================================
print("=== CA 1: con_chu_goc — bat chu sot, KHONG bao dong gia ===")
# ==================================================================
dat("dich sang tieng Viet ma con chu Han -> BAT",
    tg.con_chu_goc("Bo thu tu la Lien minh复仇", "vi"))
dat("dich sang tieng Anh ma con kana -> BAT",
    tg.con_chu_goc("The movie ドラゴン is great", "en"))
dat("ban dich sach -> KHONG bat",
    not tg.con_chu_goc("Bo thu tu la Lien minh Bao thu", "vi"))
# CUA NGON NGU DICH — day la cho de bao dong gia 100%
for ma in ("zh", "Chinese", "ja", "ko", "th"):
    dat(f"dich SANG {ma} -> chu do la KET QUA DUNG, khong bat",
        not tg.con_chu_goc("这时医生灵机一动", ma))
dat("chuoi rong -> khong bat", not tg.con_chu_goc("", "vi"))
dat("None -> khong bat", not tg.con_chu_goc(None, "vi"))     # type: ignore

# ==================================================================
print("\n=== CA 2: chia_cum_theo_tu — moc tu WordBoundary ===")
# ==================================================================
TXT = "Bo dau tien la Chien binh ngam, noi ve mot vo si xuong day xa hoi."
MOC = []
_t = 0.0
for _w in TXT.replace(",", "").replace(".", "").split():
    MOC.append([round(_t, 3), round(_t + 0.3, 3), _w])
    _t += 0.35
cum = tg.chia_cum_theo_tu(TXT, MOC, tran=30)
dat("cat ra NHIEU cum", len(cum) >= 3, f"{len(cum)} cum")
dat("moi cum <= tran ky tu (+dau cau)",
    all(len(c[2]) <= 30 + 4 for c in cum),
    f"max {max(len(c[2]) for c in cum)}")
dat("moc TANG DAN", all(cum[i][0] <= cum[i + 1][0]
                        for i in range(len(cum) - 1)))
dat("cum dau bat dau tu moc tu DAU TIEN", abs(cum[0][0] - MOC[0][0]) < 1e-6,
    f"{cum[0][0]}")
dat("KHONG mat chu: noi lai du tu",
    all(w in " ".join(c[2] for c in cum) for w in ("Bo", "ngam", "hoi")))
dat("giu DAU CAU (dau phay/cham)",
    "," in " ".join(c[2] for c in cum) and "." in " ".join(c[2] for c in cum))
# moc RONG -> tra [] de caller lui duong khac
dat("khong co moc tu -> tra [] (de caller tu lui)",
    tg.chia_cum_theo_tu(TXT, []) == [])
dat("moc KHONG khop chu nao -> tra []",
    tg.chia_cum_theo_tu(TXT, [[0.0, 0.2, "zzz"]]) == [])
# tu LAP LAI phai khop dung lan xuat hien cua no
_l = tg._khop_tu_vao_chu("the cat and the dog",
                         [[0.0, .1, "the"], [.2, .3, "cat"],
                          [.4, .5, "the"], [.6, .7, "dog"]])
dat("tu LAP LAI khop dung lan xuat hien", [x[0] for x in _l] == [0, 4, 12, 16],
    str([x[0] for x in _l]))

# ==================================================================
print("\n=== CA 3: dong_chu_theo_giong — khong ho, khong chong ===")
# ==================================================================
moc_tieng = [(0, 1.0, 6.0), (1, 7.0, 9.0)]
texts = [TXT, "Cau thu hai ngan hon nhieu."]
moc_tu = [(0, [[1.0 + i * 0.35, 1.0 + i * 0.35 + 0.3, w]
               for i, w in enumerate(TXT.replace(",", "")
                                     .replace(".", "").split())])]
ds = tg.dong_chu_theo_giong(moc_tieng, texts, moc_tu=moc_tu)
dat("cau DAI bi cat nho", len(ds) > 2, f"{len(ds)} dong")
dat("KHONG dong nao vuot tran ky tu qua nhieu",
    max(len(d[2]) for d in ds) <= tg.TRAN_KY_TU_CUM + 6,
    f"max {max(len(d[2]) for d in ds)}")
dat("moi dong co do dai duong", all(d[1] > d[0] for d in ds))
_chong = [(ds[i], ds[i + 1]) for i in range(len(ds) - 1)
          if ds[i][1] > ds[i + 1][0] + 1e-6]
dat("KHONG dong nao CHONG dong ke", not _chong, str(_chong[:1]))
dat("cau 1 KHONG lan sang moc noi cua cau 2",
    max(d[1] for d in ds if d[0] < 7.0) <= 7.0 - tg.CHU_CHUA_TRUOC_S + 1e-6)
dat("dong dau bat dau DUNG moc noi", abs(ds[0][0] - 1.0) < 1e-6)
# khong co moc tu -> VAN phai cat nho (duong lui theo ti le)
ds2 = tg.dong_chu_theo_giong(moc_tieng, texts)
dat("KHONG co moc tu van cat nho (duong lui)", len(ds2) > 2, f"{len(ds2)}")
dat("duong lui cung khong chong lan",
    all(ds2[i][1] <= ds2[i + 1][0] + 1e-6 for i in range(len(ds2) - 1)))
# BAT BIEN cu: cau NGAN van ra 1 dong, moc dung
_d1 = tg.dong_chu_theo_giong([(0, 1.0, 1.4), (1, 3.0, 3.9)], ["mot", "hai"])
dat("cau NGAN van ra dung 1 dong/cau (bat bien cong 53)",
    len(_d1) == 2 and abs(_d1[0][0] - 1.0) < 1e-6
    and abs(_d1[1][0] - 3.0) < 1e-6, str(_d1))
dat("chu toi thieu 0,90s va khong lan cau ke (bat bien cong 53)",
    _d1[0][1] >= 1.85 and _d1[0][1] <= 3.0 - 0.05, str(_d1[0]))
dat("texts rong -> bo qua, khong no",
    tg.dong_chu_theo_giong([(0, 1.0, 2.0)], [""]) == [])

# ==================================================================
print("\n=== CA 4: doi_moc_tu — tru phan da cat le im ===")
# ==================================================================
_m = tg.doi_moc_tu([[0.20, 0.50, "a"], [0.60, 0.90, "b"]], 0.16, 1.0)
dat("moc bi tru dung so giay da cat",
    abs(_m[0][0] - 0.04) < 1e-6 and abs(_m[1][0] - 0.44) < 1e-6, str(_m))
dat("moc am bi kep ve 0",
    tg.doi_moc_tu([[0.05, 0.10, "a"]], 0.20)[0][0] == 0.0)
dat("kep tran theo do dai",
    tg.doi_moc_tu([[0.5, 9.0, "a"]], 0.0, 2.0)[0][1] == 2.0)
dat("moc rac -> bo qua, khong no", tg.doi_moc_tu([["x", None, "a"]], 0.0) == [])

# ==================================================================
print("\n=== CA 5: _tham_so_duck — nguong BAM muc nhac ===")
# ==================================================================
n1, r1 = tg._tham_so_duck(-11.37)
n2, _r2 = tg._tham_so_duck(-25.0)
dat("nguong bam theo muc nhac (nhac nho -> nguong nho)", n2 < n1,
    f"{n2:.5f} < {n1:.5f}")
dat("nguong dat duoi muc nhac dung DUCK_TREN_NGUONG_DB",
    abs(20 * __import__("math").log10(n1) - (-11.37 - tg.DUCK_TREN_NGUONG_DB))
    < 1e-6)
dat("ratio = hang so DA DO, khong tinh tu cong thuc",
    abs(r1 - tg.DUCK_RATIO) < 1e-9, f"{r1}")
dat("nguong luon nam trong (0, 1]", 0 < n1 <= 1 and 0 < n2 <= 1)

# ==================================================================
print("\n=== CA 6: can_bang_giong_nhac — FAIL-SAFE khi do hong ===")
# ==================================================================
import tempfile                                            # noqa: E402
import atexit                                              # noqa: E402
import shutil                                              # noqa: E402

_sb = Path(tempfile.mkdtemp(prefix="chutheoloi_"))
atexit.register(lambda: shutil.rmtree(_sb, ignore_errors=True))

_im = _sb / "im.wav"
tg._ffmpeg(["-f", "lavfi", "-t", "2.0", "-i", "anullsrc=r=44100:cl=stereo",
            "-c:a", "pcm_s16le", str(_im)], "dung file im")
_kq = tg.can_bang_giong_nhac(_im, _im)
dat("hai track IM -> do_duoc=False, he so 0 (khong nhan he so bia)",
    not _kq["do_duoc"] and _kq["gain_giong_db"] == 0.0
    and _kq["gain_nhac_db"] == 0.0, str(_kq.get("ly_do")))
_ngan = _sb / "ngan.wav"
tg._ffmpeg(["-f", "lavfi", "-t", "0.3", "-i", "sine=f=440:r=44100",
            "-ac", "2", "-c:a", "pcm_s16le", str(_ngan)], "file qua ngan")
dat("file qua ngan -> do_duoc=False", not tg.can_bang_giong_nhac(
    _ngan, _ngan)["do_duoc"])
dat("duong_bao_muc file khong ton tai -> [] (khong no)",
    tg.duong_bao_muc(_sb / "khong_co.wav") == [])

# ==================================================================
print("\n=== CA 7: THU PHA — go bo cat cum thi bang phai DO ===")
# ==================================================================
# Dua CA CAU vao lam mot cum duy nhat (dung cach ban CU lam) -> phai vuot tran
_pha = tg.dong_chu_theo_giong(moc_tieng, texts, moc_tu=moc_tu,
                              tran=10**6)
dat("tran vo han -> ra 1 dong/cau va VUOT tran that (bo do co keu)",
    len(_pha) == 2 and max(len(d[2]) for d in _pha) > tg.TRAN_KY_TU_CUM,
    f"{len(_pha)} dong, max {max(len(d[2]) for d in _pha)} ky tu")

print(f"\n{'=' * 60}\nDAT {DAT} · HONG {FAIL}")
raise SystemExit(0 if FAIL == 0 else 1)
