"""CỔNG 78 — ĐOẠN KHÔNG ĐƯỢC ĐỌC LẠI PHẢI GIỮ GIỌNG GỐC, KHÔNG ĐƯỢC ĐỂ TRỐNG
(18/08/2026).

Anh Hùng: *"mấy cái đoạn âm thanh gốc nói tiếng Anh nó không đọc phần đó thì
lại bị **tắt tiếng** không hiểu"* · *"cái nghe được cái không"*.

BỆNH: dây chuyền BỎ HẲN giọng gốc rồi đặt giọng mới vào. Đoạn nào không được
đọc lại (câu tiếng Anh giữa phim Trung mà bộ chép lời bỏ qua, câu TTS lỗi…) thì
**không có giọng nào cả** — còn lại chỉ nhạc. Tức MẤT NỘI DUNG, nặng hơn hẳn
chuyện âm lượng.

SỐ ĐO TRÊN 4 BẢN ANH HÙNG ĐÃ XUẤT (`_do_mat_giong.py`, so LỚP GIỌNG với LỚP
GIỌNG): mất **82,3 s / 1.209,3 s = 6,8%**, dồn vào **2/4** video (**31,1 s** và
**50,4 s**) — đúng chữ *"cái nghe được cái không"*. Hai video còn lại 0,3 s và
0,6 s.

**THƯỚC CŨ `_do_mat_tieng.py` ĐO RA 0,0 s VÀ NÓ SAI** — nó so đường bao CỦA CẢ
FILE, mà bản xuất VẪN CÓ NHẠC ở đúng chỗ mất tiếng. Đã chạy thật để xác nhận
trước khi viết thước mới (họ bẫy "phép đo phát chứng nhận cho thứ vẫn hỏng":
`astats` cổng 53 · mức mờ 0,40 cổng 56b).

CỔNG NÀY CỐ Ý **KHÔNG** GỌI Demucs / Groq / mạng: nguồn dựng bằng `lavfi` nên
tiền định, chạy vài chục giây, không nhấp nháy. Phần "xuất thật rồi đo lại" là
việc của `_do_bu_goc_ab.py`.
"""
from __future__ import annotations

import ast
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                           # noqa: BLE001
    pass

FFMPEG = str(REPO / "bin" / "ffmpeg.exe")
SB = REPO / f"bq_test_bugoc_{Path(sys.argv[0]).stem}"

DAT = HONG = 0
_HONG: list[str] = []


def ok(ten: str, dieu: bool, ct: str = "") -> None:
    global DAT, HONG
    if dieu:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {ct}" if ct else ""))
    else:
        HONG += 1
        _HONG.append(ten)
        print(f"  [HỎNG] {ten}" + (f" — {ct}" if ct else ""))


def _ff(args: list[str], mo_ta: str) -> None:
    r = subprocess.run([FFMPEG, "-y", "-v", "error", *args],
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"{mo_ta}: {(r.stderr or '')[:200]}")


#: Sàn RỈ NHẠC của nguồn thử, tính theo dB DƯỚI mức "tiếng".
#:
#: **PHẢI CÓ SÀN, KHÔNG ĐƯỢC DỰNG "hoặc tiếng hoặc IM TUYỆT ĐỐI":** lớp giọng
#: Demucs thật LUÔN còn rỉ nhạc — đo trên 4 video của anh Hùng ra sàn
#: **-24,0 · -27,3 · -29,2 · -24,1 dBFS** trong khi lời cao hơn hẳn. Nguồn thử
#: không có sàn là nguồn KHÔNG GIỐNG THỰC TẾ, và bản đầu của cổng này đã vì thế
#: báo HỎNG 6 mục cho một bản vá chạy đúng trên dữ liệu thật (rồi lại lôi ra
#: được một bug thật ở phép tính sàn — xem `bu_giong_goc`).
SAN_DUOI_DB = 22.0


