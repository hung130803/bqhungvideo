# -*- coding: utf-8 -*-
"""ĐO SĂN LỖI đường THAY GIỌNG (v2.42.3 -> v2.42.8).

Chạy THẬT, không đọc mã rồi suy:
  A. `worker.tran_luong_tg` ở các bộ (nhân, RAM) BIÊN — có ra 0/âm không.
  B. `tg_chay.khoa_chong_trung` + `xep_mot`: TẮT `dd`/`htg` -> khoá phải
     giống TỪNG KÝ TỰ bản mốc (nạp bằng `git show`).
  C. `_ep_khung` codec theo đuôi: **CẢ HAI** bản (`giong_vieneu` đã vá ·
     `giong_ngoai` chưa rà) trên đủ đuôi app thật sự sinh ra.
  D. `doc_ban_dich` với engine GIẢ: ghi lại dãy `p` -> có dãy nào GIẢM không.
  E. `cat_lang_giua` ca biên: toàn lặng · 1 câu cực ngắn · không có dòng
     silencedetect nào.
  F. `nhan_ban_giong` sở hữu mẫu: hai tên khác nhau mà `_slug` giống.
"""
from __future__ import annotations

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = str(Path(__file__).resolve().parent)
sys.path.insert(0, REPO)

HOP = Path(tempfile.mkdtemp(prefix="bq_do_santg_"))
os.environ.setdefault("BQ_DATA_DIR", str(HOP / "data"))
os.environ.setdefault("BQ_DB_PATH", str(HOP / "data" / "studio.db"))
(HOP / "data").mkdir(parents=True, exist_ok=True)


def tieu(s):
    print("\n" + "=" * 70)
    print(s)
    print("=" * 70)


# ---------------------------------------------------------------- A
def do_a():
    tieu("A. tran_luong_tg — máy biên")
    from app.queue import worker as W
    print(f"   TG_TRAN={W.TG_TRAN} · NHAN_MOI_LUONG_MAY={W.NHAN_MOI_LUONG_MAY}"
          f" · RAM_MOI_LUONG_MAY_GB={W.RAM_MOI_LUONG_MAY_GB}")
    print(f"   NHAN_CHUA={W.NHAN_CHUA} · RAM_CHUA_GB={W.RAM_CHUA_GB}")
    xau = []
    print(f"   {'nhân':>5} {'RAM':>6} | {'tren_may=False':>14} {'True':>6}")
    for n in (1, 2, 4, 6, 8, 12, 16, 24, 32, 64, 128):
        for r in (0.0, 2.0, 4.0, 8.0, 16.0, 31.8, 64.0):
            a = W.tran_luong_tg(False, nhan=n, ram_gb=r)
            b = W.tran_luong_tg(True, nhan=n, ram_gb=r)
            if b < 1 or a < 1:
                xau.append((n, r, a, b))
            if r in (0.0, 8.0, 31.8):
                print(f"   {n:>5} {r:>6.1f} | {a:>14} {b:>6}")
    # ca quái: nhân âm / RAM âm / None
    for n, r in ((0, 8.0), (-4, 8.0), (4, -1.0), (None, None)):
        try:
            b = W.tran_luong_tg(True, nhan=n, ram_gb=r)
            print(f"   quái nhan={n} ram={r} -> {b}")
            if b < 1:
                xau.append((n, r, None, b))
        except Exception as e:  # noqa: BLE001
            print(f"   quái nhan={n} ram={r} -> NÉM {type(e).__name__}: {e}")
            xau.append((n, r, None, "NEM"))
    print(f"\n   >>> số bộ ra 0/âm/ném: {len(xau)}  {xau[:5]}")
    return len(xau) == 0


# ---------------------------------------------------------------- B
_MOC = "v2.42.2"


