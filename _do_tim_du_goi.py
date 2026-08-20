# -*- coding: utf-8 -*-
"""TÌM DANH SÁCH GÓI ĐÚNG bằng cách gọi CHÍNH HÀM CỦA APP trên môi trường máy
anh Hùng.

Vì sao phải làm thế này thay vì suy tiếp: danh sách tĩnh
`nhan_ban_giong._CAN_CHO_NHAN_BAN` đã chứng minh nói sai ở **CẢ HAI CHIỀU** —
thiếu `transformers` trên máy anh Hùng, thừa 3 gói trên máy dev. Và
`import vieneu` / `import vieneu.v3turbo` **THÀNH CÔNG** trong khi `transformers`
đang thiếu, vì gói nạp **LƯỜI** (chỉ khi `ref_audio=` chạy). Phép dò duy nhất nói
thật là **ĐỌC THẬT**.

═══ BẢN ĐẦU CỦA SCRIPT NÀY SAI, VÀ SAI KIỂU ĐÁNG GHI LẠI ═══
Nó tự viết lời gọi `from vieneu.v3turbo import VieNeuTTS` — **đoán tên lớp**. Máy
anh Hùng trả về:
    ImportError: cannot import name 'VieNeuTTS' from 'vieneu.v3turbo'
Tên thật là **`V3TurboVieNeuTTS`**. Tức tôi đi tìm lỗi của app bằng một phép đo
mang lỗi của chính tôi — đúng họ bẫy "phép đo hỏng phát chứng nhận", chỉ khác là
lần này nó phát ra một lỗi GIẢ.
Chữa gốc: **KHÔNG tự viết lời gọi nữa.** Gọi `giong_vieneu.doc_loat()` — đường
app THẬT SỰ đi — và ép nó dùng python của máy anh Hùng qua biến môi trường
`BQ_VN_PYTHON` (`_ung_vien_python` đọc biến này TRƯỚC mọi ứng viên khác).

Vòng: `doc_loat` -> đọc log app vừa ghi -> thấy `No module named 'X'` -> cài `X`
vào đúng venv đó -> chạy lại. Dừng khi ra WAV **CÓ TIẾNG** (đo độ dài + RMS, đọc
mẫu thẳng) hoặc hết trần.
"""
from __future__ import annotations

import array
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PY = Path(os.environ["TEMP"]) / "bq_giong8" / "venv" / "Scripts" / "python.exe"
MAU = (Path(os.environ["LOCALAPPDATA"]) / "BQHungVideo" / "_mau_giong"
       / "test.wav")
TRAN = 8

#: KHÔNG cài dù lỗi có đòi: giao diện web / máy chủ suy luận / đọc PDF — không
#: thứ nào là phụ thuộc của một lượt ĐỌC TIẾNG, và ba cái giữa không build được
#: trên Windows nên cài là gãy cả lượt.
CHAN = {"gradio", "lmdeploy", "llama-cpp-python", "triton", "triton-windows",
        "pymupdf", "fitz"}

#: tên IMPORT khác tên PIP thì phải đổi, không thì pip báo không tìm thấy gói.
DOI = {"sklearn": "scikit-learn", "cv2": "opencv-python", "PIL": "pillow",
       "yaml": "PyYAML"}

print(f"python : {PY}")
print(f"mẫu    : {MAU}  (tồn tại: {MAU.is_file()})")
if not PY.is_file() or not MAU.is_file():
    print("*** thiếu python hoặc file mẫu — dừng")
    raise SystemExit(2)

# Hộp cát RIÊNG cho DATA_DIR: app sẽ ghi log vào đây, và đó là chỗ tôi đọc lỗi
# ra. Đặt TRƯỚC khi import `app.*` — `config.DATA_DIR` đọc biến lúc nạp.
SB = Path(tempfile.mkdtemp(prefix="bq_timgoi_"))
os.environ["BQ_DATA_DIR"] = str(SB)
os.environ["BQ_DB_PATH"] = str(SB / "studio.db")
os.environ["BQ_VN_PYTHON"] = str(PY)          # ÉP dùng python của máy anh Hùng
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core import giong_vieneu as VN                      # noqa: E402

print(f"app sẽ dùng python: {VN._python_vieneu()[0]}")
LOG = SB / "logs"


