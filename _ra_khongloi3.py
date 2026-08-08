# -*- coding: utf-8 -*-
"""CHẠY LẠI THẬT `generate_highlights` trên video KHÔNG LỜI của lượt e2e,
in MỌI dòng tiến độ -> thấy tận mắt `_khong_loi` có bật không và AI đi đường nào.

    .venv\\Scripts\\python _ra_khongloi3.py <sandbox_e2e> [tên kênh]

Chép DB sandbox ra chỗ khác rồi chạy trên bản chép -> KHÔNG đụng dữ liệu gốc.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

sb = Path(sys.argv[1])
ten_kenh = sys.argv[2] if len(sys.argv) > 2 else "KHÔNG LỜI"
_TD = Path(tempfile.mkdtemp(prefix="ra_kl3_"))
for e in ("", "-wal", "-shm"):
    try:
        shutil.copy(str(sb / "studio.db") + e, str(_TD / "studio.db") + e)
    except OSError:
        pass
os.environ["BQ_DATA_DIR"] = str(_TD)
os.environ["BQ_DB_PATH"] = str(_TD / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(_TD / "s.ini")

# key Groq qua ENV (không ghi file)
_env = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "BQHungVideo" / ".env"
if _env.exists():
    for ln in _env.read_text(encoding="utf-8", errors="replace").splitlines():
        k, _, v = ln.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k in ("GROQ_API_KEYS", "GROQ_KEYS_FILE") and v:
            os.environ.setdefault(k, v)

import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from app.database.db import db  # noqa: E402


class Ctx:
    profile = {}

    def progress(self, p, m=""):
        if m:
            print(f"   [{p:.2f}] {m}")
            sys.stdout.flush()

    def check_canceled(self):
        pass


def main() -> int:
    v = db.query_one(
        "SELECT v.id, v.src_path, v.duration, p.name kenh FROM videos v "
        "JOIN projects p ON p.id=v.project_id WHERE p.name LIKE ?",
        (f"%{ten_kenh}%",))
    if not v:
        print("không thấy video của kênh", ten_kenh)
        return 2
    # gốc đã vào Thùng rác -> trỏ lại cho đúng
    src = Path(v["src_path"])
    if not src.exists():
        cand = list((sb / "daychuyen" / "_DaXoa").rglob(src.name))
        if cand:
            src = cand[0]
            db.execute("UPDATE videos SET src_path=? WHERE id=?",
                       (str(src), v["id"]))
            print(f"gốc lấy lại từ Thùng rác: {src.name}")
    print(f"video #{v['id']} · {v['kenh']} · {v['duration']:.0f}s · "
          f"gốc {'CÓ' if src.exists() else 'MẤT'}")
    # xoá clip cũ để chạy sạch
    db.execute("DELETE FROM clips WHERE video_id=?", (v["id"],))

    from app.modules.m1_highlight import generate_highlights
    print("\n── chạy generate_highlights ──")
    res = generate_highlights({"video_id": v["id"], "preset": {}}, Ctx())
    print("\n── kết quả ──")
    print({k: x for k, x in res.items() if k != "clip_ids"})
    for c in db.query("SELECT id,start_sec,end_sec,title,signals FROM clips "
                      "WHERE video_id=? ORDER BY id", (v["id"],)):
        s = db.loads(c["signals"], {}) or {}
        print(f"  clip #{c['id']} {c['start_sec']:.1f}-{c['end_sec']:.1f}s "
              f"«{(c['title'] or '')[:50]}»")
        print(f"     llm_used={s.get('llm_used')} xem_hinh={s.get('xem_hinh')} "
              f"khong_loi={s.get('khong_loi')} ai={s.get('ai')}")
    shutil.rmtree(_TD, ignore_errors=True)
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    sys.exit(main())
