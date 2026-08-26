# -*- coding: utf-8 -*-
"""CỔNG 63 — BIẾN THỂ GIỌNG (`pitch`) NỐI ĐỦ 3 CHỖ GỌI TTS.

VÌ SAO CÓ CỔNG NÀY (16/08/2026): edge-tts chỉ có 2 giọng tiếng Việt, 200-300
kênh dùng chung 2 giọng thì kênh nào cũng kêu giống nhau. `pitch` sinh thêm
biến thể mà không tốn thêm lượt mạng nào.

**MỆNH ĐỀ ĐẮT NHẤT CỔNG NÀY CANH:** `thay_giong.py` có **BA** chỗ gọi
`dubbing._synth_all_words` — `doc_ban_dich` · `rut_gon_vua_khung` ·
`doc_nhanh_vua_khung`. Sót MỘT chỗ thì những câu đi qua chỗ đó đọc bằng cao
độ GỐC, ra video **lẫn hai giọng**, mà `rc` vẫn 0 và không một dòng nào báo.
Đúng họ bẫy "cửa chờ ffmpeg bị xoá mà không ai biết" (cổng 36b) và "cookie
phải bản-sao-tạm ở MỌI chỗ spawn".

MỆNH ĐỀ 2 — **BẤT BIẾN CHUỖI CŨ**: mã giọng không có `|` phải đi qua
`tach_giong_pitch` ra Y NGUYÊN + `"+0Hz"`, và `+0Hz` phải ghép ngược ra ĐÚNG
chuỗi cũ. Nếu không thì mọi mẫu đã lưu và mọi job đang nằm trong DB đổi nghĩa.

MỆNH ĐỀ 3 — nhãn tiếng Việt, KHÔNG EMOJI, và combo KHÔNG đẻ dòng trùng.

MỆNH ĐỀ 4 (CA 6, thêm 25/08/2026) — **MỖI GIỌNG NHÂN BẢN MỘT MÃ RIÊNG.**
CA 4c bắt được lỗi thật: hai bản ghi *"Giọng chị Lan"* và *"Giọng của tôi"* trỏ
CÙNG một file mẫu, mà mã ``vnb:`` khoá theo ĐƯỜNG DẪN MẪU -> hai tên ra MỘT mã
(đo được **70 mã / 69 khác nhau**). Anh Hùng chọn *"Giọng chị Lan"*, app đọc
bằng *"Giọng của tôi"*, **không một dòng báo** — họ lỗi "chọn X ra Y" đã sập
bốn lần (``ov:nu_am`` · ``vn:`` · ``cb:`` · ``kk:``).
CA 4c chỉ thấy được lỗi khi sổ THẬT trên máy đang hỏng, nên nó là canary chứ
không phải phép kiểm. CA 6 dựng lại đúng ca đó trong **hộp cát riêng** để mệnh
đề được chấm mỗi lượt, kèm hai bất biến tương thích ngược mà bản vá không được
phá: **đổi tên KHÔNG đổi mã** và **mã CŨ vẫn tra ra đúng giọng**.

  .venv\\Scripts\\python -u _test_bien_the_giong.py
"""
from __future__ import annotations

import ast
import hashlib
import math
import os
import shutil
import struct
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

DAT = HONG = 0


def kiem(ten: str, dk: bool, ct: str = "") -> None:
    global DAT, HONG
    if dk:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {ct}" if ct else ""))
    else:
        HONG += 1
        print(f"  HỎNG {ten}" + (f" — {ct}" if ct else ""))


def co_emoji(s: str) -> bool:
    return any(ord(c) > 0x2100 for c in s)


def _wav(p: Path, giay: float, hz: float) -> None:
    """WAV 24 kHz mono CÓ TIẾNG THẬT (sin) — đủ qua `kiem_mau`.

    Phải là tiếng thật chứ không phải im lặng: `kiem_mau` chặn mẫu "chủ yếu im
    lặng" (`TY_LE_TIENG_MIN`), mẫu câm thì `them_giong` từ chối và CA 6a hỏng
    oan vì lý do chẳng liên quan gì tới mã giọng.
    """
    sr = 24000
    d = b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * hz * i / sr)))
                 for i in range(int(sr * giay)))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"RIFF" + struct.pack("<I", 36 + len(d)) + b"WAVEfmt " +
                  struct.pack("<IHHIIHH", 16, 1, 1, sr, sr * 2, 2, 16) +
                  b"data" + struct.pack("<I", len(d)) + d)


