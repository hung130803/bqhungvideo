# -*- coding: utf-8 -*-
"""GIỌNG RIÊNG THEO KÊNH + XOAY VÒNG GIỌNG + NGHE THỬ (200-300 kênh).

**VÌ SAO CÓ FILE NÀY.** Anh Hùng chạy 200-300 kênh kiếm tiền. Trước lượt này
giọng đọc là **MỘT giá trị TOÀN CỤC** (``QSettings["recap_voice"]``), tức mọi
kênh ra cùng một giọng. Repo này đã đi đúng con đường đó một lần rồi và anh
Hùng đã kêu: mẫu phụ đề cũng từng là một giá trị toàn cục, tới lúc 100 kênh ra
clip trông giống hệt nhau mới phải làm ``projects.tpl_name`` (cổng 16/19).
Giọng đọc còn dễ bị soi hơn cả mẫu chữ.

**BA VIỆC, VÀ CHÚNG KHÁC NHAU — đừng gộp:**

1. **Gán giọng cho kênh** (``projects.giong``). Kênh A luôn giọng A. Đây là
   thứ hầu hết kênh cần: khán giả quen giọng, kênh có "chất".
2. **Xoay vòng giọng** (``projects.giong_ro``, một rổ). Mỗi VIDEO một giọng
   khác. Hợp với kênh tổng hợp / kênh mới chưa chốt giọng.
3. **Nghe thử** — mượn thẳng ``thay_giong.doc_thu`` (cổng 65), KHÔNG viết
   đường đọc thứ hai.

**BẤT BIẾN SỐ 1 — MỘT VIDEO CHỈ MỘT GIỌNG (luật all-or-nothing đã có, đừng
phá).** Xoay vòng chọn theo VIDEO chứ không theo CÂU/PART. Vì vậy
``giong_cho_video`` là hàm **TIỀN ĐỊNH**: cùng (kênh · khoá video · rổ) thì
lượt nào cũng ra đúng một giọng, kể cả ở tiến trình khác.

**CRC32, KHÔNG PHẢI ``hash()`` — bẫy đã sập thật ở ``lop_phu._chon_bien``.**
``hash()`` của Python băm kèm ``PYTHONHASHSEED`` ngẫu nhiên mỗi tiến trình, mà
app chạy **3 làn xuất song song ở 3 tiến trình** -> ba Part của cùng một video
ra ba giọng khác nhau, và **không tra lại được** sau đó. ``zlib.crc32`` là
hằng số của chuỗi, mãi mãi.

**KHOÁ VIDEO PHẢI BỀN.** Dùng ``video_id`` của DB nếu có, không thì TÊN FILE
(``so_lieu.py`` đã chọn đúng như vậy: clip cũ có thể archived/xoá nhưng tên
file thì còn). Đừng dùng đường dẫn đầy đủ — dây chuyền chuyển file qua thư mục
trung chuyển nên đường dẫn đổi giữa chừng, mà đổi khoá là đổi giọng.

**CHỐT GIỌNG LÚC XẾP JOB, ĐỪNG TRA LẠI LÚC XUẤT.** ``chot_giong()`` trả một
dict để nhét vào payload. Lý do có tiền lệ đắt: ``_tpl_for_project`` phải đóng
dấu ``_ten_mau`` vào bản sao mẫu vì dây chuyền **chụp mẫu rồi xuất sau hàng
phút** — đọc lại lúc xuất là đọc cấu hình của kênh KHÁC (cổng 25b). Ở đây còn
thêm một lý do: anh Hùng sửa rổ giọng giữa chừng thì video đang dở đổi giọng
giữa các Part.

**CỜ GIỌNG *KHÔNG* ĐƯỢC VÀO HASH CHỐNG TRÙNG.** Đây là chỗ dễ mất tiền nhất:
thêm một phần tử vào tuple băm là **200-300 kênh xuất lại từ đầu**. Cùng lý do
``ovl_spec`` (cổng 42) và cờ ``che_chu`` (cổng 56e) cố ý đứng ngoài / chỉ nối
vào ĐUÔI chuỗi. Nếu sau này thật sự cần, nối vào đuôi ``sig`` và **chỉ khi
kênh có gán giọng riêng**.

**KHÔNG NẠP Qt, KHÔNG GỌI MẠNG khi nạp module.** ``nghe_thu`` có gọi mạng
(edge-tts) nhưng đó là lúc NGƯỜI DÙNG BẤM.
"""
from __future__ import annotations

import json
import zlib
from typing import Optional

from app.core import giong_mo, nhan_nha
from app.database import db