def wav_tieng(ra: Path, tong: float, noi: list[tuple[float, float]]) -> None:
    """WAV `tong` giây: sàn rỉ nhạc khắp bài + 'tiếng' rõ ở các khoảng `noi`.

    Dùng `sine` cho phần tiếng chứ không dùng nhiễu: `duong_bao_muc` đo RMS nên
    cần mức ỔN ĐỊNH để ngưỡng "nổi hơn sàn 10 dB" có nghĩa; nguồn ngẫu nhiên
    làm cổng nhấp nháy. Phần SÀN thì dùng sine tần số khác, hạ `SAN_DUOI_DB`.
    """
    bat = "+".join(f"between(t,{a},{b})" for a, b in noi) or "0"
    san = 10 ** (-SAN_DUOI_DB / 20.0)
    _ff(["-f", "lavfi", "-i", f"sine=frequency=220:duration={tong}",
         "-f", "lavfi", "-i", f"sine=frequency=90:duration={tong}",
         "-filter_complex",
         f"[0:a]volume=0:enable='not({bat})'[v];"
         f"[1:a]volume={san:.6f}[s];"
         f"[v][s]amix=inputs=2:normalize=0,aresample=44100[o]",
         "-map", "[o]", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le",
         str(ra)], "dựng wav tiếng")


