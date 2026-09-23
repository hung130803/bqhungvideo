"""Reversible display preference; never delete records or pipeline dedup history."""
import hashlib
from app.ui.appsettings import app_settings


def key(record):
    from config import DB_PATH
    identity=f'{DB_PATH}|{record["pid"]}|{record["id"]}|{record["path"]}'
    return 'batch_hidden/'+hashlib.sha256(identity.encode('utf-8')).hexdigest()


def hidden(record):
    # Active work must remain visible even if an old history item was hidden.
    return (not record['job_ids'] and record.get('source')!='Đang được Dây chuyền theo dõi'
            and str(app_settings().value(key(record),'0'))=='1')


def set_hidden(record,value):
    if value and (record['job_ids'] or record.get('source')=='Đang được Dây chuyền theo dõi'):
        raise ValueError('Video còn việc chạy/chờ; chưa ẩn hồ sơ.')
    settings=app_settings()
    if value:settings.setValue(key(record),'1')
    else:settings.remove(key(record))
