# -*- coding: utf-8 -*-
"""CỔNG 67 — ADAM (ElevenLabs) TRONG HỘP THAY GIỌNG (17/08/2026).

Anh Hùng chụp màn hình hộp **"Thay giọng nói cho cả thư mục"**, Ngôn ngữ đích
**Tiếng Anh**, combo Giọng đọc chỉ có edge-tts, và hỏi *"đâu Adam đâu"*.
Adam vốn CÓ trong app (hộp Lồng tiếng) nhưng bị `giong_dung_duoc` lọc bỏ, với
lý do THÀNH THẬT ghi ngay trong mã: *"`doc_ban_dich` gọi thẳng
`dubbing._synth_all` — hàm này CHỈ biết edge-tts"*. Bộ lọc đúng, chỉ là không
ai nối tiếp. v2.32.0 nối ở **CỬA CHUNG**; cổng này canh đúng chỗ đó.

**KHÔNG ĐỐT HẠN MỨC THẬT CỦA ANH HÙNG.** Gói free 10.000 ký tự/tháng/tài khoản
(5 tài khoản ≈ 50.000) — một cổng chạy mỗi lượt hồi quy mà gọi API thật thì
tự nó ăn hết. Nên `_eleven_tts` bị VÁ thành hàm sinh mp3 bằng ffmpeg + mốc
giả: **đường đi, chỗ rẽ, cách lùi, cách gom mốc đều là mã THẬT**, chỉ mỗi cú
HTTP là giả. Ca đối chứng với API THẬT bật bằng `BQ_EL_THAT=1` (đã chạy tay
1 lần, xem báo cáo) chứ không chạy trong hồi quy.

**TỰ KIỂM: gỡ chốt ra thì PHẢI ĐỎ** — xem CA 8.
"""
from __future__ import annotations

import ast
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

# HỘP CÁT: đặt TRƯỚC khi nạp config, không thì ghi vào DATA_DIR THẬT.
_SB = tempfile.mkdtemp(prefix="bq_eltg_")
os.environ["BQ_DATA_DIR"] = _SB
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

import _test_guard  # noqa: E402,F401  (bắt buộc: cấm mở Explorer/trình phát)

from config import settings  # noqa: E402

DAT = 0
HONG = 0
FF = settings.FFMPEG_PATH
ADAM = "el:pNInz6obpgDQGcFmaJgB"


def ok(dieu: bool, nhan: str, chi_tiet: str = "") -> None:
    global DAT, HONG
    if dieu:
        DAT += 1
        print(f"  ĐẠT  {nhan}" + (f" — {chi_tiet}" if chi_tiet else ""))
    else:
        HONG += 1
        print(f"  HỎNG {nhan}" + (f" — {chi_tiet}" if chi_tiet else ""))


def _mp3(path: str, giay: float = 1.0) -> None:
    """File mp3 THẬT (ffmpeg) — để `os.path.getsize`/`probe_duration` của mã
    thật có cái mà đo, không phải file rỗng giả vờ."""
    subprocess.run(
        [FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
         "-i", f"sine=frequency=300:duration={giay:g}", "-c:a", "libmp3lame",
         path], check=True, timeout=60)


