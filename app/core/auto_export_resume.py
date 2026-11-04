"""Persist automatic-export intent and template snapshots across app restarts."""
import copy
import json
from app.database import db


class JobMap(dict):
    def __init__(self, kind):
        self.kind = kind
        rows = db.query("SELECT c.job_id,c.data FROM job_checkpoints c JOIN jobs j ON j.id=c.job_id "
                        "WHERE c.scope='auto-export' AND c.step=? AND j.status IN ('pending','running','done')", (kind,))
        values = {}
        for r in rows:
            try:
                values[int(r['job_id'])] = json.loads(r['data'])
            except (ValueError, TypeError):
                continue
        super().__init__(values)

    def __setitem__(self, key, value):
        value = copy.deepcopy(value)
        if db.query_one('SELECT id FROM jobs WHERE id=?', (key,)):
            db.execute("INSERT INTO job_checkpoints(job_id,scope,step,data,checksum) VALUES(?,'auto-export',?,?,'') "
                       "ON CONFLICT(job_id,scope,step) DO UPDATE SET data=excluded.data",
                       (key, self.kind, json.dumps(value, ensure_ascii=False)))
        super().__setitem__(key, value)

    def pop(self, key, default=None):
        db.execute("DELETE FROM job_checkpoints WHERE job_id=? AND scope='auto-export' AND step=?", (key,self.kind))
        return super().pop(key,default)

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]
