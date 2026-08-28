# -*- coding: utf-8 -*-
"""THỬ PHÁ CỔNG 89 — mỗi phép gỡ ĐÚNG MỘT chốt, cổng phải ĐỎ.

**CỔNG KHÔNG PHẢI CON DẤU.** Cổng 89 ra `ĐẠT 73 · HỎNG 0` chẳng chứng minh gì
nếu gỡ chốt ra mà nó vẫn xanh. File này gỡ từng chốt, chạy lại cổng, rồi PHỤC
HỒI nguyên trạng.

**BA LUẬT ĐÃ HỌC BẰNG MÁU, ĐỪNG VI PHẠM:**
 1. **"KHÔNG TÌM THẤY CHỖ PHÁ" ≠ "LỌT".** Bản đầu của `_pha_dubbing_cjk.py`
    đếm chúng vào cùng một cột nên **báo cáo NGƯỢC SỰ THẬT**: 4/6 phép im lặng
    không phá được gì mà bảng ghi là "cổng để lọt". Ở đây tách hẳn ba cột
    **BẮT · LỌT · KHÔNG PHÁ ĐƯỢC**.
 2. **NEO PHẢI DUY NHẤT** — kiểm `count()` TRƯỚC khi thay. Neo khớp 2 chỗ là
    phá cả hai, cổng đỏ vì lý do KHÁC cái đang thử.
 3. **PHÁ THÌ GỠ SẠCH CHỐT, đừng đổi giá trị bên trong nó.** Bài học cổng 80
    LỌT 7: phép phá đổi `goc` thành đường dẫn không bao giờ khớp, làm hàm
    CHẶT HƠN chứ không hở ra — cổng xanh là ĐÚNG, nhưng bảng đọc thành "cổng
    không bắt được".

Repo là **CRLF** nên file đọc/ghi bằng `newline=""` để không đổi cả dòng kết
thúc của file người khác đang sửa (neo vì thế chỉ dùng MỘT dòng).

    .venv\\Scripts\\python -u _pha_khop_video.py [số phép]
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:  # noqa: BLE001
        pass

PY = str(REPO / ".venv" / "Scripts" / "python.exe")
TG = REPO / "app" / "core" / "thay_giong.py"
TC = REPO / "app" / "core" / "tg_chay.py"
JB = REPO / "app" / "queue" / "jobs.py"

#: Chạy ĐÚNG các mục liên quan thay vì cả cổng: cả cổng ~3 phút × 9 phép là 27
#: phút, mà mục 1/2/3/5 (độ to + hộp thoại) không dính bản vá này.
_RUNNER = r"""
import sys, os
sys.path.insert(0, r"{repo}")
import _test_am_va_hinh as G
G.don()
try:
    for t in "{muc}".split(","):
        getattr(G, "muc" + t)()
finally:
    print("KETQUA ĐẠT %d HỎNG %d" % (G.DAT, G.HONG))
    G.don()
