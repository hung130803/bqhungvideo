"""Không phát hành nhầm tag/version/ghi chú của bản khác."""
import ast
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

root = Path(__file__).resolve().parents[1]
tree = ast.parse((root / 'app/version.py').read_text(encoding='utf-8-sig'))
version = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == '__version__' for t in n.targets))
if len(sys.argv) != 2 or sys.argv[1] != 'v' + version:
    raise SystemExit('Tag không khớp app/version.py')
notes = (root / 'docs/GHI_CHU_PHAT_HANH.md').read_text(encoding='utf-8-sig')
if version not in notes.splitlines()[0]:
    raise SystemExit('Ghi chú phát hành chưa được cập nhật cho đúng phiên bản')
print('Version, tag và ghi chú phát hành khớp nhau.')
