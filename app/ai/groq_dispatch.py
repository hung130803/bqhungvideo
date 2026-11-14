"""Cross-process Groq backpressure. No keys, prompts or responses on disk.

KHOÁ FILE (13/11/2026, cổng 116 `_test_groq_khoa.py`). Nhật ký tháng 11 có 22
dòng "database is locked" giết bước hậu kiểm ("OperationalError: database is
locked" / "LLMError: Gọi groq thất bại: database is locked"). Gốc: mỗi lượt mở
một kết nối MỚI (timeout 2 s, nhật ký rollback = người ghi chặn người đọc) và
chạy lại 3 CREATE TABLE; `pick_keys` còn gọi `remaining()` cho TỪNG key (41 kết
nối/lượt chọn key, đo 12,3 ms vs 0,35 ms cho 1 truy vấn). Nay:
  * WAL (bền trong file) + synchronous=NORMAL: người đọc không bị người ghi chặn.
  * Tạo bảng 1 lần/tiến trình (file bị xoá thì tự tạo lại).
  * `remaining_many` = 1 truy vấn cho cả loạt key.
  * Đọc (`remaining*`) gặp khoá -> thử lại ngắn rồi trả 0.0 = "không biết hạn
    chung", y như khi file chưa có. AN TOÀN vì `llm` vẫn giữ trạng thái key
    RIÊNG của tiến trình (`_KEY_STATE`), cùng lắm gửi thử key đó và nhận 429 thật.
  * Ghi (`defer`/`clear`) gặp khoá -> thử lại ngắn rồi BỎ: mất một bản ghi hạn
    chung chỉ có nghĩa tiến trình khác có thể thử key đó và nhận 429 thật.
  KHÔNG BAO GIỜ để "database is locked" nổi lên tới chỗ gọi LLM.
"""
from contextlib import contextmanager
import hashlib
import os
import sqlite3
import threading
import time
import uuid

# Thời gian chờ khoá (busy handler của sqlite3) theo loại việc.
_TIMEOUT_DOC = 0.5      # đọc hạn chung: thà trả 0.0 còn hơn treo lượt chọn key
_TIMEOUT_GHI = 0.5      # ghi hạn chung (WAL: giao dịch ghi chỉ vài µs)
_TIMEOUT_LAN = 10.0     # giành làn (slot vẫn tự lặp lại khi 'locked')
_THU_LAI = 3            # số lần thử khi gặp khoá
_NGHI = 0.05            # nghỉ giữa các lần thử (giây)

_INIT_LOCK = threading.Lock()
_DA_TAO = set()         # đường dẫn đã tạo bảng trong tiến trình này
_DA_WAL = set()         # đường dẫn đã xác nhận journal_mode=wal


def _duong_dan():
    from config import DATA_DIR
    folder=DATA_DIR/'_cache';folder.mkdir(parents=True,exist_ok=True)
    return str(folder/'groq_dispatch.sqlite3')


def _la_khoa(exc):
    s=str(exc).lower()
    return 'locked' in s or 'busy' in s


def _tao_bang(con,path):
    if path not in _DA_WAL:
        try:
            mode=con.execute('PRAGMA journal_mode=WAL').fetchone()
            if mode and str(mode[0]).lower()=='wal':
                _DA_WAL.add(path)
        except sqlite3.OperationalError:
            pass  # Bị khoá lúc đổi nhật ký: lần mở sau thử lại; vẫn chạy được.
    con.execute('CREATE TABLE IF NOT EXISTS cooldown (identity TEXT PRIMARY KEY, until REAL NOT NULL)')
    con.execute('CREATE TABLE IF NOT EXISTS cooldown_seen (identity TEXT PRIMARY KEY, at REAL NOT NULL)')
    con.execute('CREATE TABLE IF NOT EXISTS lane (scope TEXT PRIMARY KEY, owner TEXT, until REAL NOT NULL)')
    _DA_TAO.add(path)


