# -*- coding: utf-8 -*-
"""CỔNG 71 — **TÁCH GIỌNG PHẢI DÙNG GPU KHI MÁY CÓ GPU** (18/08/2026).

Anh Hùng chụp màn hình *"Đang tách nhạc/giọng (249 giây, **cpu**)"* trên máy
có RTX 3060. Bước tách giọng nằm ở ĐẦU dây chuyền thay tiếng, nhân với 200-300
kênh nên đây là món đắt nhất còn lại.

**GỐC KHÔNG PHẢI Ở MÃ CHỌN THIẾT BỊ** — `_MA_TACH` viết đúng từ đầu
(`dev = "cuda" if torch.cuda.is_available() else "cpu"`). Chỗ hỏng là GÓI:
`cai_demucs` ghi cứng chỉ mục `whl/cpu` nên `_lib` luôn nhận `torch+cpu`, và
bản dựng đó KHÔNG có CUDA -> `is_available()` False vĩnh viễn. Máy có GPU hay
không cũng ra một kết quả, không một dòng báo.

SỐ ĐO (`_do_demucs_gpu.py` + `_do_demucs_gpu2.py`, 3 vòng ĐAN XEN, 60 giây
tiếng THẬT, hai arm đi CHUNG runner của app, khác nhau đúng một thứ là torch
nào được nạp):
  * `apply_model`  CPU 25,06s -> GPU  2,70s = **9,28 lần**
  * cả lượt (wall) CPU 29,27s -> GPU  9,28s = **3,15 lần**
  * VRAM đỉnh 1.536/12.288 MiB (Demucs chiếm thêm **893 MiB**) -> còn 10,7 GB
    cho NVENC chạy cùng.
  * CHẤT LƯỢNG KHÔNG ĐỔI, **và chỉ đọc được điều đó khi có SÀN NHIỄU**:
      GPU vs CPU lớp nhạc −19,02 / −21,54 / −21,11 dB
      CPU vs CPU lớp nhạc −19,24 / −22,05 dB   <- sàn nhiễu
    Hai cột trùng dải -> lệch là NHIỄU của chính Demucs (không tiền định),
    KHÔNG phải "GPU làm đổi tiếng". Đọc mỗi số thô −19 dB là kết luận ngược.

GIÁ: wheel CUDA **2.474,4 MB** vs `+cpu` 121,9 MB (đo HTTP HEAD). Vì vậy chỉ
lấy bản CUDA khi máy THẬT SỰ có GPU NVIDIA — máy nhân viên không đổi một byte.

CỔNG NÀY CANH 5 ĐIỀU (đều là chỗ dễ mất im lặng):
 1. `co_gpu_nvidia()` KHÔNG BAO GIỜ NÉM và **KHÔNG import torch** (import
    torch trong tiến trình đã nạp Qt là ACCESS VIOLATION, `try/except` không
    chặn — xem `thiet_bi_tach`). Quét bằng AST, không quét chuỗi.
 2. Chỉ mục pip phải do `co_gpu_nvidia()` QUYẾT ĐỊNH, không được là hằng số.
    Đây là chốt chống "dọn cho gọn" — ai ghi cứng lại `whl/cpu` là GPU mất im
    lặng y như trước, app vẫn chạy, mọi cổng khác vẫn xanh.
 3. Máy CÓ GPU -> chỉ mục CUDA · máy KHÔNG -> chỉ mục CPU (gọi thật, vá
    `co_gpu_nvidia`, chặn ở ranh giới `subprocess` nên không tải một byte nào).
 4. NHÃN phải khớp ĐƯỜNG SẼ ĐI. Nhãn ghi 155 MB rồi tải 2,5 GB là đúng lỗi cũ
    chỉ đổi chiều (trước: nút ghi 155 MB, hộp doạ 2 GB).
 5. `_MA_TACH` phải giữ nhánh tự chọn thiết bị và **KHÔNG được ép cứng** một
    thiết bị nào — ép "cuda" là máy nhân viên không GPU nổ giữa mẻ 300 video.

    .venv\\Scripts\\python -u _test_demucs_gpu.py
"""
from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

DAT = 0
HONG = 0
_HONG: list[str] = []


def ok(dk: bool, ten: str, ghi: str = "") -> None:
    global DAT, HONG
    if dk:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {ghi}" if ghi else ""))
    else:
        HONG += 1
        _HONG.append(ten)
        print(f"  HỎNG {ten}" + (f" — {ghi}" if ghi else ""))