#: Số giọng tối thiểu trong rổ thì xoay vòng mới có nghĩa. 1 giọng = không
#: phải xoay, đó là gán giọng (việc 1) — trả về thẳng cái đó chứ không đi qua
#: đường chia dư cho ra vẻ.
RO_TOI_THIEU = 2

#: Trần số giọng trong một rổ. Không phải giới hạn kỹ thuật mà là giới hạn
#: NGƯỜI: rổ 50 giọng thì anh Hùng không nghe thử hết được, mà giọng chưa nghe
#: thử là giọng chưa chốt. Đặt trần để hộp thoại có chỗ bám.
RO_TOI_DA = 20


# ---------------------------------------------------------------------------
# ĐỌC / GHI CẤU HÌNH KÊNH
# ---------------------------------------------------------------------------
def dat_giong_kenh(project_id: int, ma: str) -> None:
    """Gán giọng cho 1 kênh. ``ma=''`` = bỏ gán (kênh theo giọng chung)."""
    db.execute("UPDATE projects SET giong=? WHERE id=?",
               ((ma or "").strip(), int(project_id)))


def giong_kenh(project_id) -> str:
    """Giọng đã gán cho kênh; ``''`` = chưa gán. **KHÔNG BAO GIỜ NÉM.**

    DB cũ chưa có cột / DB vỡ -> ``''`` = y hệt hành vi trước khi có tính
    năng này. Đây là luật chung của mọi cột thêm sau: không đọc được thì trả
    về trạng thái CŨ, đừng đoán.
    """
    try:
        r = db.query_one("SELECT giong FROM projects WHERE id=?",
                         (int(project_id),))
    except (TypeError, ValueError):
        return ""
    if not r:
        return ""
    try:
        return ((r["giong"] or "")).strip()
    except (KeyError, IndexError, TypeError):
        return ""


def dat_ro_giong(project_id: int, ds) -> None:
    """Đặt RỔ giọng xoay vòng cho kênh. ``ds`` rỗng = tắt xoay vòng.

    Lọc trùng nhưng **GIỮ THỨ TỰ người dùng chọn** — thứ tự là thứ họ nhìn
    thấy trong hộp, sắp lại là lần sau mở ra thấy khác cái mình vừa đặt.
    """
    sach: list[str] = []
    for m in (ds or []):
        m = str(m or "").strip()
        if m and m not in sach:
            sach.append(m)
    db.execute("UPDATE projects SET giong_ro=? WHERE id=?",
               (json.dumps(sach[:RO_TOI_DA], ensure_ascii=False) if sach
                else "", int(project_id)))


def ro_giong(project_id) -> list[str]:
    """Rổ giọng của kênh (danh sách mã). ``[]`` = không xoay vòng.

    JSON hỏng -> ``[]`` chứ **không ném và không đoán**: một kênh có cấu hình
    hỏng không được phép làm chết cả lượt xuất của 299 kênh còn lại.
    """
    try:
        r = db.query_one("SELECT giong_ro FROM projects WHERE id=?",
                         (int(project_id),))
    except (TypeError, ValueError):
        return []
    if not r:
        return []
    try:
        raw = (r["giong_ro"] or "").strip()
    except (KeyError, IndexError, TypeError):
        return []
    if not raw:
        return []
    try:
        ds = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(ds, list):
        return []
    return [str(x).strip() for x in ds if str(x or "").strip()]


# ---------------------------------------------------------------------------
# CHỌN GIỌNG CHO MỘT VIDEO — TIỀN ĐỊNH
# ---------------------------------------------------------------------------
def khoa_video(video_id=None, ten_file: str = "") -> str:
    """Khoá BỀN của một video, để xoay vòng ra kết quả tra lại được.

    Ưu tiên ``video_id`` (số của DB, không bao giờ đổi). Không có thì tên
    file. **Không dùng đường dẫn đầy đủ**: dây chuyền chuyển file qua thư mục
    trung chuyển nên đường dẫn đổi giữa chừng, và khoá đổi là giọng đổi.
    """
    try:
        if video_id is not None and str(video_id).strip() != "":
            return f"v{int(video_id)}"
    except (TypeError, ValueError):
        pass
    return (ten_file or "").strip().lower()


