# -*- coding: utf-8 -*-
"""CHỌN ĐOẠN BẰNG AGENT "MUSE" CỦA META — TUỲ CHỌN, MẶC ĐỊNH TẮT (cổng 117).

Anh Hùng có tài khoản muse.ai (agent chạy trong máy ảo của Meta). Đo tay
13/11/2026: đưa link video, agent tự tải, tách khung, chép lời rồi trả JSON;
4 video 17-21 phút chạy song song xong trong 15-19 phút, 5/6 mốc bắt đầu lệch
1-2 s so với câu được trích, 1/6 lệch 12 s.

VÌ SAO GỌI QUA **CLI RỜI** (subprocess), KHÔNG import:
  Thư viện MuseAI-API (github.com/minhquan130599/MuseAI-API) là bản dịch
  ngược KHÔNG chính thức, KHÔNG có giấy phép. Không nạp một dòng mã của nó vào
  tiến trình app — chỉ gọi lệnh ``muse-ai`` mà anh Hùng TỰ cài ở venv riêng
  (xem HUONG_DAN_MUSE.md). Cách này giống hệt cách app gọi ffmpeg/Piper.

LỆNH CLI DÙNG (đọc từ ``muse_ai/cli.py`` + ``client.py`` của repo đó):
  * ``muse-ai [--state-dir D] --help``             -> dò có CLI không
  * ``muse-ai [--state-dir D] ping``               -> in "HTTP 200" khi đăng nhập được
  * ``muse-ai [--state-dir D] upload <local> <remote>`` -> in đường dẫn từ xa
  * ``muse-ai [--state-dir D] generate --prompt P --no-download
      --min-videos 1 --timeout T [--session-id S]``
      CLI KHÔNG có lệnh "gửi tin nhắn" riêng; ``generate`` gửi prompt qua
      ``/chat/stream`` rồi ĐỢI video. Không có video -> nó ném
      ``TimeoutError("No new Muse video appeared within Ts for session S")``
      = tin đã gửi, và câu lỗi đó mang luôn SESSION ID để đọc trả lời.
  * ``muse-ai [--state-dir D] history --session-id S --limit 40`` -> in JSON.
  * CLI **KHÔNG có lệnh xoá** (``fs.delete`` có trong client nhưng không ra
    CLI). Hàm dọn chỉ gọi ``delete`` nếu ``--help`` có liệt kê nó; không có
    thì ghi log "để lại thư mục từ xa".

BẤT BIẾN:
  * Không bao giờ ném lỗi ra ngoài, TRỪ ``CanceledError`` (bấm Huỷ).
  * Hỏng/quá giờ/JSON sai -> trả ``None`` kèm lý do; m1 rơi về Groq như cũ.
  * Không đọc, không ghi, không log cookie. Log chỉ ghi số đo + đầu/đuôi lỗi
    đã lọc dòng có chữ cookie/token.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import shlex
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Callable, Optional

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
_LOCK_SONG_SONG = None
_LOCK_INIT = threading.Lock()
_CACHE_CO: dict = {}          # {"t": monotonic, "kq": dict}
_CACHE_HONG: dict = {}        # khoá video -> (monotonic, lý do) lượt hỏng gần nhất
HONG_NHO_GIAY = 300.0
_CACHE_KQ: dict = {}          # khoá video -> (lúc, rows): vòng đợi-hết-lượt Groq gọi lại
KQ_NHO_GIAY = 1800            # KHÔNG gửi Muse lần 2; hết hạn / job xong -> quên (quen_ket_qua)
# để bấm "Phân tích lại" không nhận y nguyên Part cũ (soát 13/11/2026).


def quen_ket_qua(src: str) -> None:
    """Job chọn đoạn của video này đã XONG -> bỏ kết quả nhớ (mọi cài đặt)."""
    try:
        a = os.path.abspath(src)
        for k in [k for k in list(_CACHE_KQ) if k and k[0] == a]:
            _CACHE_KQ.pop(k, None)
    except Exception:  # noqa: BLE001
        pass


_DA_DON_TAM = [False]


def _don_tam_cu() -> None:
    """Thư mục `_muse_tam/BQ*` bỏ lại khi app bị tắt ngang (os._exit) -> dọn
    1 lần/tiến trình, chỉ cái CŨ hơn 2 giờ (cái mới có thể là việc đang chạy)."""
    if _DA_DON_TAM[0]:
        return
    _DA_DON_TAM[0] = True
    try:
        from app.core.xoa_an_toan import don_thu_muc
        goc = _data_dir() / "_muse_tam"
        if not goc.is_dir():
            return
        han = time.time() - 7200
        for d in goc.iterdir():
            if d.is_dir() and d.name.startswith("BQ") and d.stat().st_mtime < han:
                don_thu_muc(d, trong=goc, ten_bat_dau="BQ", ghi_log=ghi_log)
    except Exception:  # noqa: BLE001
        pass
CO_TTL = 600.0

# Câu báo "đã gửi" của CLI khi không có video nào sinh ra (client.py:203-206).
_RE_DA_GUI = re.compile(r"No new Muse video appeared within \d+s(?: for session (\S+))?")
_RE_SESSION = re.compile(r"session_id=(\S+)")


# ───────────────────────── cấu hình ─────────────────────────
def _st():
    from config import settings
    return settings


def la_bat(v) -> bool:
    """Bool từ cài đặt: chuỗi "0"/"false"/"" là TẮT (bool("0") là True — lỗi rà
    soát 13/11/2026: bỏ tích rồi Lưu mà Muse vẫn chạy)."""
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on")
    return bool(v)


_TU_DONG = {"t": -1e9, "kq": False}
TU_DONG_GIAY = 60.0


def bat() -> bool:
    """Cờ MUSE_CHON_DOAN. "1"/True bật · "0"/False tắt · RỖNG (chưa từng lưu) =
    TỰ ĐỘNG: bật khi tìm thấy `muse-ai` VÀ có ít nhất 1 tài khoản đã đăng nhập.
    Chỉ hỏi FILE CÓ TỒN TẠI (nhớ 60 s) — không chạy CLI, không chạm mạng."""
    try:
        v = getattr(_st(), "MUSE_CHON_DOAN", "")
        if v is None or (isinstance(v, str) and v.strip().lower() in ("", "auto", "tu_dong")):
            now = time.monotonic()
            if now - _TU_DONG["t"] > TU_DONG_GIAY:
                cli = lenh_cli()
                _TU_DONG["kq"] = bool(cli) and bool(ds_phien(cli))
                _TU_DONG["t"] = now
            return bool(_TU_DONG["kq"])
        return la_bat(v)
    except Exception:  # noqa: BLE001
        return False


def _data_dir() -> Path:
    from config import DATA_DIR
    return Path(DATA_DIR)


def ghi_log(dong: str) -> None:
    try:
        p = _data_dir() / "logs"
        p.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now()
        dong = _loc_bi_mat(str(dong))
        with open(p / f"muse_{ts:%Y%m%d}.log", "a", encoding="utf-8") as f:
            f.write(f"{ts:%H:%M:%S} {dong[:2000]}\n")
    except OSError:
        pass


def _loc_bi_mat(s: str) -> str:
    """Bỏ mọi dòng nhắc cookie/token/OTP/authorization — CLI in traceback có thể
    lộ header. Thà mất dòng log còn hơn lộ phiên đăng nhập."""
    out = []
    for ln in str(s).splitlines():
        if re.search(r"cookie|token|otp|authori[sz]ation|bearer|set-cookie|session=|csrf",
                     ln, re.I):
            out.append("[dòng có thông tin đăng nhập — đã ẩn]")
        else:
            out.append(ln)
    return "\n".join(out)


def lenh_cli() -> list[str]:
    """argv của CLI. MUSE_AI_CLI: đường dẫn exe, hoặc chuỗi lệnh có ngoặc kép
    (vd ``"C:\\py\\python.exe" "D:\\x\\cli.py"``). Rỗng -> tìm ``muse-ai`` trên PATH."""
    raw = str(getattr(_st(), "MUSE_AI_CLI", "") or "").strip()
    if not raw:
        w = shutil.which("muse-ai")
        if w:
            return [w]
        # CAI_MUSE.bat cài vào <ổ>:\MuseAI-API\.venv — tự tìm, khỏi bắt anh Hùng
        # dán đường dẫn (UI không có ô này; .env ghi từ ngoài app có thể không tới)
        for goc in _goc_muse_doan():
            exe = goc / ".venv" / "Scripts" / "muse-ai.exe"
            try:
                if exe.is_file():
                    return [str(exe)]
            except OSError:
                continue
        return []
    if os.path.isfile(raw.strip('"')):
        return [raw.strip('"')]
    try:
        parts = [p.strip('"') for p in shlex.split(raw, posix=False)]
    except ValueError:
        return []
    if not parts:
        return []
    exe = parts[0]
    if not (os.path.isfile(exe) or shutil.which(exe)):
        return []
    return parts


def _goc_muse_doan() -> list:
    """Chỗ CAI_MUSE.bat hay cài: <ổ>:/MuseAI-API (ổ C..H) và thư mục người dùng."""
    ds = [Path(f"{o}:\\") / "MuseAI-API" for o in "DCEFGH"]
    try:
        ds.append(Path.home() / "MuseAI-API")
    except (OSError, RuntimeError):
        pass
    return ds


def thu_muc_phien(cli: list[str]) -> Optional[Path]:
    """Thư mục `.muse-state` (chứa cookies.json sau `muse-ai login`). Ưu tiên
    MUSE_STATE_DIR; không đặt thì đoán `<repo MuseAI>/.muse-state` (exe nằm ở
    `<repo>/.venv/Scripts/muse-ai.exe`). Chỉ hỏi FILE CÓ TỒN TẠI, không đọc."""
    ung_vien = []
    sd = str(getattr(_st(), "MUSE_STATE_DIR", "") or "").strip()
    if sd:
        ung_vien.append(Path(sd))
    if cli:
        try:
            exe = Path(cli[-1] if cli[-1].endswith(".py") else cli[0]).resolve()
            for up in list(exe.parents)[:4]:
                ung_vien.append(up / ".muse-state")
        except OSError:
            pass
    for d in ung_vien:
        try:
            if (d / "cookies.json").is_file():
                return d
        except OSError:
            continue
    return None


# Gửi MỘT tin nhắn vào cuộc chat RIÊNG. Lệnh `generate` của CLI đọc lịch sử
# cuộc chat TRƯỚC khi gửi -> cuộc chat mới chưa có -> máy chủ trả 404 "session
# not found" (đo 13/11/2026) và việc không bao giờ được gửi. Script này chạy
# bằng python TRONG venv MuseAI (tiến trình rời, app không nạp mã của họ),
# gọi thẳng chat_stream — lần gửi đầu tiên tự tạo cuộc chat.
_MA_GUI = r'''
import asyncio, sys, argparse
sys.stdout.reconfigure(encoding="utf-8")
from muse_ai.cli import _connect
async def main(state_dir, sid, prompt_file):
    c = await _connect(argparse.Namespace(state_dir=state_dir))
    prompt = open(prompt_file, encoding="utf-8").read()
    await c.chat_stream(prompt=prompt, session_id=sid, stream_timeout=30)
    print("BQ_DA_GUI " + sid, flush=True)
asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3]))
'''


def python_muse(cli: list[str]) -> Optional[str]:
    """python.exe nằm cạnh muse-ai.exe (cùng venv). None nếu không thấy, hoặc
    MUSE_AI_CLI là dạng ``python script.py`` (không chắc python đó có muse_ai)."""
    try:
        if not cli or len(cli) != 1 or not cli[0].lower().endswith("muse-ai.exe"):
            return None
        p = Path(cli[0]).with_name("python.exe")
        return str(p) if p.is_file() else None
    except OSError:
        return None


# ───────────────────────── nhiều tài khoản ─────────────────────────
_TK_LOCK = threading.Lock()
_KHOA_CHUNG = threading.Lock()   # đường lùi `generate`: một việc một lúc
_TK_TAI: dict = {}        # str(phiên) -> số việc đang chạy trên tài khoản đó
_TK_HONG: dict = {}       # str(phiên) -> monotonic hết hạn "tạm bỏ qua"
TK_NGHI_GIAY = 600.0
# CHỈ lỗi đăng nhập THẬT. Bản đầu bắt cả chữ 'login'/'401' ở bất cứ đâu -> traceback
# của lỗi MẠNG (đi qua auth.ensure_session, in mã nguồn có 'login_referer') hay số
# '4012 byte' cũng làm tạm bỏ một tài khoản đang tốt.
_RE_LOI_TK = re.compile(r"museautherror|\bhttp[ /]?40[13]\b|status[ =:]*40[13]\b|unauthori[sz]ed")


def ds_phien(cli: list[str]) -> list:
    """Mọi thư mục phiên đã đăng nhập: MUSE_STATE_DIRS (phẩy/chấm phẩy/xuống
    dòng) rồi MUSE_STATE_DIR/đoán. Chỉ lấy thư mục CÓ cookies.json, không trùng."""
    raw = str(getattr(_st(), "MUSE_STATE_DIRS", "") or "")
    ds = [Path(x.strip().strip('"')) for x in re.split(r"[,;\r\n]+", raw) if x.strip()]
    mot = thu_muc_phien(cli)
    if mot is not None:
        ds.append(mot)
        # Thêm tài khoản = chạy THEM_TK_MUSE.bat -> thư mục `.muse-state-<tên>` cạnh
        # thư mục chính; app tự nhận, không phải sửa .env.
        try:
            ds += sorted(p for p in mot.parent.glob(".muse-state*") if p.is_dir())
        except OSError:
            pass
    out, thay = [], set()
    for d in ds:
        try:
            k = str(d.resolve()).lower()
            if k not in thay and (d / "cookies.json").is_file():
                thay.add(k)
                out.append(d)
        except OSError:
            continue
    return out


def chon_phien(ds: list, tran: int = 0) -> Optional[Path]:
    """Tài khoản đang ít việc nhất (bỏ qua tài khoản vừa lỗi đăng nhập), +1 tải.
    `tran` > 0: mỗi tài khoản tối đa `tran` việc cùng lúc; đầy hết -> None (caller đợi)."""
    if not ds:
        return None
    with _TK_LOCK:
        now = time.monotonic()
        tot = [d for d in ds if _TK_HONG.get(str(d), 0) <= now] or list(ds)
        d = min(tot, key=lambda x: _TK_TAI.get(str(x), 0))
        if tran > 0 and _TK_TAI.get(str(d), 0) >= tran:
            return None
        _TK_TAI[str(d)] = _TK_TAI.get(str(d), 0) + 1
        return d


def tran_moi_tk() -> int:
    """Số video tối đa MỖI tài khoản chạy cùng lúc. Đo 13/11/2026 trên 1 tài khoản:
    15 video cùng lúc 15/15 (sau khi có giãn nhịp + thử lại 429). Mặc định 10."""
    try:
        return max(1, int(getattr(_st(), "MUSE_MOI_TK", 16) or 16))
    except (TypeError, ValueError):
        return 10


def tra_phien(d: Optional[Path]) -> None:
    if d is None:
        return
    with _TK_LOCK:
        _TK_TAI[str(d)] = max(0, _TK_TAI.get(str(d), 0) - 1)


def _danh_dau_tk(d: Optional[Path], err: str, kiem_ping: bool = True) -> bool:
    """Lỗi kiểu đăng nhập -> True = video này nên TRÁNH tài khoản `d` ở lượt hiện tại (chuyển tài
    khoản kế nếu có). Chỉ KHOÁ CHUNG 10 phút khi ping lại cũng hỏng = hết đăng nhập THẬT.

    ĐO 14/11/2026: (a) 00:13 `history` trả 401 mà ping ngay sau đó HTTP 200 (2/2); (b) 00:50 thư viện
    ném `MuseAuthError` cho MỌI lỗi >= 400 lúc đánh thức máy ảo (auth.wake_vm), ping sau đó 200 (3/3).
    Cả hai lần app khoá tài khoản DUY NHẤT 10 phút -> cả dây chuyền đứng đợi Muse."""
    e = (err or "").lower()
    if d is None or _RE_LOI_TK.search(e) is None:
        return False
    if kiem_ping and _ping_tot(d):
        ghi_log(f"tài khoản {d.name}: lỗi dạng đăng nhập nhưng ping lại vẫn tốt — KHÔNG khoá chung, "
                "chỉ tránh ở lượt này")
        return True
    with _TK_LOCK:
        _TK_HONG[str(d)] = time.monotonic() + TK_NGHI_GIAY
    ghi_log(f"tài khoản {d.name}: lỗi đăng nhập — tạm bỏ qua {TK_NGHI_GIAY:.0f}s")
    return True


def _ping_tot(d: Path) -> bool:
    """Ping lại đúng tài khoản `d`. Lỗi gì (kể cả không có CLI) -> False = coi như hỏng thật."""
    try:
        cli = lenh_cli()
        if not cli:
            return False
        rc, out, err = _chay(_argv(cli, d, "ping"), 45, thu_429=False)
        return rc == 0 and "200" in (out or "")
    except Exception as e:  # noqa: BLE001
        if type(e).__name__ == "CanceledError":
            raise
        return False


def _argv(cli: list[str], phien: Optional[Path], *tham_so: str) -> list[str]:
    a = list(cli)
    if phien is not None:
        a += ["--state-dir", str(phien)]
    return a + [str(x) for x in tham_so]


_GIAN_LOCK = threading.Lock()
_GIAN_MOC = [0.0]
GIAN_GIAY = 0.5        # khoảng cách tối thiểu giữa 2 lần mở kết nối Muse (mọi luồng)
THU_429 = 6            # số lần thử lại khi máy chủ trả HTTP 429
LUI_429_GIAY = 3.0     # đợi lùi dần: 3, 6, 12, 24, 48 s (trần 60) + ngẫu nhiên 0-2 s


def _cho_luot_mo():
    """Giãn nhịp mở kết nối: đo 13/11/2026, 15 việc cùng mở websocket một lúc
    -> 3/15 bị máy chủ từ chối HTTP 429. Mỗi lần gọi CLI = một kết nối mới."""
    with _GIAN_LOCK:
        cho = _GIAN_MOC[0] - time.monotonic()
        if cho > 0:
            time.sleep(cho)
        _GIAN_MOC[0] = time.monotonic() + GIAN_GIAY


_RE_429 = re.compile(r"\bhttp[ /]?429\b|status[ =:]*429\b|too many requests", re.I)
# Máy chủ TỪ CHỐI MỞ KẾT NỐI (chưa gửi gì đi -> thử lại an toàn), trừ 401/403 là
# lỗi đăng nhập. Đo 13/11/2026: một lượt tải lên dính "rejected WebSocket
# connection: HTTP 400" rồi rơi Groq oan.
_RE_KET_NOI = re.compile(r"rejected websocket connection: http (?!40[13]\b)\d{3}|"
                         r"connectionreseterror|connection reset|timed out during opening handshake", re.I)
# Bước GỬI yêu cầu: "connection reset" có thể xảy ra SAU khi tin đã đi -> thử lại
# là gửi prompt 2 lần. Chỉ thử lại khi chắc chắn CHƯA gửi (từ chối lúc bắt tay / 429).
_RE_TU_CHOI = re.compile(r"rejected websocket connection: http (?!40[13]\b)\d{3}|"
                         r"timed out during opening handshake", re.I)


def _chay(argv: list[str], timeout: float, check: Optional[Callable] = None,
          thu_429: bool = True, chi_tu_choi: bool = False, them_co: int = 0) -> tuple:
    """`_chay_mot` + giãn nhịp + gặp HTTP 429 thì đợi lùi dần rồi thử lại
    (3, 6, 12, 24, 48 s + ngẫu nhiên, có kiểm Huỷ). Lỗi khác trả về ngay."""
    import random
    kq = (-1, "", "")
    for lan in range(THU_429):
        _cho_luot_mo()
        kq = _chay_mot(argv, timeout, check, them_co=them_co)
        rc, out, err = kq
        _re = _RE_TU_CHOI if chi_tu_choi else _RE_KET_NOI
        if rc == 0 or not thu_429 or not (_RE_429.search(err + "\n" + out)
                                          or _re.search(err + "\n" + out)):
            return kq
        doi = min(60.0, LUI_429_GIAY * (2 ** lan)) + random.uniform(0, 2.0) * (LUI_429_GIAY > 0)
        ghi_log(f"máy chủ Muse bận / từ chối kết nối — đợi {doi:.0f}s rồi thử lại ({lan + 1}/{THU_429})")
        moc = time.monotonic() + doi
        while time.monotonic() < moc:
            if check is not None:
                check()
            time.sleep(0.5)
    return kq


def _giet_cay(p) -> None:
    """Giết tiến trình + mọi tiến trình con. Windows: `muse-ai.exe` và python.exe
    của venv là VỎ khởi chạy, giết mỗi vỏ có thể bỏ lại python thật đang giữ kết
    nối. Không bao giờ ném."""
    try:
        if os.name == "nt" and p.poll() is None:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=_CREATE_NO_WINDOW, timeout=10)
    except Exception:  # noqa: BLE001
        pass
    try:
        if p.poll() is None:
            p.kill()
        p.wait(5)
    except Exception:  # noqa: BLE001
        pass


_JOB_GIET: list = []


def _gan_song_chet(p) -> None:
    """Gắn tiến trình con vào một Job Object "chết theo tiến trình này" (KILL_ON_JOB_CLOSE).
    Đo 14/11/2026: app tự mở lại (os._exit) bỏ lại 13 lệnh ffmpeg dựng bản nhẹ MỒ CÔI, chạy tiếp
    8-13 phút, chiếm bộ giải mã NVDEC 99% trong khi app mới dựng lại đúng các bản đó. Handle job
    KHÔNG bao giờ đóng -> chỉ khi tiến trình này chết (kể cả bị giết) thì OS mới giết các con.
    Lỗi gì cũng bỏ qua: đây là lưới dọn rác, không được làm hỏng lượt chạy."""
    if os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import wintypes
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        if not _JOB_GIET:
            class _BASIC(ctypes.Structure):
                _fields_ = [("a", ctypes.c_int64), ("b", ctypes.c_int64), ("LimitFlags", wintypes.DWORD),
                            ("c", ctypes.c_size_t), ("d", ctypes.c_size_t), ("e", wintypes.DWORD),
                            ("f", ctypes.c_size_t), ("g", wintypes.DWORD), ("h", wintypes.DWORD)]

            class _IO(ctypes.Structure):
                _fields_ = [(n, ctypes.c_uint64) for n in "abcdef"]

            class _EXT(ctypes.Structure):
                _fields_ = [("Basic", _BASIC), ("Io", _IO), ("p1", ctypes.c_size_t),
                            ("p2", ctypes.c_size_t), ("p3", ctypes.c_size_t), ("p4", ctypes.c_size_t)]
            k.CreateJobObjectW.restype = wintypes.HANDLE
            h = k.CreateJobObjectW(None, None)
            if not h:
                return
            info = _EXT()
            info.Basic.LimitFlags = 0x2000          # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not k.SetInformationJobObject(wintypes.HANDLE(h), 9, ctypes.byref(info),
                                             ctypes.sizeof(info)):
                return
            _JOB_GIET.append(h)
        k.AssignProcessToJobObject(wintypes.HANDLE(_JOB_GIET[0]), wintypes.HANDLE(int(p._handle)))
    except Exception:  # noqa: BLE001
        pass


def _chay_mot(argv: list[str], timeout: float, check: Optional[Callable] = None,
              them_co: int = 0) -> tuple:
    """Chạy CLI, trả (mã, stdout, stderr). Kiểm Huỷ mỗi 0,5 s; Huỷ -> giết tiến
    trình rồi để CanceledError nổi lên. Lỗi khởi chạy/quá giờ -> (-1, "", lý do)."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    try:
        p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             stdin=subprocess.DEVNULL, env=env,
                             creationflags=_CREATE_NO_WINDOW | them_co)
    except OSError as e:
        return -1, "", f"không chạy được CLI: {e}"
    _gan_song_chet(p)
    buf = {"o": b"", "e": b""}

    def _doc(stream, k):
        try:
            buf[k] = stream.read() or b""
        except Exception:  # noqa: BLE001
            pass
    th = [threading.Thread(target=_doc, args=(p.stdout, "o"), daemon=True),
          threading.Thread(target=_doc, args=(p.stderr, "e"), daemon=True)]
    for t in th:
        t.start()
    han = time.monotonic() + max(1.0, timeout)
    try:
        while p.poll() is None:
            if check is not None:
                check()
            if time.monotonic() > han:
                _giet_cay(p)
                return -1, "", f"CLI quá giờ {timeout:.0f}s"
            time.sleep(0.5)
    except BaseException:
        try:
            _giet_cay(p)
        except Exception:  # noqa: BLE001
            pass
        raise
    for t in th:
        t.join(5)
    dec = lambda b: b.decode("utf-8", "replace")  # noqa: E731
    return p.returncode, dec(buf["o"]), dec(buf["e"])


