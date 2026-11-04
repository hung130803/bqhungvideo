"""DỌN VIDEO TRONG THƯ MỤC KÊNH (27/10/2026, theo yêu cầu anh Hùng).

Xoá: file Part do app xuất ("Part N …") + video gốc DÀI (> 3 phút).
GIỮ: video shorts (≤ 3 phút, không mang tên "Part N"), mọi file không phải video.
KHÔNG BAO GIỜ đụng:
  * video gốc đang trong dây chuyền (đã nhận, chưa xong) hoặc có việc
    phân tích/xuất đang chạy/chờ;
  * file vừa ghi trong 10 phút (Part đang xuất dở, video đang tải).

An toàn: KHÔNG xoá ngay — CHUYỂN vào <ổ>:\\_RAC_VIDEO\\<giờ>\\… (cùng ổ nên tức
thì), giữ nguyên đường dẫn để hoàn tác. Xoá hẳn là bước riêng, phải gõ XOA.
Chỉ ĐỌC cơ sở dữ liệu của app, không sửa gì trong đó.

Chạy: DON_VIDEO_KENH.bat (cần TẮT app trước).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
VIDEO = {".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi", ".flv", ".ts"}
PART_RE = re.compile(r"(?i)^part\s*\d")
SHORTS_GIAY = 180            # ≤ 3 phút & không phải Part = shorts -> GIỮ
MOI_GHI_GIAY = 600           # file vừa ghi trong 10 phút -> bỏ qua
NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _db_path() -> Path:
    d = os.environ.get("BQ_DATA_DIR") or os.path.join(os.environ.get("LOCALAPPDATA", ""), "BQHungVideo")
    return Path(os.environ.get("BQ_DB_PATH") or os.path.join(d, "studio.db"))


def _norm(p) -> str:
    return os.path.normcase(os.path.abspath(str(p)))


def _ffprobe() -> str:
    for c in (GOC / "bin" / "ffprobe.exe", Path(r"D:\BQHungVideo\ffprobe.exe"),
              Path(r"D:\BQHungVideo\_internal\ffprobe.exe")):
        if c.exists():
            return str(c)
    return shutil.which("ffprobe") or "ffprobe"


def _thoi_luong(fp: str, f: Path) -> float | None:
    try:
        r = subprocess.run([fp, "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", str(f)],
                           capture_output=True, text=True, timeout=30, creationflags=NO_WIN)
        return float(r.stdout.strip())
    except Exception:  # noqa: BLE001
        return None


def _app_dang_chay() -> bool:
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq BQHungVideo.exe"],
                           capture_output=True, text=True, timeout=15, creationflags=NO_WIN)
        return "BQHungVideo.exe" in r.stdout
    except Exception:  # noqa: BLE001
        return False


def _doc_db():
    p = _db_path()
    if not p.exists():
        raise SystemExit(f"Không thấy cơ sở dữ liệu của app ở {p}")
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    thu_muc = set()
    for r in con.execute("SELECT export_dir, pipe_src FROM projects"):
        for v in (r["export_dir"], r["pipe_src"]):
            if v and str(v).strip():
                thu_muc.add(str(v).strip())
    for r in con.execute("SELECT DISTINCT export_path FROM clips WHERE export_path IS NOT NULL AND export_path<>''"):
        thu_muc.add(str(Path(r["export_path"]).parent))
    giu = set()
    # video gốc đang trong dây chuyền / đang có việc chạy-chờ
    for r in con.execute("SELECT v.src_path FROM videos v WHERE v.id IN (SELECT video_id FROM jobs "
                         "WHERE status IN ('pending','running') AND video_id IS NOT NULL)"):
        if r["src_path"]:
            giu.add(_norm(r["src_path"]))
    for r in con.execute("SELECT v.src_path FROM pipeline_files f JOIN videos v ON v.id=f.video_id "
                         "WHERE f.status='taken'"):
        if r["src_path"]:
            giu.add(_norm(r["src_path"]))
    con.close()
    return sorted(thu_muc), giu


#: CHỈ dọn trong thư mục này (anh Hùng 27/10: "D:\\video ssmatool\\video mỹ").
#: Quét chính nó + thư mục con 2 tầng (mỗi kênh 1 thư mục con).
GOC_DON = os.environ.get("BQ_GOC_DON") or r"D:\video ssmatool\video mỹ"


def _duoi_goc(p: str) -> bool:
    g = _norm(GOC_DON)
    k = _norm(p)
    return k == g or k.startswith(g.rstrip("\\/") + os.sep)


def quet():
    thu_muc, giu = _doc_db()
    if GOC_DON:
        ds = [d for d in thu_muc if _duoi_goc(d)]
        g = Path(GOC_DON)
        if g.is_dir():
            ds.append(str(g))
            try:
                for a in g.iterdir():
                    if a.is_dir() and not a.name.startswith("_"):
                        ds.append(str(a))
                        for b in a.iterdir():
                            if b.is_dir() and not b.name.startswith("_"):
                                ds.append(str(b))
            except OSError:
                pass
        thu_muc = sorted(set(ds))
    fp = _ffprobe()
    now = time.time()
    xoa, bo_qua = [], {"shorts": 0, "dang_chay": 0, "moi_ghi": 0, "khong_doc": 0}
    da_xem = set()
    for d in thu_muc:
        p = Path(d)
        if not p.is_dir():
            continue
        try:
            files = [f for f in p.iterdir() if f.is_file() and f.suffix.lower() in VIDEO]
        except OSError:
            continue
        for f in files:
            k = _norm(f)
            if k in da_xem:
                continue
            da_xem.add(k)
            try:
                st = f.stat()
            except OSError:
                continue
            if now - st.st_mtime < MOI_GHI_GIAY:
                bo_qua["moi_ghi"] += 1
                continue
            if k in giu:
                bo_qua["dang_chay"] += 1
                continue
            if PART_RE.match(f.name):
                xoa.append((f, st.st_size, "Part"))
                continue
            dur = _thoi_luong(fp, f)
            if dur is None:
                bo_qua["khong_doc"] += 1       # không đọc được -> GIỮ cho chắc
                continue
            if dur <= SHORTS_GIAY:
                bo_qua["shorts"] += 1
                continue
            xoa.append((f, st.st_size, "gốc dài"))
    return thu_muc, xoa, bo_qua


def _rac_cho(f: Path, gio: str) -> Path:
    o = Path(f.anchor) / "_RAC_VIDEO" / gio
    rel = Path(*f.parts[1:]) if len(f.parts) > 1 else Path(f.name)
    return o / rel


def chuyen(xoa):
    gio = time.strftime("%Y%m%d_%H%M%S")
    so = {"gio": gio, "muc": []}
    loi = 0
    for f, _sz, _loai in xoa:
        dich = _rac_cho(f, gio)
        try:
            dich.parent.mkdir(parents=True, exist_ok=True)
            os.replace(f, dich)
            so["muc"].append([str(f), str(dich)])
        except OSError as e:
            loi += 1
            print(f"  KHÔNG chuyển được {f.name}: {e}")
    roots = {Path(d).anchor for _s, d in so["muc"]}
    for r in roots:
        sf = Path(r) / "_RAC_VIDEO" / gio / "_so_hoan_tac.json"
        sf.parent.mkdir(parents=True, exist_ok=True)
        sf.write_text(json.dumps([m for m in so["muc"] if Path(m[1]).anchor == r],
                                 ensure_ascii=False, indent=0), encoding="utf-8")
    return len(so["muc"]), loi, gio


def _cac_lan_rac():
    out = []
    for o in [f"{c}:\\" for c in "CDEFGHIJ"]:
        r = Path(o) / "_RAC_VIDEO"
        if r.is_dir():
            out += [d for d in r.iterdir() if d.is_dir()]
    return sorted(out)


def hoan_tac():
    n = 0
    for lan in _cac_lan_rac():
        sf = lan / "_so_hoan_tac.json"
        if not sf.exists():
            continue
        for goc, dich in json.loads(sf.read_text(encoding="utf-8")):
            if Path(dich).exists() and not Path(goc).exists():
                Path(goc).parent.mkdir(parents=True, exist_ok=True)
                os.replace(dich, goc)
                n += 1
        con = [f for f in lan.rglob("*") if f.is_file() and f.name != "_so_hoan_tac.json"]
        if not con:                      # chỉ xoá thư mục rác khi đã TRẢ HẾT
            sf.unlink()
            shutil.rmtree(lan, ignore_errors=True)
        else:
            print(f"  Còn {len(con)} file ở {lan} chưa trả được (chỗ cũ đã có file cùng tên) — giữ nguyên.")
    print(f"Đã trả lại {n} file về chỗ cũ.")


def _mb(b):
    return f"{b / 1024 / 1024 / 1024:.1f} GB" if b > 1024 ** 3 else f"{b / 1024 / 1024:.0f} MB"


def main():
    print("\n=== DỌN VIDEO TRONG THƯ MỤC KÊNH ===")
    print(f"Thư mục: {GOC_DON}")
    print("Xoá: Part đã xuất + video gốc dài (> 3 phút). GIỮ: video shorts (≤ 3 phút).")
    print("  1) Xem danh sách rồi chuyển vào thùng rác _RAC_VIDEO (hoàn tác được)")
    print("  2) Hoàn tác: trả lại file đã chuyển")
    print("  3) Xoá HẲN thùng rác _RAC_VIDEO (không lấy lại được)")
    c = input("Chọn 1/2/3: ").strip()
    if c in ("1", "2") and _app_dang_chay():
        print("App BQ Hung Video đang mở. Tắt app rồi chạy lại (tránh chuyển nhầm file đang xuất).")
        return
    if c == "1":
        print("Đang quét (đọc độ dài từng video, có thể mất vài phút)...")
        thu_muc, xoa, bq = quet()
        part = [x for x in xoa if x[2] == "Part"]
        dai = [x for x in xoa if x[2] != "Part"]
        print(f"\nĐã quét {len(thu_muc)} thư mục kênh.")
        print(f"  Sẽ dọn: {len(part)} file Part ({_mb(sum(x[1] for x in part))})"
              f" + {len(dai)} video gốc dài ({_mb(sum(x[1] for x in dai))})")
        print(f"  GIỮ: {bq['shorts']} video shorts · {bq['dang_chay']} video đang chạy dây chuyền"
              f" · {bq['moi_ghi']} file vừa ghi < 10 phút · {bq['khong_doc']} file không đọc được")
        for f, sz, loai in xoa[:15]:
            print(f"    - [{loai}] {f}  ({_mb(sz)})")
        if len(xoa) > 15:
            print(f"    … và {len(xoa) - 15} file nữa")
        if not xoa:
            print("Không có gì để dọn.")
            return
        if input("\nChuyển các file trên vào thùng rác _RAC_VIDEO? Gõ Y để đồng ý: ").strip().lower() != "y":
            print("Đã huỷ, không đụng file nào.")
            return
        n, loi, gio = chuyen(xoa)
        print(f"\nXONG: đã chuyển {n} file vào <ổ>:\\_RAC_VIDEO\\{gio}" + (f" · {loi} file lỗi" if loi else ""))
        print("Dùng vài hôm thấy ổn thì chạy lại, chọn 3 để xoá hẳn và lấy lại dung lượng ổ.")
    elif c == "2":
        hoan_tac()
    elif c == "3":
        lan = _cac_lan_rac()
        if not lan:
            print("Không có thùng rác _RAC_VIDEO nào.")
            return
        tong = 0
        for d in lan:
            s = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            tong += s
            print(f"  {d}  {_mb(s)}")
        if input(f"XOÁ HẲN {_mb(tong)} — không lấy lại được. Gõ XOA để đồng ý: ").strip() != "XOA":
            print("Đã huỷ.")
            return
        for d in lan:
            shutil.rmtree(d, ignore_errors=True)
        print("Đã xoá hẳn.")
    else:
        print("Không chọn gì — thoát.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if e.code not in (None, 0):
            print(e)
    except Exception as e:  # noqa: BLE001
        print("LỖI:", e, "— chụp màn hình gửi Claude.")