def _nap_moc(duong: str, ten: str):
    """Nạp một file từ commit MỐC thành module riêng."""
    import importlib.util
    r = subprocess.run(["git", "show", f"{_MOC}:{duong}"], cwd=REPO,
                       capture_output=True)
    if r.returncode != 0:
        return None
    p = HOP / ten
    p.write_bytes(r.stdout)
    spec = importlib.util.spec_from_file_location(ten.replace(".py", ""), p)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def do_b():
    tieu(f"B. dedup_key — TẮT cờ phải GIỐNG TỪNG KÝ TỰ mốc {_MOC}")
    from app.core import tg_chay
    moc = _nap_moc("app/core/tg_chay.py", "moc_tg_chay.py")
    if moc is None:
        print("   !! không nạp được mốc")
        return False
    # bản mốc phải KHÁC bản đang test (chống PASS OAN)
    a_src = Path(REPO, "app/core/tg_chay.py").read_bytes()
    b_src = (HOP / "moc_tg_chay.py").read_bytes()
    print(f"   mốc KHÁC bản đang test: {a_src != b_src}")
    print(f"   mốc có 'doc_deu': {b'doc_deu' in b_src} (phải False)")

    bo = [
        dict(video=r"D:\K\a.mp4", dich_sang="vi", voice="vn:Adam",
             thu_muc_ra=r"D:\K\xuat"),
        dict(video=r"D:\K\b.mp4", dich_sang="en", voice="cb:en|D:\\m.wav",
             thu_muc_ra=r"D:\K\xuat", che_chu=True, che_chu_cach="mo",
             che_chu_muc=1.0, viet_chu=True, kieu_chu={"co_chu": 6.5}),
        dict(video=r"D:\K\c.mp4", dich_sang="vi", voice="edge",
             thu_muc_ra=r"D:\K\ra", hinh_theo_giong=True),
        dict(video=r"D:\K\d.mp4", dich_sang="vi", voice="edge",
             thu_muc_ra=r"D:\K\ra", de_giong=True, muc_nen_db=-3.0,
             muc_giong_db=2.5),
        dict(video=r"D:\K\e.mp4", dich_sang="ja", voice="kk:af_bella",
             thu_muc_ra=r"D:\K\ra", hinh_theo_giong=True, de_giong=True,
             che_chu=True),
    ]
    lech = 0
    for kw in bo:
        a = tg_chay.khoa_chong_trung(**kw)          # doc_deu mặc định False
        b = moc.khoa_chong_trung(**kw)
        if a != b:
            lech += 1
            print(f"   LỆCH: {kw['video']}\n     nay: {a}\n     mốc: {b}")
    print(f"   >>> {len(bo)} tổ hợp cờ CŨ · lệch {lech}")

    # đuôi :dd=1 phải LỒNG trong nhánh htg
    k_htg0_dd1 = tg_chay.khoa_chong_trung(
        r"D:\K\c.mp4", "vi", "edge", r"D:\K\ra",
        hinh_theo_giong=False, doc_deu=True)
    k_htg0_dd0 = tg_chay.khoa_chong_trung(
        r"D:\K\c.mp4", "vi", "edge", r"D:\K\ra",
        hinh_theo_giong=False, doc_deu=False)
    k_htg1_dd0 = tg_chay.khoa_chong_trung(
        r"D:\K\c.mp4", "vi", "edge", r"D:\K\ra",
        hinh_theo_giong=True, doc_deu=False)
    k_htg1_dd1 = tg_chay.khoa_chong_trung(
        r"D:\K\c.mp4", "vi", "edge", r"D:\K\ra",
        hinh_theo_giong=True, doc_deu=True)
    print(f"   htg=0 dd=0 -> ...{k_htg0_dd0[-30:]}")
    print(f"   htg=0 dd=1 -> ...{k_htg0_dd1[-30:]}  (phải GIỐNG dòng trên)")
    print(f"   htg=1 dd=0 -> ...{k_htg1_dd0[-30:]}")
    print(f"   htg=1 dd=1 -> ...{k_htg1_dd1[-30:]}")
    ok_long = (k_htg0_dd1 == k_htg0_dd0) and (k_htg1_dd1 != k_htg1_dd0) \
        and k_htg1_dd1.endswith(":htg=1:dd=1")
    print(f"   >>> :dd=1 lồng đúng trong htg: {ok_long}")

    # thứ tự đuôi: dd phải đứng TRƯỚC dg/mn/mg? -> chỉ cần khoá TẮT khớp mốc
    k_all = tg_chay.khoa_chong_trung(
        r"D:\K\f.mp4", "vi", "edge", r"D:\K\ra", hinh_theo_giong=True,
        de_giong=True, muc_nen_db=-3.0, muc_giong_db=2.5, doc_deu=True)
    print(f"   đủ cờ -> ...{k_all[-40:]}")
    return lech == 0 and ok_long


