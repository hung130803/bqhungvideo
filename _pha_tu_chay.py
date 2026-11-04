# -*- coding: utf-8 -*-
r"""THỬ PHÁ cổng 110/111 (Đợt 1 dây chuyền tự động): gỡ ĐÚNG 1 chốt rồi chạy cổng, phải BẮT.
    PYTHONIOENCODING=utf-8 .venv\Scripts\python _pha_tu_chay.py
Lượt 04/11/2026: BẮT 6 · LỌT 0 · KHÔNG PHÁ ĐƯỢC 0."""
from pathlib import Path
R=Path(r"D:\claude\ai-content-studio")
PHA=[("app/ui/studio_page.py","self._pipe_run(nen=True, nhom=nhom, im=True)","self._pipe_run(nen=True, nhom=nhom)","_test_tu_chay.py"),
("app/ui/studio_page.py","                if im and self._pipe_da_huy(it.project_id, khoa):","                if False and self._pipe_da_huy(it.project_id, khoa):","_test_tu_chay.py"),
("app/core/tele_bot.py","                    if fn:\n                        fn()","                    pass","_test_phieu_dot.py"),
("app/core/phieu_dot.py","                            and not nc[\"co_file\"](tm, fname)):","                            ):","_test_phieu_dot.py"),
("app/core/tu_chay.py","            cho = LUOT_DAU_GIAY if luc_mo_app else cfg.phut * 60","            cho = 0","_test_tu_chay.py"),
("app/core/phieu_dot.py",'    s = s.replace("/", "\\\\")','    pass',"_test_phieu_dot.py")]
for f,a,b,t in PHA:
    p=R/f; goc=p.read_bytes(); s=goc.decode().replace("\r\n","\n")
    if s.count(a)!=1: print("KHÔNG PHÁ ĐƯỢC",f,a[:40]); continue
    p.write_bytes(s.replace(a,b).encode())
    try:
        compile(p.read_text(encoding='utf-8'),str(p),'exec')
        r=subprocess.run([str(R/".venv/Scripts/python.exe"),t],cwd=R,capture_output=True,timeout=900)
        print("BẮT" if r.returncode else "LỌT", f, a.strip()[:50])
    finally:
        p.write_bytes(goc)