def loi_moi_nhat() -> str:
    """Dòng lỗi mới nhất app vừa ghi. Đọc log CỦA APP, không tự đoán."""
    try:
        fs = sorted(LOG.glob("giong_vieneu_*.log"),
                    key=lambda p: p.stat().st_mtime)
        if not fs:
            return ""
        return fs[-1].read_text(encoding="utf-8", errors="replace")
    except Exception:                                          # noqa: BLE001
        return ""


def do_wav(p: Path) -> tuple[float, float]:
    """(giây, RMS) — đọc mẫu THẲNG. Không tin lời hàm tự báo 'ok'."""
    if not p.is_file():
        return 0.0, 0.0
    try:
        with wave.open(str(p), "rb") as w:
            n, sr, sw = w.getnframes(), w.getframerate(), w.getsampwidth()
            raw = w.readframes(n)
        if sw != 2 or not n:
            return (n / sr if sr else 0.0), 0.0
        a = array.array("h")
        a.frombytes(raw)
        return n / sr, math.sqrt(sum(float(v) * v for v in a) / len(a)) / 32768.0
    except Exception:                                          # noqa: BLE001
        return 0.0, 0.0


tu_cai: list[str] = []
ket: dict = {"xong": False, "tu_cai": tu_cai, "vong": 0, "loi": ""}
CAU = "Xin chào, đây là giọng thử nghiệm."

for vong in range(1, TRAN + 1):
    ket["vong"] = vong
    out = SB / f"ra{vong}.wav"
    truoc = len(loi_moi_nhat())
    try:
        r = VN.doc_loat([CAU], [str(out)], "vnb:" + str(MAU))
        duoc = bool(r and r[0])
    except Exception as e:                                     # noqa: BLE001
        duoc = False
        print(f"vòng {vong}: doc_loat NÉM {type(e).__name__}: {e}"[:200])
    d, rms = do_wav(out)
    if duoc and d >= 0.5 and rms > 0.002:
        print(f"\nVÒNG {vong}: ĐỌC ĐƯỢC — WAV {d:.2f}s · RMS {rms:.5f}")
        ket.update(xong=True, giay=round(d, 2), rms=round(rms, 5))
        print(f"\n=== DANH SÁCH THẬT PHẢI CÀI: {tu_cai} ===")
        break

    moi = loi_moi_nhat()[truoc:]
    m = None
    for mm in re.finditer(r"No module named '([A-Za-z0-9_.\-]+)'", moi):
        m = mm                                    # lấy cái MỚI NHẤT
    if not m:
        dong = ""
        for ln in reversed(moi.strip().splitlines()):
            if "hỏng" in ln or "Error" in ln:
                dong = ln[:300]
                break
        print(f"\nVÒNG {vong}: hỏng nhưng KHÔNG phải thiếu module:")
        print("   " + (dong or f"(không rõ; WAV {d:.2f}s rms {rms:.5f})"))
        ket["loi"] = dong or "không rõ"
        break

    imp = m.group(1).split(".")[0]
    goi = DOI.get(imp, imp)
    if goi.lower() in CHAN:
        print(f"\nVÒNG {vong}: đòi gói BỊ CHẶN '{goi}' — dừng")
        ket["loi"] = f"đòi gói bị chặn: {goi}"
        break
    print(f"vòng {vong}: thiếu '{imp}' -> cài '{goi}'...", flush=True)
    p = subprocess.run([str(PY), "-m", "pip", "install", "--no-input",
                        "--disable-pip-version-check", goi],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=3600)
    if p.returncode != 0:
        duoi = " | ".join((p.stdout or "").strip().splitlines()[-3:])
        print(f"   pip HỎNG mã {p.returncode}: {duoi}")
        ket["loi"] = f"pip hỏng khi cài {goi}: {duoi}"
        break
    tu_cai.append(goi)
    print(f"   cài xong. đã tự cài: {tu_cai}")
else:
    print(f"\nHẾT TRẦN {TRAN} vòng. đã tự cài: {tu_cai}")
    ket["loi"] = f"hết trần {TRAN} vòng"

Path("_kq_du_goi.json").write_text(
    json.dumps(ket, ensure_ascii=False, indent=1), encoding="utf-8")
shutil.rmtree(SB, ignore_errors=True)
print("\nghi _kq_du_goi.json")
