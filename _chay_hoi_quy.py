# -*- coding: utf-8 -*-
"""CHẠY CẢ LƯỢT HỒI QUY, IN **MÃ THOÁT THẬT** CỦA TỪNG CỔNG.

BA CÁI BẪY FILE NÀY CỐ Ý TRÁNH (đều đã sập ít nhất một lần trong repo):
 1. **Nối `| tail` là NUỐT MÃ THOÁT** — mã thoát thấy được sẽ là của `tail`.
    Đây gọi `subprocess.run` rồi in `returncode` nguyên vẹn.
 2. **cp1252**: chạy hồi quy mà đổ ra file thì `print` tiếng Việt nổ
    `UnicodeEncodeError` -> cổng chết trong 0-1 giây, chạy tay lại xanh. Ép
    `PYTHONIOENCODING=utf-8` cho MỌI tiến trình con.
 3. **"xanh" vì chạy chưa tới chốt**: cổng chết sớm cũng có thể rc=0 nếu nó
    thoát trước phần kiểm. Nên in kèm **thời gian chạy** và **dòng tổng kết
    ĐẠT/HỎNG** dò được — rc=0 mà 0 giây / không có dòng tổng kết là ĐÁNG NGỜ.

    .venv\\Scripts\\python -u _chay_hoi_quy.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

PY = str(REPO / ".venv" / "Scripts" / "python.exe")

#: (nhãn, file, mốc ĐẠT mong đợi hoặc None)
CONG = [
    # 70, 69 và 68 PHẢI nằm trong danh sách này: cổng không được gọi thì nó chỉ
    # là một file .py nằm đó, và lượt hồi quy "xanh" mà không chạy cổng mới
    # chính là bẫy "ĐẠT OAN vì lượt chạy chưa tới chốt".
    #
    # Cổng 70 canh bản sửa CHẶN SẢN XUẤT (Groq khai tử `llama-3.3-70b-
    # versatile` -> 404 hàng loạt -> chết cả dây chuyền). Nó CÓ gọi Groq thật ở
    # mục 9 để chứng minh bảng phân loại lỗi khớp thân lỗi Groq trả về HÔM NAY;
    # muốn chạy offline thì đặt `BQ_BO_MANG=1`.
    # Cổng 72 canh nhóm GIỌNG NGOÀI (OmniVoice / IndexTTS). Nó KHÔNG đốt GPU
    # hay lượt Groq nào trong hồi quy (vá `_chay_ov` + `_lay_moc_groq`); ca
    # chạy THẬT bật bằng `BQ_GN_THAT=1`.
    # Mốc 40 -> 48 (18/08/2026): CA 7 thêm 5 mục canh NHÃN ĐỔI THEO MÁY (có bộ
    # gióng hàng thì con số PHỦ/RUNG trong nhãn phải khác hẳn lúc chưa có, và
    # phần GIẤY PHÉP CC-BY-NC giữ nguyên ở CẢ HAI) + 3 mục canh CHỖ ĐỂ ĐỒ
    # không nằm trong `%TEMP%` (môi trường 7,74 GB từng nằm ở đó: một lượt dọn
    # đĩa là giọng biến khỏi combo, đúng bệnh `_lib` cổng 58 CA5).
    # Cổng 74 canh bản sửa CHẶN SẢN XUẤT thứ HAI trong hai ngày: Groq áp trần
    # token đầu ra MẶC ĐỊNH (3072/2048) khi app không đặt `max_tokens`, làm JSON
    # bản dịch ĐỨT giữa chừng -> "LLM trả về không phải JSON hợp lệ". Nó nằm
    # ĐÂY vì đúng hôm qua cổng 70 vừa dính bẫy "cổng không ai gọi thì chỉ là
    # một file .py nằm đó". Không đốt lượt Groq đáng kể: chỉ CA 9 gọi thật
    # (30 câu, 1 lượt); `BQ_BO_MANG=1` để chạy hoàn toàn offline.
    # Cổng 77 canh LỖ HỔNG BẢO MẬT THẬT (18/08/2026): cổng 70 in `str(phat_key
    # ())` = NGUYÊN VĂN key Groq ra `_kq70*.txt`. Nó đứng ĐẦU danh sách vì nó
    # KHÔNG gọi mạng, chạy vài giây, và nếu có key rơi ra đĩa thì phải biết
    # NGAY chứ không đợi hết 30 cổng. Nó cũng là cổng duy nhất quét ĐĨA — chạy
    # sau các cổng khác thì nó còn bắt được key do CHÍNH LƯỢT NÀY vừa ghi ra,
    # nên đặt thêm một lượt nữa ở CUỐI (xem `CONG_CUOI`).
    # Cổng 80 ĐỨNG ĐẦU, trước cả 77 — không phải vì nó quan trọng hơn, mà vì
    # nó canh đúng cái NỀN mà 30 cổng còn lại đứng lên. Hôm nay
    # `giong_ngoai._don(Path(""))` = `rmtree('.')` đã **xoá sạch cây mã** (mất
    # `.git`, `.venv`, `bin`, `_lib`, `_giong_hang`, `_piper`, `_giong_ngoai`)
    # với mã thoát 0. Gần như cổng nào trong danh sách này cũng dựng hộp cát
    # rồi `rmtree` nó, nên chạy chúng trên một bản mã còn cửa hở là đánh cược
    # cả cây mã mỗi lượt hồi quy. Nó cũng rẻ (~15 giây, không mạng, không
    # ffmpeg, không Groq) nên đứng đầu không tốn gì.
    ("80 không xoá nhầm",   "_test_khong_xoa_nham.py",   69),
    ("77 không lộ key",     "_test_khong_lo_key.py",     27),
    # Cổng 78 canh lỗi MẤT NỘI DUNG: đoạn không được đọc lại thì mất luôn giọng
    # gốc -> chỉ còn nhạc -> im tiếng người. Đo trên 4 bản anh Hùng đã xuất:
    # 82,3s/1.209,3s = 6,8%, dồn vào 2/4 video. Cổng KHÔNG gọi Demucs/Groq/mạng
    # (nguồn dựng bằng `lavfi`) nên tiền định, không nhấp nháy.
    ("78 bù giọng gốc",     "_test_bu_giong_goc.py",     52),
    ("74 JSON bao dung",    "_test_json_bao_dung.py",     80),
    # Cổng 75 canh bản sửa CHẶN SẢN XUẤT thứ BA: clip xuất ra KHÔNG MỞ ĐƯỢC,
    # hình trắng (`0x80004005 — unsupported encoding settings`). Nó phải nằm
    # ĐÂY, không được để làm "một file .py nằm đó" — đúng bẫy cổng 70 dính hôm
    # qua. Nó KHÔNG gọi mạng (chỉ ffmpeg thật), và vì chạy vài phút nên nó còn
    # làm QUÃNG NGHỈ cho bể key Groq giữa cổng 74 (CA 9 gọi thật) và cổng 70
    # (mục "41 key còn nguyên") — đúng chỗ cổng 70 từng ĐỎ OAN vì 429 thật do
    # hai cổng đốt lượt đứng sát nhau.
    ("75 clip mở được",     "_test_clip_mo_duoc.py",     63),
    # Cổng 76 canh việc "mức nhấn nhá hiện cạnh mỗi giọng + giọng truyền cảm
    # lên trên". Nó KHÔNG gọi Groq và KHÔNG chạy ffmpeg (chấm bảng số + hàm
    # thuần) nên đứng đâu cũng được; để cạnh nhóm cổng giọng cho dễ đọc.
    ("76 nhấn nhá từng giọng", "_test_nhan_nha.py",      29),
    # Cổng 79 canh việc GOM NHÓM danh sách giọng (anh Hùng: "không phân gì cả,
    # rất lung tung"). Đo trước khi sửa: combo có 110 mã cho 90 giọng, tức
    # 20 dòng TRÙNG MÃ THẬT SỰ. Nó cũng KHÔNG gọi mạng/ffmpeg/Groq nên tiền
    # định; để cạnh cổng 76 vì hai cổng đọc chung `nhan_nha.BANG`.
    # 58 -> 84 (v2.38.0): thêm CA 8 (nhóm "khuyên dùng" làm LỐI TẮT) · CA 9
    # (mức nhấn nhá trên TỪNG dòng; biến thể cao độ KHÔNG được mượn số của
    # giọng gốc) · CA 10 (20 giọng VieNeu không phải giọng chết — gọi THẬT
    # `_synth_all_words` rồi xem nó rẽ vào đâu). NÂNG mốc = cổng CHẶT HƠN.
    ("79 gom nhóm giọng",   "_test_gom_giong.py",        84),
    # Cổng 81 canh lượt 19/08/2026: MỞ KHOÁ 185 giọng edge-tts (`giong_mo`) ·
    # giọng RIÊNG THEO KÊNH + XOAY VÒNG (`giong_kenh`) · NHÂN BẢN giọng từ mẫu
    # (`nhan_ban_giong`) · Chatterbox (`giong_chatter`). Cũng KHÔNG gọi mạng,
    # KHÔNG chạy model, KHÔNG tốn lượt Groq — nó chấm hàm thuần + DB hộp cát,
    # nên để cạnh cổng 76/79 (ba cổng cùng đọc `nhan_nha.BANG`).
    # MỆNH ĐỀ TRUNG TÂM (CA 3i): xoay vòng giọng phải TIỀN ĐỊNH qua NHIỀU
    # TIẾN TRÌNH có `PYTHONHASHSEED` KHÁC NHAU — app chạy 3 làn xuất song song
    # nên dùng `hash()` là 3 Part của CÙNG một video ra 3 giọng, và không tra
    # lại được. THỬ PHÁ (đổi `crc32` -> `hash()`): cổng ĐỎ đúng mục đó,
    # `0/3 tiến trình khớp`, mã thoát 1.
    ("81 giọng theo kênh",  "_test_giong_kenh.py",       57),
    # Cổng 82 canh lượt NỐI Chatterbox vào app (v2.38.0). Trước nó,
    # `giong_chatter.py` là 623 dòng mã mà **không một dòng nào trong
    # `giong_bang.py`/`dubbing.py` gọi tới** — đúng bẫy "cổng/tính năng không ai
    # gọi thì chỉ là một file .py nằm đó" mà cổng 70 đã dính. Nó KHÔNG gọi
    # mạng, KHÔNG nạp model thật, KHÔNG đốt GPU: phần đắt nhất (CA 7) chạy
    # CHÍNH script runner trong tiến trình con với gói `chatterbox` GIẢ mô
    # phỏng đúng tính dính `self.conds` — thứ biến "đọc kênh A rồi kênh B"
    # thành "kênh B ra giọng kênh A" mà mã thoát vẫn 0.
    ("82 Chatterbox đã nối", "_test_chatter_noi.py",     58),
    # Cổng 83 canh lượt 19/08/2026: MỞ HẾT giọng edge-tts (**76 -> 322 giọng /
    # 75 thứ tiếng**) sau khi TÁCH "đọc được" khỏi "đo nhấn nhá". Nó lôi ra hai
    # lỗi thật: `giong_mo.nen_mo` là **MÃ CHẾT** (quét AST: chỉ `loc_mo` gọi,
    # mà `loc_mo` không ai gọi -> 185 giọng "đã mở khoá" chưa bao giờ ra tới
    # combo), và 4 giọng Inuktitut chết vì regex của **thư viện khách**
    # `edge_tts` không bóc nổi locale 4 đoạn — chết TRƯỚC KHI chạm mạng.
    # Nó **KHÔNG tốn lượt Groq** và **KHÔNG đốt hạn mức ElevenLabs** (nhánh
    # `el:` chấm bằng cách vá điểm đến rồi xem nó rẽ vào đâu). CA 2 CÓ gọi mạng
    # edge-tts thật nhưng chỉ **3 giọng** (mẻ tiền định theo `crc32`, KHÔNG
    # `hash()`) — mẻ đó là thứ giữ cho bảng biên bản khỏi thành lời tự khai;
    # mạng hỏng thì nó BỎ QUA từng giọng, chỉ ĐỎ khi hỏng CẢ MẺ.
    # THỬ PHÁ nằm ngay trong cổng (CA 9, BẮT 3/3), và chốt chống-PASS-OAN của
    # mục 3f đã thử thật: `BQ_MOC_GIONG=HEAD` -> ĐỎ đúng mục đó, mã thoát 1.
    ("83 mở hết giọng",     "_test_mo_giong_het.py",     41),
    # Mốc 48 -> 98 (19/08/2026, lượt dựng lại `_giong_ngoai/`). Thêm 3 khối:
    # CA 10 môi trường nằm ĐÚNG CHỖ (không %TEMP%, không cạnh `.exe`) · CA 11
    # `cai_omnivoice` — nút dựng lại mà repo THIẾU, nên khi `_don(Path(""))`
    # xoá sạch cây mã thì 7,74 GB đó là thứ DUY NHẤT không dựng lại được ·
    # CA 12 CHỌN X RA X (câu tả phải nằm trong BẢNG TỪ ĐÓNG của model — chữ
    # ngoài bảng đã giết `ov:nu_am` một lần; mã lạ phải LÙI chứ không đọc
    # bằng giọng mặc định).
    # CA 10d LÔI RA MỘT LỖI THẬT: `goc or Path.home()` KHÔNG BAO GIỜ lùi được
    # vì `Path("")` là `WindowsPath('.')` (truthy) -> bản đóng gói có
    # DATA_DIR hỏng thì thư mục 7,7 GB rơi vào THƯ MỤC ĐANG LÀM VIỆC. Cùng họ
    # bẫy đã xoá sạch cây mã sáng nay, chỉ khác là GHI nhầm chỗ chứ không
    # XOÁ nhầm chỗ. Bản đầu của chính mục 10d ĐẠT OAN vì chỉ hỏi "có cạnh
    # .exe không" — ĐẠT vì lý do SAI.
    # THỬ PHÁ `_pha_giong_ngoai.py` (10 phép, mỗi phép gỡ ĐÚNG 1 chốt).
    ("72 giọng ngoài",      "_test_giong_ngoai.py",      98),
    # Cổng 73 canh chính `giong_hang.py`. Trước hôm nay nó chỉ được canh GIÁN
    # TIẾP qua cổng 72 — tức phần lấy mốc cho MỌI máy đọc không có cổng riêng.
    ("73 gióng hàng",       "_test_giong_hang.py",      None),
    ("71 tách giọng GPU",   "_test_demucs_gpu.py",       22),
    # Mốc 42 -> 44: mục 4 thêm 2 chốt cho phép CHE KEY (che vẫn tách được từng
    # key · bản in KHÔNG chứa nguyên văn key) — xem cổng 77.
    ("70 model Groq còn sống", "_test_groq_model.py",    44),
    ("69 viết tắt + mốc",   "_test_viet_tat.py",         95),
    # Mốc 43 -> 44: thêm mục 7a' TỰ KIỂM bản vá cách ly QSettings (18/08/2026,
    # cổng từng ĐỎ OAN vì đọc trúng registry thật của anh Hùng).
    # 44 -> 45: thêm mục TỰ KIỂM cho phép đo cỡ chữ (phải có NỀN để trừ, và cỡ
    # nhỏ vẫn phải đếm ra chữ). Trước đó phép đo cộng cả ĐỘ SÁNG CỦA PHIM vào
    # số điểm ảnh chữ nên cổng đỏ oan mỗi khi kho video đổi sang phim sáng.
    ("68 kiểu chữ thay giọng", "_test_kieu_chu_tg.py",    45),
    ("67 Adam ElevenLabs",  "_test_eleven_tg.py",        35),
    ("66 độ to đường xuất", "_test_do_to_xuat.py",       50),
    ("65 độ to + nghe thử", "_test_do_to_nghe_thu.py",   47),
    # Mốc 47 -> 57: cổng đã mọc thêm mục từ lâu (đo 53) và 18/08 thêm CA 3g
    # (nút tải Piper phải KHOÁ khi máy thiếu Python 3, như nút Demucs). Để mốc
    # thấp hơn số thật là mất khả năng bắt "mục lặng lẽ biến mất".
    ("64 Piper",            "_test_piper.py",           57),
    ("63 biến thể giọng",   "_test_bien_the_giong.py",  24),
    ("62 quét cả khung",    "_test_toan_khung.py",      33),
    ("60 chữ theo lời",     "_test_chu_theo_loi.py",    42),
    ("59 đường dài",        "_test_duong_dai.py",       46),
    ("57 bảng tiến độ",     "_test_tg_bang_tiendo.py",  57),
    ("56 che chữ",          "_test_che_chu.py",        123),
    ("55 thay giọng UI",    "_test_thay_giong_ui.py",   48),
    ("54 dubbing CJK",      "_test_dubbing_cjk.py",     44),
    ("53 thay giọng",       "_test_thay_giong.py",      44),
    ("52 CJK vá",           "_test_cjk_va.py",          46),
    ("52b mảnh cuối",       "_test_manh_cuoi.py",     None),
    ("31 nút không cụt",    "_test_nut_khong_cut.py", None),
    ("và/lỡ phụ đề",        "_test_va_lo_sub.py",       16),
    ("không popup",         "_test_no_popup.py",      None),
    ("làn cắt đói",         "_test_lane_starve.py",   None),
    ("smoke",               "_test_app_smoke.py",     None),
    # LƯỢT THỨ HAI của cổng 77, CỐ Ý đặt ở CUỐI. Lượt đầu chứng minh đĩa sạch
    # TRƯỚC khi chạy; lượt này quét lại sau khi **29 cổng vừa ghi ra `_kq_hq/`
    # và hàng loạt file tạm** — tức nó bắt được key do CHÍNH LƯỢT HỒI QUY NÀY
    # làm rơi ra, đúng kịch bản đã xảy ra hôm nay. Quét đĩa mất vài giây nên
    # chạy hai lượt gần như không tốn gì.
    ("77 không lộ key (lượt cuối)", "_test_khong_lo_key.py", 27),
]

#: Dòng tổng kết — mỗi cổng viết một kiểu, có cổng bỏ dấu tiếng Việt
#: ("DAT 42 · HONG 0"). Bắt hụt thì cột ĐẠT ra "?" và cổng bị gắn nhãn ĐÁNG
#: NGỜ oan; đã dính một lượt với cổng 60/63.
_RE_TK = re.compile(r"(?:ĐẠT|DAT|OK)\s+(\d+)\s*[·.]\s*"
                    r"(?:HỎNG|HONG|SAI)\s+(\d+)")

#: Mục cổng CỐ Ý KHÔNG CHẤM. Hiện chỉ cổng 56 có (CA17a/b/c đo THỜI GIAN, máy
#: bận thì `bo_qua()` — chấm ĐẠT là phát chứng nhận khống, chấm HỎNG là đỏ oan).
#: Không trừ phần này ra thì cổng 56 bị gắn nhãn "TỤT so mốc 123" MỖI LẦN máy
#: bận, và nhãn TỤT xuất hiện thường xuyên thì người ta thôi đọc nó — đúng cái
#: bẫy "cổng đỏ oan còn nguy hơn không có cổng" (bài học cổng 41 và 47).
_RE_BQ = re.compile(r"(?:BỎ QUA|BO QUA)\s+(\d+)")


def moi_truong() -> dict:
    e = dict(os.environ)
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONUTF8"] = "1"
    e["BQ_FFMPEG_SLOTS"] = "1"
    # KHÔNG dùng `main`: sau khi gộp thì mốc CHÍNH LÀ bản đang test -> cổng
    # đối chứng tự PASS OAN vĩnh viễn.
    #
    # VÌ SAO `v2.25.0` CHỨ KHÔNG `v2.26.0` (đã chạy nhầm một lượt, cổng bắt
    # được): mục CA23-3'' của cổng 56 đòi **bản mốc phải có TRƯỚC tính năng
    # che chữ** — không thì phép so "bật/tắt che chữ vẫn ra cùng dedup_key"
    # là so với chính tính năng đang test. Mà `che_chu` RA ĐỜI Ở v2.26.0
    # (`git show v2.25.0:app/services.py` có 0 dòng `che_chu`, v2.26.0 có 15).
    # Lấy v2.26.0 làm mốc -> CA23-3'' ĐỎ, và nó đỏ ĐÚNG: cổng đang báo mốc
    # không hợp lệ chứ không phải app hỏng. Mốc đúng = bản phát hành NGAY
    # TRƯỚC tính năng.
    e.setdefault("BQ_MOC_REF", "v2.25.0")
    return e


def main() -> int:
    env = moi_truong()
    print("=" * 78)
    print(f"HỒI QUY — {len(CONG)} cổng · BQ_MOC_REF={env['BQ_MOC_REF']}")
    print("=" * 78)
    kq = []
    for i_cong, (ten, f, moc) in enumerate(CONG):
        p = REPO / f
        if not p.exists():
            print(f"  {ten:<22} KHÔNG CÓ FILE {f}")
            kq.append((ten, f, -1, 0.0, None, None, moc, 0))
            continue
        t0 = time.time()
        r = subprocess.run([PY, "-u", str(p)], cwd=str(REPO), env=env,
                           capture_output=True, timeout=3600)
        gy = time.time() - t0
        out = (r.stdout or b"").decode("utf-8", "replace") + \
              (r.stderr or b"").decode("utf-8", "replace")
        (REPO / "_kq_hq").mkdir(exist_ok=True)
        # Tên log mang SỐ THỨ TỰ khi một file chạy nhiều lượt (cổng 77 chạy 2
        # lượt: đầu và cuối). Không có số thì lượt sau ghi đè lượt trước và mất
        # đúng cái log cần đọc.
        _lap = sum(1 for _, f2, _ in CONG if f2 == f) > 1
        _ten_log = f"{f}.{i_cong:02d}.txt" if _lap else f"{f}.txt"
        (REPO / "_kq_hq" / _ten_log).write_text(out, encoding="utf-8")
        m = None
        for m2 in _RE_TK.finditer(out):
            m = m2                            # lấy dòng tổng kết CUỐI CÙNG
        dat = int(m.group(1)) if m else None
        hong = int(m.group(2)) if m else None
        mbq = None
        for m3 in _RE_BQ.finditer(out):
            mbq = m3                          # dòng tổng kết CUỐI CÙNG
        bq = int(mbq.group(1)) if mbq else 0
        # So mốc theo ĐẠT + BỎ QUA: mục bỏ qua là mục KHÔNG CHẤM, không phải
        # mục mất đi. Vẫn in ra số bỏ qua để một lượt bỏ qua không bao giờ
        # trông giống một lượt chấm đủ.
        kq.append((ten, f, r.returncode, gy, dat, hong, moc, bq))
        co = "" if moc is None or dat is None else (
            "  (mốc %d)" % moc if dat + bq >= moc else "  << TỤT so mốc %d" % moc)
        if bq:
            co = f"  · BỎ QUA {bq}{co}"
        print(f"  {ten:<22} rc={r.returncode:<3} {gy:6.1f}s  "
              f"ĐẠT {dat if dat is not None else '?':>4} · "
              f"HỎNG {hong if hong is not None else '?':<4}{co}")

    print("=" * 78)
    do = [k for k in kq if k[2] != 0]
    ngo = [k for k in kq if k[2] == 0 and (k[4] is None or k[3] < 0.3)]
    print(f"ĐỎ: {len(do)} cổng" + (f" -> {[k[0] for k in do]}" if do else ""))
    if ngo:
        print(f"ĐÁNG NGỜ (rc=0 mà không thấy dòng tổng kết / chạy <0,3s): "
              f"{[k[0] for k in ngo]}")
    tut = [k[0] for k in kq
           if k[6] and k[4] is not None and k[4] + k[7] < k[6]]
    if tut:
        print(f"TỤT SỐ MỤC so với mốc: {tut}")
    bqua = [(k[0], k[7]) for k in kq if k[7]]
    if bqua:
        print(f"MỤC KHÔNG CHẤM (máy bận, không phải ĐẠT cũng không phải "
              f"HỎNG): {bqua}")
    return 1 if do else 0


if __name__ == "__main__":
    raise SystemExit(main())