sys.exit(0 if G.HONG == 0 else 1)
"""

#: (tên, file, neo, thay bằng, mục cần chạy, chốt đang gỡ là gì)
PHEP = [
    ("1. trả `-itsscale` về nhánh CHE CHỮ (đúng bản cũ)", TG,
     '    _ffmpeg(["-i", str(video_goc), "-i", str(audio_moi),',
     '    _ffmpeg([*its, "-i", str(video_goc), "-i", str(audio_moi),',
     "6", "hộp che phải đọc mốc NGUỒN"),

    ("2. GỠ HẲN `setpts` khỏi chuỗi filter", TG,
     '        chuoi.append(f"setpts=PTS*{k:.6f}")',
     '        pass  # PHA: gỡ setpts',
     "6", "phép giãn phải nằm trong chuỗi filter"),

    ("3. ĐẢO THỨ TỰ: `setpts` TRƯỚC khối che", TG,
     "    chuoi = [loc]",
     '    chuoi = ([f"setpts=PTS*{k:.6f}"] if k > 1.0 + 1e-6 else []) + [loc]',
     "6", "thứ tự che -> setpts -> phụ đề"),

    ("4. GỠ TRẦN theo fps (trả thẳng trần cứng)", TG,
     "    return max(1.0, min(TRAN_CHINH_HINH, fps / SAN_NHIP_HINH_FPS))",
     "    return 99.0  # PHA: gỡ trần",
     "4,8", "trần làm chậm hình theo nhịp hình còn lại"),

    ("5. `khop_thoi_gian` KHÔNG nhân hệ số vào mốc câu", TG,
     '        a = float(c["start"]) * k',
     '        a = float(c["start"])  # PHA',
     "4,8", "mốc câu phải giãn theo k để tempo về 1,0"),

    ("6. GỠ khoá `cham_tran` khỏi nhật ký (lùi IM LẶNG)", TG,
     '                "cham_tran": float(_c["k_can"]) > _tran + 1e-6,',
     '                "da_kep": float(_c["k_can"]) > _tran + 1e-6,',
     "8", "lùi về cách cũ thì phải GHI LOG"),

    # NEO PHẢI HAI DÒNG: `if hinh_theo_giong:` khớp **2 chỗ** (một ở
    # `khoa_chong_trung`, một ở `xep_mot`) -> neo một dòng là phá cả hai và
    # cổng đỏ vì lý do KHÁC cái đang thử. Đã kiểm `count()` trước, đúng luật 2.
    ("7. nối `htg` VÔ ĐIỀU KIỆN (đổi hash MỌI job cũ)", TC,
     '    if hinh_theo_giong:\n        sig += ":htg=1"',
     '    if True:  # PHA\n        sig += ":htg=1"',
     "7", "cờ chỉ vào hash KHI THẬT SỰ BẬT"),

    ("8. nối `htg` vào GIỮA chuỗi sig thay vì ĐUÔI", TC,
     '    sig = f"thaygiong:{d}:{dich_sang}:{voice}:{r}"',
     '    sig = f"thaygiong:{d}:{dich_sang}:{voice}:'
     '{\'htg=1:\' if hinh_theo_giong else \'\'}{r}"',
     "7", "đuôi nối vào CUỐI, khoá cũ là TIỀN TỐ"),

    ("9. payload ghi khoá `hinh_theo_giong` VÔ ĐIỀU KIỆN", TC,
     '    if hinh_theo_giong:\n        tt["hinh_theo_giong"] = True',
     '    if True:\n        tt["hinh_theo_giong"] = bool(hinh_theo_giong)',
     "7", "ô để mặc định thì KHÔNG sinh khoá trong payload"),

    # ───────── ĐỌC ĐỀU (bỏ bước 4c) — 5 chốt mới của MỤC 9 ─────────
    ("10. nối `dd` VÔ ĐIỀU KIỆN (đổi hash mọi job đã chỉnh hình)", TC,
     '        if doc_deu:\n            sig += ":dd=1"',
     '        sig += ":dd=1"  # PHA: vô điều kiện',
     "9", "cờ chỉ vào hash KHI THẬT SỰ BẬT"),

    ("11. nối `dd` vào GIỮA chuỗi sig thay vì ĐUÔI", TC,
     '    sig = f"thaygiong:{d}:{dich_sang}:{voice}:{r}"',
     '    sig = f"thaygiong:{d}:{dich_sang}:{voice}:'
     '{\'dd=1:\' if doc_deu else \'\'}{r}"',
     "9", "đuôi nối vào CUỐI, khoá cũ là TIỀN TỐ"),

    ("12. GỠ chốt `and hinh_theo_giong` (bỏ 4c mà không chậm hình)", TG,
     "        _deu = bool(doc_deu) and bool(hinh_theo_giong)",
     "        _deu = bool(doc_deu)  # PHA: gỡ chốt",
     "9", "bỏ 4c chỉ được phép khi ĐANG làm chậm hình"),

    ("13. `chuan_khop_cach` nhận rác thành cách MỚI (lùi sai chiều)", TG,
     "    if c not in KHOP_CACH:\n        return (False, False)",
     "    if c not in KHOP_CACH:\n        return (True, True)  # PHA",
     "9", "không nhận ra -> lùi về hành vi CŨ, không về cách mới"),

    ("14. `thay_giong_mot_video` QUÊN chuyền `doc_deu` xuống lõi", TG,
     "                         doc_deu=doc_deu,",
     "                         # PHA: quên chuyền doc_deu",
     "9", "hàm xong ≠ tính năng xong — cờ phải đi hết chặng"),

    # ───────── KÉO DÀI GIỌNG CHO ĐẦY KHUNG (MỤC 10) — 11 chốt mới ─────────
    # LUẬT 3 áp cho cả nhóm: mọi phép dưới đây **GỠ SẠCH** chốt (thay bằng
    # `if False` / hằng số TẮT / xoá dòng), KHÔNG chỉnh tham số cho nó chặt
    # hơn — chặt hơn thì cổng xanh ĐÚNG mà bảng đọc thành "không bắt được".
    ("15. `_keo` không đọc tham số (cờ chết ngay ở lõi)", TG,
     "        _keo = max(1.0, min(float(keo_dai_giong or 1.0), "
     "BANG_RATE_AM[-1][0]))",
     "        _keo = 1.0  # PHA: cờ không tới được bước 4c",
     "10", "cờ phải đi hết chặng tới máy đọc"),

    ("16. GỠ HẲN nhánh (1b) kéo dài trong `khop_thoi_gian`", TG,
     "            if keo > 1.0:",
     "            if False:  # PHA: gỡ nhánh kéo dài",
     "10", "nhánh 'lọt khung sẵn' chính là chỗ sinh ra khoảng im"),

    ("17. GỠ chốt SÀN `DAI_CAU_TOI_THIEU` (dựng lại DẢI CHẾT)", TG,
     "        if d_nat < DAI_CAU_TOI_THIEU:",
     "        if d_nat <= 0:  # PHA: dải chết 0..0,05 s như bản cũ",
     "10", "sàn phải BẰNG sàn của `_kiem_wav`, không phải 0"),

    ("18. GỠ chốt NGUỒN HỎNG khỏi `cat_le_im_moc`", TG,
     "    if not _co or probe_duration(src) <= 0:",
     "    if False:  # PHA: đưa file 0 byte thẳng cho ffmpeg",
     "10", "file hỏng không được đưa cho ffmpeg (nó NÉM, giết cả video)"),

    ("19. `rate_am_cho` cho phép VƯỢT hệ số xin", TG,
     "        if muc[0] <= float(he_so) + 1e-9:",
     "        if muc[0] <= float(he_so) * 2:  # PHA",
     "10", "đọc chậm quá khung là phải CẮT ĐUÔI = mất chữ"),

    ("20. `chuan_keo_dai` nhận rác/NaN/số âm thành mức kéo", TG,
     "    if not (v == v) or v <= 1.0 + 1e-9:      # NaN cũng rơi vào đây",
     "    if False:  # PHA: gỡ chốt rác",
     "10", "rác/None/NaN -> 1,0 = TẮT"),

    ("21. `thay_giong_mot_video` QUÊN chuyền `keo_dai_giong`", TG,
     "                         keo_dai_giong=keo_dai_giong,",
     "                         # PHA: quên chuyền keo_dai_giong",
     "10", "đúng cửa v2.45.0 đã sót -> anh Hùng bấm Chạy, 4/4 video LỖI"),

    ("22. nối `kd` VÔ ĐIỀU KIỆN (đổi hash MỌI job cũ)", TC,
     "    if _kd > 1.0:",
     "    if True:  # PHA: vô điều kiện",
     "10", "cờ chỉ vào hash KHI THẬT SỰ BẬT"),

    ("23. nối `kd` vào GIỮA chuỗi sig thay vì ĐUÔI", TC,
     '    sig = f"thaygiong:{d}:{dich_sang}:{voice}:{r}"',
     '    sig = f"thaygiong:{d}:{dich_sang}:{voice}:'
     '{\'kd=1:\' if keo_dai_giong else \'\'}{r}"',
     "10", "đuôi nối vào CUỐI, khoá cũ là TIỀN TỐ"),

    ("24. payload ghi khoá `keo_dai_giong` VÔ ĐIỀU KIỆN", TC,
     '    if kd > 1.0:\n        tt["keo_dai_giong"] = kd',
     '    if True:  # PHA\n        tt["keo_dai_giong"] = kd',
     "10", "ô để mặc định thì KHÔNG sinh khoá trong payload"),

    ("25. `jobs._thay_giong` đọc payload THÔ (bỏ `chuan_keo_dai`)", JB,
     '            keo_dai_giong=tg.chuan_keo_dai('
     'payload.get("keo_dai_giong")),',
     '            keo_dai_giong=payload.get("keo_dai_giong"),  # PHA',
     "10", "payload mang rác được — hệ số bịa nhân vào ĐỘ DÀI TIẾNG"),

    # ─────────── BƯỚC 4b' VIẾT ĐẦY (mục 11) ───────────
    ("26. GỠ HẲN cửa nghĩa — nhận bản đầy mà KHÔNG chấm", TG,
     "        if b < VIET_DAY_SAN_TRUNG_THANH or b < a - VIET_DAY_BIEN_TUT:",
     "        if False:  # PHA: gỡ hẳn cửa chấm nghĩa",
     "11", "chống BỊA — anh Hùng đòi ĐÚNG nằm trong bốn chữ"),

    ("27. KHÔNG chấm được vẫn NHẬN (fail-safe lộn chiều)", TG,
     "            kq[\"so_bo_vi_khong_cham\"] += 1  # không chấm được = KHÔNG NHẬN\n"
     "            continue",
     "            kq[\"so_bo_vi_khong_cham\"] += 1\n"
     "            giu.append(j)  # PHA: không có căn cứ vẫn nhận\n"
     "            continue",
     "11", "không có căn cứ thì GIỮ BẢN CŨ, không phải nhận bừa"),

    ("28. `them=true` (model nói thẳng là BỊA) KHÔNG bị ép trượt", TG,
     "            if bool(o.get(\"them\")):\n                b = 0.0",
     "            if False:  # PHA: bỏ cờ bịa\n                b = 0.0",
     "11", "điểm là số TRUNG BÌNH — câu bịa mà văn hay vẫn được 4"),

    ("29. GỠ TRẦN NỚI — xin bao nhiêu chữ cũng được", TG,
     "        toi_da = max(n + 1, min(dich_kt, int(n * tran_noi)))",
     "        toi_da = max(n + 1, dich_kt)  # PHA: gỡ trần nới",
     "11", "quá trần thì để im còn hơn bịa"),

    ("30. nhận bản đầy dù đọc lên KHÔNG dài hơn", TG,
     "        if d_moi <= m[\"d_nat\"] + 0.05:",
     "        if False:  # PHA: nhận cả bản ngắn hơn",
     "11", "đối xứng luật 4b — chỉ nhận khi ĐI ĐÚNG HƯỚNG thật"),

    ("31. nhận bản đầy dù TRÀN khung", TG,
     "        if d_moi > m[\"khung\"]:",
     "        if False:  # PHA: cho tràn khung",
     "11", "biến câu hụt thành câu tràn = kéo `atempo` vào chỗ vừa dọn"),

    ("32. `viet_day_vua_khung` chạy VÔ ĐIỀU KIỆN (bỏ `if viet_day`)", TG,
     "        if viet_day:\n            prog(0.775, \"Viết đầy câu hụt khung...\")",
     "        if True:  # PHA: chạy cả khi TẮT\n"
     "            prog(0.775, \"Viết đầy câu hụt khung...\")",
     "11", "TẮT là KHÔNG một lượt LLM nào thêm cho 200-300 kênh"),

    ("33. `thay_giong_mot_video` QUÊN chuyền `viet_day`", TG,
     "                         viet_day=viet_day,",
     "                         # PHA: quên chuyền viet_day",
     "11", "cửa NGOÀI CÙNG — đúng chỗ v2.45.0 sót, 4/4 video LỖI"),

    ("34. nối `vd` VÔ ĐIỀU KIỆN (đổi hash MỌI job cũ)", TC,
     "    if viet_day:\n        sig += \":vd=1\"",
     "    if True:  # PHA\n        sig += \":vd=1\"",
     "11", "cờ chỉ vào hash KHI THẬT SỰ BẬT"),

    ("35. model CHẤM nghĩa = model DỊCH (tự chấm bài mình)", TG,
     'MODEL_CHAM_VIET_DAY = "qwen/qwen3.8-27b"',
     "MODEL_CHAM_VIET_DAY = settings.GROQ_LLM_MODEL  # PHA",
     "11", "phép đo phát chứng nhận — họ bẫy `astats` cổng 53"),

    # PHÉP NÀY PHẢI PHÁ "MỀM", KHÔNG ĐƯỢC LÀM HÀM NỔ. Bản đầu thay guard bằng
    # `continue` -> `int("abc")` ném `ValueError` -> cổng CHẾT giữa chừng
    # (`ĐẠT 5 HỎNG 0`, mã 1) và bảng ghi "BẮT" cho một mục CHƯA HỀ chạy. Đó là
    # đúng cái `compile()` không bắt được, và là họ bẫy đã ghi ở đầu file.
    ("36. `_mang_hoac_mot` nới quá tay: dict LẠ cũng thành bản ghi", TG,
     "        if not isinstance(v, dict) or not str(k).strip().lstrip"
     "(\"-\").isdigit():\n            return []",
     "        if not isinstance(v, dict):  # PHA: bỏ chốt khoá-phải-là-số\n"
     "            return []\n"
     "        if not str(k).strip().lstrip(\"-\").isdigit():\n"
     "            k = 0",
     "11", "nới quá tay là bộ dò mất răng, fail-safe ở đây là KHÔNG NHẬN"),
]

BAT: list[str] = []
LOT: list[str] = []
KHONG_PHA: list[str] = []


def _doc(p: Path) -> str:
    with open(p, "r", encoding="utf-8", newline="") as f:
        return f.read()


def _ghi(p: Path, s: str) -> None:
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def chay_cong(muc: str) -> tuple[int, str]:
    ma = _RUNNER.format(repo=str(REPO), muc=muc)
    t0 = time.time()
    r = subprocess.run([PY, "-u", "-c", ma], cwd=str(REPO),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8",
                            "PYTHONUTF8": "1", "BQ_FFMPEG_SLOTS": "1"},
                       timeout=1800)
    ra = (r.stdout or "") + (r.stderr or "")
    tk = [x for x in ra.splitlines() if x.startswith("KETQUA")]
    hong = [x for x in ra.splitlines() if x.strip().startswith("HỎNG")]
    return r.returncode, (f"{time.time() - t0:.0f}s · "
                          f"{tk[-1] if tk else 'KHÔNG có dòng tổng kết'}"
                          + (f" · đỏ: {hong[0].strip()[:78]}" if hong else ""))


def mot_phep(ten: str, f: Path, neo: str, thay: str, muc: str,
             chot: str) -> None:
    print(f"\n{'=' * 74}\n[PHÁ] {ten}\n  chốt đang gỡ: {chot}")
    goc = _doc(f)
    # neo trong file là CRLF nên neo nhiều dòng phải đổi `\n` -> `\r\n`
    neo_f = neo.replace("\n", "\r\n") if "\r\n" in goc else neo
    thay_f = thay.replace("\n", "\r\n") if "\r\n" in goc else thay
    n = goc.count(neo_f)
    if n != 1:
        KHONG_PHA.append(f"{ten} (neo khớp {n} chỗ, cần ĐÚNG 1)")
        print(f"  KHÔNG PHÁ ĐƯỢC — neo khớp {n} chỗ trong {f.name}, cần ĐÚNG 1."
              f"\n  (đây là LỖI CỦA PHÉP THỬ, KHÔNG phải cổng để lọt)")
        return
    pha = goc.replace(neo_f, thay_f, 1)
    # **`compile()` LẠI BẢN ĐÃ PHÁ** — bài học `_pha_doc_lan.py`: bản phá không
    # biên dịch được thì cổng chết ngay lúc `import`, mã thoát 1, và bảng ghi
    # "BẮT" cho một chốt mà phép thử CHƯA HỀ chạm tới. Đó là phép thử tự phát
    # chứng nhận cho chính mình — cùng họ bẫy `astats` (cổng 53).
    try:
        compile(pha, str(f), "exec")
    except SyntaxError as e:
        KHONG_PHA.append(f"{ten} (bản phá KHÔNG biên dịch được: {e})")
        print(f"  KHÔNG PHÁ ĐƯỢC — bản đã phá lỗi cú pháp ({e}).\n"
              f"  (đây là LỖI CỦA PHÉP THỬ, KHÔNG phải cổng bắt được)")
        return
    try:
        _ghi(f, pha)
        rc, tt = chay_cong(muc)
        if rc != 0:
            BAT.append(ten)
            print(f"  BẮT ĐƯỢC (cổng ĐỎ, mã {rc}) — {tt}")
        else:
            LOT.append(ten)
            print(f"  *** LỌT *** cổng vẫn XANH — {tt}")
    finally:
        _ghi(f, goc)
        print(f"  đã phục hồi {f.name}")


def main() -> int:
    so = int(sys.argv[1]) if len(sys.argv) > 1 else len(PHEP)
    print(f"THỬ PHÁ CỔNG 89 — {min(so, len(PHEP))} phép\n"
          f"Mốc trước khi phá: chạy cổng đầy đủ phải ra ĐẠT 104 · HỎNG 0")
    rc0, tt0 = chay_cong("1,2,3,4,5,6,7,8,9")
    print(f"  ĐỐI CHỨNG (chưa phá): mã {rc0} — {tt0}")
    if rc0 != 0:
        print("  !!! CỔNG ĐÃ ĐỎ TRƯỚC KHI PHÁ — dừng, không đọc được bảng nào")
        return 2
    for p in PHEP[:so]:
        mot_phep(*p)
    print(f"\n{'=' * 74}\nTỔNG: BẮT {len(BAT)} · LỌT {len(LOT)} · "
          f"KHÔNG PHÁ ĐƯỢC {len(KHONG_PHA)}")
    for x in LOT:
        print(f"  LỌT: {x}")
    for x in KHONG_PHA:
        print(f"  KHÔNG PHÁ ĐƯỢC: {x}")
    return 0 if not LOT else 1


if __name__ == "__main__":
    sys.exit(main())