# ───────────────────────── dò có Muse không ─────────────────────────
_CO_LOCK = threading.Lock()


def co_muse(kiem_mang: bool = True) -> dict:
    """{co, ly_do, ho_tro_xoa}. KHÔNG BAO GIỜ NÉM. Kết quả nhớ 10 phút. Có khoá:
    10 job cùng lúc hết hạn bộ nhớ thì chỉ MỘT job đi ping, các job kia đọc lại."""
    with _CO_LOCK:
        return _co_muse(kiem_mang)


def _co_muse(kiem_mang: bool = True) -> dict:
    try:
        now = time.monotonic()
        _c = dict(_CACHE_CO)
        if kiem_mang and _c.get("kq") and now - _c.get("t", -1e9) < CO_TTL:
            return dict(_c["kq"])
        cli = lenh_cli()
        if not cli:
            return {"co": False, "ly_do": "không tìm thấy lệnh muse-ai (đặt MUSE_AI_CLI)",
                    "ho_tro_xoa": False}
        _ds = ds_phien(cli)
        phien = _ds[0] if _ds else None
        if phien is None:
            return {"co": False, "ly_do": "chưa đăng nhập Muse (không thấy .muse-state/cookies.json"
                    " — chạy `muse-ai login --email ...`, hoặc đặt MUSE_STATE_DIR)",
                    "ho_tro_xoa": False}
        rc, out, err = _chay(_argv(cli, phien, "--help"), 60)
        if rc != 0:
            return {"co": False, "ly_do": f"`muse-ai --help` lỗi (mã {rc})",
                    "ho_tro_xoa": False}
        cmds = set(re.findall(r"\b(login|ping|model|history|generate|upload|delete)\b", out))
        thieu = {"upload", "generate", "history"} - cmds
        if thieu:
            return {"co": False, "ly_do": "CLI thiếu lệnh: " + ", ".join(sorted(thieu)),
                    "ho_tro_xoa": False}
        kq = {"co": True, "ly_do": "", "ho_tro_xoa": "delete" in cmds,
              "phien": str(phien)}
        if kiem_mang:
            # Nhiều tài khoản: chỉ cần MỘT cái ping đạt là dùng được Muse; cái
            # hỏng bị đánh dấu tạm bỏ qua để việc không chọn trúng nó.
            dat = None
            loi_mang = 0
            for d in (ds_phien(cli) or [phien]):
                rc, out, err = _chay(_argv(cli, d, "ping"), 45, thu_429=False)
                if rc == 0 and re.search(r"HTTP 2\d\d", out):
                    dat = d
                    break
                ghi_log(f"co_muse: tài khoản {Path(d).name} ping không đạt (mã {rc}) | "
                        + _loc_bi_mat(err[-300:]))
                # Chỉ lỗi ĐĂNG NHẬP mới tạm bỏ tài khoản; lỗi mạng là của MÁY, thử
                # thêm tài khoản khác cũng vậy -> 2 lần là dừng (không giữ khoá lâu).
                if not _danh_dau_tk(Path(d), err):
                    loi_mang += 1
                    if loi_mang >= 2:
                        break
            if dat is None:
                kq = {"co": False, "ly_do": f"`muse-ai ping` không đạt (mã {rc}) — hết phiên"
                      " đăng nhập hoặc mất mạng", "ho_tro_xoa": False}
            else:
                kq["phien"] = str(dat)
            _CACHE_CO.clear()
            _CACHE_CO.update(t=now, kq=dict(kq))
        return kq
    except Exception as e:  # noqa: BLE001
        return {"co": False, "ly_do": f"lỗi dò Muse: {e}", "ho_tro_xoa": False}