def _than(fn) -> ast.AST:
    """AST của thân hàm — quét bằng AST chứ KHÔNG bằng chuỗi.

    Bài học cổng 56d/64: quét chuỗi thì phép phá chỉ cần giữ nguyên mặt chữ mà
    đổi ý nghĩa (`che_chu=False` vẫn khớp `che_chu=`), và chính DÒNG GHI CHÚ
    giải thích bản vá lại bị kể là vi phạm (cổng 47/51 đỏ oan).

    HAI BẪY ĐÃ SẬP NGAY KHI VIẾT HÀM NÀY, cả hai đều là lỗi CỦA CỔNG:
    (a) `inspect.getsource` mở file theo bảng mã MẶC ĐỊNH của máy (cp1252 ở
        đây) -> docstring tiếng Việt ra mojibake rồi `ast.parse` nổ. Nay đọc
        thẳng file bằng **utf-8**.
    (b) tự cắt 4 khoảng trắng đầu dòng để bỏ thụt lề thì cắt luôn vào THÂN
        DOCSTRING nhiều dòng -> `IndentationError`. Nay KHÔNG cắt gì: phân
        tích CẢ FILE rồi lấy đúng nút `FunctionDef` theo tên.
    """
    mod = ast.parse(Path(inspect.getsourcefile(fn)).read_text(encoding="utf-8"))
    ten = fn.__name__
    for n in ast.walk(mod):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and n.name == ten:
            return n
    raise AssertionError(f"KHONG TIM THAY ham {ten} — lỗi CỦA PHÉP THỬ")


def ca1_do_gpu_an_toan() -> None:
    print("\nCA 1 — DÒ GPU PHẢI AN TOÀN (không ném, không import torch)")
    from app.core import thay_giong as TG

    try:
        v = TG.co_gpu_nvidia()
        no = False
    except Exception as e:  # noqa: BLE001
        v, no = f"NÉM {e}", True
    ok(not no and isinstance(v, bool), "1a co_gpu_nvidia() trả bool, KHÔNG ném",
       f"{v}")

    cay = _than(TG.co_gpu_nvidia)
    ten_import = {n.names[0].name.split(".")[0]
                  for n in ast.walk(cay) if isinstance(n, ast.Import)}
    ten_import |= {(n.module or "").split(".")[0]
                   for n in ast.walk(cay) if isinstance(n, ast.ImportFrom)}
    ok("torch" not in ten_import,
       "1b KHÔNG import torch (tiến trình app đã nạp Qt -> ACCESS VIOLATION)",
       f"import thấy: {sorted(x for x in ten_import if x)}")

    # TỰ KIỂM BỘ DÒ: nó phải BẮT được một hàm CÓ import torch, không thì mục
    # 1b là con dấu.
    def _moi_dut() -> bool:
        import torch
        return bool(torch)

    c2 = _than(_moi_dut)
    thay = {n.names[0].name for n in ast.walk(c2) if isinstance(n, ast.Import)}
    ok("torch" in thay, "1c TỰ KIỂM: bộ dò BẮT được hàm có import torch")


def ca2_chi_muc_theo_gpu() -> None:
    print("\nCA 2 — CHỈ MỤC PIP DO MÁY QUYẾT ĐỊNH, KHÔNG PHẢI HẰNG SỐ")
    from app.core import thay_giong as TG

    cay = _than(TG.cai_demucs)
    goi = {n.func.id for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    ok("co_gpu_nvidia" in goi,
       "2a `cai_demucs` GỌI THẬT co_gpu_nvidia() (không ghi cứng chỉ mục)",
       f"gọi: {sorted(goi)[:6]}")

    # `--extra-index-url` phải đi kèm một BIẾN, không phải chuỗi hằng.
    hang = []
    for n in ast.walk(cay):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) \
                and "download.pytorch.org/whl/" in n.value:
            hang.append(n.value)
    ok(not hang,
       "2b thân `cai_demucs` KHÔNG còn chuỗi chỉ mục ghi cứng",
       f"còn: {hang}" if hang else "sạch")
    ok(TG.CHI_MUC_TORCH_CUDA.endswith("/cu126")
       and TG.CHI_MUC_TORCH_CPU.endswith("/cpu"),
       "2c hai hằng chỉ mục trỏ đúng chỗ",
       f"{TG.CHI_MUC_TORCH_CUDA} · {TG.CHI_MUC_TORCH_CPU}")


