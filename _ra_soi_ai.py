# -*- coding: utf-8 -*-
"""Soi SÂU kết quả AI của 1 sandbox e2e — CHỈ ĐỌC.

    .venv\\Scripts\\python _ra_soi_ai.py <sandbox>

Trả lời: video nào ra clip AI, video nào rơi 'Cắt cơ bản' và **VÌ SAO**;
video KHÔNG LỜI có đi đường XEM HÌNH không; chép lời ra bao nhiêu từ.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass


def main() -> int:
    sb = Path(sys.argv[1])
    p = sb / "studio.db"
    t = Path(tempfile.mktemp(suffix=".db"))
    for e in ("", "-wal", "-shm"):
        try:
            shutil.copy(str(p) + e, str(t) + e)
        except OSError:
            pass
    c = sqlite3.connect(t)
    c.row_factory = sqlite3.Row

    for v in c.execute("SELECT v.id, v.duration, p.name kenh "
                       "FROM videos v JOIN projects p ON p.id=v.project_id "
                       "ORDER BY v.id"):
        print(f"\n══ {v['kenh']}  ({v['duration'] or 0:.0f}s)")
        # chép lời
        a = c.execute("SELECT kind,status,engine,LENGTH(data) n,data FROM "
                      "analysis WHERE video_id=? AND kind='transcript'",
                      (v["id"],)).fetchone()
        if a:
            try:
                d = json.loads(a["data"])
                segs = d.get("segments") or []
                words = d.get("words") or []
                chu = sum(len((s.get("text") or "").split()) for s in segs)
                txt = " ".join((s.get("text") or "") for s in segs)[:110]
                print(f"   chép lời: {a['engine']} · {len(segs)} đoạn · "
                      f"{len(words)} từ-mốc · ~{chu} từ · ngôn ngữ "
                      f"{d.get('language')!r}")
                print(f"      «{txt}»")
            except Exception as e:      # noqa: BLE001
                print("   chép lời: đọc hỏng", e)
        else:
            print("   chép lời: KHÔNG CÓ")
        for k in ("scenes", "audio"):
            r = c.execute("SELECT status,LENGTH(data) n FROM analysis WHERE "
                          "video_id=? AND kind=?", (v["id"], k)).fetchone()
            if r:
                print(f"   {k}: {r['status']} ({r['n']} byte)")
        for cl in c.execute("SELECT id,start_sec,end_sec,title,signals,status "
                            "FROM clips WHERE video_id=? ORDER BY id",
                            (v["id"],)):
            s = {}
            try:
                s = json.loads(cl["signals"] or "{}")
            except Exception:      # noqa: BLE001
                pass
            nhan = "AI" if s.get("llm_used") else "CẮT CƠ BẢN"
            them = []
            if s.get("xem_hinh"):
                them.append("XEM HÌNH")
            if s.get("ai"):
                them.append(str(s.get("ai")))
            if s.get("n_seg"):
                them.append(f"{s['n_seg']} đoạn")
            print(f"   clip #{cl['id']} [{nhan}{' · ' + ' · '.join(them) if them else ''}] "
                  f"{cl['start_sec']:.1f}-{cl['end_sec']:.1f}s "
                  f"«{(cl['title'] or '')[:46]}» {cl['status']}")
            bo = {k: v2 for k, v2 in s.items()
                  if k not in ("segments", "words") and not isinstance(v2, (list, dict))}
            print(f"      signals: {bo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