# ───────────────────────── bản nhẹ (proxy) ─────────────────────────
def dung_proxy(src: str, dst: str, check: Optional[Callable] = None,
               cao: int = 0, fps: float = 0.0) -> tuple:
    """Bản nhẹ để TẢI LÊN nhanh: cao <= 480 px, ~2 khung/giây, CRF 34, tiếng
    mono 24 kbps 16 kHz. Trả (ok, lý do)."""
    st = _st()
    cao = int(cao or getattr(st, "MUSE_PROXY_CAO", 480) or 480)
    fps = float(fps or getattr(st, "MUSE_PROXY_FPS", 2.0) or 2.0)
    ff = str(getattr(st, "FFMPEG_PATH", "ffmpeg") or "ffmpeg")
    # fps TRƯỚC scale (bỏ khung rồi mới thu nhỏ — trước đây thu nhỏ CẢ 30 khung/giây
    # rồi mới vứt 28) + GPU GIẢI MÃ (NVDEC) + ưu tiên BELOW_NORMAL như lượt xuất.
    # ĐO 13/11/2026 (5 phút video thật, đan xen 2 vòng): bản cũ 201 CPU-giây ở ưu
    # tiên THƯỜNG = thủ phạm "máy đơ"; GPU giải mã 34 CPU-giây (-83%), file ra Y
    # HỆT 7,86 MB. GPU lỗi / máy không có NVIDIA -> lùi giải mã CPU (vẫn fps trước).
    vf = f"fps={fps:g},scale=-2:'min({cao},ih)':flags=bilinear"
    duoi = ["-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "34",
            "-g", str(max(1, int(fps * 10))), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ac", "1", "-ar", "16000", "-b:a", "24k",
            "-threads", "2", "-movflags", "+faststart", str(dst)]
    dau = [ff, "-hide_banner", "-loglevel", "error", "-y"]
    thu = []
    if _co_gpu():
        thu.append(dau + ["-hwaccel", "cuda", "-i", str(src)] + duoi)
    thu.append(dau + ["-threads", "4", "-i", str(src)] + duoi)
    rc, err = -1, ""
    for argv in thu:
        rc, _o, err = _chay(argv, 3600, check, thu_429=False, them_co=_BELOW_NORMAL)
        if rc == 0 and os.path.isfile(dst) and os.path.getsize(dst) >= 1000:
            return True, ""
    return False, f"ffmpeg dựng bản nhẹ lỗi (mã {rc}): {err[-300:]}"