def ca3_chay_that_hai_ca() -> None:
    """GỌI THẬT `cai_demucs`, chặn ở ranh giới `subprocess` -> 0 byte tải về.

    Vá `subprocess.Popen` (đúng RANH GIỚI MẠNG/tiến trình) chứ không vá
    `cai_demucs`, để toàn bộ phần quyết định chỉ mục vẫn là mã THẬT.
    """
    print("\nCA 3 — CHẠY THẬT: CÓ GPU -> CUDA · KHÔNG GPU -> CPU")
    import subprocess as SP

    from app.core import thay_giong as TG

    bat: dict[str, list] = {}

    class _Gia:
        def __init__(self, args, **kw):
            bat["args"] = list(args)
            self.stdout = iter(("Collecting torch", "Successfully installed"))

        def wait(self, timeout=None):
            return 0

        def kill(self):
            pass

    g_popen, g_gpu = SP.Popen, TG.co_gpu_nvidia
    g_gan, g_bo = TG._gan_job, TG._bo_gan_job
    g_do = TG.do_goi_tach_giong
    try:
        SP.Popen = _Gia
        TG._gan_job = lambda p: None
        TG._bo_gan_job = lambda p: None
        TG.do_goi_tach_giong = lambda lib: {g: {"lib": True}
                                            for g in TG.GOI_TACH_GIONG}
        for co_gpu, mong in ((True, "cu126"), (False, "cpu")):
            bat.clear()
            TG.co_gpu_nvidia = (lambda v: (lambda: v))(co_gpu)
            r = TG.cai_demucs()
            args = bat.get("args") or []
            i = args.index("--extra-index-url") if "--extra-index-url" in args else -1
            duoc = args[i + 1] if i >= 0 else "(KHÔNG CÓ)"
            ok(r.get("ok") is True and duoc.endswith("/" + mong),
               f"3{'a' if co_gpu else 'b'} máy "
               f"{'CÓ' if co_gpu else 'KHÔNG'} GPU -> chỉ mục {mong}",
               f"{duoc} · gpu={r.get('gpu')}")
            ok(r.get("gpu") is co_gpu,
               f"3{'a' if co_gpu else 'b'}' kết quả NÓI RA đã đi đường nào",
               f"gpu={r.get('gpu')}")
            # 0 byte tải: phép vá phải THẬT SỰ ăn, không thì cổng vừa đốt 2,5 GB
            ok(args and args[0] != "(chua chay)",
               f"3{'a' if co_gpu else 'b'}'' phép vá ĂN được (không tải thật)",
               f"{' '.join(args[-3:])[:60]}")
    finally:
        SP.Popen, TG.co_gpu_nvidia = g_popen, g_gpu
        TG._gan_job, TG._bo_gan_job = g_gan, g_bo
        TG.do_goi_tach_giong = g_do


def ca4_nhan_khop_duong_di() -> None:
    print("\nCA 4 — NHÃN PHẢI KHỚP DUNG LƯỢNG ĐƯỜNG SẼ ĐI")
    from app.core import thay_giong as TG

    g = TG.co_gpu_nvidia
    try:
        TG.co_gpu_nvidia = lambda: True
        n_gpu = TG.nhan_nut_tai({"thieu": []})
        TG.co_gpu_nvidia = lambda: False
        n_cpu = TG.nhan_nut_tai({"thieu": []})
    finally:
        TG.co_gpu_nvidia = g
    ok("2,5 GB" in n_gpu and "155 MB" not in n_gpu,
       "4a máy CÓ GPU -> nhãn nói 2,5 GB (không hứa 155 MB rồi tải 2,5 GB)",
       n_gpu)
    ok("155 MB" in n_cpu and "2,5 GB" not in n_cpu,
       "4b máy KHÔNG GPU -> nhãn giữ nguyên 155 MB", n_cpu)
    ok(n_gpu != n_cpu, "4c hai nhãn KHÁC NHAU (nhãn cố định = cái nhãn)")
    for n in (n_gpu, n_cpu):
        ok(all(ord(c) < 0x2190 for c in n),
           "4d nhãn KHÔNG EMOJI (máy anh Hùng thiếu glyph -> ô đen)", n[:40])


def ca5_runner_khong_ep_cung() -> None:
    print("\nCA 5 — RUNNER PHẢI TỰ CHỌN THIẾT BỊ, KHÔNG ÉP CỨNG")
    from app.core import thay_giong as TG

    ma = TG._MA_TACH
    ok("torch.cuda.is_available()" in ma,
       "5a runner còn nhánh tự dò `torch.cuda.is_available()`")
    ok('dev = "cuda" if' in ma and '"cpu"' in ma,
       "5b ... và vẫn có đường lui CPU (máy nhân viên KHÔNG có GPU)")
    ok('device=dev' in ma.replace(" ", ""),
       "5c thiết bị được TRUYỀN vào apply_model (không phải biến trang trí)")
    # Ép cứng 'cuda' là máy không GPU nổ giữa mẻ 300 video.
    ok('device="cuda"' not in ma.replace(" ", "").replace("'", '"')
       .replace('device="cuda"if', ""),
       "5d KHÔNG ép cứng device='cuda'")
    # Kết quả phải NÓI RA thiết bị thật — không nói thì không ai biết đang
    # chạy CPU (đúng cách anh Hùng phát hiện ra bệnh này).
    ok('"thiet_bi": dev' in ma,
       "5e kết quả trả về NÓI RA thiết bị thật đã chạy")


def main() -> int:
    print("=" * 74)
    print("CỔNG 71 — TÁCH GIỌNG DÙNG GPU KHI MÁY CÓ GPU")
    print("=" * 74)
    ca1_do_gpu_an_toan()
    ca2_chi_muc_theo_gpu()
    ca3_chay_that_hai_ca()
    ca4_nhan_khop_duong_di()
    ca5_runner_khong_ep_cung()
    print("\n" + "=" * 74)
    print(f"CỔNG 71 — ĐẠT {DAT} · HỎNG {HONG}")
    for d in _HONG:
        print(f"   HỎNG: {d}")
    print("=" * 74)
    return 1 if HONG else 0


if __name__ == "__main__":
    sys.exit(main())
