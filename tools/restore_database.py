import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding='utf-8')
from app.core.db_restore import main

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f'Không khôi phục: {error}')
        raise SystemExit(1)