# ══════════════════════════════════════════════════════════════════
def main() -> int:                                          # noqa: C901
    from app.core import dubbing

    print("=" * 74)
    print("CỔNG 67 — ADAM (ElevenLabs) TRONG HỘP THAY GIỌNG")
    print("=" * 74)

    # ---- VÁ: thay cú HTTP bằng hàm sinh mp3 + mốc, đếm số lần gọi ----
    goi = {"n": 0, "text": [], "hong_tu": None}

    def _gia(text, voice, out_path, model="", on_msg=None, words_out=None,
             **kw):
        goi["n"] += 1
        goi["text"].append(text)
        if goi["hong_tu"] is not None and goi["n"] > goi["hong_tu"]:
            if on_msg:
                on_msg("hết credit (giả lập)")
            return False
        _mp3(str(out_path), 1.0)
        if words_out is not None:
            tu = [t for t in str(text).split() if t]
            b = 1.0 / max(1, len(tu))
            words_out.extend([[round(i * b, 3), round((i + 1) * b, 3), w]
                              for i, w in enumerate(tu)])
        return True

    that = dubbing._eleven_tts
    dubbing._eleven_tts = _gia
    # key GIẢ: `_eleven_hay_khong` chỉ hỏi "có key không" chứ không gọi mạng;
    # không đặt thì cửa rẽ tưởng máy chưa cắm key rồi đi thẳng edge-tts và
    # CẢ CỔNG NÀY tự PASS oan.
    #
    # PHẢI GÁN LÊN **CLASS**, KHÔNG PHẢI INSTANCE — đã sập đúng một lần khi
    # viết cổng này: `config.settings` là một *instance*, còn
    # `elevenlabs_keys` là `@classmethod` đọc `cls.ELEVENLABS_API_KEYS`. Gán
    # lên instance thì classmethod KHÔNG thấy -> `_eleven_keys()` trả rỗng ->
    # cửa rẽ đi thẳng edge-tts, và mấy ca "phải trả False" tự ĐẠT vì lý do
    # NGƯỢC HẲN với cái chúng canh.
    type(settings).ELEVENLABS_API_KEYS = "sk_test_gia_khong_goi_mang"
    ok(bool(dubbing._eleven_keys()),
       "vá key giả ĂN được (chốt chống PASS OAN: không có key thì mọi ca "
       "ElevenLabs bên dưới đo nhầm đường edge)",
       f"{len(dubbing._eleven_keys())} key")
    dubbing._ELEVEN_QUOTA_CACHE.clear()
    dubbing.eleven_credit_remain = lambda *a, **k: None   # bỏ pre-flight quota
    san = Path(_SB) / "wav"
    san.mkdir(parents=True, exist_ok=True)
    CAU = ["He opened the door and froze completely",
           "Nobody in the room said a single word"]

    # ═══════════ CA 1 — chọn `el:` thì THẬT SỰ dùng ElevenLabs ═══════════
    print("\nCA 1 — chọn `el:` thì THẬT SỰ đi ElevenLabs (không âm thầm lùi)")
    goi["n"] = 0
    p = [str(san / f"a{i}.mp3") for i in range(len(CAU))]
    ok1, moc1 = asyncio.run(
        dubbing._synth_all_words(CAU, ADAM, p, lang="en"))
    ok(goi["n"] == len(CAU), "gọi ElevenLabs ĐÚNG số câu (không lùi edge)",
       f"{goi['n']} lượt gọi cho {len(CAU)} câu")
    ok(all(ok1), "mọi câu ra file hợp lệ", f"ok={ok1}")
    ok(all(Path(x).exists() and Path(x).stat().st_size > 200 for x in p),
       "file mp3 có thật, không phải 0 byte")

    # ═══════════ CA 2 — MỐC TỪNG CHỮ ra thật ═══════════
    print("\nCA 2 — mốc từng chữ lấy được THẬT (không rỗng, không bịa)")
    ok(len(moc1) == len(CAU), "đủ một ô mốc cho mỗi câu", f"{len(moc1)} ô")
    ok(all(m for m in moc1), "KHÔNG câu nào mốc rỗng",
       f"số câu có mốc: {sum(1 for m in moc1 if m)}/{len(CAU)}")
    ok(all(len(m) == len(c.split()) for m, c in zip(moc1, CAU)),
       "số mốc = số từ của chính câu đó",
       f"{[len(m) for m in moc1]} vs {[len(c.split()) for c in CAU]}")
    tang = all(all(m[i][0] <= m[i + 1][0] for i in range(len(m) - 1))
               for m in moc1 if m)
    ok(tang, "mốc TĂNG DẦN theo thời gian (mốc lộn xộn = chữ nhảy loạn)")
    ok(all(isinstance(x[2], str) and x[2] for m in moc1 for x in m),
       "mỗi mốc có kèm CHỮ (để căn lại được, không chỉ là hai con số)")

    # ═══════════ CA 3 — `_synth_all` (không mốc) cũng đi đúng cửa ═══════
    print("\nCA 3 — `_synth_all` (cửa KHÔNG mốc) cũng rẽ ElevenLabs")
    goi["n"] = 0
    p2 = [str(san / f"b{i}.mp3") for i in range(len(CAU))]
    ok2 = asyncio.run(dubbing._synth_all(CAU, ADAM, p2, lang="en"))
    ok(goi["n"] == len(CAU) and all(ok2),
       "sót cửa này là video LẪN HAI GIỌNG mà rc vẫn 0",
       f"{goi['n']} lượt gọi · ok={ok2}")

    # ═══════════ CA 4 — HẾT HẠN MỨC: lùi ÊM và NÓI RA ═══════════
    print("\nCA 4 — hết hạn mức giữa chừng -> lùi edge ÊM + NÓI RA")
    goi["n"] = 0
    goi["hong_tu"] = 1                     # câu đầu xong, câu sau chết
    nhan: list = []
    p3 = [str(san / f"c{i}.mp3") for i in range(len(CAU))]
    ok3, _m3 = asyncio.run(
        dubbing._synth_all_words(CAU, ADAM, p3, lang="en",
                                 on_msg=nhan.append))
    ok(any("ElevenLabs" in str(x) for x in nhan),
       "có DÒNG BÁO nêu ElevenLabs hỏng (lùi mà im lặng = hỏng âm thầm)",
       f"{len(nhan)} dòng báo")
    ok(all(ok3), "vẫn ra đủ file bằng giọng edge-tts (video KHÔNG mất tiếng)",
       f"ok={ok3}")

    # ═══════════ CA 5 — LƯỢT ĐỌC LẠI: KHÔNG được lùi (lẫn 2 giọng) ═══════
    print("\nCA 5 — lượt ĐỌC LẠI hết hạn mức -> GIỮ BẢN CŨ, KHÔNG trộn giọng")
    goi["n"] = 0
    goi["hong_tu"] = 0                     # chết ngay từ câu đầu
    p4 = [str(san / f"d{i}.mp3") for i in range(len(CAU))]
    ok4, _m4 = asyncio.run(
        dubbing._synth_all_words(CAU, ADAM, p4, lang="en", el_lui=False))
    # CHỐT CHỐNG PASS OAN: ca này ĐẠT cả khi cửa rẽ bị bịt (lúc đó cũng ra
    # toàn False vì lý do khác hẳn). Phải chứng minh nó ĐÃ THỬ ElevenLabs.
    ok(goi["n"] > 0, "đã THỬ ElevenLabs rồi mới bỏ (không phải chưa thử)",
       f"{goi['n']} lượt gọi")
    ok(not any(ok4),
       "trả toàn False = caller GIỮ bản ElevenLabs cũ (không đọc lại bằng "
       "edge rồi nhét vào giữa clip)", f"ok={ok4}")
    ok(not any(Path(x).exists() for x in p4),
       "KHÔNG đẻ ra file edge-tts nào để lỡ tay dùng nhầm")
    goi["hong_tu"] = None

    # ═══════════ CA 6 — BA chỗ gọi của `thay_giong` đi ĐÚNG CỬA ═══════
    print("\nCA 6 — cả 3 chỗ gọi của `thay_giong.py` đi qua CỬA CHUNG")
    tg_src = (REPO / "app" / "core" / "thay_giong.py").read_text(
        encoding="utf-8")
    cay = ast.parse(tg_src)
    goi_w = [n for n in ast.walk(cay)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "_synth_all_words"]
    ok(len(goi_w) == 3, "vẫn ĐÚNG 3 chỗ gọi (thêm chỗ thứ 4 là cổng 63 đỏ)",
       f"{len(goi_w)} chỗ")
    co_lang = [n for n in goi_w
               if any(k.arg == "lang" for k in n.keywords)]
    ok(len(co_lang) == 3,
       "cả 3 đều truyền `lang` (thiếu -> lùi edge ra giọng SAI NGÔN NGỮ)",
       f"{len(co_lang)}/3")
    # Hai lượt ĐỌC LẠI phải khoá đường lùi; lượt đọc ĐẦU thì không.
    khoa = [n for n in goi_w
            if any(k.arg == "el_lui"
                   and isinstance(k.value, ast.Constant)
                   and k.value.value is False for k in n.keywords)]
    ok(len(khoa) == 2,
       "ĐÚNG 2 chỗ (rút gọn · đọc nhanh) khoá `el_lui=False`; chỗ thứ 3 là "
       "lượt đọc ĐẦU nên được phép lùi", f"{len(khoa)}/2")

    # ═══════════ CA 7 — COMBO: có Adam, vẫn chặn gemini ═══════════
    print("\nCA 7 — combo hộp Thay giọng: CÓ Adam · gemini VẪN chặn")
    from app.ui.thay_giong_dialog import giong_dung_duoc
    ds = [("Adam (ElevenLabs)", ADAM),
          ("Gemini Puck", "gemini:Puck"),
          ("Andrew", "en-US-AndrewNeural")]
    ra = giong_dung_duoc(ds)
    ma = [v for _n, v in ra]
    ok(ADAM in ma, "Adam CHỌN ĐƯỢC trong hộp Thay giọng (câu hỏi của anh Hùng)")
    ok(not any(str(v).startswith("gemini:") for v in ma),
       "gemini VẪN bị chặn — nó KHÔNG trả mốc từng chữ, nhận vào là chữ quay "
       "lại kiểu đổ cả cụm")
    ok(any(str(v).startswith("en-US") for v in ma),
       "giọng edge-tts vẫn còn nguyên (không phá đường cũ)")

    # ═══════════ CA 8 — TỰ KIỂM: gỡ chốt ra thì cổng PHẢI ĐỎ ═══════════
    print("\nCA 8 — TỰ KIỂM bộ dò (gỡ chốt ra thì mấy ca trên phải kêu)")
    from app.core import dubbing as D
    luu = D._eleven_hay_khong
    D._eleven_hay_khong = lambda v: False          # phá: bịt cửa rẽ
    goi["n"] = 0
    p5 = [str(san / f"e{i}.mp3") for i in range(len(CAU))]
    try:
        asyncio.run(D._synth_all_words(CAU, ADAM, p5, lang="en"))
    except Exception:                               # noqa: BLE001
        pass
    ok(goi["n"] == 0,
       "bịt cửa rẽ -> KHÔNG lượt ElevenLabs nào (chứng minh CA 1 đo thật, "
       "không phải con dấu)", f"{goi['n']} lượt")
    D._eleven_hay_khong = luu
    goi["n"] = 0
    asyncio.run(D._synth_all_words(CAU, ADAM,
                                   [str(san / f"f{i}.mp3")
                                    for i in range(len(CAU))], lang="en"))
    ok(goi["n"] == len(CAU), "trả chốt về -> lại đi ElevenLabs",
       f"{goi['n']} lượt")

    # ═══════════ CA 9 — CẢNH BÁO CHI PHÍ ═══════════
    print("\nCA 9 — cảnh báo chi phí (tiền của anh Hùng)")
    from app.core import tg_so
    u = tg_so.uoc_ky_tu([f"v{i}.mp4" for i in range(20)],
                        do_dai_giay=lambda _p: 107.24)
    ok(u["ky_tu"] > 0 and not u["khong_do_duoc"],
       "ước lượng ra số ký tự cho cả mẻ", f"{u['ky_tu']} ký tự / 20 video")
    ok(u["mau"] <= tg_so.MAU_DO_DAI_TOI_DA,
       "chỉ đo mẫu, không ffprobe cả 300 video lúc user vừa bấm Chạy",
       f"mẫu {u['mau']}")
    thieu = tg_so.loi_chi_phi(u, 5000)
    ok("THIẾU" in thieu and "edge-tts" in thieu,
       "thiếu hạn mức -> nói THIẾU BAO NHIÊU + nói rõ sẽ lùi edge-tts")
    ok("ước lượng" in tg_so.loi_chi_phi(u, 999999),
       "luôn ghi chữ 'ước lượng' (video nói dày/thưa lệch nhau nhiều)")
    ok("KHÔNG đọc được hạn mức" in tg_so.loi_chi_phi(u, None),
       "không đọc được hạn mức -> NÓI THẲNG, không coi như còn nhiều")
    u0 = tg_so.uoc_ky_tu(["v.mp4"], do_dai_giay=lambda _p: 0)
    ok("KHÔNG ước lượng được" in tg_so.loi_chi_phi(u0, 47833),
       "không đo được độ dài -> nói KHÔNG ước lượng được, đừng hiện 0")

    # ═══════════ CA 10 — DÒNG TIẾN TRÌNH CÓ TÊN VIDEO ═══════════
    print("\nCA 10 — dòng tiến trình hiện TÊN VIDEO (ảnh anh Hùng chụp)")
    from app.ui import queue_panel as qp

    class _J(dict):
        def keys(self):
            return dict.keys(self)

        def __getitem__(self, k):
            return dict.get(self, k)

    j = _J(type="thay_giong", chan_name=None, vid_path=None,
           payload=json.dumps({"video": r"D:\Kho\kenh 21\Chuyen la.mp4",
                               "kenh": "kenh 21"}))
    nhan_j = qp._job_name(j)[0]
    ok("Chuyen la" in nhan_j, "hiện TÊN VIDEO", nhan_j)
    ok("kenh 21" in nhan_j, "hiện TÊN KÊNH", nhan_j)
    ok(nhan_j.count("thay_giong") == 0,
       "KHÔNG còn lặp mã loại việc `thay_giong` ở chỗ đáng lẽ là tên video",
       nhan_j)
    ok("—" not in nhan_j, "không còn ô trống '—'", nhan_j)
    for xau in ("{RAC", "", "null", "[]"):
        try:
            qp._job_name(_J(type="thay_giong", chan_name=None, vid_path=None,
                            payload=xau))
        except Exception as e:                       # noqa: BLE001
            ok(False, f"payload xấu {xau!r} làm SẬP bảng hàng đợi", str(e))
            break
    else:
        ok(True, "payload rỗng/hỏng KHÔNG làm sập bảng (chỉ mất cái tên)")
    j2 = _J(type="m1_export_clip", chan_name="Kenh A",
            vid_path=r"D:\v\abc.mp4", payload='{"part_no":3}')
    ok("abc" in qp._job_name(j2)[0] and "Kenh A" in qp._job_name(j2)[0],
       "đường XUẤT CLIP cũ KHÔNG đổi", qp._job_name(j2)[0])

    dubbing._eleven_tts = that
    print()
    print("=" * 74)
    print(f"ĐẠT {DAT} · HỎNG {HONG}")
    print("=" * 74)
    return 1 if HONG else 0


if __name__ == "__main__":
    raise SystemExit(main())