def _md5(p) -> str:
    q = Path(str(p or ""))
    return hashlib.md5(q.read_bytes()).hexdigest() if q.is_file() else ""


def ca6_giong_nhan_ban() -> None:
    """CA 6 — hai bản ghi giọng nhân bản KHÁC TÊN không được ra CÙNG một mã.

    **CHẠY TRONG HỘP CÁT RIÊNG.** `nhan_ban_giong.thu_muc_mau()`/`duong_so()`
    đọc `config.DATA_DIR` MỖI LẦN GỌI (cố ý, bài học `tg_so.duong_so`), nên đổi
    hằng số đó là dời được cả sổ lẫn thư mục mẫu. Bắt buộc phải sandbox: ca này
    THÊM/XOÁ giọng, chạy thẳng trên sổ thật là làm bẩn giọng của anh Hùng và
    xoá file trong `_mau_giong` — đúng thứ luật cấm.
    """
    print("\nCA 6 — giọng nhân bản: mỗi bản ghi MỘT MÃ RIÊNG")
    import config
    from app.core import giong_bang as GB
    from app.core import nhan_ban_giong as NB

    cu_data = getattr(config, "DATA_DIR", "")
    hop = Path(tempfile.mkdtemp(prefix="bq_cong63_nb_"))
    config.DATA_DIR = str(hop)
    try:
        a, b = hop / "src" / "a.wav", hop / "src" / "b.wav"
        _wav(a, 8.0, 180.0)
        _wav(b, 8.0, 300.0)

        # --- 6a/6b: CHẶN từ lượt thêm. `_slug` ánh xạ NHIỀU-THÀNH-MỘT nên hai
        #     tên này ra cùng một tên file nếu không ai chặn, và ffmpeg `-y`
        #     ghi đè mẫu của bản ghi trước.
        r1 = NB.them_giong("Giọng chị Lan", str(a), lang="vi")
        md5_1 = _md5(NB._muc(NB._doc_so(), "Giọng chị Lan").get("mau"))
        r2 = NB.them_giong("giọng chị lan", str(b), lang="vi")
        kiem("6a hai tên `_slug` TRÙNG vẫn thêm được cả hai",
             r1.get("ok") and r2.get("ok"),
             f"{r1.get('loi')!r} · {r2.get('loi')!r}")
        kiem("6b ... và ra HAI MÃ KHÁC NHAU",
             bool(r1.get("ma")) and r1.get("ma") != r2.get("ma"),
             f"{Path(r1.get('ma') or '').name} vs {Path(r2.get('ma') or '').name}")
        kiem("6c ... KHÔNG ghi đè file mẫu của bản ghi trước (mẫu cũ y nguyên)",
             md5_1 and _md5(NB._muc(NB._doc_so(), "Giọng chị Lan").get("mau"))
             == md5_1)

        # --- 6d..6h: sổ ĐÃ hỏng sẵn (chép tay / bản app cũ ghi đè mẫu).
        chung = NB.thu_muc_mau() / "chung.wav"
        _wav(chung, 8.0, 220.0)
        md5_chung = _md5(chung)
        ma_cu = NB.ma_giong  # tra tên -> mã, dùng lại bên dưới
        NB._ghi_so({"Giọng chị Lan": {"mau": str(chung), "may": "vieneu",
                                      "lang": "vi", "giay": 8.0},
                    "Giọng của tôi": {"mau": str(chung), "may": "vieneu",
                                      "lang": "vi", "giay": 8.0}})
        MA_CHUNG = "vnb:" + str(chung)          # mã CŨ, dạng theo đường dẫn
        ds = NB.danh_sach()
        mas = [m for m, _n in ds]
        kiem("6d sổ dùng chung mẫu -> `danh_sach()` ra HAI MÃ KHÁC NHAU",
             len(mas) == 2 and len(set(mas)) == 2,
             f"{len(mas)} mã / {len(set(mas))} khác nhau")
        # TƯƠNG THÍCH NGƯỢC: mã cũ nằm trong cấu hình kênh + payload job đã lưu
        # trong DB. Bản ghi ĐẦU theo thứ tự chữ phải GIỮ NGUYÊN mã cũ, nếu
        # không thì kênh đang gán tra không ra -> rơi về giọng mặc định, im
        # lặng. `ten_theo_ma` cùng phép `sorted` nên kênh KHÔNG đổi hành vi.
        kiem("6e mã CŨ (dạng theo đường dẫn) VẪN tra ra đúng giọng",
             NB.ten_theo_ma(MA_CHUNG) == "Giọng chị Lan",
             f"{NB.ten_theo_ma(MA_CHUNG)!r}")
        kiem("6f ... và nó vẫn là mã của CHÍNH bản ghi đó",
             ma_cu("Giọng chị Lan") == MA_CHUNG)
        kiem("6g file mẫu dùng chung KHÔNG bị xoá/sửa khi chữa",
             _md5(chung) == md5_chung and md5_chung != "")
        # Đổi tên KHÔNG được đụng file mẫu -> mã đứng yên (bất biến đang có).
        truoc = ma_cu("Giọng của tôi")
        kiem("6h đổi tên -> mã KHÔNG đổi",
             NB.doi_ten("Giọng của tôi", "Giọng anh Hùng")
             and ma_cu("Giọng anh Hùng") == truoc and bool(truoc))
        # Xoá bản ghi này không được làm bản ghi kia MẤT MẪU.
        NB._ghi_so({"Giọng chị Lan": {"mau": str(chung), "may": "vieneu",
                                      "lang": "vi", "giay": 8.0},
                    "Giọng của tôi": {"mau": str(chung), "may": "vieneu",
                                      "lang": "vi", "giay": 8.0}})
        NB.xoa("Giọng chị Lan", xoa_ca_mau=True)
        kiem("6i xoá bản ghi dùng CHUNG mẫu -> bản ghi kia KHÔNG mất mẫu",
             bool(ma_cu("Giọng của tôi")) and chung.is_file(),
             f"mã còn lại {ma_cu('Giọng của tôi')!r}")

        # --- 6j: sổ LÀNH thì đường vẽ combo KHÔNG được ghi gì. Chữa sổ là một
        #     lượt DI TRÚ, không phải việc làm mỗi lần dựng combo.
        lanh = NB.duong_so().read_bytes()
        kiem("6j sổ LÀNH -> `sua_mau_trung` không sửa gì, sổ không bị ghi lại",
             NB.sua_mau_trung() == [] and NB.duong_so().read_bytes() == lanh)

        # --- 6k: KHÔNG đẻ tiền tố mới. Tiền tố chưa đăng ký bị coi là edge-tts
        #     -> đúng cái bẫy đã sập 4 lần.
        ma = ma_cu("Giọng của tôi")
        kiem("6k mã vẫn mang tiền tố `vnb:` (KHÔNG đẻ tiền tố thứ ba)",
             ma.startswith("vnb:") and GB.nguon(ma) == GB.VIENEU,
             f"nguon={GB.nguon(ma)!r}")
        kiem("6l ... và `la_giong_nhan_ban` vẫn nhận ra",
             NB.la_giong_nhan_ban(ma))
    finally:
        config.DATA_DIR = cu_data
        shutil.rmtree(hop, ignore_errors=True)


