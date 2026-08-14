# -*- coding: utf-8 -*-
"""CỔNG 59 — TÊN VIDEO DÀI KHÔNG ĐƯỢC GIẾT LƯỢT THAY GIỌNG (`WinError 206`).

LỖI THẬT anh Hùng gặp 14/08/2026: chạy "Thay giọng nói" trên 6 video reup
tiếng Trung ra **4 Xong · 2 Lỗi**, hai dòng lỗi ghi::

    FileNotFoundError: [WinError 206] The filename or extension is too long

**TÊN LỖI DẪN THẲNG TỚI CHẨN ĐOÁN SAI.** Nó nghe y hệt "đường dẫn vượt
`MAX_PATH` 260", nhưng đo ra (`_do_duong_dai.py`) đường dài nhất của cả lượt
chỉ **183 ký tự** — 0/6 video vượt. Con số "150 ký tự" đọc được lúc đầu là
**BYTE UTF-8** (`${#f}` của bash), không phải KÝ TỰ: chữ Hán 3 byte/ký tự.

Nguyên nhân THẬT (`_do_cmdline.py` + `_do_206.py`): `CreateProcess` từ chối khi
**DÒNG LỆNH** vượt ~32.767 ký tự, và nó trả về đúng mã 206. Chỗ phình là
`thay_giong._ghep_track_giong` — MỖI CÂU một `-i <đường dẫn wav>` cộng một
`adelay`, ~170 ký tự/câu. Video 484,9s = 278 câu = **47.794 ký tự**.

Vì vậy dấu hiệu "hai video TÊN DÀI NHẤT bị lỗi" chỉ đúng một nửa: tên dài làm
mỗi đường dẫn dài thêm, nhưng thứ nhân lên 278 lần là **SỐ CÂU** — tức ĐỘ DÀI
VIDEO. Đo lại đúng: 2 video lỗi là 2 video DÀI NHẤT (484,9s · 403,0s), còn
video tên 58 ký tự (dài hơn một trong hai video lỗi) thì XONG.

Chạy: `.venv\\Scripts\\python _test_duong_dai.py`
Mốc đối chứng: `BQ_MOC_REF=v2.27.1` (bản anh Hùng đang chạy).
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

import _test_guard                                          # noqa: E402,F401

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                            # noqa: BLE001
    pass

_NOWIN = 0x0800_0000 if os.name == "nt" else 0
SB = REPO / f"bq_test_dd_{os.getpid()}"

DAT = 0
HONG = 0


def bao(ten: str, ok: bool, chi_tiet: str = "") -> None:
    global DAT, HONG
    if ok:
        DAT += 1
    else:
        HONG += 1
    print(f"  [{'ĐẠT' if ok else 'HỎNG'}] {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))


# ------------------------------------------------------------------ dụng cụ
#: Tên kiểu anh Hùng: tiêu đề tiếng Trung đầy đủ + hashtag. 56 ký tự = đúng
#: video `（完整）男孩励志…` đã lỗi thật.
TEN_DAI = "（完整）男孩励志要出去闯荡一番，可村长却禁止他出村半步 #我的观影报告 #影视解说 #犯罪电影 #宅家dou剧场"
#: CÙNG tiêu đề, chỉ khác HASHTAG ở cuối — đây là ca trùng phần đầu THẬT hay
#: gặp nhất ở video reup (cùng phim, đăng lại với bộ hashtag khác), và nó
#: trùng nhau tới 40+ ký tự đầu nên cắt cụt không băm là ra CÙNG thư mục tạm.
TEN_DAI_2 = "（完整）男孩励志要出去闯荡一番，可村长却禁止他出村半步 #我的观影报告 #影视解说 #求生电影 #宅家dou剧场"
TEN_NGAN = "video ngan"


def ffmpeg(args: list[str], timeout: int = 300) -> int:
    from config import settings
    cmd = [settings.FFMPEG_PATH, "-y", "-hide_banner", "-loglevel", "error",
           *args]
    p = _test_guard.chay_that(cmd, capture_output=True, timeout=timeout,
                              creationflags=_NOWIN)
    return p.returncode


def lam_manh(n: int, thu_muc: Path, cach: float = 0.5,
             dai: float = 0.22) -> list[tuple[float, str]]:
    """`n` mảnh wav đặt cách nhau `cach` giây.

    Sinh MỘT file rồi CHÉP ra `n` bản — sinh từng file bằng ffmpeg là `n` lượt
    spawn (278 lượt ~ 40 giây), không đáng.
    """
    thu_muc.mkdir(parents=True, exist_ok=True)
    goc = thu_muc / "khop_0000.wav"
    ffmpeg(["-f", "lavfi", "-i", f"sine=frequency=440:duration={dai}:r=44100",
            "-ac", "2", "-c:a", "pcm_s16le", str(goc)])
    manh = [(0.0, str(goc))]
    for i in range(1, n):
        dst = thu_muc / f"khop_{i:04d}.wav"
        shutil.copyfile(goc, dst)
        manh.append((round(i * cach, 3), str(dst)))
    return manh


def nap_moc() -> tuple[object, str]:
    """Nạp `app/core/thay_giong.py` của BẢN MỐC thành module riêng."""
    moc = os.environ.get("BQ_MOC_REF", "v2.27.1")
    r = subprocess.run(["git", "-C", str(REPO), "show",
                        f"{moc}:app/core/thay_giong.py"],
                       capture_output=True, creationflags=_NOWIN, timeout=60)
    out = (r.stdout or b"").decode("utf-8", errors="replace")
    if r.returncode != 0 or len(out) < 5000:
        bao(f"lấy được thay_giong.py của `{moc}`", False,
            f"git rc={r.returncode} · {len(out)} ký tự")
        return None, moc
    nay = (REPO / "app" / "core" / "thay_giong.py").read_text(
        encoding="utf-8", errors="replace")
    # CHỐNG PASS OAN: mốc TRÙNG file đang test = "so nó với chính nó". Ở cổng
    # NÀY nó còn nguy hơn cổng bất-biến thường: CA 1 đòi bản mốc phải NỔ, mốc
    # trùng bản đã vá thì nó KHÔNG nổ và ta kết luận ngược hẳn.
    if out.strip() == nay.strip():
        bao(f"mốc `{moc}` phải KHÁC bản đang test", False,
            "git show trả về CHÍNH file đang test -> CA 1 không tái hiện được "
            "lỗi. Đặt BQ_MOC_REF về commit TRƯỚC bản vá.")
        return None, moc
    f = SB / "tg_moc.py"
    f.write_text(out, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("tg_moc", str(f))
    if spec is None or spec.loader is None:
        bao("nạp được module mốc", False, "spec/loader None")
        return None, moc
    m = importlib.util.module_from_spec(spec)
    sys.modules["tg_moc"] = m
    try:
        spec.loader.exec_module(m)
    except Exception as e:                                   # noqa: BLE001
        bao("nạp được module mốc", False, f"{type(e).__name__}: {e}")
        return None, moc
    return m, moc


def duong_khop(goc: Path, ten: str) -> Path:
    """Thư mục `khop` THẬT mà app sẽ dùng cho video tên `ten` (đọc từ mã thật)."""
    from app.core.tg_chay import thu_muc_lam_cho
    return Path(thu_muc_lam_cho(goc / "nguon" / f"{ten}.mp4",
                                str(goc / "xuất"))) / "khop"


def do_rms(path: Path, start: float = 0.0, dur: float = 0.0) -> float:
    """RMS trong MỘT CỬA SỔ — cắt bằng `atrim`, KHÔNG dùng `-ss`.

    **KHÔNG gọi `thay_giong.do_rms` cho phép đo cửa sổ.** Hàm đó đặt `-ss`
    TRƯỚC `-i` (seek nhanh, nhảy theo gói của demuxer) nên cửa sổ hẹp rơi lệch
    chỗ: đo bản đầu của cổng này ra **0,033** ở một khoảng LẶNG (mảnh bên cạnh
    0,053) và suýt kết luận oan là "chia mẻ làm mảnh trôi mốc". Đo lại đúng
    khoảng đó bằng `atrim`: **-inf = im lặng tuyệt đối**, mảnh nằm đúng mốc.
    Đây là bản anh em của bẫy `startswith`/`astats` (cổng 44/53): phép đo hỏng
    thì kết luận sai theo CẢ HAI chiều, lần này là báo động GIẢ.
    """
    from config import settings
    af = ""
    if dur > 0:
        af = f"atrim=start={start:.4f}:end={start + dur:.4f},"
    elif start > 0:
        af = f"atrim=start={start:.4f},"
    r = _test_guard.chay_that(
        [settings.FFMPEG_PATH, "-hide_banner", "-nostats", "-i", str(path),
         "-map", "0:a:0", "-af",
         f"{af}astats=measure_overall=RMS_level:measure_perchannel=none",
         "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=600, creationflags=_NOWIN)
    for line in (r.stderr or "").splitlines():
        if "RMS level dB:" in line:                  # `in`, KHÔNG startswith
            raw = line.split(":")[-1].strip()
            if raw.lower().lstrip("-") in ("inf", "nan"):
                return 0.0
            try:
                return 10.0 ** (float(raw) / 20.0)
            except ValueError:
                return -1.0
    return -1.0


# ------------------------------------------------------------------- các ca
def ca1_tai_hien(moc, ten_moc: str) -> Path | None:
    """CA 1 — bản CŨ phải NỔ WinError 206, bản MỚI phải chạy trót lọt."""
    print(f"\n[CA 1] TÁI HIỆN LỖI trên tên kiểu anh Hùng (mốc `{ten_moc}`)")
    from app.core import thay_giong as tg

    goc = SB / "ca1"
    kh = duong_khop(goc, TEN_DAI)
    n = 278                                      # đúng số câu video 484,9s
    manh = lam_manh(n, kh)
    tong = n * 0.5 + 1.0
    ra_moc = kh.parent / "tieng_moi_moc.wav"
    ra_moi = kh.parent / "tieng_moi.wav"
    dai_cmd = tg._dai_dong_lenh(tg._args_ghep(manh, tong, ra_moc))
    print(f"       {n} mảnh · đường dẫn wav {len(manh[0][1])} ký tự · "
          f"dòng lệnh {dai_cmd} ký tự (trần {tg.TRAN_CMD_WINDOWS})")

    if moc is not None:
        try:
            moc._ghep_track_giong(manh, tong, ra_moc)
            bao(f"bản mốc `{ten_moc}` NỔ WinError 206", False,
                "nó CHẠY ĐƯỢC -> ca này không tái hiện được lỗi, mọi kết luận "
                "phía sau vô nghĩa")
        except OSError as e:
            we = getattr(e, "winerror", None)
            bao(f"bản mốc `{ten_moc}` NỔ WinError 206", we == 206,
                f"{type(e).__name__} WinError {we}: {str(e)[:70]}")
        except Exception as e:                               # noqa: BLE001
            bao(f"bản mốc `{ten_moc}` NỔ WinError 206", False,
                f"nổ nhưng KHÁC loại: {type(e).__name__}: {str(e)[:90]}")

    try:
        tg._ghep_track_giong(manh, tong, ra_moi)
        bao("bản MỚI chạy trót lọt", ra_moi.exists() and
            ra_moi.stat().st_size > 10240,
            f"{ra_moi.stat().st_size // 1024 if ra_moi.exists() else 0} KiB")
    except Exception as e:                                   # noqa: BLE001
        bao("bản MỚI chạy trót lọt", False, f"{type(e).__name__}: {e}")
        return None
    return ra_moi


def ca2_file_ra(ra: Path | None) -> None:
    """CA 2 — file ffmpeg ĐẺ RA phải có tiếng, đúng độ dài, RMS > 0."""
    print("\n[CA 2] CHẠY THẬT ffmpeg — kiểm FILE RA (mã 0 mà file rỗng đã xảy ra)")
    if ra is None:
        bao("có file để kiểm", False, "CA 1 không ra file")
        return
    from app.core.thay_giong import probe_duration

    n, cach = 278, 0.5
    tong = n * cach + 1.0
    d = probe_duration(ra)
    bao("đúng độ dài", abs(d - tong) < 0.25, f"{d:.3f}s (mong {tong:.3f}s)")
    rms = do_rms(ra)
    bao("RMS cả file > 0", rms > 0.001, f"RMS {rms:.5f}")

    # MẢNH CUỐI phải CÓ MẶT — đây mới là phép đo nói lên "chia mẻ không mất
    # câu nào". Mảnh cuối nằm ở mẻ CUỐI, tức phần bản cũ chưa bao giờ ghi được.
    t_cuoi = (n - 1) * cach
    r_cuoi = do_rms(ra, t_cuoi + 0.02, 0.15)
    bao("mảnh CUỐI (mẻ cuối) có tiếng", r_cuoi > 0.01,
        f"RMS tại {t_cuoi:.2f}s = {r_cuoi:.5f}")
    r_dau = do_rms(ra, 0.02, 0.15)
    bao("mảnh ĐẦU (mẻ đầu) có tiếng", r_dau > 0.01, f"RMS tại 0,02s = {r_dau:.5f}")
    # khoảng lặng giữa 2 mảnh phải IM -> chứng minh mảnh nằm ĐÚNG MỐC, không
    # bị dồn/trôi khi ghép mẻ
    r_im = do_rms(ra, 0.30, 0.15)
    bao("khoảng lặng vẫn IM (mảnh đúng mốc)", r_im < r_dau / 10.0,
        f"RMS {r_im:.6f} so với mảnh {r_dau:.5f}")


def ca3_chia_me_bang_mot_luot() -> None:
    """CA 3 — CHIA MẺ phải ra ĐÚNG cái mà một lượt ra (phép đo mạnh nhất).

    Lấy số mảnh VỪA một lệnh -> chạy đường một-lượt; rồi HẠ ngân sách để ép
    đúng dữ liệu đó đi đường chia mẻ -> hai file phải giống nhau TỪNG BYTE.
    Đây là cách duy nhất chứng minh "amix normalize=0 là phép cộng" thay vì
    tin vào lời ghi chú.
    """
    print("\n[CA 3] CHIA MẺ == MỘT LƯỢT (so MD5 file wav)")
    from app.core import thay_giong as tg

    goc = SB / "ca3"
    kh = duong_khop(goc, TEN_NGAN)
    n = 40
    manh = lam_manh(n, kh)
    tong = n * 0.5 + 1.0
    a = kh.parent / "mot_luot.wav"
    b = kh.parent / "chia_me.wav"

    cu = tg.NGAN_SACH_CMD
    try:
        tg._ghep_track_giong(manh, tong, a)          # vừa -> một lượt
        tg.NGAN_SACH_CMD = 2500                      # ép chia mẻ
        me = tg._chia_me(manh, tong, b)
        tg._ghep_track_giong(manh, tong, b)
    finally:
        tg.NGAN_SACH_CMD = cu
    ha = hashlib.md5(a.read_bytes()).hexdigest()
    hb = hashlib.md5(b.read_bytes()).hexdigest()
    bao(f"chia được nhiều mẻ ({len(me)} mẻ)", len(me) >= 3,
        f"{len(me)} mẻ cho {n} mảnh")
    bao("chia mẻ ra file GIỐNG TỪNG BYTE bản một lượt", ha == hb,
        f"md5 {ha[:12]} vs {hb[:12]}")


def ca4_khong_de_nhau() -> None:
    """CA 4 — 2 tên DÀI khác nhau, cắt ngắn ra GIỐNG NHAU -> KHÔNG được đè."""
    print("\n[CA 4] KHÔNG ĐÈ NHAU (2 tên trùng phần đầu)")
    from app.core.tg_chay import TEN_TAM_TOI_DA, ten_tam_cho, thu_muc_lam_cho

    goc = SB / "ca4"
    a = goc / "nguon" / f"{TEN_DAI}.mp4"
    b = goc / "nguon" / f"{TEN_DAI_2}.mp4"
    chung = os.path.commonprefix([TEN_DAI, TEN_DAI_2])
    bao(f"hai tên thử NGHIỆM trùng nhau >= {TEN_TAM_TOI_DA} ký tự đầu",
        len(chung) >= TEN_TAM_TOI_DA,
        f"trùng {len(chung)} ký tự đầu — cắt cụt không băm là ra cùng thư mục")
    ta, tb = ten_tam_cho(a), ten_tam_cho(b)
    bao("thư mục tạm KHÁC nhau", ta != tb, f"{ta} vs {tb}")
    bao("thư mục tạm NGẮN", max(len(ta), len(tb)) <= TEN_TAM_TOI_DA + 9,
        f"{len(ta)} và {len(tb)} ký tự")
    # cùng video -> LUÔN cùng thư mục (dọn rác/chạy lại phải tìm lại được)
    bao("cùng video -> cùng thư mục tạm (tiền định)",
        ten_tam_cho(a) == ten_tam_cho(a), ta)
    # cùng TÊN nhưng KHÁC thư mục nguồn -> vẫn phải khác
    c = goc / "nguon2" / f"{TEN_DAI}.mp4"
    bao("trùng tên nhưng khác thư mục nguồn -> vẫn khác",
        ten_tam_cho(a) != ten_tam_cho(c), f"{ta} vs {ten_tam_cho(c)}")
    # và file ĐÍCH vẫn mang TÊN GỐC ĐẦY ĐỦ (anh Hùng phải nhận ra video nào)
    from app.core.tg_so import duong_ra
    ra_a = duong_ra(a, str(goc / "xuất"))
    ra_b = duong_ra(b, str(goc / "xuất"))
    bao("file ĐÍCH giữ NGUYÊN tên gốc đầy đủ",
        Path(ra_a).name == f"{TEN_DAI}.mp4" and Path(ra_b).name == f"{TEN_DAI_2}.mp4",
        f"…{Path(ra_a).name[-24:]}")
    bao("2 file đích KHÁC nhau", ra_a != ra_b)
    _ = thu_muc_lam_cho(a, str(goc / "xuất"))


def ca5_bat_bien(moc, ten_moc: str) -> None:
    """CA 5 — video tên NGẮN phải ra Y HỆT bản mốc (tên file + nội dung)."""
    print(f"\n[CA 5] BẤT BIẾN: video tên NGẮN == bản mốc `{ten_moc}`")
    if moc is None:
        bao("có bản mốc để so", False, "nạp mốc lỗi")
        return
    from app.core import thay_giong as tg

    goc = SB / "ca5"
    kh = duong_khop(goc, TEN_NGAN)
    n = 30
    manh = lam_manh(n, kh)
    tong = n * 0.5 + 1.0

    # (a) DÒNG LỆNH phải giống TỪNG KÝ TỰ -> bắt `_ffmpeg` của cả 2 module
    bat: dict[str, list[str]] = {}

    def _bat(ten):
        def f(args, what, timeout=900):
            bat[ten] = list(args)
        return f
    cu_moi, cu_moc = tg._ffmpeg, moc._ffmpeg
    try:
        tg._ffmpeg = _bat("moi")
        moc._ffmpeg = _bat("moc")
        tg._ghep_track_giong(manh, tong, kh.parent / "x.wav")
        moc._ghep_track_giong(manh, tong, kh.parent / "x.wav")
    finally:
        tg._ffmpeg, moc._ffmpeg = cu_moi, cu_moc
    bao("dòng lệnh ffmpeg GIỐNG TỪNG KÝ TỰ bản mốc",
        bat.get("moi") == bat.get("moc"),
        f"{len(bat.get('moi') or [])} tham số vs {len(bat.get('moc') or [])}")

    # (b) và file ĐẺ RA giống từng byte
    a = kh.parent / "moi.wav"
    b = kh.parent / "moc.wav"
    tg._ghep_track_giong(manh, tong, a)
    moc._ghep_track_giong(manh, tong, b)
    ha = hashlib.md5(a.read_bytes()).hexdigest()
    hb = hashlib.md5(b.read_bytes()).hexdigest()
    bao("file wav ra GIỐNG TỪNG BYTE bản mốc", ha == hb,
        f"md5 {ha[:12]} vs {hb[:12]}")


def ca6_pha(moc, ten_moc: str) -> None:
    """CA 6 — BỎ BẢN VÁ thì CA 1 phải FAIL (cổng không phải con dấu)."""
    print("\n[CA 6] CỐ TÌNH PHÁ: bỏ bản vá -> CA 1 phải hỏng lại")
    from app.core import thay_giong as tg

    goc = SB / "ca6"
    kh = duong_khop(goc, TEN_DAI)
    manh = lam_manh(278, kh)
    tong = 278 * 0.5 + 1.0
    ra = kh.parent / "pha.wav"
    cu = tg.NGAN_SACH_CMD
    try:
        # ngân sách vô hạn = đúng hành vi bản cũ (không bao giờ chia mẻ)
        tg.NGAN_SACH_CMD = 10 ** 9
        tg._ghep_track_giong(manh, tong, ra)
        bao("bỏ bản vá -> NỔ lại WinError 206", False,
            "KHÔNG nổ -> CA 1 không đo cái nó tưởng đang đo")
    except OSError as e:
        we = getattr(e, "winerror", None)
        bao("bỏ bản vá -> NỔ lại WinError 206", we == 206,
            f"{type(e).__name__} WinError {we}")
    except Exception as e:                                   # noqa: BLE001
        bao("bỏ bản vá -> NỔ lại WinError 206", False,
            f"nổ khác loại: {type(e).__name__}: {str(e)[:80]}")
    finally:
        tg.NGAN_SACH_CMD = cu

    # QUÉT TĨNH bằng AST: `_ghep_track_giong` phải THẬT SỰ hỏi độ dài dòng lệnh
    # (tìm bằng chuỗi thì đổi `<=` thành `>=` vẫn xanh — bài học cổng 56d).
    import ast
    cay = ast.parse((REPO / "app" / "core" / "thay_giong.py").read_text(
        encoding="utf-8"))
    ham = next((n for n in ast.walk(cay)
                if isinstance(n, ast.FunctionDef)
                and n.name == "_ghep_track_giong"), None)
    goi = {n.func.id for n in ast.walk(ham) if ham is not None
           and isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    bao("`_ghep_track_giong` có gọi `_dai_dong_lenh` (AST)",
        "_dai_dong_lenh" in goi, ", ".join(sorted(goi)) or "(không hàm nào)")
    bao("`_ghep_track_giong` có gọi `_chia_me` (AST)", "_chia_me" in goi)


def ca7_don_rac() -> None:
    """CA 7 — DỌN SẠCH mẻ tạm, KỂ CẢ khi lỗi giữa chừng."""
    print("\n[CA 7] DỌN SẠCH FILE TẠM (mỗi mẻ là 1 wav dài bằng cả video)")
    from app.core import thay_giong as tg

    goc = SB / "ca7"
    kh = duong_khop(goc, TEN_NGAN)
    n = 40
    manh = lam_manh(n, kh)
    tong = n * 0.5 + 1.0
    ra = kh.parent / "ok.wav"
    cu = tg.NGAN_SACH_CMD
    try:
        tg.NGAN_SACH_CMD = 2500
        tg._ghep_track_giong(manh, tong, ra)
        con = sorted(p.name for p in kh.parent.glob("_me*.wav"))
        con += sorted(p.name for p in kh.parent.glob("_cg*.wav"))
        bao("chạy XONG -> không còn mẻ tạm", not con, ", ".join(con) or "sạch")

        # LỖI GIỮA CHỪNG: mảnh cuối trỏ vào file KHÔNG TỒN TẠI -> mẻ cuối chết
        hong = list(manh)
        hong[-1] = (hong[-1][0], str(kh / "khong_co_that.wav"))
        ra2 = kh.parent / "hong.wav"
        try:
            tg._ghep_track_giong(hong, tong, ra2)
            bao("lỗi giữa chừng -> NÉM lỗi (không nuốt)", False, "chạy trót lọt")
        except Exception as e:                               # noqa: BLE001
            bao("lỗi giữa chừng -> NÉM lỗi (không nuốt)", True,
                f"{type(e).__name__}")
        con2 = sorted(p.name for p in kh.parent.glob("_me*.wav"))
        con2 += sorted(p.name for p in kh.parent.glob("_cg*.wav"))
        bao("lỗi giữa chừng -> VẪN không còn mẻ tạm", not con2,
            ", ".join(con2) or "sạch")
    finally:
        tg.NGAN_SACH_CMD = cu


def ca8_max_path() -> None:
    """CA 8 — đường dẫn phải còn xa `MAX_PATH` 260 để đích SÂU vẫn chạy."""
    print("\n[CA 8] MAX_PATH: thư mục đích SÂU vài cấp vẫn phải chạy được")
    from app.core.thay_giong import DAU_DA_LAM
    from app.core.tg_chay import thu_muc_lam_cho

    # đúng cảnh sản xuất của anh Hùng: 200-300 kênh, mỗi kênh một thư mục
    sau = r"D:\KhoVideo\Kênh tiếng Trung\（完整）phim lẻ reup 2026\xuất"
    v = Path(r"C:\Users\Admin\Downloads\longtieng") / f"{TEN_DAI}.mp4"
    tam = Path(thu_muc_lam_cho(v, sau))
    ds = [tam / "khop" / "khop_0000.wav",
          tam / "tach" / "htdemucs" / "goc" / "other.wav",
          tam / "rutgon" / "sach1" / "sach_0000.wav",
          tam / f"ban{DAU_DA_LAM}.mp4",
          Path(sau) / v.name]
    dai = max(len(str(p)) for p in ds)
    bao("đích sâu + tên 56 ký tự vẫn dưới MAX_PATH 259", dai <= 259,
        f"dài nhất {dai} ký tự (đích {len(sau)} ký tự)")
    print(f"       dài nhất: {max((len(str(p)), str(p)) for p in ds)[1][:150]}")


def main() -> int:
    print("=" * 78)
    print("CỔNG 59 — TÊN VIDEO DÀI / VIDEO DÀI KHÔNG ĐƯỢC GIẾT LƯỢT THAY GIỌNG")
    print("=" * 78)
    SB.mkdir(parents=True, exist_ok=True)
    try:
        moc, ten_moc = nap_moc()
        ra = ca1_tai_hien(moc, ten_moc)
        ca2_file_ra(ra)
        ca3_chia_me_bang_mot_luot()
        ca4_khong_de_nhau()
        ca5_bat_bien(moc, ten_moc)
        ca6_pha(moc, ten_moc)
        ca7_don_rac()
        ca8_max_path()
    finally:
        shutil.rmtree(SB, ignore_errors=True)
    print("\n" + "=" * 78)
    print(f"ĐẠT {DAT} · HỎNG {HONG}")
    print("=" * 78)
    return 0 if HONG == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
