# -*- coding: utf-8 -*-
"""CỔNG 75 — **CLIP XUẤT RA PHẢI MỞ ĐƯỢC** (18/08/2026).

LỖI THẬT anh Hùng gửi ảnh trình phát Windows:

    We can't open "Part 1 Turning My Challenger Into a Beast – Full Power! …"
    It uses unsupported encoding settings.  0x80004005

nguyên văn: *"khi phân tích cắt các part cứ báo lỗi, video bị trắng, mở ra cứ
báo cái lỗi này"*.

GỐC RỄ: `ffmpeg_utils._enc_args` — hàm sinh tham số encode cho **FILE THÀNH
PHẨM** — có `-pix_fmt yuv420p` ở nhánh `h264_nvenc` nhưng nhánh `libx264` thì
**KHÔNG**. Thiếu nó thì x264 lấy pix_fmt theo ĐẦU RA FILTER GRAPH, mà graph lấy
theo NGUỒN:

    nguồn yuv420p 8-bit -> yuv420p     -> High                  -> mở được
    nguồn 10-bit        -> yuv420p10le -> **High 10**           -> TỪ CHỐI
    nguồn 4:4:4         -> yuv444p     -> **High 4:4:4 Predictive** -> TỪ CHỐI

Trình phát dựng sẵn của Windows KHÔNG giải mã được High 10 / High 4:4:4 — đúng
lời lỗi `0x80004005` **và** đúng triệu chứng KHUNG TRẮNG. Mà ffmpeg vẫn **mã
thoát 0**, đủ khung, đủ `moov`, file to bình thường -> **không một cổng nào cũ
bắt được**. Đây là họ bẫy nặng nhất của repo này: *thành công giả*.

VÌ SAO CHỈ HỎNG THỈNH THOẢNG (khớp ảnh anh Hùng: Part này mở được Part kia
không): chỉ những lượt **LÙI VỀ libx264** mới ra file hỏng —
`_run_with_fallback` lùi khi NVENC lỗi (hết session NVENC, driver, hoặc máy
nhân viên không có GPU).

Đây là ANH EM của lỗi đã vá ở `_enc_mezz` (cổng 42): hôm đó vá đúng MỘT hàm,
còn `_enc_args` — hàm sinh ra file người dùng bấm mở — thì bị bỏ sót.

════════════════════════════════════════════════════════════════════════════
CỔNG NÀY **TỰ KIỂM** (mục 7): nó dựng một bản `ffmpeg_utils` **ĐÃ GỠ CHỐT**
`yuv420p` rồi đòi:
  (a) bộ dò tham số phải kêu, VÀ
  (b) chạy ffmpeg THẬT trên nguồn **10-bit** bằng bản gỡ chốt phải ra file
      **KHÔNG PHẢI yuv420p**.
Tức nó chứng minh cả hai vế: chốt đang có mặt, VÀ gỡ chốt ra là ra đúng cái
file hỏng anh Hùng gặp. Không có (b) thì mục này chỉ là con dấu — bài học cổng
56d (quét chuỗi "có mặt không" thì luôn có phép phá giữ nguyên mặt chữ).

KHÔNG ĐẾM ĐIỂM ẢNH ĐỂ KẾT LUẬN VỀ HÌNH: mục 5 trích khung ra PNG và ghi đường
dẫn để NGƯỜI TỰ MỞ RA NHÌN (bài học tofu: 2.431 px vs chữ thật 517 px = ngược
4,7 lần). Cổng chỉ chấm những thứ đếm được: khung không đơn sắc, giải mã đủ
khung, không có khung lỗi.

    .venv\\Scripts\\python -u _test_clip_mo_duoc.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import types
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

import _test_guard  # noqa: E402,F401  (utf-8 + cấm mở cửa sổ trên máy user)

FFMPEG = str(REPO / "bin" / "ffmpeg.exe")
FFPROBE = str(REPO / "bin" / "ffprobe.exe")
_CNW = 0x08000000 if os.name == "nt" else 0

DAT = 0
HONG = 0
_LOI: list[str] = []


def ok(dieu: bool, nhan: str, chi_tiet: str = "") -> bool:
    global DAT, HONG
    if dieu:
        DAT += 1
        print(f"  ĐẠT  {nhan}" + (f" — {chi_tiet}" if chi_tiet else ""))
    else:
        HONG += 1
        _LOI.append(nhan)
        print(f"  HỎNG {nhan}" + (f" — {chi_tiet}" if chi_tiet else ""))
    return dieu


# ════════════════════════════════════════════════════════════════════════════
#  Dụng cụ đo — mỗi cái trả SỐ THẬT, hỏng thì NÉM (không trả None âm thầm:
#  bài học `astats` cổng 53 · `startswith` cổng 44 — phép đo hỏng nguy hiểm
#  hơn không đo, vì nó phát chứng nhận).
# ════════════════════════════════════════════════════════════════════════════
def soi(path: str | Path) -> dict:
    """`ffprobe` đầy đủ những gì trình phát quan tâm."""
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_streams",
         "-show_format", "-print_format", "json", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120, creationflags=_CNW)
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe mã {r.returncode}: {(r.stderr or '')[-300:]}")
    d = json.loads(r.stdout or "{}")
    st = (d.get("streams") or [{}])[0]
    fm = d.get("format") or {}
    return {
        "codec": st.get("codec_name", ""),
        "profile": st.get("profile", ""),
        "level": st.get("level", 0),
        "pix_fmt": st.get("pix_fmt", ""),
        "w": int(st.get("width") or 0),
        "h": int(st.get("height") or 0),
        "fps": st.get("r_frame_rate", ""),
        "nb_frames": int(st.get("nb_frames") or 0),
        "dur": float(fm.get("duration") or st.get("duration") or 0.0),
        "size": int(fm.get("size") or 0),
    }


def co_tieng(path: str | Path) -> bool:
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "a",
                        "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                        str(path)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=60, creationflags=_CNW)
    return "audio" in (r.stdout or "")


def hop_mp4(path: str | Path) -> list[str]:
    """Danh sách BOX cấp cao nhất của mp4 — để trả lời "có `moov` không".

    Đọc thẳng cấu trúc box, KHÔNG hỏi ffprobe: ffprobe mà đọc được file thì
    hiển nhiên đã thấy `moov`, nên dùng nó để kiểm `moov` là hỏi vòng.
    `+faststart` còn đòi `moov` nằm TRƯỚC `mdat` (phát dần được).
    """
    ten: list[str] = []
    with open(path, "rb") as f:
        while True:
            hd = f.read(8)
            if len(hd) < 8:
                break
            sz = struct.unpack(">I", hd[:4])[0]
            nm = hd[4:8].decode("latin-1", "replace")
            ten.append(nm)
            if sz == 1:                      # 64-bit largesize
                sz = struct.unpack(">Q", f.read(8))[0]
                f.seek(sz - 16, os.SEEK_CUR)
            elif sz == 0:                    # tới hết file
                break
            else:
                f.seek(sz - 8, os.SEEK_CUR)
    return ten


def giai_ma_het(path: str | Path) -> tuple[int, str]:
    """GIẢI MÃ TỪNG KHUNG tới hết file. Trả (số khung đọc được, log lỗi).

    Đây là phép kiểm "mở được không" ĐÚNG NGHĨA và **thay cho `ffplay`** —
    tuyệt đối KHÔNG mở trình phát trên máy anh Hùng. Mã thoát 0 KHÔNG ĐỦ:
    đã đo được ca ffmpeg trả 0 mà file 0 KiB.
    """
    r = subprocess.run(
        [FFMPEG, "-hide_banner", "-nostdin", "-v", "error",
         "-i", str(path), "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=600, creationflags=_CNW)
    loi = (r.stderr or "").strip()
    r2 = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "v:0", "-count_frames",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=600, creationflags=_CNW)
    s = (r2.stdout or "").strip()
    return (int(s) if s.isdigit() else 0), loi


def do_khung(path: str | Path, giay: float, ra_png: Path) -> dict:
    """Trích 1 khung ra PNG rồi đo: đơn sắc chưa? trắng chưa? sáng bao nhiêu?

    "Hình trắng" là triệu chứng anh Hùng nêu, nên phải đo được nó. Dùng
    `signalstats` của chính ffmpeg (YMIN/YMAX/YAVG) — khung TRẮNG TRƠN thì
    YMIN==YMAX và YAVG sát 255; khung ĐEN thì YAVG ~0.
    """
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-v", "error", "-nostdin",
                    "-ss", f"{giay:.3f}", "-i", str(path), "-frames:v", "1",
                    str(ra_png)],
                   capture_output=True, timeout=180, creationflags=_CNW)
    r = subprocess.run(
        [FFMPEG, "-hide_banner", "-nostdin", "-ss", f"{giay:.3f}",
         "-i", str(path), "-frames:v", "1",
         "-vf", "signalstats,metadata=print", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=180, creationflags=_CNW)
    t = (r.stderr or "")

    def lay(k: str) -> float:
        m = re.search(rf"lavfi\.signalstats\.{k}=(-?[\d.]+)", t)
        return float(m.group(1)) if m else -1.0

    ymin, ymax, yavg = lay("YMIN"), lay("YMAX"), lay("YAVG")
    return {"YMIN": ymin, "YMAX": ymax, "YAVG": yavg,
            "don_sac": ymin >= 0 and ymin == ymax,
            "png": str(ra_png), "png_co": (ra_png.stat().st_size
                                           if ra_png.exists() else 0)}


def nguon_10bit(dst: Path, giay: float = 6.0) -> Path:
    """Sinh nguồn **10-bit** (`yuv420p10le`) bằng `lavfi` — không phụ thuộc
    file trên máy.

    Vì sao phải có nguồn 10-bit: kho video của anh Hùng HÔM NAY toàn 8-bit
    (đã quét 400 nguồn: 100% `yuv420p`), nên trên kho đó thiếu `-pix_fmt` cũng
    chưa lộ. Nhưng yt-dlp lấy `bestvideo` trên YouTube thì gặp VP9 Profile 2 /
    AV1 HDR là 10-bit. Cổng phải chứng minh được ca ĐÓ, không chỉ ca may mắn.
    """
    subprocess.run(
        [FFMPEG, "-y", "-hide_banner", "-v", "error", "-nostdin",
         "-f", "lavfi", "-i", f"testsrc2=s=640x360:r=25:d={giay:g}",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={giay:g}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p10le", "-profile:v", "high10",
         "-crf", "20", "-c:a", "aac", "-shortest", str(dst)],
        capture_output=True, timeout=300, creationflags=_CNW)
    return dst


def nap_ban_pha(bo_chot: bool) -> types.ModuleType:
    """Nạp `app.core.ffmpeg_utils` thành module RIÊNG, tuỳ chọn GỠ CHỐT
    `-pix_fmt yuv420p` khỏi nhánh `libx264` của `_enc_args` (= bản v2.36.0).

    Đây là phép THỬ PHÁ: nó dựng lại đúng con bệnh rồi bắt cổng phải kêu.
    """
    src = (REPO / "app" / "core" / "ffmpeg_utils.py").read_text(encoding="utf-8")
    if bo_chot:
        cu = ('return ["-c:v", "libx264", "-preset", "veryfast", "-crf", crf,\n'
              '            "-pix_fmt", "yuv420p", "-profile:v", "high",\n'
              '            "-threads", str(encode_threads())]')
        moi = ('return ["-c:v", "libx264", "-preset", "veryfast", "-crf", crf,\n'
               '            "-threads", str(encode_threads())]')
        if cu not in src:
            raise RuntimeError(
                "KHÔNG TÌM THẤY CHỖ PHÁ trong `_enc_args` — phép thử phá "
                "không chạm được vào mã. Đây là LỖI CỦA PHÉP THỬ, không phải "
                "bằng chứng app đúng (bài học cổng 54: CRLF làm 4/6 phép phá "
                "im lặng không phá được gì mà còn bị đếm vào cột LỌT).")
        src = src.replace(cu, moi, 1)
    mod = types.ModuleType("_fu_pha" if bo_chot else "_fu_that")
    mod.__file__ = str(REPO / "app" / "core" / "ffmpeg_utils.py")
    sys.modules[mod.__name__] = mod
    exec(compile(src, mod.__file__, "exec"), mod.__dict__)
    return mod


def co_chot(args: list[str]) -> bool:
    """BỘ DÒ: bộ tham số encode có ép `yuv420p` không (đúng cặp KỀ NHAU)."""
    for i in range(len(args) - 1):
        if args[i] == "-pix_fmt" and args[i + 1] == "yuv420p":
            return True
    return False


def co_profile(args: list[str]) -> bool:
    for i in range(len(args) - 1):
        if args[i] == "-profile:v" and args[i + 1] == "high":
            return True
    return False


# ════════════════════════════════════════════════════════════════════════════
def ca1_tham_so(fu) -> None:
    print("\n── CA 1: THAM SỐ ENCODE — cả hai nhánh phải ép yuv420p ──")
    for enc in ("h264_nvenc", "libx264"):
        for q in ("high", "thap"):
            a = fu._enc_args(enc, q)
            ok(co_chot(a), f"1a `_enc_args({enc}, {q})` có -pix_fmt yuv420p",
               " ".join(a))
            ok(co_profile(a), f"1b `_enc_args({enc}, {q})` có -profile:v high")
    a = fu._enc_mezz("libx264")
    ok(co_chot(a), "1c `_enc_mezz(libx264)` có yuv420p (cổng 42 đã vá)")


def ca2_manh_mezzanine() -> None:
    """Mảnh mezzanine của đường GHÉP NHIỀU PART — đọc bằng AST.

    Đọc bằng AST chứ KHÔNG tìm chuỗi trong cả file: chính DÒNG GHI CHÚ giải
    thích bản vá có chữ `yuv420p`, nên quét chuỗi là **ĐỎ/XANH OAN** (bài học
    cổng 47/51/53/54 — sập 4 lần). AST không thấy comment.
    """
    print("\n── CA 2: MẢNH MEZZANINE (ghép nhiều part) — cả 2 nhánh ──")
    import ast
    t = ast.parse((REPO / "app" / "core" / "ffmpeg_utils.py")
                  .read_text(encoding="utf-8"))
    ham = {}
    for n in ast.walk(t):
        if isinstance(n, ast.FunctionDef) and n.name in ("_build_seg", "_build_xf"):
            ham[n.name] = n
    ok(set(ham) == {"_build_seg", "_build_xf"},
       "2a tìm thấy cả `_build_seg` và `_build_xf`", f"{sorted(ham)}")
    for ten, node in sorted(ham.items()):
        nhanh = None
        for x in ast.walk(node):
            if isinstance(x, ast.If) and "h264_nvenc" in ast.dump(x.test):
                nhanh = x
                break
        if not ok(nhanh is not None, f"2b {ten}: có nhánh rẽ theo encoder"):
            continue
        for nhan, than in (("nvenc", nhanh.body), ("libx264", nhanh.orelse)):
            hs = [c.value for c in ast.walk(ast.Module(body=than, type_ignores=[]))
                  if isinstance(c, ast.Constant) and isinstance(c.value, str)]
            ok("yuv420p" in hs and "-pix_fmt" in hs,
               f"2c {ten} nhánh {nhan}: ép -pix_fmt yuv420p")


def ca3_khung_chan(fu) -> None:
    print("\n── CA 3: KÍCH THƯỚC LẺ phải bị ép về CHẴN ──")
    for wi, hi, we, he in ((1080, 1920, 1080, 1920), (1081, 1921, 1080, 1920),
                           (539, 959, 538, 958), (1, 1, 2, 2), (0, 0, 2, 2)):
        w, h = fu.khung_chan(wi, hi)
        ok((w, h) == (we, he), f"3a khung_chan({wi},{hi}) -> ({we},{he})",
           f"ra ({w},{h})")
    ok(all(v % 2 == 0 for v in fu.khung_chan(1081, 1921)),
       "3b kết quả luôn CHẴN cả hai chiều")


def ca4_xuat_that(fu, sand: Path, nguon: Path, nhan: str,
                  hook_first: bool) -> dict:
    """XUẤT THẬT bằng `export_canvas_clip`, ép `libx264` = đúng đường LÙI.

    Ép libx264 vì đó là nhánh HỎNG: nhánh nvenc có chốt sẵn nên xuất bằng nvenc
    thì không chứng minh được gì.
    """
    dst = sand / f"ra_{nhan}.mp4"
    info = fu.probe(str(nguon))
    dai = info.duration
    if hook_first:
        # HOOK-FIRST = NGƯỢC THỜI GIAN (đoạn sau đứng trước). Bắt buộc phải test
        # đường này: nó là đường thật của app và là chỗ lệch tiếng-hình v1.87.
        segs = [(dai * 0.55, dai * 0.75), (dai * 0.05, dai * 0.30)]
    else:
        segs = [(dai * 0.05, dai * 0.30), (dai * 0.55, dai * 0.75)]
    fu.export_canvas_clip(
        str(nguon), str(dst), segs, (0.5, 0.5, 1.0), bg="blur",
        out_w=1080, out_h=1920, encoder="libx264",
    )
    return {"dst": dst, "segs": segs}


def ca5_kiem_file(dst: Path, nhan: str, sand: Path) -> dict:
    print(f"\n── CA 4/5: FILE RA «{nhan}» — trình phát Windows có mở được? ──")
    d = soi(dst)
    print(f"     ffprobe: codec={d['codec']} profile={d['profile']} "
          f"level={d['level']} pix_fmt={d['pix_fmt']} {d['w']}x{d['h']} "
          f"fps={d['fps']} nb_frames={d['nb_frames']} dur={d['dur']:.3f}s "
          f"size={d['size']/1e6:.2f} MB")
    ok(d["pix_fmt"] == "yuv420p", f"5a [{nhan}] pix_fmt = yuv420p",
       d["pix_fmt"])
    ok(d["profile"] == "High", f"5b [{nhan}] profile = High (KHÔNG High 10 / "
                               f"4:4:4)", d["profile"])
    ok(d["codec"] == "h264", f"5c [{nhan}] codec = h264", d["codec"])
    ok(d["w"] % 2 == 0 and d["h"] % 2 == 0,
       f"5d [{nhan}] kích thước CHẴN", f"{d['w']}x{d['h']}")
    ok(d["nb_frames"] > 0, f"5e [{nhan}] nb_frames > 0", str(d["nb_frames"]))
    ok(d["dur"] > 0.5, f"5f [{nhan}] độ dài > 0", f"{d['dur']:.3f}s")
    ok(d["size"] > 1024, f"5g [{nhan}] file KHÔNG rỗng "
                         f"(ffmpeg từng trả mã 0 mà file 0 KiB)",
       f"{d['size']} byte")

    boxes = hop_mp4(dst)
    ok("moov" in boxes, f"5h [{nhan}] CÓ box `moov`", " ".join(boxes[:8]))
    if "moov" in boxes and "mdat" in boxes:
        ok(boxes.index("moov") < boxes.index("mdat"),
           f"5i [{nhan}] `moov` đứng TRƯỚC `mdat` (+faststart)")
    ok(co_tieng(dst), f"5j [{nhan}] có luồng tiếng")

    n, loi = giai_ma_het(dst)
    ok(n > 0 and not loi,
       f"5k [{nhan}] GIẢI MÃ HẾT {n} khung, 0 lỗi (thay cho ffplay)",
       loi[:200] if loi else f"{n} khung")

    kh = do_khung(dst, min(1.0, d["dur"] / 3), sand / f"khung_{nhan}.png")
    print(f"     khung: YMIN={kh['YMIN']} YMAX={kh['YMAX']} "
          f"YAVG={kh['YAVG']} · PNG {kh['png_co']} byte")
    ok(kh["png_co"] > 1000, f"5l [{nhan}] trích được PNG", str(kh["png_co"]))
    ok(not kh["don_sac"], f"5m [{nhan}] khung KHÔNG đơn sắc (không phải màn "
                          f"trắng/đen trơn)", f"YMIN={kh['YMIN']} YMAX={kh['YMAX']}")
    ok(kh["YAVG"] < 245.0, f"5n [{nhan}] khung KHÔNG trắng xoá",
       f"YAVG={kh['YAVG']}")
    print(f"     >>> ẢNH ĐỂ NGƯỜI TỰ NHÌN: {kh['png']}")
    return d


def ca6_llm_rong() -> None:
    print("\n── CA 6: AI TRẢ VỀ RỖNG (char 0) — thử lại + báo ĐÚNG BỆNH ──")
    from app.ai import llm

    that = llm.complete_text
    dem = {"n": 0}
    tra: list[str] = []

    def gia(prompt, system="", temperature=0.4, provider=None, model=None,
            json_mode=False):
        dem["n"] += 1
        llm._LAN.ket_thuc = "stop"
        llm._LAN.chan_doan = {"model": "openai/gpt-oss-120b",
                              "ket_thuc": "stop", "so_ky_tu": 0, "rong": True,
                              "chi_khoang_trang": False, "token_ra": 0,
                              "token_vao": 1413, "dau_than": ""}
        return tra[min(dem["n"] - 1, len(tra) - 1)]

    llm.complete_text = gia          # type: ignore[assignment]
    try:
        # (a) rỗng cả 3 lượt -> LLMRong, ĐÚNG 3 lượt (tức CÓ thử lại)
        tra[:] = ["", "", ""]
        dem["n"] = 0
        e = None
        try:
            llm.complete_json("x", system="s")
        except Exception as ex:      # noqa: BLE001
            e = ex
        ok(isinstance(e, llm.LLMRong),
           "6a thân rỗng -> ném `LLMRong` (KHÔNG phải LLMError chung)",
           type(e).__name__ if e else "không ném")
        ok(dem["n"] == 3, "6b ĐÃ THỬ LẠI khi rỗng", f"{dem['n']} lượt")
        msg = str(e or "")
        ok("không trả về nội dung" in msg.lower()
           or "KHÔNG TRẢ VỀ NỘI DUNG" in msg,
           "6c lời lỗi nói 'AI không trả về nội dung'", msg[:90])
        ok("không phải JSON hợp lệ" not in msg,
           "6d lời lỗi KHÔNG còn nói 'không phải JSON hợp lệ' (báo sai bệnh)")
        ok(not llm.is_rate_limit_error(msg),
           "6e KHÔNG bị coi là hết-lượt -> KHÔNG phạt key, KHÔNG đợi 15 phút")

        # (b) rỗng lượt 1, đúng lượt 2 -> phải HỒI PHỤC
        tra[:] = ["", '{"ok": 1}', ""]
        dem["n"] = 0
        r = llm.complete_json("x", system="s")
        ok(r == {"ok": 1} and dem["n"] == 2,
           "6f rỗng lượt 1 rồi trả đúng lượt 2 -> HỒI PHỤC", f"{r} · {dem['n']} lượt")

        # (c) chỉ khoảng trắng cũng là RỖNG
        tra[:] = ["  \n\t "] * 3
        dem["n"] = 0
        e2 = None
        try:
            llm.complete_json("x", system="s")
        except Exception as ex:      # noqa: BLE001
            e2 = ex
        ok(isinstance(e2, llm.LLMRong),
           "6g thân CHỈ KHOẢNG TRẮNG cũng ra `LLMRong`",
           type(e2).__name__ if e2 else "không ném")

        # (d) `char 1837` (bị CẮT) vẫn phải là LLMCatCut, KHÔNG bị bản vá này
        #     cướp mất — hai bệnh khác nhau phải ra hai lời khác nhau.
        def gia_cat(prompt, system="", temperature=0.4, provider=None,
                    model=None, json_mode=False):
            dem["n"] += 1
            llm._LAN.ket_thuc = "length"
            llm._LAN.chan_doan = {"model": "m", "ket_thuc": "length",
                                  "so_ky_tu": 1837, "rong": False,
                                  "chi_khoang_trang": False, "token_ra": 3072,
                                  "token_vao": 1413, "dau_than": "["}
            return '[{"i":0,"t":"a"},{"i":1,"t":"b'

        llm.complete_text = gia_cat  # type: ignore[assignment]
        dem["n"] = 0
        e3 = None
        try:
            llm.complete_json("x", system="s")
        except Exception as ex:      # noqa: BLE001
            e3 = ex
        # vớt được phần hoàn chỉnh -> KHÔNG ném là ĐÚNG; ném thì phải là CatCut
        ok(e3 is None or isinstance(e3, llm.LLMCatCut),
           "6h ca BỊ CẮT (char 1837) vẫn đi đường `LLMCatCut`, không bị "
           "nhánh RỖNG cướp", type(e3).__name__ if e3 else "vớt được, không ném")
    finally:
        llm.complete_text = that     # type: ignore[assignment]


def ca7_thu_pha(sand: Path) -> None:
    """TỰ KIỂM: gỡ chốt `yuv420p` ra thì cổng PHẢI kêu — và file PHẢI hỏng."""
    print("\n── CA 7: THỬ PHÁ (tự kiểm) — gỡ chốt ra thì phải ĐỎ ──")
    pha = nap_ban_pha(bo_chot=True)
    a = pha._enc_args("libx264", "high")
    ok(not co_chot(a),
       "7a phép phá ĂN được (bản gỡ chốt thật sự không còn yuv420p)",
       " ".join(a))
    ok(co_chot(pha._enc_args("h264_nvenc", "high")),
       "7b phép phá chỉ đụng nhánh libx264 (nvenc còn nguyên)")

    # Vế thứ hai — QUAN TRỌNG NHẤT: chạy ffmpeg THẬT trên nguồn 10-bit.
    # Không có vế này thì mục 7 chỉ chứng minh "chuỗi có mặt", đúng cái bẫy
    # PASS OAN của cổng 56d.
    src10 = nguon_10bit(sand / "nguon10.mp4")
    d10 = soi(src10)
    if not ok(d10["pix_fmt"] == "yuv420p10le",
              "7c dựng được nguồn 10-bit để thử", d10["pix_fmt"]):
        return

    ra_pha = sand / "pha_10bit.mp4"
    ra_that = sand / "that_10bit.mp4"
    dai = fu_that.probe(str(src10)).duration
    # ★ CẤU HÌNH PHẢI LÀ **1 ĐOẠN + nền `fill`**, KHÔNG phải nhiều đoạn + `blur`.
    # ĐO ĐƯỢC 18/08/2026 (`_do_nvenc_that.py`, 12 arm trên nguồn 10-bit THẬT):
    # bản gỡ chốt ra `yuv420p` — tức **KHÔNG tái hiện được bệnh** — ở MỌI arm
    # dùng `blur` hoặc nhiều đoạn, vì có HAI thứ vô tình che mất:
    #   · NHIỀU ĐOẠN đi qua mezzanine `_build_seg`, mà mezz ĐÃ ép `yuv420p`
    #     sẵn (vá từ cổng 42) -> đầu vào lượt encode cuối đã là 420p rồi;
    #   · nền `blur` dùng `overlay`, mà `overlay` của ffmpeg mặc định
    #     `format=yuv420` -> nó GHIM 420p bất kể nguồn.
    # Chỉ đường **1 đoạn + không overlay** mới thả nguồn 10-bit xuống thẳng
    # encoder. Đo trên đúng cấu hình này: gỡ chốt -> `yuv420p10le / High 10`
    # (đúng file anh Hùng không mở được) · bản thật -> `yuv420p / High`.
    # Chạy thử phá trên cấu hình bị che thì mục 7e chỉ là con dấu.
    segs = [(0.5, min(dai * 0.95, 14.0))]
    loi_pha = ""
    try:
        pha.export_canvas_clip(str(src10), str(ra_pha), segs, (0.5, 0.5, 1.0),
                               bg="fill", out_w=540, out_h=960,
                               encoder="libx264")
    except Exception as e:           # noqa: BLE001
        loi_pha = f"{type(e).__name__}: {e}"
    fu_that.export_canvas_clip(str(src10), str(ra_that), segs, (0.5, 0.5, 1.0),
                               bg="fill", out_w=540, out_h=960,
                               encoder="libx264")

    d_that = soi(ra_that)
    ok(d_that["pix_fmt"] == "yuv420p" and d_that["profile"] == "High",
       "7d BẢN THẬT trên nguồn 10-bit -> vẫn yuv420p/High (MỞ ĐƯỢC)",
       f"{d_that['pix_fmt']} / {d_that['profile']}")

    if ra_pha.exists() and ra_pha.stat().st_size > 1024:
        d_pha = soi(ra_pha)
        print(f"     BẢN GỠ CHỐT: pix_fmt={d_pha['pix_fmt']} "
              f"profile={d_pha['profile']} (đây là file anh Hùng KHÔNG mở được)")
        ok(d_pha["pix_fmt"] != "yuv420p" or d_pha["profile"] != "High",
           "7e BẢN GỠ CHỐT ra file KHÔNG phải yuv420p/High -> tức chốt "
           "THẬT SỰ là thứ chặn lỗi, không phải trang trí",
           f"{d_pha['pix_fmt']} / {d_pha['profile']}")
    else:
        ok(bool(loi_pha),
           "7e BẢN GỠ CHỐT chết hẳn khi xuất (cũng là bằng chứng chốt cần "
           "thiết)", loi_pha[:200])


# ════════════════════════════════════════════════════════════════════════════
def main() -> int:
    print("=" * 78)
    print("CỔNG 75 — CLIP XUẤT RA PHẢI MỞ ĐƯỢC (pix_fmt · profile · kích thước "
          "chẵn · moov · khung)")
    print("=" * 78)

    for p in (FFMPEG, FFPROBE):
        if not Path(p).exists():
            print(f"THIẾU {p}")
            return 2

    global fu_that
    fu_that = nap_ban_pha(bo_chot=False)

    sand = Path(tempfile.mkdtemp(prefix="bq_cong75_"))
    try:
        ca1_tham_so(fu_that)
        ca2_manh_mezzanine()
        ca3_khung_chan(fu_that)

        # Nguồn THẬT của anh Hùng nếu có; không có thì lavfi (cổng không được
        # ĐỎ OAN chỉ vì kho đĩa đổi — bài học cổng 47 CA2 / cổng 68).
        nguon = None
        for goc in (Path(r"C:\Users\Admin\Downloads\Video"),
                    Path(r"D:\video ssmatool\video mỹ")):
            if not goc.is_dir():
                continue
            cand = sorted(x for x in goc.rglob("*.mp4")
                          if not x.name.startswith("Part "))
            if cand:
                nguon = sand / "nguon_that.mp4"
                shutil.copyfile(cand[0], nguon)   # COPY — không đụng gốc
                print(f"\nNGUỒN THẬT (bản sao): {cand[0].name}")
                break
        if nguon is None:
            nguon = sand / "nguon_lavfi.mp4"
            subprocess.run(
                [FFMPEG, "-y", "-hide_banner", "-v", "error", "-nostdin",
                 "-f", "lavfi", "-i", "testsrc2=s=1280x720:r=30:d=20",
                 "-f", "lavfi", "-i", "sine=frequency=330:duration=20",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                 "-c:a", "aac", "-shortest", str(nguon)],
                capture_output=True, timeout=300, creationflags=_CNW)
            print("\nNGUỒN: lavfi (không tìm thấy video thật)")

        for nhan, hf in (("ghep_hookfirst", True), ("ghep_xuoi", False)):
            r = ca4_xuat_that(fu_that, sand, nguon, nhan, hf)
            ca5_kiem_file(r["dst"], nhan, sand)

        ca6_llm_rong()
        ca7_thu_pha(sand)
    finally:
        print(f"\n(hộp cát: {sand})")

    print("\n" + "=" * 78)
    print(f"ĐẠT {DAT} · HỎNG {HONG}")
    if _LOI:
        for x in _LOI:
            print(f"   HỎNG: {x}")
    print("=" * 78)
    return 1 if HONG else 0


if __name__ == "__main__":
    sys.exit(main())