def giong_cho_video(project_id, video_id=None, ten_file: str = "",
                    mac_dinh: str = "") -> tuple[str, str]:
    """Giọng của MỘT video. Trả ``(mã giọng, lý do)``.

    Thứ tự quyết định — **đọc từ trên xuống, dừng ở dòng đầu tiên khớp**:

    1. kênh có **RỔ >= 2 giọng** -> xoay vòng theo khoá video (tiền định);
    2. kênh có **gán giọng riêng** -> đúng giọng đó;
    3. còn lại -> ``mac_dinh`` (giọng đang chọn ở Cài đặt) — **y hệt hành vi
       trước khi có file này**.

    Rổ đứng TRƯỚC gán riêng là cố ý: đặt rổ là một hành động rõ ràng hơn (phải
    chọn nhiều giọng), còn ô "giọng riêng" có thể còn sót giá trị cũ. Ai đặt
    rổ rồi mà vẫn ra một giọng cố định thì sẽ tưởng tính năng hỏng.

    ``lý do`` là chuỗi tiếng Việt để ghi vào nhật ký dây chuyền — nhật ký
    không nói vì sao chọn giọng đó thì lúc anh Hùng thấy giọng lạ sẽ không có
    đường nào truy (bài học "nhật ký ghi mẫu «(mẫu đã chốt)»" = vô dụng).
    """
    ro = ro_giong(project_id)
    if len(ro) >= RO_TOI_THIEU:
        k = khoa_video(video_id, ten_file)
        if k:
            i = zlib.crc32(k.encode("utf-8")) % len(ro)
            return ro[i], f"xoay vòng {i + 1}/{len(ro)} theo video «{k}»"
        # Không có khoá bền thì KHÔNG bốc ngẫu nhiên: ngẫu nhiên ở đây nghĩa
        # là hai Part của cùng một video ra hai giọng. Lấy phần tử đầu và
        # NÓI RA là đã lùi.
        return ro[0], "xoay vòng nhưng THIẾU khoá video -> lấy giọng đầu rổ"
    rieng = giong_kenh(project_id)
    if rieng:
        return rieng, "giọng riêng của kênh"
    if len(ro) == 1:
        return ro[0], "rổ chỉ có 1 giọng -> dùng luôn"
    return (mac_dinh or ""), "giọng chung ở Cài đặt (kênh chưa gán)"


def chot_giong(project_id, video_id=None, ten_file: str = "",
               mac_dinh: str = "") -> dict:
    """Đơn thuốc giọng để **nhét vào payload job lúc XẾP**, không tra lại
    lúc xuất.

    Trả ``{"giong": mã, "vi_sao": lý do}``. Nơi gọi lúc xuất chỉ đọc khoá
    ``giong``; **thiếu khoá = job cũ nằm sẵn trong DB** -> phải lùi về đường
    cũ chứ không được coi là "giọng rỗng" (cùng luật ``che_chu=None`` khác
    ``che_chu=False`` ở cổng 56).
    """
    ma, ly_do = giong_cho_video(project_id, video_id, ten_file, mac_dinh)
    return {"giong": ma, "vi_sao": ly_do}


def giong_tu_payload(payload: dict, mac_dinh: str = "") -> str:
    """Đọc giọng đã chốt trong payload. Thiếu khoá -> ``mac_dinh``.

    Phân biệt "job cũ không có khoá" với "job mới chốt giọng rỗng" bằng
    ``in`` chứ không bằng ``.get() or``: ``.get() or mac_dinh`` biến một lựa
    chọn THẬT (rỗng = theo mặc định) thành không phân biệt được.
    """
    if not isinstance(payload, dict) or "giong" not in payload:
        return mac_dinh or ""
    return str(payload.get("giong") or "") or (mac_dinh or "")


# ---------------------------------------------------------------------------
# CHIA GIỌNG CHO NHIỀU KÊNH — việc "300 kênh đừng cùng một giọng"
# ---------------------------------------------------------------------------
def chia_giong_cho_kenh(project_ids, ro) -> dict[int, str]:
    """Chia đều một rổ giọng cho danh sách kênh. Trả ``{pid: mã giọng}``.

    **CHIA THEO pid, KHÔNG theo thứ tự trong danh sách** — danh sách kênh đổi
    thứ tự (đổi nhóm, đổi tên, thêm kênh mới) là toàn bộ 300 kênh đổi giọng.
    Chia theo ``pid % len(ro)`` thì kênh cũ giữ nguyên giọng khi thêm kênh
    mới, và tra lại được bằng tay.

    Hàm này **KHÔNG ghi DB** — nó chỉ tính. Nơi gọi tự quyết định ghi cho
    kênh nào (bài học cổng 29: hộp gán mẫu bản đầu chỉ có GÁN-HẾT / ĐỂ-NGUYÊN
    nên gán hết là phá mẫu của nhóm khác; phải cho tích từng kênh).
    """
    sach = [str(m).strip() for m in (ro or []) if str(m or "").strip()]
    if not sach:
        return {}
    ra: dict[int, str] = {}
    for p in (project_ids or []):
        try:
            pid = int(p)
        except (TypeError, ValueError):
            continue
        ra[pid] = sach[pid % len(sach)]
    return ra