_BELOW_NORMAL = 0x00004000 if os.name == "nt" else 0
_GPU: dict = {}

# ───────────────────────── ảnh tổng hợp ─────────────────────────
# ĐO 13/11/2026 (phim thật 19 phút + 4 thẻ hình 6 s cài lệch lưới 30 s, đúng prompt app, 2 vòng
# A/B song song): Muse TỰ trích khung bằng ffmpeg mỗi 30-38 s (video 56 phút có khoảng hở 240 s)
# nên chỉ bắt 1/4 · 0/4 thẻ; kèm ảnh tổng hợp 1 khung/5 s có ghi giây -> 4/4 · 4/4, và Muse trả
# lời NHANH hơn (80/50 s vs 96/80 s) vì khỏi tự trích. Dựng từ BẢN NHẸ: 0,2 s · 1,4 MB/19 phút.
BANG_COT, BANG_HANG = 6, 4
BANG_TOI_DA = 40            # video dài: giãn nhịp khung để không quá 40 ảnh (960 khung)


def _font_bang() -> str:
    for f in (r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if os.path.isfile(f):
            return f.replace("\\", "/").replace(":", "\\:")
    return ""


def _so_ban_nhe() -> int:
    """Số bản nhẹ dựng cùng lúc trên cả máy. Anh Hùng ĐANG dùng máy -> 1 (`BQ_MUSE_BAN_NHE_DUNG`);
    rời máy >= `_RANH_GIAY` -> 3 (`BQ_MUSE_BAN_NHE`).

    ĐO 14/11/2026 13:20-13:30, anh Hùng: "máy đơ hết luôn, chết máy". CPU KHÔNG phải thủ phạm (trễ
    lập lịch 0,5 ms kể cả trên nhân phụ đang 100%, máy rảnh 56%, RAM còn 16,8 GB, ổ đĩa bận 0%);
    thứ duy nhất kín là bộ giải mã NVDEC của card (93%) vì bản nhẹ giải mã CẢ phim bằng GPU. Ép còn
    1 bản cùng lúc -> NVDEC 93% -> 8%, anh Hùng: "giờ ít đơ rồi"."""
    try:
        from app.core import ffmpeg_utils as fu
        roi = fu.giay_roi_may()
        dang_dung = roi is None or roi < fu._RANH_GIAY
    except Exception:  # noqa: BLE001
        dang_dung = True
    ten, mac = ("BQ_MUSE_BAN_NHE_DUNG", "1") if dang_dung else ("BQ_MUSE_BAN_NHE", "3")
    try:
        return max(0, int(os.environ.get(ten, mac)))
    except ValueError:
        return int(mac)


def nhip_bang(duration: float) -> float:
    """Giây giữa 2 khung của ảnh tổng hợp (0 = tắt)."""
    g = float(getattr(_st(), "MUSE_BANG_GIAY", 5.0) or 0)
    if g <= 0 or duration <= 0:
        return 0.0
    tran = BANG_TOI_DA * BANG_COT * BANG_HANG
    return max(g, float(int(-(-duration // tran))))   # làm tròn LÊN giây


def dung_bang(prox: str, thu_muc: str, duration: float,
              check: Optional[Callable] = None) -> tuple:
    """Dựng ảnh tổng hợp 6x4 từ bản nhẹ, mỗi khung ghi số giây. Trả (ds đường dẫn, nhịp giây).
    Lỗi gì cũng trả ([], 0) -> lượt chọn đoạn vẫn chạy như cũ."""
    g = nhip_bang(duration)
    font = _font_bang()
    if not g or not font:
        return [], 0.0
    try:
        os.makedirs(thu_muc, exist_ok=True)
        ff = str(getattr(_st(), "FFMPEG_PATH", "ffmpeg") or "ffmpeg")
        vf = (f"fps=1/{g:g},scale=240:-2,drawtext=fontfile='{font}':text='%{{eif\\:t\\:d}}s':"
              f"fontsize=22:fontcolor=yellow:box=1:boxcolor=black@0.7:x=4:y=4,"
              f"tile={BANG_COT}x{BANG_HANG}")
        rc, _o, err = _chay([ff, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                             "-threads", "2", "-i", str(prox), "-vf", vf, "-q:v", "4",
                             os.path.join(thu_muc, "bang_%02d.jpg")], 600, check,
                            thu_429=False, them_co=_BELOW_NORMAL)
        ds = sorted(str(p) for p in Path(thu_muc).glob("bang_*.jpg") if p.stat().st_size > 1000)
        if rc != 0 or not ds:
            ghi_log(f"dựng ảnh tổng hợp lỗi (mã {rc}): {err[-200:]}")
            return [], 0.0
        return ds, g
    except Exception as e:  # noqa: BLE001 - lỗi CanceledError vẫn phải nổi lên
        if type(e).__name__ == "CanceledError":
            raise
        ghi_log(f"dựng ảnh tổng hợp lỗi: {e}")
        return [], 0.0


def _tai_bang(cli: list, phien, ma: str, prox: str, thu_muc: str, thu_muc_xa: str,
              duration: float, check: Optional[Callable] = None,
              progress: Optional[Callable] = None) -> tuple:
    """Dựng + tải ảnh tổng hợp SONG SONG (tải lần lượt tốn +50 s/10 ảnh). Trả (số ảnh, nhịp
    giây); thiếu một ảnh là bỏ cả bộ -> (0, 0) = prompt + lượt chọn y như chưa có tính năng."""
    from concurrent.futures import ThreadPoolExecutor
    t0 = time.monotonic()
    ds, g = dung_bang(prox, thu_muc, duration, check)
    if not ds:
        return 0, 0.0
    if progress:
        progress(f"Muse: tải lên {len(ds)} ảnh tổng hợp...")

    def _mot(f):
        return _chay(_argv(cli, phien, "upload", f, f"{thu_muc_xa}/bang/{os.path.basename(f)}"),
                     600, check)
    with ThreadPoolExecutor(max_workers=4) as ex:
        kq = list(ex.map(_mot, ds))
    hong = [i for i, (rc, _o, _e) in enumerate(kq) if rc != 0]
    kb = sum(os.path.getsize(f) for f in ds) // 1024
    if hong:
        ghi_log(f"[{ma}] tải ảnh tổng hợp lỗi {len(hong)}/{len(ds)} -> gửi như cũ: "
                f"{_loc_bi_mat(kq[hong[0]][2][-200:])}")
        return 0, 0.0
    ghi_log(f"[{ma}] ảnh tổng hợp {len(ds)} ảnh · {kb} KB · {g:g} s/khung · "
            f"dựng + tải {time.monotonic() - t0:.1f}s")
    return len(ds), g


def _co_gpu() -> bool:
    """Máy có GPU NVIDIA (nvidia-smi chạy được). Nhớ kết quả cả tiến trình.
    `BQ_MUSE_GPU=0` tắt hẳn đường GPU."""
    if os.environ.get("BQ_MUSE_GPU", "").strip() == "0":
        return False
    if "co" not in _GPU:
        try:
            r = subprocess.run(["nvidia-smi", "-L"], capture_output=True, timeout=10,
                               stdin=subprocess.DEVNULL, creationflags=_CREATE_NO_WINDOW)
            _GPU["co"] = r.returncode == 0 and b"GPU" in (r.stdout or b"")
        except Exception:  # noqa: BLE001
            _GPU["co"] = False
    return bool(_GPU["co"])


def ghi_transcript(segs: list, dst: str) -> int:
    """Ghi transcript của app: mỗi dòng 'bd-kt | lời'. Trả số dòng."""
    n = 0
    with open(dst, "w", encoding="utf-8") as f:
        for s in segs or []:
            try:
                t = str(s.get("text", "")).replace("\n", " ").strip()
                f.write(f'{float(s["start"]):.1f}-{float(s["end"]):.1f} | {t}\n')
                n += 1
            except (KeyError, TypeError, ValueError):
                continue
    return n


# ───────────────────────── prompt ─────────────────────────
UNG_VIEN_DU = 3     # Muse đề xuất count + 3 ứng viên


def dung_prompt(ma: str, thu_muc_xa: str, ten_video: str, ten_loi: str,
                cfg: dict, lang_name: str, duration: float, khong_loi: bool = False,
                bang: tuple = (0, 0.0)) -> str:
    count = int(cfg.get("count", 0) or 0)
    mn = float(cfg.get("min_len", 60.0) or 0)
    mx = float(cfg.get("max_len", 0.0) or 0)
    # Đề xuất DƯ ứng viên: bước chấm của app (critic) có thể loại 1-2 cái; Muse chỉ
    # trả ĐÚNG `count` thì loại 1 là thiếu Part (đo 13/11/2026: đặt 3 ra 2). App vẫn
    # cắt cứng về đúng `count` ở `_llm_select_clips` (cổng 12).
    so = (f"{count + UNG_VIEN_DU} ứng viên KHÁC NHAU, không trùng đoạn nhau, xếp từ hay nhất "
          f"xuống (app sẽ giữ {count} cái tốt nhất)" if count > 0
          else "3-6 clip hay nhất")
    # ĐO 14/11/2026: video 494 s mà xin 6 ứng viên x 100-180 s KHÔNG TRÙNG -> Muse trả lời bằng CHỮ
    # ("không đủ cho 6 clip... cần tối thiểu 600 giây") thay vì JSON -> app đợi tới hết giờ. Đêm đó
    # MỌI video Muse "không trả lời" đều < 600 s (354-505 s), mọi video trả lời đều >= 637 s.
    # Video không đủ chỗ -> xin đúng số VỪA độ dài + dặn trả ÍT hơn bằng JSON. Đủ chỗ -> prompt y cũ.
    vua = int(duration // mn) if (count > 0 and mn > 0 and duration > 0) else 0
    if count > 0 and 0 < vua < count + UNG_VIEN_DU:
        n = max(1, vua)
        so = (f"tối đa {n} ứng viên KHÁC NHAU, không trùng đoạn nhau, xếp từ hay nhất xuống "
              f"(video ngắn nên không đủ chỗ cho nhiều hơn — được trả ÍT hơn {n}, nhưng LUÔN trả "
              "bằng khối JSON dưới đây, KHÔNG BAO GIỜ trả lời bằng chữ)")
    elif count > 0 and vua == 0 and mn > 0 and duration > 0:
        so = ("1 ứng viên (video ngắn hơn độ dài tối thiểu — chọn đoạn hay nhất có thể; LUÔN trả "
              "bằng khối JSON dưới đây, KHÔNG BAO GIỜ trả lời bằng chữ)")
    dai = (f"mỗi clip tổng dài {mn:.0f}-{mx:.0f} giây" if mn and mx else
           f"mỗi clip tổng dài ít nhất {mn:.0f} giây" if mn else "độ dài tự do")
    goi_y = []
    try:
        from app.modules.m1_highlight import _PURPOSE_HINT, _STYLE_HINT
        if _PURPOSE_HINT.get(cfg.get("purpose", "")):
            goi_y.append(_PURPOSE_HINT[cfg["purpose"]])
        if _STYLE_HINT.get(cfg.get("style", "")):
            goi_y.append(_STYLE_HINT[cfg["style"]])
    except Exception:  # noqa: BLE001
        pass
    p = (
        f"BQ_LENH_{ma}\n"
        "QUAN TRỌNG: KHÔNG cài thêm gói nào, KHÔNG truy cập bất kỳ trang web/Internet "
        "nào, KHÔNG xin quyền, KHÔNG hỏi lại. Chỉ dùng 2 file đã tải lên dưới đây.\n"
        f"Thư mục: {thu_muc_xa}/ (trong workspace của bạn)\n"
        f"- {ten_video}: bản xem nhanh của video (480p, ~2 khung/giây), dài {duration:.0f} giây.\n"
        + (f"- {ten_loi}: video KHÔNG có lời nói — XEM hình và NGHE nhạc/tiếng động để chọn; "
           "cắt ở chỗ chuyển cảnh.\n" if khong_loi else
           f"- {ten_loi}: lời thoại ĐÃ chép sẵn, mỗi dòng 'giây_bắt_đầu-giây_kết_thúc | lời'. "
           "KHÔNG chép lời lại — dùng file này.\n") +
        f"Việc: xem khung hình + đọc lời, chọn {so} viral cho TikTok/Shorts, {dai}. "
        "Mỗi clip là một câu chuyện trọn vẹn (dẫn dắt - cao trào - chốt), có thể ghép "
        "nhiều đoạn (tối đa 6) theo đúng thứ tự, cắt đúng ranh giới câu trong file lời. "
        "Bỏ intro chào kênh, kêu gọi đăng ký, quảng cáo, lời tạm biệt.\n"
        + ("".join("- " + g + "\n" for g in goi_y)) +
        "title = tiêu đề TIẾNG VIỆT CÓ DẤU; "
        f"title_pub = tiêu đề giật tít bằng {lang_name}; hook = 3-7 từ bằng {lang_name}; "
        "hook_time = [giây, giây] 2-4 giây nằm trong segments; score 0-100; "
        "segments = mảng [giây_bắt_đầu, giây_kết_thúc] (SỐ GIÂY của video gốc); "
        f"hashtags = 3-4 hashtag bằng {lang_name}, liền không dấu cách, sát nội dung.\n"
        "Trả lời DUY NHẤT một khối JSON, không chữ nào khác, dạng: "
        '{"job": "<MÃ VIỆC>", "clips": [{"title": "...", "title_pub": "...", "hook": "...", '
        '"hook_time": [a, b], "score": 85, "reason": "...", "segments": [[a, b], [c, d]], '
        '"hashtags": ["#...", "#..."]}]}\n'
        f"Trong đó <MÃ VIỆC> là: {ma}"
    )
    n_bang, giay_bang = bang or (0, 0.0)
    if n_bang:
        # Không có ảnh -> prompt GIỐNG TỪNG KÝ TỰ bản cũ (bất biến cổng 117).
        p = p.replace("Chỉ dùng 2 file đã tải lên dưới đây.", "Chỉ dùng các file đã tải lên dưới đây.")
        p = p.replace("Việc: xem khung hình + đọc lời", (
            f"- bang/: {n_bang} ảnh tổng hợp, mỗi ảnh {BANG_COT * BANG_HANG} khung "
            f"({BANG_COT} cột x {BANG_HANG} hàng), cứ {giay_bang:g} giây 1 khung, số giây ghi ở góc "
            "trên trái từng khung. Xem HẾT các ảnh này để biết hình của TOÀN video — không cần tự "
            "trích khung.\nViệc: xem khung hình + đọc lời"), 1)
    return p


# ───────────────────────── đọc trả lời ─────────────────────────
def _cac_chuoi(v, out: list) -> None:
    if isinstance(v, str):
        out.append(v)
    elif isinstance(v, dict):
        for x in v.values():
            _cac_chuoi(x, out)
    elif isinstance(v, list):
        for x in v:
            _cac_chuoi(x, out)


def tim_tra_loi(lich_su_json: str, ma: str) -> Optional[list]:
    """Tìm trong JSON lịch sử chuỗi có MÃ VIỆC, KHÔNG phải chính prompt (prompt
    mang dấu `BQ_LENH_<mã>`), bóc JSON -> list clip. Không thấy -> None."""
    try:
        data = json.loads(lich_su_json)
    except (ValueError, TypeError):
        return None
    from app.ai import llm
    chuoi: list = []
    _cac_chuoi(data, chuoi)
    for s in reversed(chuoi):              # mới nhất trước
        if ma not in s or f"BQ_LENH_{ma}" in s:
            continue
        try:
            obj = llm.boc_json(s, cho_vot=False)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(obj, dict) and str(obj.get("job", "")).strip() == ma \
                and isinstance(obj.get("clips"), list):
            rows = [r for r in obj["clips"] if isinstance(r, dict)]
            return rows
    return None


# ───────────────────────── chạy 1 việc ─────────────────────────
def _han_cho(duration: float) -> float:
    st = _st()
    he = float(getattr(st, "MUSE_TIMEOUT_HE_SO", 0.1) or 0.1)
    them = float(getattr(st, "MUSE_TIMEOUT_THEM", 300) or 300)
    tran = float(getattr(st, "MUSE_TIMEOUT_MAX", 3600) or 3600)
    return min(tran, max(120.0, he * max(0.0, duration) + them))


def _khoa_song_song():
    global _LOCK_SONG_SONG
    with _LOCK_INIT:
        if _LOCK_SONG_SONG is None:
            n = max(1, int(getattr(_st(), "MUSE_SONG_SONG", 100) or 100))
            _LOCK_SONG_SONG = threading.BoundedSemaphore(n)
    return _LOCK_SONG_SONG


def _khoa_viec(src: str, cfg: dict) -> tuple:
    """Cùng file (đường dẫn + cỡ + giờ sửa) + cùng cài đặt chọn Part = cùng việc."""
    return (os.path.abspath(src), os.path.getsize(src), os.path.getmtime(src),
            int(cfg.get("count", 0) or 0), float(cfg.get("min_len", 0) or 0),
            float(cfg.get("max_len", 0) or 0), cfg.get("purpose", ""), cfg.get("style", ""))


def chon_doan(src: str, segs: list, duration: float, cfg: dict, lang_name: str,
              video_id=None, check: Optional[Callable] = None,
              progress: Optional[Callable] = None) -> tuple:
    """Như `_chon_doan_mot`, nhưng tài khoản nào hỏng ĐĂNG NHẬP thì tự thử tài
    khoản kế (mỗi tài khoản tối đa 1 lần/việc). Lỗi KHÁC (quá giờ, JSON sai,
    lỗi video) không đổi tài khoản — đổi cũng ra y vậy, chỉ phí thời gian."""
    tranh: set = set()

    def _nho_hong(ly: str) -> None:
        # Vòng đợi-hết-lượt Groq (`_call_waiting_quota`) gọi lại cả bước chọn
        # đoạn; không nhớ thì mỗi vòng lại dựng + tải bản nhẹ lên Muse. Chỉ nhớ
        # khi đang BẬT tự chuyển Groq — tắt thì người dùng muốn thử Muse lại.
        if ly.startswith("Muse vừa hỏng") or not la_bat(getattr(_st(), "MUSE_LUI_GROQ", True)):
            return
        try:
            _CACHE_HONG[_khoa_viec(src, cfg)] = (time.monotonic(), str(ly)[:120])
        except OSError:
            pass

    while True:
        rows, ly, tk_loi = _chon_doan_mot(src, segs, duration, cfg, lang_name,
                                          video_id, check, progress, tranh)
        if rows or tk_loi is None:
            if not rows:
                _nho_hong(ly)
            return rows, ly
        tranh.add(str(tk_loi))
        con = [d for d in ds_phien(lenh_cli()) if str(d) not in tranh]
        if not con:
            _nho_hong(ly)
            return rows, ly
        ghi_log(f"video_id={video_id}: tài khoản {Path(tk_loi).name} lỗi đăng nhập — "
                f"chuyển sang {len(con)} tài khoản còn lại")


def _chon_doan_mot(src: str, segs: list, duration: float, cfg: dict, lang_name: str,
                   video_id=None, check: Optional[Callable] = None,
                   progress: Optional[Callable] = None, tranh=frozenset()) -> tuple:
    """Chạy 1 lượt Muse trên MỘT tài khoản. Trả (rows | None, lý do, tài khoản
    lỗi-đăng-nhập | None). rows là list dict CÙNG schema
    JSON chọn đoạn của Groq (đưa thẳng vào `_normalize_clip`). Chỉ CanceledError
    được nổi lên."""
    from app.queue.worker import CanceledError
    khoa = None
    _TK_LOI = [None]
    try:
        khoa = _khoa_viec(src, cfg)
        _kq = _CACHE_KQ.get(khoa)
        if _kq and time.monotonic() - _kq[0] < KQ_NHO_GIAY:
            return [dict(r) for r in _kq[1]], "dùng lại kết quả Muse đã có", _TK_LOI[0]
        _hong = _CACHE_HONG.get(khoa)
        if _hong and time.monotonic() - _hong[0] < HONG_NHO_GIAY:
            return None, "Muse vừa hỏng với video này: " + _hong[1], _TK_LOI[0]
    except OSError:
        return None, "không đọc được file video gốc", _TK_LOI[0]
    co = co_muse()
    if not co.get("co"):
        return None, co.get("ly_do") or "không có Muse", _TK_LOI[0]
    sem = _khoa_song_song()
    while not sem.acquire(timeout=1.0):
        if check is not None:
            check()
    # TỪ ĐÂY mọi lối ra (kể cả Huỷ lúc đang đợi chỗ, DB khoá trong progress) đều
    # phải trả chỗ song song + tải tài khoản -> tất cả nằm trong try/finally.
    # (Soát 13/11/2026: Huỷ lúc đợi chỗ làm rò chỗ song song VĨNH VIỄN.)
    ma = f"BQ{video_id or 0}_{uuid.uuid4().hex[:10]}"
    thu_muc_xa = f"workspace/bq/{ma}"
    tam = None
    da_tai_len = False
    cli: list = []
    giu_khoa = [False]
    phien = None
    dem_tai = [False]          # phien đã được +1 tải (phải -1 lúc ra)
    t0 = time.monotonic()
    try:
        tam = _data_dir() / "_muse_tam" / ma
        _don_tam_cu()
        cli = lenh_cli()
        _ds = [d for d in ds_phien(cli) if str(d) not in tranh]
        phien = chon_phien(_ds, tran_moi_tk())
        dem_tai[0] = phien is not None
        while phien is None and _ds:
            # mọi tài khoản đã đủ `MUSE_MOI_TK` việc -> đợi một chỗ trống (kiểm Huỷ)
            if progress:
                progress(f"Muse: mọi tài khoản đang đủ {tran_moi_tk()} video — đợi chỗ trống…")
            if check is not None:
                check()
            time.sleep(1.0)
            phien = chon_phien(_ds, tran_moi_tk())
            dem_tai[0] = phien is not None
        if phien is None and not tranh and co.get("phien"):
            phien = Path(co["phien"])
            with _TK_LOCK:               # dự phòng cũng phải ĐẾM, không thì -1 lúc ra
                _TK_TAI[str(phien)] = _TK_TAI.get(str(phien), 0) + 1
            dem_tai[0] = True
        if phien is None:
            return None, "hết tài khoản Muse dùng được", None
        t0 = time.monotonic()
        ghi_log(f"[{ma}] BẮT ĐẦU video_id={video_id} dài={duration:.0f}s "
                f"tài khoản={phien.name if phien else '?'} "
                f"cfg=count:{cfg.get('count')} min:{cfg.get('min_len')} max:{cfg.get('max_len')}")
        tam.mkdir(parents=True, exist_ok=True)
        if progress:
            progress("Muse: dựng bản nhẹ để tải lên...")
        prox = tam / "video.mp4"
        # KHÔNG xếp hàng ở cửa đọc ổ D (đã thử 14/11 sáng rồi GỠ): dựng bản nhẹ bị GIẢI MÃ chặn chứ
        # không bị ĐĨA chặn — đo lúc 2 bản nhẹ giữ 2 chỗ của cửa, ổ D chỉ đọc 3,4 MB/s mà 2 chỗ bị giữ
        # 9 phút (video 64 phút) -> 9 việc chép lời (mỗi việc vài giây đọc đĩa) đứng đợi 11 phút.
        # NHƯNG phải giới hạn số bản nhẹ dựng CÙNG LÚC (mọi tiến trình phân tích cộng lại): đo 14/11
        # 12:30, 14 bản cùng lúc -> bộ giải mã NVDEC 99%, mỗi bản 262-460 s, và lượt XUẤT Part cũng
        # giải mã bằng NVDEC. Ít lượt cùng lúc thì từng video xong sớm, sang bước cắt sớm.
        from app.core.cua_doc_dia import giu_cho_ten as _giu_ten
        with _giu_ten("muse_ban_nhe", _so_ban_nhe(),
                      bao=(lambda m: progress("Muse: " + m)) if progress else None,
                      kiem_huy=check, nhan="đang đợi lượt dựng bản nhẹ"):
            # tới lượt thì PHẢI đổi chữ: không thì thanh tiến trình đứng ở "đang đợi lượt … 396 giây"
            # suốt lúc đang dựng thật (đo 14/11: video 75 phút dựng 11 phút, trông như treo)
            if progress:
                progress(f"Muse: đã tới lượt — đang dựng bản nhẹ (video {duration/60:.0f} phút)...")
            ok, ly = dung_proxy(src, str(prox), check)
        if not ok:
            ghi_log(f"[{ma}] {ly}")
            return None, ly, _TK_LOI[0]
        loi = tam / "loi_thoai.txt"
        n_dong = ghi_transcript(segs, str(loi))
        if not n_dong:            # video KHÔNG LỜI: Muse chọn theo hình + tiếng
            loi.write_text("(video này KHÔNG có lời nói — chọn đoạn theo HÌNH ẢNH và "
                           "ÂM THANH: nhạc, tiếng động, hành động)\n", encoding="utf-8")
        mb = prox.stat().st_size / 1e6
        ghi_log(f"[{ma}] bản nhẹ {mb:.2f} MB ({time.monotonic()-t0:.1f}s) · lời {n_dong} dòng")
        for f in (prox, loi):
            if progress:
                progress(f"Muse: tải lên {f.name} ({f.stat().st_size/1e6:.1f} MB)...")
            t1 = time.monotonic()
            rc, out, err = _chay(_argv(cli, phien, "upload", str(f), f"{thu_muc_xa}/{f.name}"),
                                 1800, check)
            if rc != 0:
                if _danh_dau_tk(phien, err):
                    _TK_LOI[0] = phien
                ly = f"tải lên {f.name} lỗi (mã {rc}): {_loc_bi_mat(err[-300:])}"
                ghi_log(f"[{ma}] {ly}")
                return None, ly, _TK_LOI[0]
            da_tai_len = True
            ghi_log(f"[{ma}] tải lên {f.name} {f.stat().st_size/1e6:.2f} MB "
                    f"trong {time.monotonic()-t1:.1f}s -> {out.strip()[:200]}")
        bang = _tai_bang(cli, phien, ma, str(prox), str(tam / "bang"), thu_muc_xa, duration,
                         check, progress)
        prompt = dung_prompt(ma, thu_muc_xa, prox.name, loi.name, cfg, lang_name, duration,
                             khong_loi=not n_dong, bang=bang)
        ghi_log(f"[{ma}] PROMPT ({len(prompt)} ký tự):\n{prompt}")
        if progress:
            progress("Muse: gửi yêu cầu chọn đoạn...")
        # Không có --session-id thì CLI dồn MỌI việc vào cuộc chat CHÍNH (đo
        # 13/11/2026: 3 việc khác nhau chung chat_id) -> chạy song song là lẫn
        # trả lời. Gửi một mã MỚI thì máy chủ tự mở cuộc chat RIÊNG (đã đo:
        # 7 -> 8 phiên, history của mã đó chỉ chứa đúng việc này).
        sid = str(uuid.uuid4())
        py = python_muse(cli)
        if py and phien is not None:
            (tam / "gui.py").write_text(_MA_GUI, encoding="utf-8")
            (tam / "prompt.txt").write_text(prompt, encoding="utf-8")
            rc, out, err = _chay([py, "-I", str(tam / "gui.py"), str(phien), sid,
                                  str(tam / "prompt.txt")], 300, check, thu_429=True,
                                 chi_tu_choi=True)
            if rc != 0 or "BQ_DA_GUI" not in out:
                if _danh_dau_tk(phien, err):
                    _TK_LOI[0] = phien
                ly = f"gửi yêu cầu lỗi (mã {rc}): {_loc_bi_mat((err or out)[-300:])}"
                ghi_log(f"[{ma}] {ly}")
                return None, ly, _TK_LOI[0]
        else:
            # Không có python của venv MuseAI -> chỉ còn lệnh `generate`, mà nó đọc
            # lịch sử TRƯỚC khi gửi nên mã phiên MỚI ra 404. Dùng phiên đặt sẵn
            # (MUSE_SESSION_ID) hoặc phiên CHÍNH, và giữ khoá cho tới khi đọc xong
            # trả lời để 2 việc không chen nhau trong cùng một cuộc chat.
            sid = str(getattr(_st(), "MUSE_SESSION_ID", "") or "").strip()
            while not _KHOA_CHUNG.acquire(timeout=1.0):
                if check is not None:
                    check()
            giu_khoa[0] = True
            tham = ["generate", "--prompt", prompt, "--no-download", "--min-videos", "1",
                    "--timeout", "15"] + (["--session-id", sid] if sid else [])
            rc, out, err = _chay(_argv(cli, phien, *tham), 300, check, thu_429=False)
            m = _RE_DA_GUI.search(err + "\n" + out)
            m2 = _RE_SESSION.search(out)
            if m:
                sid = sid or (m.group(1) or "")
            elif rc == 0 and m2:
                sid = sid or m2.group(1)
            if not (m or (rc == 0 and m2)):
                if _danh_dau_tk(phien, err):
                    _TK_LOI[0] = phien
                ly = f"gửi yêu cầu lỗi (mã {rc}): {_loc_bi_mat((err or out)[-300:])}"
                ghi_log(f"[{ma}] {ly}")
                return None, ly, _TK_LOI[0]
        # mã phiên vào nhật ký: lượt Muse không trả lời thì mới đọc lại được Muse đã nói gì
        ghi_log(f"[{ma}] ĐÃ GỬI · phiên={sid or 'không rõ'} · tài khoản={phien.name if phien else '?'}")
        han = _han_cho(duration)
        nhip = max(2.0, float(getattr(_st(), "MUSE_POLL_GIAY", 20) or 20))
        t_gui = time.monotonic()
        lan = 0
        while time.monotonic() - t_gui < han:
            if progress:
                progress(f"Muse đang xem & chọn đoạn ({int(time.monotonic()-t_gui)}s / "
                         f"tối đa {int(han)}s)...")
            tham_h = ["history", "--limit", "40"] + (["--session-id", sid] if sid else [])
            rc, out, err = _chay(_argv(cli, phien, *tham_h), 120, check)
            lan += 1
            if rc == 0:
                rows = tim_tra_loi(out, ma)
                if rows is not None:
                    ghi_log(f"[{ma}] NHẬN trả lời sau {time.monotonic()-t_gui:.0f}s "
                            f"({lan} lượt đọc) · {len(rows)} clip")
                    if not rows:
                        return None, "Muse trả 0 clip", _TK_LOI[0]
                    _CACHE_KQ[khoa] = (time.monotonic(), [dict(r) for r in rows])
                    return rows, "", _TK_LOI[0]
            else:
                ghi_log(f"[{ma}] history lỗi (mã {rc}): {_loc_bi_mat(err[-200:])}")
                if _danh_dau_tk(phien, err):
                    _TK_LOI[0] = phien
                    return None, "tài khoản Muse hết đăng nhập giữa chừng", _TK_LOI[0]
            dung = time.monotonic() + nhip
            while time.monotonic() < dung:
                if check is not None:
                    check()
                time.sleep(0.5)
        ly = f"quá giờ đợi Muse ({han:.0f}s, {lan} lượt đọc)"
        ghi_log(f"[{ma}] {ly}")
        return None, ly, _TK_LOI[0]
    except CanceledError:
        ghi_log(f"[{ma}] HUỶ bởi người dùng")
        raise
    except Exception as e:  # noqa: BLE001
        ghi_log(f"[{ma}] lỗi: {e}")
        return None, f"lỗi Muse: {e}", _TK_LOI[0]
    finally:
        try:
            if da_tai_len:
                if co.get("ho_tro_xoa"):
                    rc, _o, err = _chay(_argv(cli, phien, "delete", thu_muc_xa), 120)
                    ghi_log(f"[{ma}] xoá thư mục từ xa {thu_muc_xa}: mã {rc}")
                else:
                    ghi_log(f"[{ma}] CLI không có lệnh delete — để lại {thu_muc_xa} trên Muse")
        except BaseException:  # noqa: BLE001
            pass
        try:
            if tam is not None:
                from app.core.xoa_an_toan import don_thu_muc
                don_thu_muc(tam, trong=_data_dir() / "_muse_tam", ten_bat_dau="BQ",
                            ghi_log=ghi_log)
        except Exception:  # noqa: BLE001
            pass
        if dem_tai[0]:
            tra_phien(phien)
        if giu_khoa[0]:
            _KHOA_CHUNG.release()
        sem.release()


# ───────────────────────── quản lý tài khoản (hộp Cài đặt AI) ─────────────────────────
_RE_TEN_TK = re.compile(r"^[A-Za-z0-9_-]{1,24}$")


def goc_tai_khoan() -> Optional[Path]:
    """Thư mục chứa các `.muse-state*` (cạnh tài khoản chính, thường D:\\MuseAI-API)."""
    cli = lenh_cli()
    mot = thu_muc_phien(cli)
    if mot is not None:
        return mot.parent
    try:
        if cli and cli[0].lower().endswith("muse-ai.exe"):
            return Path(cli[0]).resolve().parents[2]     # <repo>/.venv/Scripts/muse-ai.exe
    except (OSError, IndexError):
        pass
    return None


def ten_tk(d) -> str:
    n = Path(d).name
    return "chính" if n == ".muse-state" else n.replace(".muse-state-", "", 1)


def ds_tai_khoan() -> list:
    """[{ten, thu_muc, trang_thai, dang_chay}] cho bảng trong Cài đặt AI. Không gọi mạng."""
    out = []
    now = time.monotonic()
    for d in ds_phien(lenh_cli()):
        hong = _TK_HONG.get(str(d), 0) > now
        out.append({"ten": ten_tk(d), "thu_muc": str(d),
                    "trang_thai": ("tạm bỏ qua (lỗi đăng nhập)" if hong else "đã đăng nhập"),
                    "dang_chay": int(_TK_TAI.get(str(d), 0))})
    return out


def kiem_tk(thu_muc: str) -> tuple:
    """Ping MỘT tài khoản. (True, "dùng được") / (False, lý do). Đạt thì gỡ dấu 'tạm bỏ qua'."""
    cli = lenh_cli()
    if not cli:
        return False, "không tìm thấy muse-ai"
    rc, out, err = _chay(_argv(cli, Path(thu_muc), "ping"), 90)
    if rc == 0 and re.search(r"HTTP 2\d\d", out):
        with _TK_LOCK:
            _TK_HONG.pop(str(Path(thu_muc)), None)
        _CACHE_CO.clear()
        return True, "dùng được"
    if _danh_dau_tk(Path(thu_muc), err):
        return False, "hết đăng nhập — bấm Đăng nhập lại"
    return False, f"không kết nối được (mã {rc}): {_loc_bi_mat(err[-160:]) or 'mất mạng?'}"


def thu_muc_tk_moi(ten: str) -> tuple:
    """(Path, "") hoặc (None, lý do). Tên chỉ chữ/số/-/_ (thành tên thư mục)."""
    ten = (ten or "").strip()
    if not _RE_TEN_TK.match(ten):
        return None, "Tên chỉ gồm chữ không dấu, số, - hoặc _ (tối đa 24 ký tự)."
    goc = goc_tai_khoan()
    if goc is None:
        return None, "Chưa cài MuseAI-API (chạy CAI_MUSE.bat trước)."
    if ten.lower() == "chinh":
        return goc / ".muse-state", ""
    return goc / f".muse-state-{ten}", ""


def doi_ten_tk(thu_muc: str, ten_moi: str) -> tuple:
    d = Path(thu_muc)
    if d.name == ".muse-state":
        return False, "Không đổi tên tài khoản chính (app dùng nó để tìm các tài khoản khác)."
    if _TK_TAI.get(str(d), 0):
        return False, "Tài khoản đang chạy video — đợi xong rồi đổi tên."
    moi, ly = thu_muc_tk_moi(ten_moi)
    if moi is None:
        return False, ly
    if moi.exists():
        return False, "Đã có tài khoản tên đó."
    try:
        d.rename(moi)
    except OSError as e:
        return False, f"không đổi được: {e}"
    with _TK_LOCK:
        _TK_HONG.pop(str(d), None)
    _CACHE_CO.clear()
    return True, ""


def go_tk(thu_muc: str) -> tuple:
    """Gỡ tài khoản khỏi app: CẤT thư mục vào `_tk_da_go/` (không xoá — muốn dùng
    lại thì chép về). Tài khoản đang chạy video -> từ chối."""
    d = Path(thu_muc)
    if _TK_TAI.get(str(d), 0):
        return False, "Tài khoản đang chạy video — đợi xong rồi gỡ."
    if not (d / "cookies.json").is_file():
        return False, "Không thấy tài khoản này."
    kho = d.parent / "_tk_da_go"
    try:
        kho.mkdir(exist_ok=True)
        dich = kho / f"{d.name}_{time.strftime('%Y%m%d_%H%M%S')}"
        d.rename(dich)
    except OSError as e:
        return False, f"không gỡ được: {e}"
    with _TK_LOCK:
        _TK_HONG.pop(str(d), None)
    _CACHE_CO.clear()
    ghi_log(f"gỡ tài khoản {ten_tk(d)} -> {dich}")
    return True, str(dich)


class DangNhap:
    """Đăng nhập một tài khoản từ trong app: chạy `muse-ai login` ở tiến trình rời,
    đợi nó gửi mã OTP về email rồi nhận mã NGƯỜI DÙNG gõ (app không đoán, không
    lưu mã). Chạy ở luồng nền; giao diện đọc `.trang_thai` / `.cho_ma` / `.xong`."""

    LOI_NHAC = b"Muse OTP: "

    def __init__(self, thu_muc, email: str):
        self.thu_muc = Path(thu_muc)
        self.email = (email or "").strip()
        self.trang_thai = "Đang gửi mã OTP về email…"
        self.cho_ma = False
        self.xong = False
        self.ok = False
        self._p = None
        self._buf = bytearray()

    def bat_dau(self) -> None:
        threading.Thread(target=self._chay, daemon=True).start()

    def _chay(self) -> None:
        try:
            cli = lenh_cli()
            if not cli:
                raise RuntimeError("không tìm thấy muse-ai (chạy CAI_MUSE.bat trước)")
            if "@" not in self.email:
                raise RuntimeError("email không hợp lệ")
            self.thu_muc.mkdir(parents=True, exist_ok=True)
            env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1",
                       PYTHONUNBUFFERED="1")
            self._p = subprocess.Popen(
                _argv(cli, self.thu_muc, "login", "--email", self.email),
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                env=env, creationflags=_CREATE_NO_WINDOW)
            han = time.monotonic() + 120
            _p = self._p

            def _canh():          # read(1) chặn: hết 120 s mà chưa xin mã -> giết
                if _p.poll() is None and not self.cho_ma:
                    _giet_cay(_p)
            _t = threading.Timer(120, _canh)
            _t.daemon = True
            _t.start()
            while time.monotonic() < han:
                ch = self._p.stdout.read(1)
                if not ch:
                    break
                self._buf += ch
                if self._buf.endswith(self.LOI_NHAC):
                    self.cho_ma = True
                    self.trang_thai = "Đã gửi mã về email. Gõ mã OTP vào ô bên dưới."
                    return               # đợi nhap_ma()
            raise RuntimeError(self._duoi() or "không nhận được yêu cầu nhập mã")
        except Exception as e:  # noqa: BLE001
            if self._p is not None:
                _giet_cay(self._p)
            self._ket(False, f"Đăng nhập lỗi: {e}")

    def nhap_ma(self, ma: str) -> None:
        threading.Thread(target=self._gui_ma, args=(ma,), daemon=True).start()

    def _gui_ma(self, ma: str) -> None:
        try:
            self.cho_ma = False
            self.trang_thai = "Đang xác nhận mã…"
            self._p.stdin.write(((ma or "").strip() + "\n").encode())
            self._p.stdin.flush()
            self._p.stdin.close()
            self._buf += self._p.stdout.read() or b""
            try:
                self._p.wait(60)
            except subprocess.TimeoutExpired:
                _giet_cay(self._p)
            if self._p.returncode == 0 and (self.thu_muc / "cookies.json").is_file():
                ok, ly = kiem_tk(str(self.thu_muc))
                self._ket(ok, "Đăng nhập xong — tài khoản dùng được." if ok
                          else "Đã lưu đăng nhập nhưng kiểm tra chưa đạt: " + ly)
            else:
                self._ket(False, "Mã sai hoặc hết hạn: " + self._duoi())
        except Exception as e:  # noqa: BLE001
            self._ket(False, f"Đăng nhập lỗi: {e}")

    def huy(self) -> None:
        try:
            if self._p is not None and self._p.poll() is None:
                self._p.kill()
        except Exception:  # noqa: BLE001
            pass
        if not self.xong:
            self._ket(False, "Đã huỷ.")

    def _duoi(self) -> str:
        t = bytes(self._buf).decode("utf-8", "replace")
        dong = [x for x in t.splitlines() if x.strip()]
        return _loc_bi_mat(dong[-1] if dong else "")[:200]

    def _ket(self, ok: bool, msg: str) -> None:
        self.ok, self.trang_thai, self.xong = ok, msg, True
        _CACHE_CO.clear()
        ghi_log(f"đăng nhập tài khoản {ten_tk(self.thu_muc)}: "
                f"{'đạt' if ok else 'chưa đạt'} — {msg}")