def ca7_ghi_ra_duoi_mp3() -> None:
    """CA 7 — MỌI hàm ghi file tiếng phải CHỊU ĐƯỢC đích đuôi `.mp3`.

    ═══ LỖI THẬT, ĐO 26/08/2026 (`_do_ghi_tieng.py`) ═══
    Mọi cửa `dubbing._synth_all` / `_synth_all_words` nhận `paths` đuôi
    **`.mp3`** — `thay_giong.doc_ban_dich` đặt `cau_XXXX.mp3`,
    `doc_nhanh_vua_khung` đặt `nhanh_XXXX.mp3`. Hợp đồng ghi ngay ở docstring
    `dubbing._synth_all`: *"Ghi WAV vào paths[i] (tên .mp3 cũng được — ffmpeg/
    ffprobe sniff nội dung)"*.
    Ba hàm ghi ra đúng đường dẫn đó đều KHÔNG ép muxer, nên ffmpeg chọn theo
    ĐUÔI rồi bị nhồi PCM vào mp3. Đo trước khi vá, cùng nguồn 1,5 s:

        giong_ngoai._ep_khung  (ov: · **và cb:**)  -> False ·      0 byte
        giong_vbee._ghi_wav    (vbee:)             -> False ·      0 byte
        giong_vieneu._ep_khung (vn: · vnb:)        -> False ·  5.228 byte
                                                     nhưng ffprobe đo 1,200 s!

    Hai kiểu hỏng KHÁC NHAU, và kiểu thứ hai mới là kiểu nguy:
      · `giong_ngoai`/`giong_vbee` — ffmpeg chết hẳn (`rc=-22 Invalid
        argument` · *"Nothing was written into output file"*).
      · `giong_vieneu` — bản vá 20/08 đã bỏ `-c:a` cho đuôi khác `.wav` nên
        ffmpeg ghi ra mp3 THẬT, **rc=0, file tốt**. Nhưng chốt cuối của hàm là
        `dai_wav()`, mà `dai_wav` mở bằng `wave.open` -> **chỉ đọc được WAV**
        -> trả 0.0 -> *"Ép khung ra file 0 giây -> bỏ"*. Tức bản vá chỉ đổi
        DÒNG LOG, bệnh còn nguyên. Đây đúng họ *"phép đo hỏng phát chứng
        nhận"* (`astats` cổng 53 · `startswith` cổng 44), chỉ đảo chiều: phép
        đo hỏng phát **giấy báo tử** cho một file lành.

    HẬU QUẢ Ở CẢ BA: cả loạt hỏng -> chốt all-or-nothing -> lùi edge-tts. Anh
    Hùng chọn giọng nhân bản của mình / giọng Vbee trả tiền, video ra giọng
    edge-tts, **`rc` vẫn 0, chỉ có một dòng log**. Đúng mệnh đề trung tâm của
    cổng này. Với Vbee thì nó là **100%** (hàm chạy cho MỌI câu ở MỌI bước,
    không phụ thuộc `tempo`) — 3 giọng Việt trả tiền chưa từng ra một câu nào.

    PHÉP ĐO CÓ RĂNG: cùng ba hàm, đích `.wav`, phải ĐẠT — không có cột đối
    chứng đó thì "cả ba đều hỏng" có thể chỉ là hộp cát dựng sai.
    """
    import subprocess
    from config import settings
    from app.core import giong_ngoai as GN
    from app.core import giong_vbee as VB
    from app.core import giong_vieneu as VN

    print("\nCA 7 — hàm ghi file tiếng phải chịu được đích đuôi `.mp3`")
    hop = Path(tempfile.mkdtemp(prefix="bq_t63_mp3_"))
    try:
        src = hop / "raw.wav"
        _wav(src, 1.5, 440.0)
        au = src.read_bytes()

        def dai(p: Path) -> float:
            """Độ dài THẬT — thước ĐỘC LẬP với `dai_wav` mà hàm đang dùng."""
            if not p.exists():
                return 0.0
            r = subprocess.run(
                [settings.FFPROBE_PATH, "-v", "error", "-show_entries",
                 "format=duration", "-of", "default=nw=1:nk=1", str(p)],
                capture_output=True, text=True)
            try:
                return float((r.stdout or "0").strip())
            except ValueError:
                return 0.0

        bo = (("giong_ngoai._ep_khung  (ov: · cb:)", "gn",
               lambda d: GN._ep_khung(src, d, 1.25)),
              ("giong_vieneu._ep_khung (vn: · vnb:)", "vn",
               lambda d: VN._ep_khung(src, d, 1.25)),
              ("giong_vbee._ghi_wav    (vbee:)", "vb",
               lambda d: VB._ghi_wav(au, d)))

        for ten, ma, fn in bo:
            for duoi, nhan in ((".mp3", "ĐÚNG đuôi đường thật"),
                               (".wav", "đối chứng, phép đo CÓ RĂNG")):
                d = hop / f"{ma}{duoi}"
                if d.exists():
                    d.unlink()
                tra = bool(fn(d))
                dt = dai(d)
                byte = d.stat().st_size if d.exists() else 0
                kiem(f"7{ma}{duoi[1:]} {ten} · đích `{duoi}` ({nhan})",
                     tra and dt > 0.02,
                     f"trả {tra} · {byte} byte · ffprobe {dt:.3f}s")

        # ─── CHỐT CHỐNG PASS OAN: file phải là NỘI DUNG WAV, không chỉ "mở
        # được". Nếu ai đó chữa bằng cách đổi codec theo đuôi (bản vá 20/08)
        # thì `.mp3` ra mp3 thật -> `dai_wav` mù -> hàm tự vứt file của mình,
        # và mục trên sẽ ĐỎ. Mục này nói THẲNG ra bất biến đó để người sau
        # không "dọn cho gọn" bằng cách bỏ `-f wav`.
        for ma in ("gn", "vn", "vb"):
            p = hop / f"{ma}.mp3"
            kiem(f"7{ma}-wav nội dung là WAV (`dai_wav` đọc được) dù tên .mp3",
                 GN.dai_wav(p) > 0.02, f"dai_wav={GN.dai_wav(p):.3f}s")

        # ─── QUÉT TĨNH bằng AST, KHÔNG quét chuỗi ───────────────────────────
        # Quét bằng chuỗi thì chính KHỐI GHI CHÚ giải thích bản vá (có chữ
        # `-f wav`) bị kể là "đã có" -> PASS OAN (bài học 47/51/53/56d/73/85).
        # Và bộ dò kiểu `tokenize` bỏ STRING cũng SAI ở đây theo chiều NGƯỢC
        # lại — thứ cần tìm CHÍNH LÀ một chuỗi, bỏ STRING đi là mục ĐỎ OAN
        # vĩnh viễn (đã sập đúng chỗ này khi viết CA 7).
        # ĐÚNG: đọc DANH SÁCH đối số truyền cho `subprocess.run`, chỉ xét lệnh
        # nào THẬT SỰ mã hoá tiếng (`-c:a pcm_s16le`), rồi đòi `-f` `wav`
        # đứng LIỀN NHAU trong chính danh sách đó.
        def lenh_ma_hoa(p: Path) -> list[list]:
            cay = ast.parse(p.read_text("utf-8"))
            ra = []
            for nut in ast.walk(cay):
                if not (isinstance(nut, ast.Call) and nut.args
                        and isinstance(nut.args[0], (ast.List, ast.Tuple))):
                    continue
                f = nut.func
                if not (isinstance(f, ast.Attribute) and f.attr == "run"):
                    continue
                hs = [e.value if isinstance(e, ast.Constant) else None
                      for e in nut.args[0].elts]
                if "pcm_s16le" in hs:
                    ra.append(hs)
            return ra

        def co_f_wav(hs: list) -> bool:
            return any(hs[i] == "-f" and i + 1 < len(hs)
                       and hs[i + 1] == "wav" for i in range(len(hs)))

        for ten, f in (("giong_ngoai", "app/core/giong_ngoai.py"),
                       ("giong_vieneu", "app/core/giong_vieneu.py"),
                       ("giong_vbee", "app/core/giong_vbee.py")):
            ds = lenh_ma_hoa(REPO / f)
            kiem(f"7q-{ten} MỌI lệnh ffmpeg ghi tiếng đều ép muxer `-f wav`",
                 bool(ds) and all(co_f_wav(x) for x in ds),
                 f"{sum(1 for x in ds if co_f_wav(x))}/{len(ds)} lệnh")
        # TỰ KIỂM BỘ DÒ — thiếu mục này thì `co_f_wav` trả True bừa cũng xanh.
        kiem("7q-tự-kiểm bộ dò BẮT được lệnh thiếu `-f wav`",
             not co_f_wav(["ffmpeg", "-i", "a.wav", "-c:a", "pcm_s16le",
                           "b.mp3"])
             and co_f_wav(["ffmpeg", "-c:a", "pcm_s16le", "-f", "wav", "b"]))
    finally:
        shutil.rmtree(hop, ignore_errors=True)