def ro_goi_y(lang: str = "en", so: int = 8,
             toi_thieu: float = 0.0) -> list[str]:
    """Rổ giọng GỢI Ý cho một ngôn ngữ: lấy giọng nhấn nhá cao nhất.

    Chỉ lấy từ ``nhan_nha.BANG`` (giọng ĐÃ ĐO) nên mọi giọng gợi ý đều đã đọc
    thật 4 câu đúng tiếng của nó. ``toi_thieu`` là sàn nhấn nhá — đặt 3,1 thì
    bỏ hẳn nhóm "đều đều".

    **KHÔNG tự ghi vào DB, KHÔNG tự bật xoay vòng.** Gợi ý là gợi ý; anh Hùng
    nghe thử rồi mới chốt (``nhan_nha`` đã ghi rõ: *"Tôi không có tai"*).
    """
    pre = (lang or "").strip().lower()
    ds = [(m, v) for m, v in nhan_nha.BANG.items()
          if giong_mo.la_ma_edge(m) and v >= toi_thieu
          and (not pre or m.lower().startswith(pre + "-"))]
    ds.sort(key=lambda kv: (-kv[1], kv[0]))
    return [m for m, _ in ds[:max(0, int(so))]]


def nhan_giong_kenh(project_id, mac_dinh: str = "") -> str:
    """Một dòng TIẾNG VIỆT mô tả kênh đang dùng giọng gì. KHÔNG EMOJI.

    Dùng cho cột bảng Dây chuyền / nhật ký. Nhãn phải HIỆN MẶC ĐỊNH THẬT khi
    kênh chưa gán — ghi trơ *"(mặc định)"* thì anh Hùng tưởng kênh chưa có
    giọng (đúng bài học cổng 16 v2.6.25a: nhãn phải là
    ``(mẫu đang chọn: <TÊN>)``).
    """
    ro = ro_giong(project_id)
    if len(ro) >= RO_TOI_THIEU:
        return f"xoay vòng {len(ro)} giọng"
    rieng = giong_kenh(project_id) or (ro[0] if ro else "")
    if rieng:
        return f"{rieng}{nhan_nha.nhan(rieng)}"
    md = (mac_dinh or "").strip()
    return (f"(giọng chung: {md})" if md
            else "(giọng chung: tự chọn theo tiếng video)")


# ---------------------------------------------------------------------------
# NGHE THỬ — mượn cửa đã có, KHÔNG viết đường đọc thứ hai
# ---------------------------------------------------------------------------
def nghe_thu(ma: str, cau: str = "", ra_wav: Optional[str] = None) -> dict:
    """Đọc thử một câu bằng giọng ``ma``. Trả dict của ``thay_giong.doc_thu``.

    **ĐI ĐÚNG CỬA LƯỢT XUẤT ĐI.** ``doc_thu`` (cổng 65) đã tự lo: tách biến
    thể cao độ ``|<pitch>``, cắt lề im ~1,07 s của edge-tts, nhánh rẽ Piper /
    ElevenLabs, cache theo (giọng·pitch·câu). Viết một đường đọc riêng ở đây
    là tự tay đẻ ra chuyện *"nghe thử một đằng, video ra một nẻo"* — và cổng
    63 sẽ đỏ vì số chỗ gọi ``_synth_all_words`` vượt mốc (đúng chuyện đã xảy
    ra với chính ``doc_thu`` lúc nó gọi thẳng).

    Khoá ``nguon`` trong kết quả là **NGUỒN THẬT SỰ ĐÃ ĐỌC**, không phải cái
    người dùng chọn — nơi gọi PHẢI hiện nó ra.
    """
    from pathlib import Path

    import config
    from app.core import thay_giong

    if not str(ma or "").strip():
        return {"ra": "", "nguon": "", "cache": False, "loi": "Chưa chọn giọng"}
    if ra_wav is None:
        kho = Path(config.DATA_DIR) / "_nghe_thu"
        kho.mkdir(parents=True, exist_ok=True)
        ra_wav = str(kho / "_nghe_thu_kenh.wav")
    return thay_giong.doc_thu(str(ma).strip(), ra_wav, cau or "")