def main() -> int:
    print("=" * 72)
    print("CỔNG 78 — BÙ GIỌNG GỐC Ở ĐOẠN KHÔNG ĐƯỢC ĐỌC LẠI")
    print("=" * 72)
    from app.core import thay_giong as TG

    shutil.rmtree(SB, ignore_errors=True)
    SB.mkdir(parents=True, exist_ok=True)
    try:
        # ─── MỤC 1: khoang_khong_giong — hàm THUẦN ────────────────────────
        print("\nMỤC 1 — `khoang_khong_giong`: tìm đúng khoảng KHÔNG có giọng mới")
        import unittest.mock as M
        # `probe_duration` bị vá để độ dài mảnh nằm trong TÊN FILE -> ca đơn vị
        # tiền định, không phải ghi 20 file wav ra đĩa.
        with M.patch.object(TG, "probe_duration",
                            lambda p: float(str(p).split("#")[1])):
            r = TG.khoang_khong_giong([(0.0, "a#2.0"), (3.0, "b#1.0"),
                                       (10.0, "c#2.0")], 15.0)
            ok("tìm ra đủ 3 khoảng trống (giữa câu 1-2, 2-3, và phần đuôi)",
               len(r) == 3, str(r))
            ok("mỗi mép LÙI 0,10s để không chồng lên giọng mới",
               r[0] == (2.1, 2.9) and r[1] == (4.1, 9.9), str(r))
            ok("phủ KÍN -> KHÔNG bù gì",
               TG.khoang_khong_giong([(0.0, "a#15.0")], 15.0) == [])
            ok("mảnh CHỒNG nhau -> gộp đúng, không đẻ khoảng ảo",
               TG.khoang_khong_giong(
                   [(0.0, "a#5.0"), (2.0, "b#5.0")], 15.0) == [(7.1, 14.9)])
            ok("khoảng NGẮN hơn 0,35s -> bỏ (nhịp nghỉ giữa câu, không phải mất)",
               TG.khoang_khong_giong(
                   [(0.0, "a#2.0"), (2.2, "b#2.0")], 4.2) == [])
            ok("danh sách mảnh RỖNG -> cả video là một khoảng trống",
               len(TG.khoang_khong_giong([], 10.0)) == 1)
            ok("tong <= 0 -> [] (không nổ)",
               TG.khoang_khong_giong([(0.0, "a#1.0")], 0.0) == [])

        # ─── MỤC 1b: `duong_bao_muc` phải trả SỐ HỮU HẠN ──────────────────
        print("\nMỤC 1b — `duong_bao_muc`: cửa sổ im tuyệt đối phải ra -120, KHÔNG -inf")
        im = SB / "im_han.wav"
        _ff(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
             "-t", "2", "-c:a", "pcm_s16le", str(im)], "dựng wav im hẳn")
        b_im = TG.duong_bao_muc(im, buoc=0.05)
        ok("đo được đường bao của file im hẳn", len(b_im) > 10, f"{len(b_im)} ô")
        ok("KHÔNG ô nào là -inf (docstring hứa -120,0 từ đầu mà thực tế trả -inf)",
           all(v != float("-inf") for v in b_im),
           f"min={min(b_im) if b_im else '?'}")
        ok("mọi ô HỮU HẠN -> trung bình/bách phân vị còn tính được",
           bool(b_im) and sum(b_im) / len(b_im) > -1e6,
           f"TB={sum(b_im)/max(1,len(b_im)):.1f}")

        # ─── MỤC 2: bu_giong_goc trên nguồn dựng sẵn ──────────────────────
        print("\nMỤC 2 — `bu_giong_goc`: CHỈ bù chỗ lớp giọng GỐC có tiếng thật")
        TONG = 20.0
        # Lớp giọng gốc: nói ở 0-3s, 6-9s, 12-15s. Khoảng 16-20s CỐ Ý IM.
        gg = SB / "giong_goc.wav"
        wav_tieng(gg, TONG, [(0.0, 3.0), (6.0, 9.0), (12.0, 15.0)])
        # Giọng MỚI chỉ phủ 0-3s và 12-15s -> hở 3-12s (gốc nói 6-9s) và 15-20s
        # (gốc IM từ 16s, và 15-16 gần như hết tiếng).
        m1 = SB / "moi1.wav"
        m2 = SB / "moi2.wav"
        wav_tieng(m1, 3.0, [(0.0, 3.0)])
        wav_tieng(m2, 3.0, [(0.0, 3.0)])
        manh = [(0.0, str(m1)), (12.0, str(m2))]
        bu = TG.bu_giong_goc(gg, manh, TONG, SB / "bu")
        ok("có mảnh bù", bu.get("so_bu", 0) >= 1,
           f"{bu.get('so_bu')} mảnh / {bu.get('giay_bu')}s")
        kh = [tuple(x) for x in bu.get("khoang", [])]
        co69 = any(a <= 6.2 and b >= 8.8 for a, b in kh)
        ok("BÙ đúng khoảng gốc CÓ tiếng mà giọng mới không phủ (6-9s)",
           co69, str(kh))
        im_bi_bu = [x for x in kh if x[0] >= 15.9]
        ok("KHÔNG bù khoảng gốc cũng IM (16-20s) — không nhét nhiễu vào",
           not im_bi_bu, f"khoảng bù: {kh} · bỏ qua {bu.get('bo_qua')}")
        ok("ngưỡng lấy theo SÀN NHIỄU của chính file, không phải hằng số dBFS",
           "san_db" in bu and "nguong_db" in bu,
           f"sàn {bu.get('san_db')} · ngưỡng {bu.get('nguong_db')} dBFS")
        for off, p in bu["manh"]:
            assert Path(p).exists() and Path(p).stat().st_size > 1024, p
        ok("mảnh bù ghi ra file THẬT, đủ kích thước (ffmpeg mã 0 + 0 KiB là bẫy)",
           all(Path(p).stat().st_size > 1024 for _o, p in bu["manh"]))
        # mốc bù phải nằm TRONG khoảng trống, không đè lên giọng mới
        de = [(o, p) for o, p in bu["manh"]
              if o < 3.0 - 1e-6 or (3.0 < o < 12.0 and
                                    o + TG.probe_duration(p) > 12.0 + 1e-6)]
        ok("mảnh bù KHÔNG đè lên vùng đã có giọng mới (cấm hai giọng cùng nói)",
           not de, str(de))

        print("\nMỤC 2c — KHỚP MỨC: giọng gốc bù phải to NGANG giọng mới")
        # Nguồn thử: giọng gốc to -24 dBFS. Dựng track giọng MỚI NHỎ HƠN 9 dB để
        # buộc phép khớp phải hạ phần bù xuống — nếu không hạ thì chỗ bù NHẢY TO
        # (đúng kiểu "chỗ to chỗ nhỏ") và `can_bang_giong_nhac` còn bớt nâng
        # giọng TTS ở CẢ video.
        nho1, nho2 = SB / "nho1.wav", SB / "nho2.wav"
        for src, dst in ((m1, nho1), (m2, nho2)):
            _ff(["-i", str(src), "-af", "volume=-9dB",
                 "-c:a", "pcm_s16le", str(dst)], "hạ giọng mới 9 dB")
        manh_nho = [(0.0, str(nho1)), (12.0, str(nho2))]
        bu_n = TG.bu_giong_goc(gg, manh_nho, TONG, SB / "bu_nho")
        ok("đo được mức CẢ HAI bên (không bên nào None)",
           bu_n.get("muc_giong_moi_db") is not None
           and bu_n.get("muc_giong_goc_db") is not None,
           f"mới {bu_n.get('muc_giong_moi_db')} · gốc "
           f"{bu_n.get('muc_giong_goc_db')} dBFS")
        g = bu_n.get("gain_khop_db")
        ok("giọng mới NHỎ hơn -> phần bù bị HẠ (gain âm, đúng CHIỀU)",
           g is not None and g < -5.0, f"gain {g} dB")
        ok("gain nằm trong trần ±12 dB", g is not None and abs(g) <= 12.0,
           f"{g} dB")
        # ĐO THẬT trên mảnh đã ghi: mức phần bù phải xấp xỉ mức giọng mới
        if bu_n["manh"]:
            b_bu = TG.duong_bao_muc(bu_n["manh"][0][1], buoc=0.05)
            hu = [v for v in b_bu if v > -119.0]
            m_bu = sorted(hu)[int(len(hu) * 0.90)] if hu else -120.0
            m_moi = bu_n["muc_giong_moi_db"]
            ok("mảnh bù ĐO RA xấp xỉ mức giọng mới (lệch <= 2 dB)",
               abs(m_bu - m_moi) <= 2.0,
               f"bù {m_bu:.2f} vs mới {m_moi:.2f} dBFS")

        print("\nMỤC 2b — BẤT BIẾN: phủ kín thì KHÔNG bù mảnh nào")
        full = SB / "full.wav"
        wav_tieng(full, TONG, [(0.0, TONG)])
        bu0 = TG.bu_giong_goc(gg, [(0.0, str(full))], TONG, SB / "bu0")
        ok("giọng mới phủ kín -> 0 mảnh bù (danh sách mảnh giữ NGUYÊN)",
           bu0.get("so_bu", 0) == 0 and not bu0["manh"], str(bu0.get("ly_do")))
        bu1 = TG.bu_giong_goc("", manh, TONG, SB / "bu1")
        ok("thiếu lớp giọng gốc -> trả rỗng, KHÔNG ném (đừng giết lượt xuất)",
           bu1["manh"] == [], str(bu1.get("ly_do")))

        # ─── MỤC 3: đo THẬT trên track đã ghép ────────────────────────────
        print("\nMỤC 3 — ĐO track giọng sau khi ghép: khoảng trống HẾT im")
        t_khong = SB / "track_khong_bu.wav"
        t_co = SB / "track_co_bu.wav"
        TG.ghep_track_am(manh, TONG, t_khong, ten_viec="ghép (không bù)")
        TG.ghep_track_am(manh + bu["manh"], TONG, t_co,
                         ten_viec="ghép (có bù)")
        b_khong = TG.duong_bao_muc(t_khong, buoc=0.05)
        b_co = TG.duong_bao_muc(t_co, buoc=0.05)

        def muc_tb(bao: list[float], a: float, b: float) -> float:
            i0, i1 = int(a / 0.05), int(b / 0.05)
            x = [v for v in bao[i0:i1] if v > -119.0]
            return (sum(x) / len(x)) if x else -120.0

        # cửa sổ 6,5-8,5s = chỗ gốc nói mà giọng mới KHÔNG có
        k0 = muc_tb(b_khong, 6.5, 8.5)
        k1 = muc_tb(b_co, 6.5, 8.5)
        ok("chỗ không được đọc lại: TRƯỚC gần như IM", k0 < -60.0,
           f"{k0:.1f} dBFS")
        ok("chỗ không được đọc lại: SAU khi bù thì CÓ TIẾNG", k1 > -40.0,
           f"{k1:.1f} dBFS")
        ok("mức tăng ĐỦ NGHE (>= 20 dB)", (k1 - k0) >= 20.0,
           f"+{k1 - k0:.1f} dB")
        # BẤT BIẾN: vùng ĐÃ có giọng mới không được đổi
        v0 = muc_tb(b_khong, 0.5, 2.5)
        v1 = muc_tb(b_co, 0.5, 2.5)
        ok("vùng ĐÃ có giọng mới KHÔNG bị đổi (lệch < 0,5 dB)",
           abs(v1 - v0) < 0.5, f"{v0:.2f} -> {v1:.2f} dBFS")
        # và vùng gốc CŨNG im thì vẫn im (không nhét nhiễu)
        i0 = muc_tb(b_khong, 17.0, 19.5)
        i1 = muc_tb(b_co, 17.0, 19.5)
        ok("vùng gốc CŨNG im -> vẫn im sau khi bù", abs(i1 - i0) < 0.5,
           f"{i0:.1f} -> {i1:.1f} dBFS")

        print("\nMỤC 3b — TỔNG THỜI LƯỢNG IM-MÀ-GỐC-CÓ-TIẾNG (chốt của việc này)")
        bao_g = TG.duong_bao_muc(gg, buoc=0.05)
        huu = sorted(v for v in bao_g if v > -119.0)
        san_g = huu[int(len(huu) * 0.20)]

        def giay_mat(bao_x: list[float]) -> tuple[float, float]:
            """(giây mất tính theo KHOẢNG, giây mất tính theo Ô lẻ).

            **PHẢI CHẤM Ở CỘT "KHOẢNG", ĐÚNG CỘT `_do_mat_giong.py` DÙNG.** Hai
            phép đo phải cùng một thước, nếu không thì con số 82,3 s của anh
            Hùng và con số của cổng nói hai chuyện khác nhau. Ô lẻ < 0,30 s là
            ranh giới mép, không phải nội dung mất — chính vì thế thước kia cũng
            bỏ chúng. Vẫn TRẢ VỀ cả cột ô lẻ để không che gì.

            Vì sao còn ô lẻ: `BU_GOC_LUI` cố ý lùi mỗi mép khoảng trống 0,10 s
            để phần bù KHÔNG chồng lên đuôi/đầu giọng mới (hai giọng cùng nói là
            lỗi nặng hơn). Phần dư vì thế bị chặn bởi mép ĐÓ, không phụ thuộc
            độ dài nội dung.
            """
            n = min(len(bao_g), len(bao_x))
            hx = sorted(bao_x)
            sx = hx[int(len(hx) * 0.20)]
            mat = [bao_g[i] > san_g + 12.0 and bao_x[i] < sx + 4.0
                   for i in range(n)]
            tho = round(sum(0.05 for m in mat if m), 2)
            # gom ô liền nhau (cho hở 2 ô) rồi bỏ khoảng < 0,30 s
            kh, i = [], 0
            while i < n:
                if not mat[i]:
                    i += 1
                    continue
                j, ho, k2 = i, 0, i
                while k2 < n:
                    if mat[k2]:
                        j, ho = k2, 0
                    else:
                        ho += 1
                        if ho > 2:
                            break
                    k2 += 1
                if (j + 1 - i) * 0.05 >= 0.30:
                    kh.append((i * 0.05, (j + 1) * 0.05))
                i = k2
            return round(sum(b - a for a, b in kh), 2), tho

        g0, t0_ = giay_mat(b_khong)
        g1, t1_ = giay_mat(b_co)
        ok("TRƯỚC: có giây bị mất (phép đo có răng)", g0 > 1.0,
           f"{g0}s (ô lẻ {t0_}s)")
        ok("SAU: tổng thời lượng im-mà-gốc-có-tiếng = 0",
           g1 == 0.0, f"{g0}s -> {g1}s (ô lẻ {t1_}s, chặn bởi mép "
                      f"BU_GOC_LUI={TG.BU_GOC_LUI}s mỗi đầu)")
        ok("phần dư ô lẻ KHÔNG quá 2 mép lùi mỗi khoảng trống",
           t1_ <= 2 * TG.BU_GOC_LUI * max(1, bu.get("so_bu", 1)) + 1e-9,
           f"{t1_}s <= {2 * TG.BU_GOC_LUI * max(1, bu.get('so_bu', 1))}s")

        # ─── MỤC 4: nối vào ĐÚNG CỬA, quét bằng AST ───────────────────────
        print("\nMỤC 4 — nối vào cửa chung (AST, không quét chuỗi)")
        src = (REPO / "app" / "core" / "thay_giong.py").read_text(
            encoding="utf-8")
        cay = ast.parse(src)
        ham = None
        for n in ast.walk(cay):
            if isinstance(n, ast.FunctionDef) and n.name == "thay_giong_video":
                ham = n
        ok("tìm được `thay_giong_video`", ham is not None)
        if ham is not None:
            goi = {c.func.id for c in ast.walk(ham)
                   if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
            ok("`thay_giong_video` GỌI THẬT `bu_giong_goc`",
               "bu_giong_goc" in goi)
            # và kết quả phải đi VÀO `tron_thay_giong`, không phải trộn sau khi
            # đã chuẩn hoá độ to (trộn sau là làm sai chính con số vừa đo).
            tron = [c for c in ast.walk(ham)
                    if isinstance(c, ast.Call)
                    and getattr(c.func, "id", "") == "tron_thay_giong"]
            ok("có lời gọi `tron_thay_giong`", len(tron) == 1, str(len(tron)))
            if tron:
                arg2 = tron[0].args[1] if len(tron[0].args) > 1 else None
                ten = getattr(arg2, "id", "")
                ok("mảnh đưa vào `tron_thay_giong` là danh sách ĐÃ CỘNG phần bù"
                   " (không phải `kh[\"manh\"]` trần)",
                   ten == "manh_tron", f"tham số 2 = {ten or type(arg2).__name__}")
            # cờ mặc định phải BẬT: để trống là MẤT NỘI DUNG
            mac = None
            for a, d in zip(ham.args.args[-len(ham.args.defaults):],
                            ham.args.defaults):
                if a.arg == "bu_giong_goc_bat":
                    mac = getattr(d, "value", None)
            ok("cờ `bu_giong_goc_bat` MẶC ĐỊNH BẬT", mac is True, str(mac))

        # ─── MỤC 5: TỰ KIỂM BỘ DÒ ─────────────────────────────────────────
        print("\nMỤC 5 — TỰ KIỂM: gỡ chốt ra thì phép đo PHẢI kêu")
        # (a) bỏ cửa "chỉ bù chỗ gốc có tiếng" -> phải bù cả vùng IM 16-20s
        goc_nguong = TG.BU_GOC_NOI_DB
        try:
            TG.BU_GOC_NOI_DB = -200.0        # cửa mở toang
            bx = TG.bu_giong_goc(gg, manh, TONG, SB / "bu_pha")
            khx = [tuple(x) for x in bx.get("khoang", [])]
            # Vùng 16-20s là vùng gốc IM. Khoảng trống cuối là (15,1 .. 19,9)
            # nên chốt phải hỏi "có khoảng nào LẤN vào sau 16s không", đừng so
            # mốc BẮT ĐẦU với 15,5 (bản đầu so thế -> HỎNG OAN dù phép phá đã
            # phá đúng).
            ok("gỡ cửa 'gốc phải có tiếng' -> BÙ CẢ vùng im (bộ dò có răng)",
               any(b > 16.0 for _a, b in khx), str(khx))
        finally:
            TG.BU_GOC_NOI_DB = goc_nguong
        # (b) `dai_min` phải THẬT SỰ chặn.
        # **BẪY ĐÃ SẬP:** `khoang_khong_giong(dai_min=BU_GOC_DAI_MIN)` lấy hằng
        # số làm GIÁ TRỊ MẶC ĐỊNH, mà mặc định được chốt lúc ĐỊNH NGHĨA hàm ->
        # gán lại `TG.BU_GOC_DAI_MIN` KHÔNG đổi được gì, và phép phá "im lặng
        # không phá được" lại bị đếm là LỌT. Phải truyền THẲNG tham số.
        with M.patch.object(TG, "probe_duration",
                            lambda p: float(str(p).split("#")[1])):
            ok("`dai_min` truyền thẳng CÓ chặn (0 khoảng khi đặt vô hạn)",
               TG.khoang_khong_giong([(0.0, "a#2.0"), (10.0, "b#2.0")],
                                     20.0, dai_min=9999.0) == [],
               "đặt 9999s -> []")
            ok("cùng dữ liệu, `dai_min` mặc định thì CÓ khoảng (chốt có răng)",
               len(TG.khoang_khong_giong([(0.0, "a#2.0"), (10.0, "b#2.0")],
                                         20.0)) == 2)
    finally:
        shutil.rmtree(SB, ignore_errors=True)

    print("\n" + "=" * 72)
    print(f"CỔNG 78 — ĐẠT {DAT} · HỎNG {HONG}")
    for d in _HONG:
        print(f"   HỎNG: {d}")
    print("=" * 72)
    return 1 if HONG else 0


if __name__ == "__main__":
    sys.exit(main())
