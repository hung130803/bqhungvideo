"""Cross-process Groq backpressure. No keys, prompts or responses on disk."""
from contextlib import contextmanager
import hashlib
import os
import sqlite3
import time
import uuid


def _connect():
    from config import DATA_DIR
    folder=DATA_DIR/'_cache';folder.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(str(folder/'groq_dispatch.sqlite3'),timeout=2)
    con.execute('CREATE TABLE IF NOT EXISTS cooldown (identity TEXT PRIMARY KEY, until REAL NOT NULL)')
    con.execute('CREATE TABLE IF NOT EXISTS cooldown_seen (identity TEXT PRIMARY KEY, at REAL NOT NULL)')
    con.execute('CREATE TABLE IF NOT EXISTS lane (scope TEXT PRIMARY KEY, owner TEXT, until REAL NOT NULL)')
    return con


def _identity(key,scope):
    return hashlib.sha256((scope+'\0'+key).encode()).hexdigest()


def remaining(key,scope):
    con=_connect()
    try:
        row=con.execute('SELECT until FROM cooldown WHERE identity=?',(_identity(key,scope),)).fetchone()
        return max(0.,row[0]-time.time()) if row else 0.
    finally:con.close()


def defer(key,scope,seconds):
    con=_connect()
    try:
        with con:
            con.execute('INSERT INTO cooldown_seen VALUES(?,?) ON CONFLICT(identity) DO UPDATE SET at=excluded.at',(_identity(key,scope),time.time()))
            con.execute('INSERT INTO cooldown VALUES(?,?) ON CONFLICT(identity) DO UPDATE '
                        'SET until=MAX(until,excluded.until)',(_identity(key,scope),time.time()+seconds))
    finally:con.close()


def clear(key,scope,observed_at):
    con=_connect()
    try:
        with con:
            con.execute('DELETE FROM cooldown WHERE identity=? AND NOT EXISTS '
                '(SELECT 1 FROM cooldown_seen WHERE identity=? AND at>?)',
                (_identity(key,scope),_identity(key,scope),observed_at))
    finally:con.close()


def _pid_song(pid):
    """Tiến trình `pid` còn sống? Không biết chắc -> coi là CÒN (không cướp làn)."""
    try:
        import psutil
        return psutil.pid_exists(int(pid))
    except Exception:  # noqa: BLE001
        return True


def _claim(scope,owner):
    con=_connect()
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
    con=_connect()
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
                if 'locked' not in str(exc).lower():
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