# ---------------------------------------------------------------- B2
def do_b2():
    tieu("B2. xep_mot GỌI THẬT -> dedup_key qua pool giả")
    from app.core import tg_chay, tg_so

    ghi = []

    class PoolGia:
        def enqueue(self, loai, tt, **kw):
            ghi.append((loai, dict(tt), kw.get("dedup_key")))
            return len(ghi)

    tg_so.can_chay = lambda v: True          # bỏ sổ
    nguon = HOP / "nguon"
    dich = HOP / "dich"
    nguon.mkdir(exist_ok=True)
    v = nguon / "x.mp4"
    v.write_bytes(b"0")

    p = PoolGia()
    tg_chay.xep_mot(p, v, "vi", "edge", dich, hinh_theo_giong=True,
                    doc_deu=False)
    tg_chay.xep_mot(p, v, "vi", "edge", dich, hinh_theo_giong=True,
                    doc_deu=True)
    tg_chay.xep_mot(p, v, "vi", "edge", dich, hinh_theo_giong=False,
                    doc_deu=True)
    for i, (loai, tt, dk) in enumerate(ghi):
        print(f"   #{i} doc_deu trong payload={tt.get('doc_deu')!r} "
              f"htg={tt.get('hinh_theo_giong')!r}")
        print(f"       dedup=...{dk[-30:]}")
    ok = (ghi[0][2] != ghi[1][2]) and (ghi[2][2] == ghi[0][2].replace(
        ":htg=1", ""))
    print(f"   >>> payload+khoá đúng luật: {ok}")
    return True


# ---------------------------------------------------------------- C
def _sinh_wav(p: Path, giay=2.0):
    from config import settings
    subprocess.run(
        [settings.FFMPEG_PATH, "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={giay}",
         "-ac", "1", "-ar", "24000", str(p)],
        capture_output=True, check=False)


def do_c():
    tieu("C. _ep_khung — codec theo ĐUÔI file đích (cả 2 bản)")
    from app.core import giong_ngoai as GN
    from app.core import giong_vieneu as VN

    src = HOP / "src.wav"
    _sinh_wav(src, 2.0)
    print(f"   nguồn: {src.stat().st_size} byte")

    duoi = [".wav", ".mp3", ".m4a", ".opus", ".ogg"]
    kq = {}
    for ten, fn in (("giong_ngoai", GN._ep_khung), ("giong_vieneu", VN._ep_khung)):
        print(f"\n   --- {ten}._ep_khung, tempo=1.25 ---")
        for d in duoi:
            dst = HOP / f"ra_{ten}{d}"
            if dst.exists():
                dst.unlink()
            ok = fn(src, dst, 1.25)
            co = dst.exists() and dst.stat().st_size or 0
            kq[(ten, d)] = (ok, co)
            print(f"     {d:<7} ok={str(ok):<5} byte={co}")
    return kq


