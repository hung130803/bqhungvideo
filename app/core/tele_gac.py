"""BOT GÁC CỔNG — điều khiển được từ điện thoại cả khi APP ĐANG TẮT hoặc đang
đứng ở màn ĐĂNG NHẬP.

Vì sao cần: bot chính (`tele_bot`) sống TRONG app và chỉ bật sau khi đăng nhập.
App tắt / đứng ở màn đăng nhập = điện thoại gõ gì cũng không ai nghe.

Cách chạy: một TIẾN TRÌNH NỀN riêng (`BQHungVideo.exe --self-check --gac`,
chạy nguồn: `python main.py --self-check --gac`), không cửa sổ, không Qt.
App tự bật nó khi mở; Windows tự bật nó khi đăng nhập máy (lối tắt Startup).

LUẬT KHÔNG GIÀNH NHAU: Telegram chỉ cho MỘT nơi gọi getUpdates mỗi lúc (nơi thứ
hai ăn 409). Bot chính ghi nhịp sống vào `DATA_DIR/tele_bot_song` mỗi vòng;
còn nhịp (dưới SONG_GIAY) thì gác cổng KHÔNG nghe gì, chỉ ngủ. Gác cổng nghe
bằng long-poll NGẮN (POLL_GIAY) để nhường chỗ nhanh khi bot chính lên.

Lệnh (chỉ chat có trong TELEGRAM_CHAT_IDS):
    /moapp    — app tắt: mở app (app tự đăng nhập bằng mật khẩu đã ghi nhớ);
                app đang ở màn đăng nhập: bấm Đăng nhập hộ.
    /dongapp  — app đang ở màn đăng nhập: đóng nó (cờ); không đóng được trong
                CHO_DONG_GIAY thì hỏi "Tắt cưỡng bức". App ĐÃ đăng nhập thì bot
                chính lo việc đóng (hỏi xác nhận, nói rõ số việc đang chạy).
    /trangthai — app đang tắt / chờ đăng nhập / đang chạy.
Không xoá, không sửa dữ liệu: chỉ mở/đóng app và gửi cờ.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import socket
import time
from pathlib import Path

POLL_GIAY = 6          # long-poll ngắn: bot chính lên thì nhường trong <= 6s
SONG_GIAY = 75         # nhịp sống bot chính cũ hơn số này = bot chính đã tắt
CHO_LEN_GIAY = 150     # sau /moapp chờ bot chính lên tối đa bấy nhiêu rồi báo
CHO_DONG_GIAY = 20     # sau /dongapp chờ app thoát tối đa bấy nhiêu rồi báo
CO_DONG_HAN_GIAY = 60  # cờ đóng app cũ hơn số này = bỏ (không đóng nhầm lần sau)
MANH_HAN_GIAY = 120    # nút "Tắt cưỡng bức" chỉ có hiệu lực bấy nhiêu giây
#: app đứng ở màn ĐĂNG NHẬP quá chừng này giây (khi đang bật Tự chạy dây
#: chuyền) -> báo đỏ 1 lần (#5: phiên Supabase hết hạn = mất cả ngày).
KET_DANG_NHAP_GIAY = 300

_PHIM = {"inline_keyboard": [[{"text": "🔓 Mở app + đăng nhập", "callback_data": "/moapp"},
                              {"text": "Trạng thái", "callback_data": "/trangthai"}],
                             [{"text": "⛔ Đóng app", "callback_data": "/dongapp"}]]}


def _data_dir() -> Path:
    from config import DATA_DIR
    return Path(DATA_DIR)


def file_song() -> Path:
    return _data_dir() / "tele_bot_song"


def file_co_dang_nhap() -> Path:
    return _data_dir() / "dang_nhap_ngay.flag"


def file_co_dong_app() -> Path:
    return _data_dir() / "dong_app_ngay.flag"


def co_dong_app_moi(now: float | None = None) -> bool:
    """Màn đăng nhập gọi: có cờ ĐÓNG APP còn mới không. Đọc xong XOÁ cờ (dù mới
    hay cũ) — cờ cũ sót lại không được đóng app ở lần mở sau."""
    f = file_co_dong_app()
    try:
        ts = float(f.read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        if not f.exists():
            return False
        ts = 0.0
    try:
        f.unlink()
    except OSError:
        pass
    return 0 <= (now or time.time()) - ts <= CO_DONG_HAN_GIAY


def file_khoa() -> Path:
    return _data_dir() / "tele_gac.lock"


def bot_chinh_song(now: float | None = None) -> bool:
    try:
        return (now or time.time()) - file_song().stat().st_mtime < SONG_GIAY
    except OSError:
        return False


def app_pid() -> int:
    """PID của app đang mở (đọc khoá 1-app-1-lúc QLockFile), 0 = app tắt."""
    try:
        dong = (_data_dir() / "app.lock").read_text(encoding="utf-8",
                                                     errors="ignore").split()
        pid = int(dong[0]) if dong else 0
    except (OSError, ValueError):
        return 0
    if pid <= 0 or pid == os.getpid():
        return 0
    try:
        import psutil
        return pid if psutil.pid_exists(pid) else 0
    except Exception:  # noqa: BLE001
        return pid


def lenh_mo_app() -> list[str]:
    """Lệnh mở APP (không phải gác cổng)."""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    goc = Path(__file__).resolve().parents[2]
    py = Path(sys.executable)
    pyw = py.with_name("pythonw.exe")
    return [str(pyw if pyw.exists() else py), str(goc / "main.py")]


def lenh_gac() -> list[str]:
    return lenh_mo_app() + ["--self-check", "--gac"]


def _chay_tach(cmd: list[str]) -> None:
    co = 0
    for ten in ("DETACHED_PROCESS", "CREATE_NEW_PROCESS_GROUP", "CREATE_NO_WINDOW"):
        co |= getattr(subprocess, ten, 0)
    subprocess.Popen(cmd, creationflags=co, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL,
                     cwd=str(Path(cmd[-1]).parent) if cmd[-1].endswith(".py") else None)


# ---------------------------------------------------------------- khoá --
_KHOA_FH = None


def giu_khoa() -> bool:
    """1 gác cổng / máy. Giữ handle mở suốt đời tiến trình (msvcrt lock)."""
    global _KHOA_FH
    try:
        import msvcrt
        f = file_khoa()
        fh = open(f, "a+")
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        _KHOA_FH = fh
        return True
    except Exception:  # noqa: BLE001
        return False


def dang_chay() -> bool:
    """Có gác cổng nào đang giữ khoá không (thử khoá rồi nhả ngay)."""
    if _KHOA_FH is not None:
        return True
    try:
        import msvcrt
        with open(file_khoa(), "a+") as fh:
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        return False
    except OSError:
        return True
    except Exception:  # noqa: BLE001
        return False


def bat_neu_chua(log=None) -> bool:
    """App gọi lúc mở: chưa có gác cổng thì bật 1 cái (tiến trình tách rời,
    sống tiếp khi app tắt). Không có token / đang test -> không làm gì."""
    try:
        if os.environ.get("BQ_TAT_BOT") or os.environ.get("BQ_QSETTINGS_INI") \
                or os.environ.get("BQ_DATA_DIR"):
            return False
        from app.core.tele_bot import _cfg
        tok, _ = _cfg()
        if not tok or dang_chay():
            return False
        _chay_tach(lenh_gac())
        if log:
            log("bật bot gác cổng (tiến trình nền)")
        return True
    except Exception as e:  # noqa: BLE001
        if log:
            log(f"không bật được gác cổng: {e!r}")
        return False


# ----------------------------------------------------------------- gác --
class Gac:
    def __init__(self, token: str, cho_phep: set[int], goi=None, mo_app=None):
        from app.core.tele_bot import BotQuanLy
        # mượn phần MẠNG của bot chính (IPv4 riêng luồng, giãn gửi, giấu token
        # khỏi log) — không dùng phần dây chuyền nào.
        self._bot = BotQuanLy(token, cho_phep, None)
        self.cho_phep = set(cho_phep)
        self._goi = goi or self._bot._goi
        self._mo_app = mo_app or (lambda: _chay_tach(lenh_mo_app()))
        self._offset = 0
        self._dang_cho = False
        self._ket_tu = None
        self._da_bao_ket = False

    def kiem_ket_dang_nhap(self, now: float | None = None, pid: int | None = None,
                           song: bool | None = None, tu_chay: bool | None = None):
        """#5: app mở (có pid) mà bot chính không sống = đứng ở màn đăng nhập.
        Quá KET_DANG_NHAP_GIAY -> báo đỏ ĐÚNG 1 lần cho tới khi trạng thái đổi.
        Chỉ khi đang bật Tự chạy (tắt = hành vi như cũ). Trả lời đã gửi/None."""
        now = time.time() if now is None else now
        if tu_chay is None:
            try:
                from app.ui.appsettings import app_settings
                tu_chay = bool(app_settings().value("pipe_auto_bat", False, type=bool))
            except Exception:  # noqa: BLE001
                tu_chay = False
        pid = app_pid() if pid is None else pid
        song = bot_chinh_song(now) if song is None else song
        if not (tu_chay and pid and not song):
            self._ket_tu, self._da_bao_ket = None, False
            return None
        if self._ket_tu is None:
            self._ket_tu = now
            return None
        if self._da_bao_ket or now - self._ket_tu < KET_DANG_NHAP_GIAY:
            return None
        self._da_bao_ket = True
        msg = (f"🔴 <b>App trên máy {socket.gethostname()} kẹt ở MÀN ĐĂNG NHẬP "
               f"{int((now - self._ket_tu) // 60)} phút</b> — dây chuyền tự chạy KHÔNG "
               "chạy. Bấm /moapp để đăng nhập hộ (phiên đăng nhập có thể đã hết "
               "hạn: phải nhập lại mật khẩu trên máy).")
        for cid in self.cho_phep:
            self.gui(cid, msg, phim=True)
        _log("báo kẹt màn đăng nhập")
        return msg

    def gui(self, cid: int, text: str, phim=False) -> None:
        data = {"chat_id": cid, "text": text, "parse_mode": "HTML",
                "disable_web_page_preview": True}
        if phim:
            data["reply_markup"] = _PHIM if phim is True else phim
        try:
            self._goi("sendMessage", data)
        except Exception as e:  # noqa: BLE001
            _log(f"gửi lỗi: {str(e)[:120]}")

    def trang_thai(self) -> str:
        if bot_chinh_song():
            return "🟢 App ĐANG CHẠY và đã đăng nhập — bot chính đang trả lời."
        if app_pid():
            return ("🟡 App đang mở nhưng CHƯA ĐĂNG NHẬP (đứng ở màn đăng nhập).\n"
                    "Bấm /moapp để đăng nhập hộ.")
        return "🔴 App đang TẮT. Bấm /moapp để mở app (app tự đăng nhập)."

    def mo_app(self, cid: int) -> None:
        if bot_chinh_song():
            self.gui(cid, "🟢 App đã chạy + đăng nhập rồi. Gõ /tiendo để xem.")
            return
        if app_pid():
            try:
                file_co_dang_nhap().write_text(str(time.time()), encoding="utf-8")
            except OSError as e:
                self.gui(cid, f"⚠ Không gửi được lệnh đăng nhập: {e}")
                return
            self.gui(cid, "🔑 App đang ở màn đăng nhập — đã bấm Đăng nhập hộ. "
                          "Chờ bot chính báo 🟢 (khoảng 10-30 giây).")
            _log(f"chat {cid}: /moapp -> gửi cờ đăng nhập")
        else:
            try:
                self._mo_app()
            except Exception as e:  # noqa: BLE001
                self.gui(cid, f"⚠ Không mở được app: {e}")
                _log(f"mở app lỗi: {e!r}")
                return
            self.gui(cid, "🚀 Đang MỞ app… app sẽ tự đăng nhập bằng mật khẩu đã "
                          "ghi nhớ. Khi xong bot chính báo 🟢 (khoảng 30-90 giây).")
            _log(f"chat {cid}: /moapp -> mở app")
        self._cho_ket_qua(cid)

    def dong_app(self, cid: int) -> None:
        """App ở màn ĐĂNG NHẬP (bot chính chưa lên): gửi cờ -> màn đăng nhập tự
        đóng. App đã đăng nhập thì bot CHÍNH lo (có hỏi xác nhận + số việc)."""
        if bot_chinh_song():
            self.gui(cid, "App đang chạy — bot chính sẽ hỏi xác nhận. Bấm ⛔ Đóng app "
                          "lại sau vài giây.")
            return
        pid = app_pid()
        if not pid:
            self.gui(cid, "🔴 App đang TẮT sẵn rồi.", phim=True)
            return
        try:
            file_co_dong_app().write_text(str(time.time()), encoding="utf-8")
        except OSError as e:
            self.gui(cid, f"⚠ Không gửi được lệnh đóng: {e}")
            return
        _log(f"chat {cid}: /dongapp -> gửi cờ đóng (pid {pid})")
        self.gui(cid, "⛔ App đang ở màn đăng nhập — đã gửi lệnh ĐÓNG. Chờ vài giây…")

        def cho():
            han = time.time() + CHO_DONG_GIAY
            while time.time() < han:
                if not app_pid():
                    self.gui(cid, "✅ Đã ĐÓNG app. Bấm 🔓 Mở app để mở lại.", phim=True)
                    _log("app đã đóng theo lệnh")
                    return
                time.sleep(1)
            try:
                file_co_dong_app().unlink()
            except OSError:
                pass
            self.gui(cid, f"⚠ Sau {CHO_DONG_GIAY} giây app vẫn chưa đóng (có thể đang "
                          "treo hoặc đang mở hộp thoại). Muốn TẮT CƯỠNG BỨC thì bấm "
                          "nút dưới — việc đang dở sẽ chạy lại khi mở app.",
                     phim={"inline_keyboard": [[
                         {"text": "Tắt cưỡng bức",
                          "callback_data": f"/dongappmanh {int(time.time())} {pid}"},
                         {"text": "Thôi", "callback_data": "/trangthai"}]]})
            _log("app không đóng theo cờ -> hỏi tắt cưỡng bức")
        threading.Thread(target=cho, daemon=True).start()

    def dong_manh(self, cid: int, text: str) -> None:
        """Tắt cưỡng bức app (cả tiến trình con ffmpeg). Chỉ khi: nút còn mới,
        ĐÚNG pid đã hỏi, và bot chính KHÔNG sống (sống thì phải đóng êm)."""
        phan = text.split()
        try:
            ts, pid = int(phan[1]), int(phan[2])
        except (IndexError, ValueError):
            ts, pid = 0, 0
        if not ts or time.time() - ts > MANH_HAN_GIAY:
            self.gui(cid, "Nút đã CŨ — không tắt. Bấm ⛔ Đóng app lại.", phim=True)
            return
        if bot_chinh_song():
            self.gui(cid, "App đã hồi lại (bot chính đang chạy) — không tắt cưỡng bức. "
                          "Bấm ⛔ Đóng app để đóng êm.")
            return
        if not pid or app_pid() != pid:
            self.gui(cid, "App đã tắt hoặc đã là phiên khác — không tắt gì.", phim=True)
            return
        try:
            import psutil
            p = psutil.Process(pid)
            con = p.children(recursive=True)
            for c in con:
                try:
                    c.kill()
                except psutil.Error:
                    pass
            p.kill()
            p.wait(10)
        except Exception as e:  # noqa: BLE001
            self.gui(cid, f"⚠ Không tắt được: {e}")
            _log(f"tắt cưỡng bức lỗi: {e!r}")
            return
        _log(f"chat {cid}: tắt cưỡng bức app pid {pid} (+{len(con)} tiến trình con)")
        self.gui(cid, "✅ Đã TẮT CƯỠNG BỨC app. Bấm 🔓 Mở app để mở lại.", phim=True)

    def _cho_ket_qua(self, cid: int) -> None:
        if self._dang_cho:
            return
        self._dang_cho = True

        def cho():
            try:
                han = time.time() + CHO_LEN_GIAY
                while time.time() < han:
                    if bot_chinh_song():
                        return            # bot chính tự chào "🟢 App đã mở"
                    time.sleep(3)
                ly_do = ("app không mở lên được" if not app_pid() else
                         "app đã mở nhưng chưa đăng nhập được (sai mật khẩu / "
                         "chưa tick 'Ghi nhớ mật khẩu' / mất mạng)")
                self.gui(cid, f"⚠ Sau {CHO_LEN_GIAY // 60} phút bot chính vẫn chưa lên: "
                              f"{ly_do}. Xem logs/dang_nhap_*.log trên máy.", phim=True)
                _log(f"chờ bot chính quá hạn: {ly_do}")
            finally:
                self._dang_cho = False
        threading.Thread(target=cho, daemon=True).start()

    def xu_ly(self, cid: int, text: str) -> None:
        if cid not in self.cho_phep:
            return                        # bot chính lo phần báo id; ở đây im
        from app.core.tele_bot import doi_nut
        text = doi_nut(text)
        lenh = (text or "").strip().split()[0].split("@")[0].lower() if text else ""
        if lenh in ("/moapp", "/dangnhap", "/mo"):
            self.mo_app(cid)
        elif lenh == "/dongapp":
            self.dong_app(cid)
        elif lenh == "/dongappmanh":
            self.dong_manh(cid, text)
        elif lenh in ("/start", "/menu", "/help"):
            from app.core.tele_bot import BAN_PHIM
            self.gui(cid, "⌨ Bảng nút đã hiện dưới ô chat.", phim=BAN_PHIM)
            self.gui(cid, self.trang_thai(), phim=True)
        elif lenh in ("/trangthai", "/tt"):
            self.gui(cid, self.trang_thai(), phim=True)
        else:
            self.gui(cid, self.trang_thai() + "\n(Lệnh khác chỉ chạy khi app đã "
                                              "đăng nhập.)", phim=True)

    def mot_vong(self) -> None:
        kq = self._goi("getUpdates", {"offset": self._offset, "timeout": POLL_GIAY,
                                      "allowed_updates": ["message", "callback_query"]},
                       timeout=POLL_GIAY + 10)
        for u in kq or []:
            self._offset = max(self._offset, u["update_id"] + 1)
            try:
                if "callback_query" in u:
                    cq = u["callback_query"]
                    try:
                        self._goi("answerCallbackQuery", {"callback_query_id": cq["id"]})
                    except Exception:  # noqa: BLE001
                        pass
                    self.xu_ly(cq["message"]["chat"]["id"], cq.get("data") or "")
                elif "message" in u:
                    m = u["message"]
                    self.xu_ly(m["chat"]["id"], m.get("text") or "")
            except Exception as e:  # noqa: BLE001
                _log(f"update lỗi: {e!r}")
        if kq:
            # XÁC NHẬN ngay: không thì bot chính lên sẽ nhận lại /moapp cũ
            try:
                self._goi("getUpdates", {"offset": self._offset, "timeout": 0}, timeout=10)
            except Exception:  # noqa: BLE001
                pass

    def _bao_app_tat(self) -> None:
        """Bot chính vừa im: nếu nhịp sống CÒN (không bị xoá) mà đã cũ = app
        SẬP / treo, không phải tắt êm (tắt êm thì `BotQuanLy.dung` XOÁ file
        nhịp sống). Rà soát 01/11/2026: trước đây gác cổng chỉ lặng lẽ nhận
        lệnh, app sập lúc 2 giờ sáng là im tới khi anh Hùng tự hỏi."""
        try:
            if not file_song().exists():
                return                    # tắt êm (bấm đóng / /dongapp)
            pid = app_pid()
            may = socket.gethostname()
            msg = (f"🔴 <b>App trên máy {may} vừa TẮT ĐỘT NGỘT hoặc không phản hồi</b>"
                   + (" (tiến trình vẫn còn — có thể đang treo)" if pid else "")
                   + ". Việc đang dở sẽ tự chạy tiếp khi mở lại. Gõ /moapp để mở lại app.")
            for cid in self.cho_phep:
                self.gui(cid, msg)
        except Exception as e:  # noqa: BLE001
            _log(f"báo app tắt lỗi: {e!r}")

    def chay(self) -> None:
        cho = 2.0
        song_truoc = None
        while True:
            song = bot_chinh_song()
            if song_truoc is True and not song:
                self._bao_app_tat()
            song_truoc = song
            try:
                self.kiem_ket_dang_nhap(song=song)
            except Exception as e:  # noqa: BLE001
                _log(f"kiểm kẹt đăng nhập lỗi: {e!r}")
            if song:
                self._offset = 0          # bot chính giữ offset; lần sau lấy lại
                time.sleep(10)
                continue
            try:
                self.mot_vong()
                cho = 2.0
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                if "409" not in msg:      # 409 = bot chính đang nghe -> chuyện thường
                    _log(f"nghe lỗi: {msg[:160]}")
                time.sleep(10 if "409" in msg else cho)
                cho = min(60.0, cho * 2)


def _log(dong: str) -> None:
    try:
        from app.core.tele_bot import _ghi_log
        _ghi_log("[gác cổng] " + dong)
    except Exception:  # noqa: BLE001
        pass


def main() -> int:
    from app.core.tele_bot import _bat_ipv4, _cfg
    tok, ids = _cfg()
    if not tok:
        return 0
    if not giu_khoa():
        return 0                          # đã có gác cổng khác
    _bat_ipv4()
    _log(f"bật (pid {os.getpid()}), {len(ids)} chat được phép")
    g = Gac(tok, ids)
    from app.core.tele_bot import dang_ky_menu
    dang_ky_menu(g._goi)
    g.chay()
    return 0
