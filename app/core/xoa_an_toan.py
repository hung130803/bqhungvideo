# -*- coding: utf-8 -*-
"""CỬA DUY NHẤT ĐỂ XOÁ THƯ MỤC TẠM — chống "xoá nhầm cả cây mã".

═══════════════ ĐÃ XOÁ SẠCH CẢ REPO MỘT LẦN, 19/08/2026 ═══════════════
`giong_ngoai._doc_omnivoice` gọi ``_don(Path(ket.get("_sandbox") or ""))`` ở
nhánh LỖI. Nhìn thì vô hại. Nhưng **``Path("")`` KHÔNG RỖNG — nó là
``WindowsPath('.')``**, tức THƯ MỤC ĐANG LÀM VIỆC:

    >>> Path("")            # WindowsPath('.')
    >>> str(Path(""))       # '.'      -> truthy, lọt mọi canh `if d`
    >>> Path("").is_dir()   # True     -> lọt mọi canh `is_dir()`
    >>> shutil.rmtree(Path(""))        # XOÁ SẠCH THƯ MỤC ĐANG LÀM VIỆC

Hậu quả thật: mất `.git` (chỉ còn `objects`), `.venv`, `bin`, `_lib`,
`_giong_hang`, `_piper`, `_giong_ngoai`. **Mã thoát vẫn 0**, không một dòng
báo. Phải dựng lại repo từ `.git/objects`.

VÌ SAO PHẢI CÓ FILE NÀY THAY VÌ VÁ TỪNG CHỖ: quét ngày 19/08/2026 tìm được
**5 cửa** cùng hình dạng đó trong `app/` (`giong_ngoai`, `giong_vieneu`,
`piper_tts`, `queue/jobs`, `services`) — vá lẻ từng chỗ là bỏ sót chỗ thứ 6
mà người sau thêm vào. Cửa chung + cổng 80 quét tĩnh mới chặn được cả lớp.

BỐN CHỐT, XẾP THEO THỨ TỰ NGUY HIỂM (đừng gỡ chốt nào):
  1. `None` / chuỗi rỗng / chuỗi toàn khoảng trắng.
  2. **THƯ MỤC ĐANG LÀM VIỆC và mọi thư mục CHA của nó** — đây là chốt bắt
     `Path("")` và `"."`, tức chốt đã cứu được cả cây mã. Chặn cả cha vì
     `rmtree("..")` cũng xoá luôn cwd.
  3. **GỐC Ổ ĐĨA** (`D:\\`, `C:\\`, `\\\\máy\\chia-sẻ\\`) và thư mục người dùng.
  4. `trong=` (tuỳ chọn): chỉ cho xoá thứ nằm THẬT SỰ BÊN TRONG một gốc đã
     biết. Lớp thứ hai cho những nơi biết trước gốc — hai lớp vì lớp một dễ
     bị một bản vá sau làm hỏng mà không ai thấy.

KHÔNG BAO GIỜ NÉM. Mọi hàm ở đây nuốt lỗi và trả về giá trị (bài học rò
`_seg_*`, cổng 42): một lượt dọn hỏng không được phép giết lượt xuất.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Callable, Optional

__all__ = ["ly_do_cam", "don_thu_muc", "an_toan_de_xoa"]


def _goc_repo() -> Optional[Path]:
    """Thư mục gốc cây mã — dùng để CẤM xoá chính nó. None nếu không dò được."""
    try:
        return Path(__file__).resolve().parents[2]
    except (OSError, IndexError):  # pragma: no cover - chỉ khi cây file lạ
        return None


def _thu_muc_he_thong() -> list[Path]:
    """Những thư mục KHÔNG BAO GIỜ được xoá, dù caller có nói gì."""
    ra: list[Path] = []
    for ten in ("SystemRoot", "windir", "ProgramFiles", "ProgramFiles(x86)",
                "ProgramData", "USERPROFILE", "LOCALAPPDATA", "APPDATA",
                "TEMP", "TMP"):
        v = (os.environ.get(ten) or "").strip()
        if not v:
            continue
        try:
            ra.append(Path(v).resolve())
        except OSError:
            continue
    try:
        ra.append(Path.home().resolve())
    except (OSError, RuntimeError):
        pass
    g = _goc_repo()
    if g is not None:
        ra.append(g)
    return ra


def ly_do_cam(d) -> str:
    """LÝ DO không được xoá `d`. Chuỗi RỖNG = an toàn để xoá.

    Trả LÝ DO (chứ không phải bool) để nơi gọi ghi được vào log — một lượt
    lùi ÊM mà im lặng thì đúng bằng hỏng âm thầm.
    """
    if d is None:
        return "đường dẫn là None"
    try:
        tho = str(d)
    except Exception:                                        # noqa: BLE001
        return "đường dẫn không đọc được"
    if not tho.strip():
        return "đường dẫn là chuỗi rỗng"

    try:
        p = Path(d).resolve()
    except (OSError, ValueError):
        return "đường dẫn không phân giải được: " + tho[:120]

    # --- CHỐT 3: gốc ổ đĩa / chia sẻ mạng ---
    # `WindowsPath('D:/').parent` CHÍNH LÀ nó -> dấu hiệu chắc chắn của gốc.
    if p.parent == p or str(p) == p.anchor:
        return "GỐC Ổ ĐĨA: " + str(p)

    # --- CHỐT 2: thư mục đang làm việc và mọi thư mục CHA của nó ---
    # Đây là chốt bắt `Path("")` và `"."`. `Path("").resolve()` == cwd.
    try:
        cwd = Path.cwd().resolve()
    except OSError:
        cwd = None
    if cwd is not None:
        if p == cwd:
            return "THƯ MỤC ĐANG LÀM VIỆC: " + str(p)
        if p in cwd.parents:
            return "thư mục CHA của thư mục đang làm việc: " + str(p)

    # --- CHỐT 3b: thư mục hệ thống / người dùng / gốc cây mã ---
    for cam in _thu_muc_he_thong():
        if p == cam:
            return "thư mục hệ thống/người dùng: " + str(p)
    g = _goc_repo()
    if g is not None and (p == g or p in g.parents):
        return "gốc cây mã (hoặc thư mục chứa nó): " + str(p)

    return ""


def an_toan_de_xoa(d, trong=None) -> bool:
    """True nếu `d` xoá được. `trong` (tuỳ chọn) = gốc mà `d` PHẢI nằm bên trong.

    Hàm THUẦN, không đụng đĩa ngoài `resolve()` — để cổng test gọi thoải mái.
    """
    if ly_do_cam(d):
        return False
    if trong is None:
        return True
    try:
        p = Path(d).resolve()
        goc = Path(trong).resolve()
    except (OSError, ValueError):
        return False
    # `p == goc` cũng CẤM: hộp cát luôn là thư mục CON; xoá cả gốc là xoá luôn
    # môi trường (7,7 GB của giọng ngoài đã suýt mất kiểu đó).
    return p != goc and goc in p.parents


def don_thu_muc(d, trong=None, ghi_log: Optional[Callable[[str], None]] = None,
                ten_bat_dau: str = "") -> bool:
    """Xoá thư mục tạm `d`. Trả True nếu ĐÃ xoá. **KHÔNG BAO GIỜ NÉM.**

    `trong`        — nếu có, `d` phải nằm THẬT SỰ BÊN TRONG gốc này.
    `ten_bat_dau`  — nếu có, TÊN thư mục phải bắt đầu bằng tiền tố này. Chốt
                     rẻ mà chặt cho những nơi tự đặt tên thư mục tạm
                     (`_piper_...`): đường dẫn lạ nào cũng bị chặn.
    """
    def _log(s: str) -> None:
        if ghi_log:
            try:
                ghi_log(s)
            except Exception:                                # noqa: BLE001
                pass

    ly_do = ly_do_cam(d)
    if ly_do:
        _log("TỪ CHỐI dọn — " + ly_do)
        return False
    try:
        p = Path(d).resolve()
    except (OSError, ValueError):
        return False
    if ten_bat_dau and not p.name.startswith(ten_bat_dau):
        _log("TỪ CHỐI dọn " + str(p) + " — tên không bắt đầu bằng "
             + ten_bat_dau)
        return False
    if trong is not None and not an_toan_de_xoa(p, trong=trong):
        _log("TỪ CHỐI dọn " + str(p) + " — nằm ngoài " + str(trong))
        return False
    try:
        if not p.is_dir():
            return False
        shutil.rmtree(p, ignore_errors=True)
        return True
    except Exception:                                        # noqa: BLE001
        return False
