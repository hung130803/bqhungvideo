# -*- coding: utf-8 -*-
"""Kiểm nhanh các hàm THUẦN của chuyển cảnh + cửa chờ (không gọi ffmpeg)."""
import os, sys, tempfile
sb = os.path.join(tempfile.gettempdir(), "bqchk")
os.makedirs(sb, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", sb)
os.environ.setdefault("BQ_DB_PATH", os.path.join(sb, "c.db"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from app.core import ffmpeg_utils as fu
print("slots auto  =", fu.so_ffmpeg_song_song())
os.environ["BQ_FFMPEG_SLOTS"] = "3"
print("slots env=3 =", fu.so_ffmpeg_song_song())
del os.environ["BQ_FFMPEG_SLOTS"]
print("decode_threads =", fu.decode_threads(), "encode_threads =", fu.encode_threads())
print("global opts  =", fu._global_enc_opts())
print("so kieu xfade =", len(fu.XFADE_KIEU), "trung lap:",
      len(fu.XFADE_KIEU) - len(set(fu.XFADE_KIEU)))
segs = [(60.0, 70.0), (20.0, 30.0), (30.5, 31.8), (200.0, 215.0)]
print("loai cho noi  =", [fu._loai_cho_noi(segs, i) for i in range(3)])
for m in ("tat", "nhe", "vua", "manh"):
    print("  muc %-5s ->" % m, fu.chon_chuyen_canh(segs, m))
xf = fu.chon_chuyen_canh(segs, "vua")
bu = fu._bu_xfade(segs, xf, 6394.0)
print("bu            =", bu)
g, v, a = fu._graph_xfade(4, xf, bu, [e - s for s, e in segs], True)
print("nhan v/a      =", v, a)
for ln in g.split(";"):
    print("   ", ln)
print("bu khi HET PHIM (dur=70.2) =", fu._bu_xfade(segs, xf, 70.2))