def _connect(timeout=_TIMEOUT_LAN):
    path=_duong_dan()
    moi=not os.path.exists(path)
    con=sqlite3.connect(path,timeout=timeout)
    try:
        con.execute('PRAGMA synchronous=NORMAL')
        if moi or path not in _DA_TAO or path not in _DA_WAL:
            with _INIT_LOCK:
                if moi:
                    _DA_TAO.discard(path);_DA_WAL.discard(path)
                _tao_bang(con,path)
    except BaseException:
        con.close();raise
    return con


def _quen_bang():
    """File bị xoá/thay giữa chừng ('no such table') -> lần mở sau tạo lại."""
    _DA_TAO.clear();_DA_WAL.clear()


def _chay(fn,timeout,mac_dinh,nuot):
    """Chạy fn(con) với thử lại khi khoá. nuot=True: hết lượt thử thì trả mac_dinh."""
    for lan in range(_THU_LAI):
        try:
            con=_connect(timeout)
            try:
                return fn(con)
            finally:
                con.close()
        except sqlite3.OperationalError as exc:
            if 'no such table' in str(exc).lower():
                _quen_bang()
                continue
            if not _la_khoa(exc):
                raise
            if lan+1>=_THU_LAI:
                if nuot:
                    return mac_dinh
                raise
            time.sleep(_NGHI*(lan+1))
    return mac_dinh


def _identity(key,scope):
    return hashlib.sha256((scope+'\0'+key).encode()).hexdigest()


def remaining_many(keys,scope):
    """{key: giây còn hạn chung} cho cả loạt key bằng MỘT truy vấn.

    Ngữ nghĩa y hệt `remaining()` từng key: max(0, until-now), không có -> 0.0.
    Khoá kéo dài -> mọi key 0.0 (xem docstring module vì sao an toàn)."""
    keys=list(keys)
    if not keys:
        return {}
    ids={_identity(k,scope):k for k in keys}
    def fn(con):
        out={k:0. for k in keys}
        lst=list(ids)
        now=time.time()
        for i in range(0,len(lst),500):
            part=lst[i:i+500]
            q='SELECT identity,until FROM cooldown WHERE identity IN (%s)'%','.join('?'*len(part))
            for ident,until in con.execute(q,part).fetchall():
                out[ids[ident]]=max(0.,until-now)
        return out
    return _chay(fn,_TIMEOUT_DOC,{k:0. for k in keys},True)


def remaining(key,scope):
    def fn(con):
        row=con.execute('SELECT until FROM cooldown WHERE identity=?',(_identity(key,scope),)).fetchone()
        return max(0.,row[0]-time.time()) if row else 0.
    return _chay(fn,_TIMEOUT_DOC,0.,True)


def defer(key,scope,seconds):
    def fn(con):
        with con:
            con.execute('INSERT INTO cooldown_seen VALUES(?,?) ON CONFLICT(identity) DO UPDATE SET at=excluded.at',(_identity(key,scope),time.time()))
            con.execute('INSERT INTO cooldown VALUES(?,?) ON CONFLICT(identity) DO UPDATE '
                        'SET until=MAX(until,excluded.until)',(_identity(key,scope),time.time()+seconds))
    _chay(fn,_TIMEOUT_GHI,None,True)


def clear(key,scope,observed_at):
    def fn(con):
        with con:
            con.execute('DELETE FROM cooldown WHERE identity=? AND NOT EXISTS '
                '(SELECT 1 FROM cooldown_seen WHERE identity=? AND at>?)',
                (_identity(key,scope),_identity(key,scope),observed_at))
    _chay(fn,_TIMEOUT_GHI,None,True)


def _pid_song(pid):
    """Tiến trình `pid` còn sống? Không biết chắc -> coi là CÒN (không cướp làn)."""
    try:
        import psutil
        return psutil.pid_exists(int(pid))
    except Exception:  # noqa: BLE001
        return True