def main() -> int:
    print("=" * 70)
    print("CỔNG 63 — BIẾN THỂ GIỌNG (pitch) NỐI ĐỦ 3 CHỖ GỌI TTS")
    print("=" * 70)

    from app.core import thay_giong as TG

    # ═══════════ CA 1 — tách/ghép mã, BẤT BIẾN chuỗi cũ ═══════════
    print("\nCA 1 — `tach_giong_pitch` / `ma_bien_the`")
    cu = "vi-VN-NamMinhNeural"
    kiem("1a mã CŨ (không có `|`) -> nguyên vẹn + `+0Hz`",
         TG.tach_giong_pitch(cu) == (cu, "+0Hz"), f"{TG.tach_giong_pitch(cu)}")
    kiem("1b mã biến thể tách đúng 2 phần",
         TG.tach_giong_pitch(f"{cu}|-20Hz") == (cu, "-20Hz"))
    kiem("1c `+0Hz` ghép ngược ra ĐÚNG chuỗi cũ (không đẻ hậu tố)",
         TG.ma_bien_the(cu, "+0Hz") == cu, TG.ma_bien_the(cu, "+0Hz"))
    kiem("1d ghép rồi tách lại ra chính nó (round-trip)",
         all(TG.tach_giong_pitch(TG.ma_bien_the(cu, p)) == (cu, p)
             for p in ("-20Hz", "-10Hz", "+10Hz", "+20Hz")))
    # mã pitch LẠ không được làm chết lượt thay giọng
    kiem("1e mã pitch LẠ -> bỏ pitch, KHÔNG ném",
         TG.tach_giong_pitch(f"{cu}|nhanh") == (cu, "+0Hz"),
         f"{TG.tach_giong_pitch(f'{cu}|nhanh')}")
    kiem("1f chuỗi rỗng -> không nổ", TG.tach_giong_pitch("") == ("", "+0Hz"))

    # ═══════════ CA 2 — BA chỗ gọi TTS đều truyền `pitch` ═══════════
    # Đây là mục đắt nhất: sót 1 chỗ = video lẫn hai giọng, rc vẫn 0.
    print("\nCA 2 — BA chỗ gọi `_synth_all_words` đều truyền `pitch`")
    than = Path(TG.__file__).read_text(encoding="utf-8")
    cay = ast.parse(than)

    goi = [n for n in ast.walk(cay)
           if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute)
           and n.func.attr == "_synth_all_words"]
    kiem("2a tìm thấy ĐÚNG 3 chỗ gọi (thêm chỗ thứ 4 thì cổng này phải đỏ "
         "để người thêm biết là còn phải nối pitch)",
         len(goi) == 3, f"{len(goi)} chỗ")

    thieu = []
    hang_so = []
    for n in goi:
        kw = {k.arg: k.value for k in n.keywords}
        if "pitch" not in kw:
            thieu.append(n.lineno)
        elif isinstance(kw["pitch"], ast.Constant):
            # `pitch="+0Hz"` giữ nguyên mặt chữ mà vô hiệu hoá cả tính năng
            hang_so.append(n.lineno)
    kiem("2b MỌI chỗ gọi đều có `pitch=`", not thieu,
         f"thiếu ở dòng {thieu}" if thieu else "3/3")
    kiem("2c ... và truyền BIẾN, không phải hằng số", not hang_so,
         f"hằng số ở dòng {hang_so}" if hang_so else "3/3")

    # ═══════════ CA 3 — bảng biến thể ═══════════
    print("\nCA 3 — bảng biến thể + nhãn")
    ds = TG.bien_the_giong()
    kiem("3a có biến thể cho cả 2 giọng Việt",
         len({TG.tach_giong_pitch(m)[0] for m, _n in ds}) == 2,
         f"{sorted({TG.tach_giong_pitch(m)[0] for m, _n in ds})}")
    nhan = [n for _m, n in ds]
    kiem("3b nhãn KHÔNG EMOJI", not any(co_emoji(x) for x in nhan))
    # "CÓ DẤU TIẾNG VIỆT" LÀ CHỐT SAI BẢN CHẤT — đã hỏng oan 2 lần khi viết
    # cổng này: bản 1 liệt kê tay 15 chữ có dấu nên thiếu `ọ`/`ố` ("giọng
    # gốc"); bản 2 dùng dải `À-ỹ` thì vẫn đỏ vì **"Nam Minh — cao" là tiếng
    # Việt mà không có một dấu nào**. Mệnh đề THẬT cần canh không phải "có
    # dấu" mà là **nhãn không phơi mã máy / chữ tiếng Anh ra cho anh Hùng**.
    XAU = ("hz", "|", "pitch", "high", "low", "male", "female", "neural",
           "vi-vn", "+", "default")
    lo = [x for x in nhan if any(t in x.lower() for t in XAU)]
    kiem("3c nhãn KHÔNG phơi mã máy/chữ tiếng Anh ra giao diện",
         not lo, f"lộ: {lo}" if lo else f"{len(nhan)} nhãn sạch")
    kiem("3d không có nhãn trùng nhau", len(set(nhan)) == len(nhan))
    kiem("3e không có mã trùng nhau",
         len({m for m, _n in ds}) == len(ds))
    kiem("3f giọng KHÔNG phải tiếng Việt -> `[]` (combo giữ nguyên như cũ)",
         TG.bien_the_giong("en-US-AndrewNeural") == [])
    # mọi pitch trong bảng phải hợp lệ (không thì `ma_bien_the` âm thầm bỏ)
    kiem("3g mọi mã trong bảng tách lại ra ĐÚNG pitch của nó",
         all(TG.tach_giong_pitch(m)[1] == p
             for v, b in TG.BIEN_THE_PITCH.items() for p, _n in b
             if (m := TG.ma_bien_the(v, p)) and p != "+0Hz"))

    # ═══════════ CA 4 — COMBO trong hộp Thay giọng ═══════════
    print("\nCA 4 — combo hộp Thay giọng nhận biến thể, KHÔNG đẻ dòng trùng")
    import _test_guard  # noqa: F401  (luật: mọi cổng đụng UI phải import)
    from app.ui.thay_giong_dialog import giong_dung_duoc

    vao = [("Tiếng Việt", ""),
           ("Nam - Nam Minh", "vi-VN-NamMinhNeural"),
           ("Nu - Hoai My", "vi-VN-HoaiMyNeural"),
           ("Tieng Anh", ""),
           ("Andrew", "en-US-AndrewNeural")]
    ra = giong_dung_duoc(vao)
    ma = [v for _n, v in ra if v]
    kiem("4a giọng gốc VẪN CÒN (không bị biến thể thay chỗ)",
         "vi-VN-NamMinhNeural" in ma and "vi-VN-HoaiMyNeural" in ma)
    kiem("4b có mã biến thể trong combo",
         any("|" in v for v in ma), f"{[v for v in ma if '|' in v][:3]}")
    kiem("4c KHÔNG có mã trùng (mục `+0Hz` phải bị bỏ, nó trùng giọng gốc)",
         len(set(ma)) == len(ma),
         f"{len(ma)} mã / {len(set(ma))} khác nhau")
    kiem("4d giọng KHÁC ngôn ngữ không bị chèn biến thể",
         ma.count("en-US-AndrewNeural") == 1
         and not any(v.startswith("en-US") and "|" in v for v in ma))
    kiem("4e biến thể nằm NGAY SAU giọng gốc của nó",
         ma.index("vi-VN-NamMinhNeural") + 1 < len(ma)
         and ma[ma.index("vi-VN-NamMinhNeural") + 1].startswith(
             "vi-VN-NamMinhNeural|"))
    kiem("4f nhãn trong combo KHÔNG EMOJI",
         not any(co_emoji(n) for n, _v in ra))

    # ═══════════ CA 5 — BẤT BIẾN: chưa chọn biến thể thì y hệt cũ ═══════════
    print("\nCA 5 — BẤT BIẾN: mẫu CŨ (mã không có `|`) chạy y hệt trước")
    kiem("5a mọi giọng mặc định theo ngôn ngữ đều KHÔNG có `|`",
         all("|" not in TG.giong_theo_ngon_ngu(x)
             for x in ("vi", "en", "zh", "ja", "ko")))
    kiem("5b `+0Hz` = KHÔNG truyền pitch cho edge-tts (đường cũ nguyên vẹn)",
         TG.tach_giong_pitch("vi-VN-HoaiMyNeural")[1] == "+0Hz")

    ca6_giong_nhan_ban()
    ca7_ghi_ra_duoi_mp3()

    print("\n" + "=" * 70)
    print(f"ĐẠT {DAT} · HỎNG {HONG}")
    print("=" * 70)
    return 1 if HONG else 0


if __name__ == "__main__":
    raise SystemExit(main())
