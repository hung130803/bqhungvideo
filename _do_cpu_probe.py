# -*- coding: utf-8 -*-
"""TỰ KIỂM BỘ ĐO CPU-GIÂY — chạy TRƯỚC mọi phép đo dùng nó.

Đốt CPU một khoảng ĐÃ BIẾT trong tiến trình con rồi hỏi lại BA bộ đo. Bộ đo
trả ~0 nghĩa là môi trường không cho đọc, và lúc đó mọi bảng "CPU-giây" dựa
trên nó là SỐ RÁC — phải nói ra chứ không in như thật (họ bẫy `astats` cổng
53: phép đo hỏng phát chứng nhận).
"""
import subprocess
import sys
import time

import psutil

sys.stdout.reconfigure(encoding="utf-8")   # bài học cp1252, xem CLAUDE.md

MA = "x=0\nfor i in range(40000000): x+=i\nprint(x)"


def _tong_he_thong() -> float:
    t = psutil.cpu_times()
    return float(t.user + t.system)


t_he0 = _tong_he_thong()
t0 = time.time()
p = subprocess.Popen([sys.executable, "-c", MA], stdout=subprocess.PIPE,
                     text=True)
ps = psutil.Process(p.pid)
m = 0.0
while p.poll() is None:
    try:
        m = max(m, sum(ps.cpu_times()[:2]))
    except Exception:                                  # noqa: BLE001
        break
    time.sleep(0.05)
p.stdout.read()
p.wait()
wall = time.time() - t0
he = _tong_he_thong() - t_he0

print(f"wall {wall:.2f}s")
print(f"  [A] psutil cpu_times CỦA TIẾN TRÌNH CON : {m:.3f}s  -> "
      + ("DÙNG ĐƯỢC" if m > 0.2 * wall else "KHÔNG ĐỌC ĐƯỢC"))
print(f"  [B] psutil cpu_times CẢ MÁY (hiệu)      : {he:.3f}s  -> "
      + ("DÙNG ĐƯỢC" if he > 0.2 * wall else "KHÔNG ĐỌC ĐƯỢC"))