def _claim(scope,owner):
    con=_connect(_TIMEOUT_GHI)
    try:
        with con:
            now=time.time()
            # LÀN CỦA TIẾN TRÌNH ĐÃ CHẾT -> nhả NGAY (31/10/2026). Trước đây phải
            # đợi lease 180 s: tiến trình phân tích bị Huỷ/giết hay app thoát
            # bằng os._exit khi đang gọi AI là CẢ MÁY đứng gọi AI 3 phút.
            row=con.execute('SELECT owner,until FROM lane WHERE scope=?',(scope,)).fetchone()
            if row and row[0] and row[1]>now and ':' in str(row[0]):
                pid=str(row[0]).split(':',1)[0]
                if pid.isdigit() and int(pid)!=os.getpid() and not _pid_song(pid):
                    con.execute('UPDATE lane SET owner=NULL,until=? WHERE scope=? AND owner=?',
                                (now,scope,row[0]))
            # SDK automatic retries are disabled; one HTTP call has <=120s timeout.
            cursor=con.execute('INSERT INTO lane VALUES(?,?,?) ON CONFLICT(scope) DO UPDATE '
                'SET owner=excluded.owner,until=excluded.until WHERE lane.until<=?',
                (scope,owner,now+180,now))
            return cursor.rowcount==1
    finally:con.close()


def _release(scope,owner):
    con=_connect(_TIMEOUT_GHI)
    try:
        with con:
            con.execute('UPDATE lane SET owner=NULL,until=? WHERE scope=? AND owner=?',
                        (time.time()+.35,scope,owner))
    finally:con.close()


def so_lan(scope):
    """Số lượt gọi CÙNG LÚC cho cả máy (mọi tiến trình) của một dịch vụ Groq.

    31/10/2026: bản cũ cho ĐÚNG 1 lượt/dịch vụ. Đo thật lúc chạy 7 luồng AI:
    làn `chat` BẬN 81% thời gian (11 lượt/90 s, ~8 s/lượt) trong khi luôn có
    7-16 key RẢNH (TB 12) -> 7 video xếp hàng một-một, mỗi video chờ ~56 phút
    trước khi được phân tích. Mở 3 làn: cùng model, cùng câu hỏi, cùng mức suy
    nghĩ -> chất lượng KHÔNG đổi, chỉ bớt xếp hàng. Không mở cao hơn: mỗi key
    chịu ~1 lượt suy nghĩ cao/phút (8.000 token/phút), mở quá là 429 hàng loạt.
    `vision`/`audio` giữ 1 như cũ. Đặt `GROQ_SONG_SONG=1` để trả về hành vi cũ."""
    import os
    if scope != 'chat':
        return 1
    try:
        from config import settings
        v = int(os.environ.get('GROQ_SONG_SONG') or getattr(settings, 'GROQ_SONG_SONG', 3) or 3)
    except (TypeError, ValueError):
        v = 3
    return max(1, min(8, v))


def _ten_lan(scope, i):
    # Làn 0 GIỮ ĐÚNG tên cũ -> tiến trình bản cũ còn chạy vẫn tôn trọng nhau.
    return scope if i == 0 else f'{scope}#{i}'


@contextmanager
def slot(scope,check=lambda:None):
    """Tối đa `so_lan(scope)` lượt/dịch vụ cho cả máy; lease chết tự hết hạn; đợi huỷ được."""
    from app.ai.llm import LLMError
    # owner = '<pid>:<uuid>' để người sau nhận ra làn của tiến trình đã chết.
    owner=f'{os.getpid()}:{uuid.uuid4().hex}';deadline=time.monotonic()+180
    lan=None
    while lan is None:
        check()
        for i in range(so_lan(scope)):
            try:
                if _claim(_ten_lan(scope,i),owner):
                    lan=_ten_lan(scope,i);break
            except sqlite3.OperationalError as exc:
                if 'no such table' in str(exc).lower():
                    _quen_bang();continue  # file bị xoá giữa chừng: tạo lại
                if not _la_khoa(exc):
                    raise LLMError('Không mở được bộ điều tiết Groq; chưa gửi yêu cầu.') from exc
        if lan is not None:
            break
        if time.monotonic()>=deadline:
            raise LLMError('Groq đang bận với video khác; đã giữ tiến độ, hãy thử lại sau.')
        time.sleep(.15)
    try:
        check()
        yield
    finally:
        # A temporary local lock must not discard an already received answer.
        # The lease still expires if cleanup fails.
        try:_release(lan,owner)
        except (OSError,sqlite3.Error):pass
