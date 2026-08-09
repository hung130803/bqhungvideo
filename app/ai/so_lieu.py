# -*- coding: utf-8 -*-
"""NHẬN SỐ LIỆU **VIEW THẬT** TỪ TIKTOK / YOUTUBE — và dạy AI bằng nó.

=== NÓI THẲNG APP KHÔNG LÀM ĐƯỢC GÌ ===
App **KHÔNG tự lấy được** số view. Không có API, không đăng nhập kênh của anh
Hùng, và 200-300 kênh thì càng không. Vì vậy file này CHỈ dựng **ĐƯỜNG NHẬN**:
anh Hùng bấm "Xuất dữ liệu" trên trang thống kê của TikTok/YouTube, được một
file CSV (hoặc JSON), rồi nhập vào app. Không có file -> **prompt Y HỆT hiện
tại**, không đổi một chữ.

=== ANH HÙNG CẦN XUẤT FILE THẾ NÀO ===
Chỉ cần MỘT bảng có 3 cột (tên cột viết sao cũng được, xem `_COT` bên dưới):

    ten_file, view, xem_tb
    Part 1 - Ngoi nha cu.mp4, 128000, 21.4
    Part 2 - Ngoi nha cu.mp4, 3100, 4.2

  * `ten_file`  — TÊN FILE CLIP đã đăng (hoặc tiêu đề bài đăng, nếu anh giữ
                  nguyên tên). Đây là cầu nối duy nhất giữa thống kê và clip.
  * `view`      — số lượt xem.
  * `xem_tb`    — thời lượng xem trung bình, tính bằng GIÂY. Nếu file của
                  TikTok ghi theo dạng "0:21" thì cũng đọc được.
  * (tuỳ chọn) `dai` — thời lượng clip, giây. Có cột này thì tính được **TỈ LỆ
                  XEM HẾT** = `xem_tb / dai`, thước tốt hơn view rất nhiều vì
                  không phụ thuộc kênh to hay nhỏ.

TikTok: *Studio sáng tạo -> Phân tích -> Nội dung -> Tải xuống dữ liệu*.
YouTube: *YouTube Studio -> Số liệu phân tích -> Nâng cao -> Xuất -> CSV*
(cột "Thời lượng xem trung bình" và "Số lượt xem").
Cột thừa cứ để nguyên, app bỏ qua. Xuất tiếng Anh hay tiếng Việt đều đọc được.

=== NỐI VÀO AI THẾ NÀO ===
Đúng cơ chế 👍/👎 đang chạy: `so_lieu_cua_kenh()` trả về vài clip **TỐT NHẤT**
và vài clip **TỆ NHẤT** theo số liệu THẬT, `khoi_prompt_so_lieu()` biến chúng
thành mấy dòng ví dụ trong prompt chọn đoạn của CHÍNH kênh đó.
BẤT BIẾN: chưa nhập gì -> `khoi_prompt_so_lieu` trả `""` -> prompt KHÔNG ĐỔI.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re

#: Cần bao nhiêu clip mới dám nói "clip này tốt hơn clip kia". Dưới mức này thì
#: số liệu chỉ là may rủi của thuật toán TikTok, đưa vào prompt là dạy AI học
#: cái nhiễu. Cố ý đặt ở 6 (3 tốt + 3 tệ).
TOI_THIEU = 6
#: Số ví dụ mỗi bên đưa vào prompt (prompt chọn đoạn đã sát mức 413 — cổng 26).
VI_DU = 3
#: Trần ký tự khối prompt — cùng trần với `chon_doan.khoi_prompt_gu`.
TRAN_CHU = 900

#: tên cột chấp nhận -> khoá chuẩn. Viết thường, bỏ dấu, bỏ ký tự lạ.
_COT = {
    "tenfile": "ten_file", "ten_file": "ten_file", "tenclip": "ten_file",
    "filename": "ten_file", "file": "ten_file", "video": "ten_file",
    "videotitle": "ten_file", "tieude": "ten_file", "title": "ten_file",
    "tenvideo": "ten_file", "noidung": "ten_file", "post": "ten_file",
    "view": "view", "views": "view", "luotxem": "view", "soluotxem": "view",
    "videoviews": "view", "viewcount": "view", "playcount": "view",
    "xemtb": "xem_tb", "xem_tb": "xem_tb", "thoiluongxemtrungbinh": "xem_tb",
    "averagewatchtime": "xem_tb", "avgwatchtime": "xem_tb",
    "averageviewduration": "xem_tb", "thoigianxemtrungbinh": "xem_tb",
    "watchtimeavg": "xem_tb",
    "dai": "dai", "thoiluong": "dai", "duration": "dai", "videolength": "dai",
    "length": "dai",
}


def _chuan_cot(s: str) -> str:
    """'Thời lượng xem trung bình' -> 'thoiluongxemtrungbinh'."""
    import unicodedata
    s = str(s or "").lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s)


def _so(v) -> float:
    """'1,234' · '1.2K' · '0:21' · '1:02:03' -> số. Không đọc được -> 0.

    Phải chịu được cả 3 kiểu vì mỗi trang xuất một kiểu, và TikTok còn xuất
    thời lượng theo dạng đồng hồ.
    """
    s = str(v or "").strip().replace(" ", " ")
    if not s:
        return 0.0
    if ":" in s:                       # 0:21 · 1:02:03
        p = s.split(":")
        try:
            n = 0.0
            for x in p:
                n = n * 60 + float(str(x).replace(",", ".") or 0)
            return n
        except ValueError:
            return 0.0
    m = re.match(r"^([\d.,\s]+)\s*([kmb])?$", s, re.I)
    if not m:
        return 0.0
    so = m.group(1).replace(" ", "")
    # '1,234' (ngăn nghìn) vs '1,5' (thập phân kiểu Việt): dấu phẩy đứng trước
    # ĐÚNG 3 chữ số và có chữ số phía trước -> ngăn nghìn.
    if re.search(r"\d,\d{3}(\D|$)", so) or so.count(",") > 1:
        so = so.replace(",", "")
    so = so.replace(",", ".")
    if so.count(".") > 1:              # '1.234.567' kiểu Việt
        so = so.replace(".", "")
    try:
        n = float(so)
    except ValueError:
        return 0.0
    return n * {"k": 1e3, "m": 1e6, "b": 1e9}.get((m.group(2) or "").lower(), 1)


def doc_file(duong_dan: str) -> tuple:
    """Đọc CSV/JSON -> `([{ten_file, view, xem_tb, dai}], lý do)`. Hàm THUẦN.

    KHÔNG BAO GIỜ NÉM LỖI: file hỏng/sai định dạng -> `([], lý do đọc được)`.
    Số liệu là thứ THÊM VÀO, không được làm app chết vì một file lạ.
    """
    p = str(duong_dan or "")
    if not p or not os.path.exists(p):
        return [], "không thấy file"
    try:
        tho = open(p, "rb").read()
    except OSError as e:
        return [], f"không đọc được file ({e.__class__.__name__})"
    for enc in ("utf-8-sig", "utf-8", "utf-16", "cp1258", "latin-1"):
        try:
            txt = tho.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        return [], "không đoán được bảng mã của file"
    hang: list = []
    t = txt.lstrip()
    if t.startswith("{") or t.startswith("["):
        try:
            d = json.loads(txt)
        except (ValueError, TypeError) as e:
            return [], f"JSON hỏng: {str(e)[:60]}"
        if isinstance(d, dict):
            for k in ("data", "items", "videos", "rows", "list"):
                if isinstance(d.get(k), list):
                    d = d[k]
                    break
        if not isinstance(d, list):
            return [], "JSON không phải danh sách bản ghi"
        hang = [x for x in d if isinstance(x, dict)]
    else:
        try:
            mau = csv.Sniffer().sniff(txt[:4000], delimiters=",;\t")
            dl = mau.delimiter
        except csv.Error:
            dl = "\t" if txt.count("\t") > txt.count(",") else ","
        try:
            hang = list(csv.DictReader(io.StringIO(txt), delimiter=dl))
        except csv.Error as e:
            return [], f"CSV hỏng: {str(e)[:60]}"
    if not hang:
        return [], "file rỗng (0 dòng dữ liệu)"
    ra, thieu = [], set()
    for h in hang:
        d: dict = {}
        for k, v in (h or {}).items():
            khoa = _COT.get(_chuan_cot(k))
            # cột 'ten_file' có nhiều tên đồng nghĩa; giữ cái ĐẦU TIÊN gặp để
            # không bị cột 'title' ghi đè cột 'filename' đúng hơn.
            if khoa and not (khoa == "ten_file" and d.get("ten_file")):
                d[khoa] = v
        ten = " ".join(str(d.get("ten_file") or "").split())
        if not ten:
            thieu.add("ten_file")
            continue
        ra.append({"ten_file": ten[:200], "view": int(_so(d.get("view"))),
                   "xem_tb": round(_so(d.get("xem_tb")), 2),
                   "dai": round(_so(d.get("dai")), 2)})
    if not ra:
        return [], ("không thấy cột tên file/tiêu đề — cần ít nhất 2 cột: "
                    "tên file và số view"
                    + (f" (thiếu: {', '.join(sorted(thieu))})" if thieu else ""))
    if not any(r["view"] or r["xem_tb"] for r in ra):
        return [], (f"đọc được {len(ra)} dòng nhưng KHÔNG dòng nào có số view "
                    "hay thời lượng xem — kiểm lại tên cột")
    return ra, f"đọc được {len(ra)} dòng"


def _diem(r: dict) -> float:
    """Thước xếp hạng: ưu tiên **TỈ LỆ XEM HẾT**, không có thì mới dùng view.

    Vì sao không dùng thẳng view: view phụ thuộc kênh to/nhỏ và cú hích thuật
    toán, còn "người ta xem được bao nhiêu phần clip" mới nói lên đoạn cắt có
    giữ chân được không — đúng thứ khâu chọn đoạn cần học.
    """
    dai = float(r.get("dai") or 0)
    xem = float(r.get("xem_tb") or 0)
    if dai > 0 and xem > 0:
        return max(0.0, min(2.0, xem / dai))
    return float(r.get("view") or 0)


def nhap_vao_db(duong_dan: str, project_id: int, db, nguon: str = "") -> tuple:
    """Nhập file vào bảng `clip_so_lieu` -> `(số dòng, lý do)`.

    Ghép sang clip trong DB theo TÊN FILE (`clips.export_path`) khi tìm được —
    có ghép thì lấy luôn tiêu đề/thoại/số đoạn thật để prompt có ví dụ CỤ THỂ.
    Không ghép được vẫn LƯU (anh Hùng có thể đã xoá clip cũ): số liệu vẫn dùng
    được ở mức "tên bài đăng + số đo".
    """
    hang, ly = doc_file(duong_dan)
    if not hang:
        return 0, ly
    n = 0
    for r in hang:
        ten = r["ten_file"]
        goc = os.path.splitext(os.path.basename(ten))[0]
        cid = tieu_de = thoai = ""
        n_seg = 0
        dai = float(r.get("dai") or 0)
        try:
            row = db.query_one(
                "SELECT c.id, c.title, c.transcript, c.reason, c.signals, "
                "c.start_sec, c.end_sec FROM clips c "
                "JOIN videos v ON v.id=c.video_id "
                "WHERE v.project_id=? AND c.export_path IS NOT NULL "
                "AND c.export_path LIKE ? ORDER BY c.id DESC LIMIT 1",
                (int(project_id), f"%{goc}%"))
        except Exception:  # noqa: BLE001 — DB lỗi không được chặn việc nhập
            row = None
        if row:
            cid = row["id"]
            tieu_de = str(row["title"] or "")[:160]
            thoai = " ".join(str(row["transcript"] or row["reason"]
                                 or "").split())[:180]
            try:
                n_seg = len((db.loads(row["signals"], {}) or {})
                            .get("segments") or [])
            except Exception:  # noqa: BLE001
                n_seg = 0
            if dai <= 0:
                dai = max(0.0, float(row["end_sec"] or 0)
                          - float(row["start_sec"] or 0))
        try:
            db.execute(
                "INSERT INTO clip_so_lieu(project_id,clip_id,ten_file,view,"
                "xem_tb,dai,tieu_de,thoai,n_seg,nguon) "
                "VALUES(?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(project_id,ten_file) DO UPDATE SET "
                "clip_id=excluded.clip_id, view=excluded.view, "
                "xem_tb=excluded.xem_tb, dai=excluded.dai, "
                "tieu_de=excluded.tieu_de, thoai=excluded.thoai, "
                "n_seg=excluded.n_seg, nguon=excluded.nguon, "
                "created_at=datetime('now')",
                (int(project_id), cid or None, ten, int(r["view"]),
                 float(r["xem_tb"]), float(dai), tieu_de, thoai, n_seg,
                 str(nguon or "")[:20]))
            n += 1
        except Exception as e:  # noqa: BLE001
            return n, f"lỗi ghi DB sau {n} dòng: {type(e).__name__}"
    return n, f"đã nhập {n} dòng ({ly})"


def so_lieu_cua_kenh(project_id, db, vi_du: int = VI_DU,
                     toi_thieu: int = TOI_THIEU) -> dict:
    """`{"tot": [...], "te": [...], "n": tổng}` — clip TỐT/TỆ nhất theo số thật.

    Dưới `toi_thieu` clip -> trả `n` nhưng danh sách RỖNG: chưa đủ để nói ai
    hơn ai, và dạy AI bằng 2 điểm dữ liệu là dạy nó cái nhiễu.
    """
    ra: dict = {"tot": [], "te": [], "n": 0}
    if project_id is None:
        return ra
    try:
        rows = db.query(
            "SELECT ten_file, view, xem_tb, dai, tieu_de, thoai, n_seg "
            "FROM clip_so_lieu WHERE project_id=?", (int(project_id),))
    except Exception:  # noqa: BLE001 — bảng chưa có (DB cũ) -> coi như chưa nhập
        return ra
    ds = [dict(r) for r in rows or []]
    ra["n"] = len(ds)
    if len(ds) < int(toi_thieu):
        return ra
    ds.sort(key=_diem, reverse=True)
    k = max(1, int(vi_du))
    ra["tot"] = ds[:k]
    ra["te"] = list(reversed(ds[-k:]))
    return ra


def khoi_prompt_so_lieu(sl: dict, max_chars: int = TRAN_CHU) -> str:
    """Khối "SỐ LIỆU THẬT" cho prompt chọn đoạn. Hàm THUẦN.

    **BẤT BIẾN: chưa nhập số liệu -> trả "" -> prompt Y HỆT hiện tại.** Cùng
    hợp đồng với `chon_doan.khoi_prompt_gu`.
    """
    if not isinstance(sl, dict):
        return ""
    tot = [d for d in (sl.get("tot") or []) if isinstance(d, dict)]
    te = [d for d in (sl.get("te") or []) if isinstance(d, dict)]
    if not tot or not te:
        return ""

    def _dong(d: dict) -> str:
        t = " ".join(str(d.get("tieu_de")
                         or d.get("ten_file") or "").split())[:80]
        p = f'  - "{t or "(không tiêu đề)"}"'
        so = []
        v = int(d.get("view") or 0)
        if v:
            so.append(f"{v:,} view".replace(",", "."))
        dai, xem = float(d.get("dai") or 0), float(d.get("xem_tb") or 0)
        if dai > 0 and xem > 0:
            so.append(f"xem hết {100 * min(1.0, xem / dai):.0f}% "
                      f"({xem:.0f}s/{dai:.0f}s)")
        elif xem > 0:
            so.append(f"xem trung bình {xem:.0f}s")
        if so:
            p += " — " + " · ".join(so)
        m = " ".join(str(d.get("thoai") or "").split())[:90]
        if m:
            p += f" — {m}"
        return p

    out = ("\n\nSỐ LIỆU THẬT CỦA KÊNH NÀY (khán giả đã xem thật, không phải "
           "cảm nhận): đây là bằng chứng MẠNH NHẤT về cái gì giữ chân người "
           "xem trên chính kênh này.")
    out += "\n✓ Các clip CHẠY TỐT NHẤT — hãy chọn đoạn theo kiểu này:"
    for d in tot:
        out += "\n" + _dong(d)
    out += "\n✗ Các clip CHẠY TỆ NHẤT — tránh kiểu này:"
    for d in te:
        out += "\n" + _dong(d)
    return out[:max_chars]


def huong_dan() -> str:
    """Chỉ dẫn NGẮN cho anh Hùng, hiện thẳng trên hộp thoại nhập."""
    return (
        "App KHÔNG tự lấy được số view (không có API, không đăng nhập kênh). "
        "Anh xuất file rồi nhập vào đây:\n\n"
        "• TikTok: Studio sáng tạo → Phân tích → Nội dung → Tải xuống dữ liệu\n"
        "• YouTube: YouTube Studio → Số liệu phân tích → Nâng cao → Xuất → CSV"
        "\n\nFile chỉ cần có 3 cột (tên cột tiếng Việt hay tiếng Anh đều được):"
        "\n  - tên file clip (hoặc tiêu đề bài đăng)\n  - số lượt xem"
        "\n  - thời lượng xem trung bình (giây, hoặc dạng 0:21)\n"
        "Có thêm cột thời lượng clip thì càng tốt — app tính được TỈ LỆ XEM "
        "HẾT, thước chuẩn hơn số view.\n\n"
        f"Cần ít nhất {TOI_THIEU} clip có số liệu thì AI mới dùng; ít hơn thì "
        "prompt giữ nguyên như hiện nay.")