# ---------------------------------------------------------------- D
def do_d():
    tieu("D. doc_ban_dich với engine GIẢ -> dãy p có GIẢM không?")
    import asyncio
    from app.core import thay_giong as TG
    from app.core import dubbing

    N = 12
    texts = [f"cau so {i}" for i in range(N)]
    day = []

    def on_prog(p, m):
        day.append((round(float(p), 4), str(m)[:48]))

    async def gia(txts, voice, paths, on_done=None, pitch=None, lang="vi",
                  on_msg=None, rate="+0%", **kw):
        # mô phỏng máy đọc CHẠY-TRÊN-MÁY: báo N/M rồi tới lượt gọi on_done
        for i in range(len(txts)):
            if on_msg:
                on_msg(f"Doc cau {i+1}/{len(txts)}")
            _sinh_wav(Path(paths[i]), 0.6)
        if on_done:
            for i in range(len(txts)):
                on_done(i)
        return [True] * len(txts), [[] for _ in txts]

    that = dubbing._synth_all_words
    dubbing._synth_all_words = gia
    try:
        TG.doc_ban_dich(texts, HOP / "dbd", voice="vn:Adam", dich_sang="vi",
                        on_progress=on_prog)
    finally:
        dubbing._synth_all_words = that

    lui = []
    for i in range(1, len(day)):
        if day[i][0] < day[i - 1][0] - 1e-9:
            lui.append((i, day[i - 1], day[i]))
    print(f"   {len(day)} nhịp báo. 12 nhịp đầu:")
    for p, m in day[:12]:
        print(f"     {p:6.3f}  {m}")
    print(f"   ... 6 nhịp cuối:")
    for p, m in day[-6:]:
        print(f"     {p:6.3f}  {m}")
    print(f"\n   >>> số lần TỤT LÙI: {len(lui)}")
    for i, a, b in lui[:8]:
        print(f"       nhịp {i}: {a[0]} ({a[1]}) -> {b[0]} ({b[1]})")
    return len(lui)


# ---------------------------------------------------------------- E
def do_e():
    tieu("E. cat_lang_giua — ca biên")
    from app.core import giong_chatter as GC
    from config import settings

    def mk(ten, loc):
        p = HOP / ten
        subprocess.run(
            [settings.FFMPEG_PATH, "-hide_banner", "-loglevel", "error", "-y",
             "-f", "lavfi", "-i", loc, "-ac", "1", "-ar", "24000", str(p)],
            capture_output=True, check=False)
        return p

    ca = [
        ("toàn lặng 3s", mk("lang.wav", "anullsrc=r=24000:cl=mono:d=3")),
        ("1 câu cực ngắn 0,25s", mk("ngan.wav",
                                    "sine=frequency=300:duration=0.25")),
        ("liên tục 3s (không có lặng)", mk("lien.wav",
                                           "sine=frequency=300:duration=3")),
        ("tiếng-lặng-tiếng", mk(
            "hon.wav",
            "sine=frequency=300:duration=1,apad=pad_dur=1.2,"
            "atrim=0:2.2")),
    ]
    for ten, p in ca:
        dst = p.with_suffix(".gon.wav")
        try:
            kq = GC.cat_lang_giua(p, dst)
        except Exception as e:  # noqa: BLE001
            print(f"   {ten:<30} NÉM {type(e).__name__}: {e}")
            continue
        co = dst.exists() and dst.stat().st_size or 0
        print(f"   {ten:<30} ok={str(kq.get('ok')):<5} "
              f"truoc={kq.get('giay_truoc')} sau={kq.get('giay_sau')} "
              f"cat={kq.get('giay_cat')} khoang={kq.get('so_khoang')} "
              f"byte_ra={co} ly_do={kq.get('ly_do')}")
    # file KHÔNG tồn tại
    try:
        kq = GC.cat_lang_giua(HOP / "khong_co.wav", HOP / "x.wav")
        print(f"   file KHÔNG tồn tại              -> {kq}")
    except Exception as e:  # noqa: BLE001
        print(f"   file KHÔNG tồn tại              -> NÉM {type(e).__name__}: {e}")


# ---------------------------------------------------------------- F
def do_f():
    tieu("F. nhan_ban_giong — sở hữu mẫu / _slug nhiều-về-một")
    from app.core import nhan_ban_giong as NB
    ten = ["Giọng của tôi", "giong cua toi", "Giọng Của Tôi!!!",
           "Giong-Cua-Toi", "a b", "a  b", "  a b  ", "★", "☆"]
    for t in ten:
        try:
            print(f"   _slug({t!r:<22}) = {NB._slug(t)!r}")
        except Exception as e:  # noqa: BLE001
            print(f"   _slug({t!r:<22}) NÉM {type(e).__name__}: {e}")


if __name__ == "__main__":
    try:
        do_a()
        do_b()
        do_b2()
        do_c()
        do_d()
        do_e()
        do_f()
    finally:
        print(f"\n[hộp cát] {HOP}")
        try:
            shutil.rmtree(HOP, ignore_errors=True)
        except Exception:  # noqa: BLE001
            pass
