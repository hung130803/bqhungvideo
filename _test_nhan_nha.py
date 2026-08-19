"""CỔNG 76 — MỨC NHẤN NHÁ HIỆN CẠNH MỖI GIỌNG + GIỌNG TRUYỀN CẢM LÊN TRÊN.

**VIỆC NÀY CANH CÁI GÌ:** anh Hùng chọn giọng trong một combo dài 88 dòng mà
trước lượt này combo **không nói giọng nào lên xuống nhiều, giọng nào đọc đều
đều**. Thứ tự thì đọc từ bảng ``_HOT_VOICES`` VIẾT TAY, nên giọng nhấn nhá cao
nhất có thể nằm tận cuối nhóm — ``en-GB-Ryan`` (**5,38**, cao nhất trong 47
giọng Anh) đúng là một ca như vậy.

Nay mỗi dòng combo mang đuôi ``- nhấn nhá 5,4 rất truyền cảm`` lấy từ
``app/core/nhan_nha.py`` (bảng 82 giọng ĐO THẬT), và mọi nhóm sắp giảm dần
theo số đó.

**BỐN LỖI THẬT ĐÃ BẮT ĐƯỢC TRONG LÚC LÀM, MỖI CÁI MỘT CA CANH LẠI:**

* ``ov:nu_am`` là **GIỌNG CHẾT** — câu tả gửi cho OmniVoice chứa chữ ``warm``
  không có trong bảng từ đóng của model, nên **0/4 câu đọc được (2/2 lượt)**
  rồi lùi êm về edge-tts: anh Hùng chọn nó là nghe giọng khác hẳn mà không một
  dòng báo. → CA 2 quét câu tả phải nằm trong bảng từ hợp lệ.
* **KHOÁ BẢNG KHÔNG PHẢI MÃ GIỌNG THẬT**: bảng ghi ``piper:vais1000`` trong
  khi app dùng ``piper:vi_VN-vais1000-medium`` → tra ra ``None``, số đo đúng
  mà không bao giờ hiện. Phép đo KHÔNG lộ ra lỗi này (``_piper_hay_khong``
  nhận mọi id ``piper:``). → CA 3 đòi mọi khoá phải là mã app THẬT SỰ dùng.
* **SỐ HIỆN vs CHỮ HIỆN nói ngược nhau**: Jenny đo 3,06, hiện "3,1" nhưng chấm
  ngưỡng trên số THÔ nên chữ ra "đều đều" — người đọc thấy 3,1 >= ngưỡng 3,1.
  → CA 6.
* **PHÉP ĐO CHO MODEL TIẾNG VIỆT ĐỌC CÂU TIẾNG ANH**: ``cau_cho()`` tách tiền
  tố bằng ``split("-")`` nên ``piper:vais1000`` rơi vào nhánh lùi tiếng Anh →
  ra 1,88 (thấp nhất toàn bảng), trông y hệt một kết luận thật; đo lại bằng
  câu Việt ra **3,11**, lệch **1,23**. → CA 8 canh chính hàm đó.

**BẤT BIẾN SỐNG CÒN (CA 7):** sắp xếp lại **không được làm mất một giọng nào**.
Đổi thứ tự là chỗ rất dễ đánh rơi phần tử mà nhìn combo không ra. Mốc đối
chứng ``BQ_MOC_REF`` = bản phát hành NGAY TRƯỚC tính năng này (**v2.37.0**),
nạp bằng ``git show`` — **KHÔNG dùng ``main``** (sau khi gộp thì ``main``
chính là bản đang test, cổng tự PASS OAN vĩnh viễn — bài học cổng 36/51/52),
kèm chốt "mốc TRÙNG bản đang test -> HỎNG".

Cổng **KHÔNG gọi mạng, KHÔNG tốn lượt Groq, KHÔNG chạy ffmpeg** — nó chấm bảng
số và các hàm thuần. Danh sách giọng edge đọc từ cache 7 ngày; máy chưa có
cache thì các ca cần danh sách tự **BỎ QUA** (không ĐẠT, không HỎNG) chứ không
đỏ oan.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_QSETTINGS_INI", "1")

DAT = HONG = BOQUA = 0
_HONG: list[str] = []
_BOQUA: list[str] = []


def ok(ten: str, dieu_kien: bool, chi_tiet: str = "") -> None:
    global DAT, HONG
    if dieu_kien:
        DAT += 1
        print(f"  ĐẠT  {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))
    else:
        HONG += 1
        _HONG.append(ten)
        print(f"  HỎNG {ten}" + (f" — {chi_tiet}" if chi_tiet else ""))


def bo_qua(ten: str, ly_do: str) -> None:
    global BOQUA
    BOQUA += 1
    _BOQUA.append(ten)
    print(f"  BỎ QUA {ten} — {ly_do}")


def _so_trong_nhan(nhan: str) -> float | None:
    m = re.search(r"nhấn nhá (\d+),(\d+)", nhan)
    return float(f"{m.group(1)}.{m.group(2)}") if m else None


# ----------------------------------------------------------------- CA 1
def ca1_bang_khop_phep_do() -> None:
    """Bảng trong mã phải khớp TỪNG SỐ với file kết quả của phép đo."""
    import json
    from app.core import nhan_nha as nn
    print("\nCA 1 — bảng số khớp chính phép đo")
    f = REPO / "bq_do_nhan_nha_bang" / "ket_qua.json"
    if not f.exists():
        bo_qua("1a bảng khớp file đo", f"chưa có {f.name} trên máy này")
        return
    do = json.loads(f.read_text(encoding="utf-8"))
    dat = {k: v["nhan_nha"] for k, v in do.items() if not v.get("loi")}
    # khoá Piper trong file đo là tên gõ tay lúc đo -> quy về mã THẬT
    from app.core import piper_tts
    for cu in [k for k in dat if k.startswith("piper:")]:
        dat[piper_tts.MA_GIONG] = dat.pop(cu)
    lech = [(k, nn.BANG[k], dat[k]) for k in nn.BANG
            if k in dat and round(nn.BANG[k], 2) != round(dat[k], 2)]
    ok("1a bảng khớp file đo từng số", not lech, str(lech[:3]) or "0 lệch")
    thieu = [k for k in dat if k not in nn.BANG]
    ok("1b không giọng nào đo được mà bị bỏ khỏi bảng", not thieu,
       str(thieu) or "0 sót")
    it_cau = [k for k, v in do.items()
              if not v.get("loi") and v.get("so_cau", 0) < 4]
    ok("1c mọi số trong bảng đo trên ĐỦ 4 câu", not it_cau,
       str(it_cau) or "82/82 đủ 4 câu")


# ----------------------------------------------------------------- CA 2
#: Bảng từ ĐÓNG mà OmniVoice nhận, **chép NGUYÊN VĂN từ lời lỗi của chính
#: model** (`logs/giong_ngoai_20260818.log`: *"Valid English items: ..."*).
#: Câu tả dùng chữ ngoài bảng này -> `ValueError: Unsupported instruct items`
#: -> giọng đọc 0 câu -> lùi êm về edge-tts = "chọn X ra Y".
#:
#: **BẢN ĐẦU CỦA CHÍNH BẢNG NÀY CHÉP THIẾU `young adult` -> CỔNG ĐỎ OAN 2
#: GIỌNG ĐANG CHẠY TỐT.** Ghi lại vì đó là cách hỏng điển hình của mọi ca
#: "quét tĩnh theo danh sách trắng": danh sách chép tay sai thì cổng tố cáo mã
#: LÀNH, mà cổng đỏ oan thì người ta bỏ qua nó (bài học cổng 41 và 47). Sửa
#: bảng này thì phải chép lại từ lời lỗi thật, đừng gõ từ trí nhớ.
TU_HOP_LE = {
    "american accent", "australian accent", "british accent",
    "canadian accent", "child", "chinese accent", "elderly", "female",
    "high pitch", "indian accent", "japanese accent", "korean accent",
    "low pitch", "male", "middle-aged", "moderate pitch",
    "portuguese accent", "russian accent", "teenager", "very high pitch",
    "very low pitch", "whisper", "young adult",
}


def ca2_giong_ov_khong_chet() -> None:
    print("\nCA 2 — câu tả OmniVoice phải nằm trong bảng từ của model")
    from app.core import giong_ngoai as gn
    xau: list[str] = []
    for ma, tt, _ten in gn.GIONG_OV:
        for phan in [p.strip() for p in str(tt).split(",") if p.strip()]:
            if phan not in TU_HOP_LE:
                xau.append(f"{ma}: {phan!r}")
    ok("2a mọi giọng ov: dùng từ hợp lệ", not xau,
       "; ".join(xau) or f"{len(gn.GIONG_OV)}/{len(gn.GIONG_OV)} hợp lệ")
    # TỰ KIỂM BỘ DÒ: bộ dò phải BẮT được câu tả hỏng của bản cũ.
    hong_that = [p for p in "female, middle-aged, warm low pitch".split(", ")
                 if p not in TU_HOP_LE]
    ok("2b TỰ KIỂM bộ dò bắt được câu tả hỏng bản cũ", bool(hong_that),
       f"bắt {hong_that}")


# ----------------------------------------------------------------- CA 3
def ca3_khoa_la_ma_giong_that() -> None:
    """Mọi khoá trong bảng phải là mã giọng app THẬT SỰ đọc được."""
    print("\nCA 3 — khoá bảng phải là mã giọng app dùng thật")
    from app.core import dubbing, giong_ngoai as gn, nhan_nha as nn
    from app.core import piper_tts
    hop_le = {m for m, _t, _n in gn.GIONG_OV} | {piper_tts.MA_GIONG}
    # VieNeu: 20 giọng dựng sẵn vào bảng ngày 19/08/2026. Danh sách hợp lệ
    # phải lấy TỪ CHÍNH `giong_vieneu.GIONG_VN` — gõ tay 20 tên có dấu vào
    # đây là tự đẻ ra một bản sao trôi khác module thật, đúng cái mục 3b này
    # đang canh cho Piper. Thiếu nguồn này thì cổng ĐỎ OAN mỗi lần bảng nhận
    # thêm một họ giọng mới, mà cổng đỏ oan thì người ta bỏ qua nó (bài học
    # cổng 41 và 47).
    try:
        from app.core import giong_vieneu as gv
        hop_le |= {gv.TIEN_TO + k for k, _m in gv.GIONG_VN}
    except Exception:                                          # noqa: BLE001
        pass
    allv = dubbing._fetch_all_voices()
    if not allv:
        bo_qua("3a khoá là mã giọng thật", "chưa có cache danh sách giọng")
        return
    hop_le |= {v["ShortName"] for v in allv}
    la = sorted(k for k in nn.BANG if k not in hop_le)
    ok("3a mọi khoá tra ra được một giọng thật", not la,
       str(la) or f"{len(nn.BANG)}/{len(nn.BANG)} khoá hợp lệ")
    # TỰ KIỂM BỘ DÒ: mục 3a chỉ có nghĩa nếu nó THẬT SỰ bắt được khoá lạ.
    # Không có mục này thì mọi lượt nới `hop_le` đều có thể vô tình biến 3a
    # thành con dấu (đúng bẫy "quét tĩnh chỉ hỏi có mặt không", cổng 56d).
    ok("3a' TỰ KIỂM bộ dò bắt được khoá lạ",
       "xx-YY-KhongTonTaiNeural" not in hop_le
       and "vn:KhongCoGiongNay" not in hop_le)
    # đúng lỗi đã sập: mã Piper phải là mã ĐẦY ĐỦ
    ok("3b mã Piper trong bảng là mã đầy đủ của app",
       nn.muc(piper_tts.MA_GIONG) is not None,
       f"{piper_tts.MA_GIONG} -> {nn.muc(piper_tts.MA_GIONG)}")


# ----------------------------------------------------------------- CA 4
def ca4_moi_giong_gon_co_so() -> None:
    print("\nCA 4 — mọi giọng của danh sách gọn phải NÓI RÕ mình ở đâu")
    from app.core import dubbing, nhan_nha as nn
    allv = dubbing._fetch_all_voices()
    if not allv:
        bo_qua("4a giọng gọn có đuôi", "chưa có cache danh sách giọng")
        return
    gon = [v["ShortName"] for v in allv
           if v.get("ShortName") in dubbing._HOT_VOICES
           or dubbing._la_giong_mo_them(v)]
    # 19/08/2026 — MỆNH ĐỀ ĐỔI VÌ *LUẬT* ĐỔI, VÀ NÓ CHẶT HƠN BẢN CŨ.
    # Bản cũ: *"mọi giọng gọn phải CÓ SỐ"*. Mệnh đề đó chỉ đúng khi tấm vé vào
    # combo do phép đo NHẤN NHÁ cấp — và chính nó đã khoá 137 giọng của 60 thứ
    # tiếng lại (xem `app/core/giong_doc.py`). Nay vé do bằng chứng ĐỌC THẬT
    # cấp, nên combo có giọng chưa đo nhấn nhá là chuyện ĐÚNG THIẾT KẾ.
    # Cái thật sự phải canh không phải "có số" mà là **KHÔNG BAO GIỜ CÓ DÒNG
    # TRỐNG TRƠN**: mỗi dòng phải hoặc mang số, hoặc NÓI THẲNG là chưa đo. Dòng
    # trống là chỗ người đọc không phân biệt được "chưa đo" với "app quên", và
    # đó mới là bệnh mục này sinh ra để chặn.
    cam = sorted(s for s in gon if not nn.nhan(s))
    ok("4a không dòng nào TRỐNG TRƠN (có số, hoặc nói thẳng 'chưa đo')",
       not cam, str(cam[:5]) or f"{len(gon)}/{len(gon)} dòng có đuôi")
    _chua = sorted(s for s in gon if nn.muc(s) is None)
    ok("4a' giọng chưa đo -> ĐÚNG chữ 'chưa đo', KHÔNG một chữ số nào",
       all(nn.nhan(s) == nn.CHUA_DO for s in _chua)
       and not any(c.isdigit() for s in _chua for c in nn.nhan(s)),
       f"{len(_chua)} giọng chưa đo / {len(gon)} giọng gọn")
    anh = [s for s in gon if s.startswith("en-")]
    ok("4b đủ 47 giọng tiếng Anh và giọng nào cũng có số",
       len(anh) == 47 and all(nn.muc(s) is not None for s in anh),
       f"{len(anh)} giọng en-*")


# ----------------------------------------------------------------- CA 5
def ca5_nhan_va_thu_tu() -> None:
    print("\nCA 5 — nhãn combo mang số, và mỗi nhóm sắp GIẢM DẦN")
    from app.core import dubbing, nhan_nha as nn
    if not dubbing._fetch_all_voices():
        bo_qua("5a nhãn + thứ tự", "chưa có cache danh sách giọng")
        return
    ds = dubbing.list_recap_voices()
    thieu_so = [lbl for lbl, vid in ds
                if vid and nn.muc(vid) is not None
                and _so_trong_nhan(lbl) is None]
    ok("5a giọng có số thì nhãn PHẢI hiện số", not thieu_so,
       str(thieu_so[:3]) or "0 dòng thiếu")
    sai_so = [(lbl, vid) for lbl, vid in ds
              if vid and _so_trong_nhan(lbl) is not None
              and abs(_so_trong_nhan(lbl) - round(nn.muc(vid), 1)) > 0.001]
    ok("5b số trên nhãn khớp bảng", not sai_so, str(sai_so[:3]) or "0 lệch")
    # thứ tự: cắt theo nhóm (dòng voice_id rỗng = nhãn nhóm)
    nhom: list[list[float]] = []
    cur: list[float] = []
    for _lbl, vid in ds:
        if not vid:
            if cur:
                nhom.append(cur)
            cur = []
        else:
            v = nn.muc(vid)
            if v is not None:
                cur.append(v)
    if cur:
        nhom.append(cur)
    xau = [g for g in nhom if g != sorted(g, reverse=True)]
    ok("5c mọi nhóm sắp nhấn nhá GIẢM DẦN", not xau,
       f"{len(nhom)} nhóm, {len(xau)} nhóm sai thứ tự")
    # giọng CHƯA ĐO phải nằm CUỐI nhóm, không chen giữa
    chen = 0
    cur2: list[bool] = []
    for _lbl, vid in ds:
        if not vid:
            if cur2 and any(cur2[i] and not cur2[i + 1]
                            for i in range(len(cur2) - 1)):
                chen += 1
            cur2 = []
        else:
            cur2.append(nn.muc(vid) is None)
    ok("5d giọng CHƯA ĐO nằm cuối nhóm, không chen giữa", chen == 0,
       f"{chen} nhóm bị chen")


# ----------------------------------------------------------------- CA 6
def ca6_nhan_tu_nhat_quan() -> None:
    print("\nCA 6 — số hiện và chữ hiện không được nói ngược nhau")
    from app.core import nhan_nha as nn
    xau = []
    for v in nn.BANG:
        s = nn.nhan(v)
        so = _so_trong_nhan(s)
        if so is not None and nn.chu(so) not in s:
            xau.append((v, s))
    ok("6a chữ chấm trên SỐ ĐÃ LÀM TRÒN", not xau,
       str(xau[:3]) or f"{len(nn.BANG)}/{len(nn.BANG)} nhất quán")
    # đúng ca đã sập: Jenny 3,06 -> hiện 3,1 thì chữ phải là mức của 3,1
    j = nn.nhan("en-US-JennyNeural")
    ok("6b ca Jenny (3,06 -> 3,1) hiện đúng mức của số làm tròn",
       "3,1" in j and nn.chu(3.1) in j, j.strip())
    ok("6c giọng CHƯA ĐO trả nhãn RỖNG, không bịa số",
       nn.nhan("khong-co-that-9x") == "", "rỗng")
    co_emoji = [v for v in nn.BANG if any(ord(c) > 0x2100 for c in nn.nhan(v))]
    ok("6d nhãn nhấn nhá KHÔNG EMOJI", not co_emoji, str(co_emoji[:3]) or "0")


# ----------------------------------------------------------------- CA 7
def ca7_bat_bien_khong_mat_giong() -> None:
    print("\nCA 7 — BẤT BIẾN: sắp lại KHÔNG được làm mất giọng nào")
    import importlib.util
    from app.core import dubbing
    moc = os.environ.get("BQ_MOC_REF", "v2.37.0")
    r = subprocess.run(["git", "show", f"{moc}:app/core/dubbing.py"],
                       capture_output=True, cwd=str(REPO), timeout=60)
    if r.returncode != 0:
        bo_qua("7a bất biến tập giọng", f"không lấy được mốc {moc}")
        return
    src = r.stdout.decode("utf-8")
    nay = (REPO / "app" / "core" / "dubbing.py").read_text(encoding="utf-8")
    # CHỐNG PASS OAN: mốc trùng bản đang test thì phép so vô nghĩa
    ok("7a bản mốc KHÁC bản đang test", src != nay, f"mốc {moc}")
    if src == nay:
        return
    tmp = REPO / "_moc_dubbing_cong76.py"
    tmp.write_text(src, encoding="utf-8")
    try:
        spec = importlib.util.spec_from_file_location("_moc_dub76", tmp)
        m = importlib.util.module_from_spec(spec)
        sys.modules["_moc_dub76"] = m
        spec.loader.exec_module(m)
        if not dubbing._fetch_all_voices():
            bo_qua("7b bất biến tập giọng", "chưa có cache danh sách giọng")
            return
        a = {v for _l, v in m.list_recap_voices() if v}
        b = {v for _l, v in dubbing.list_recap_voices() if v}
        ok("7b recap: KHÔNG mất giọng nào so với mốc", not (a - b),
           f"mất {sorted(a - b)}" if a - b else f"mốc {len(a)} -> nay {len(b)}")
        for lang in ("vi", "en"):
            x = {v for _l, v in m.list_voices_for(lang) if v}
            y = {v for _l, v in dubbing.list_voices_for(lang) if v}
            ok(f"7c list_voices_for({lang!r}) giữ NGUYÊN tập giọng", x == y,
               f"mốc {len(x)} -> nay {len(y)}")
    finally:
        sys.modules.pop("_moc_dub76", None)
        tmp.unlink(missing_ok=True)


# ----------------------------------------------------------------- CA 8
def ca8_phep_do_dung_tieng() -> None:
    print("\nCA 8 — phép đo phải cho mỗi giọng đọc ĐÚNG TIẾNG của nó")
    import importlib
    m = importlib.import_module("_do_nhan_nha_bang")
    from app.core import piper_tts
    ok("8a giọng Piper đọc câu TIẾNG VIỆT (không phải tiếng Anh)",
       m.cau_cho(piper_tts.MA_GIONG) == m.CAU["vi"], "vi")
    ok("8b giọng OmniVoice đọc câu TIẾNG VIỆT",
       m.cau_cho("ov:nam_tre") == m.CAU["vi"], "vi")
    ok("8c giọng edge vẫn đọc đúng tiếng của locale",
       m.cau_cho("ja-JP-KeitaNeural") == m.CAU["ja"]
       and m.cau_cho("en-GB-RyanNeural") == m.CAU["en"], "ja/en")
    # TỰ KIỂM: cách tách CŨ (split "-") đúng là trả về tiếng Anh cho Piper
    cu = m.CAU.get(piper_tts.MA_GIONG.split("-")[0].lower()) or m.CAU["en"]
    ok("8d TỰ KIỂM bẫy cũ: split('-') cho Piper ra câu tiếng ANH",
       cu == m.CAU["en"], "bẫy tái hiện được")


# ----------------------------------------------------------------- CA 9
def ca9_nhan_giong_ngoai() -> None:
    print("\nCA 9 — nhãn giọng ngoài (OmniVoice / Piper) cũng mang số")
    from app.core import giong_ngoai as gn, nhan_nha as nn, piper_tts
    thieu = [m for m, _t, _n in gn.GIONG_OV
             if nn.muc(m) is not None
             and _so_trong_nhan(gn.nhan_giong(m)) is None]
    ok("9a mọi giọng ov: hiện số trong nhãn", not thieu, str(thieu) or "5/5")
    ok("9b nhãn Piper hiện số",
       _so_trong_nhan(piper_tts.NHAN_GIONG) is not None,
       piper_tts.NHAN_GIONG)
    ok("9c nhãn Piper KHÔNG EMOJI",
       not any(ord(c) > 0x2100 for c in piper_tts.NHAN_GIONG), "sạch")
    # số của giọng anh Hùng đang dùng — mệnh đề bị chép sai suốt nhiều lượt
    ok("9d ov:nam_tre KHÔNG ở đáy thang (đề bài ghi 2,16 là TRẢI 11 giọng)",
       nn.muc("ov:nam_tre") is not None
       and nn.muc("ov:nam_tre") > nn.muc("vi-VN-NamMinhNeural"),
       f"ov:nam_tre {nn.muc('ov:nam_tre')} > NamMinh "
       f"{nn.muc('vi-VN-NamMinhNeural')}")


if __name__ == "__main__":
    print("CỔNG 76 — NHẤN NHÁ HIỆN CẠNH MỖI GIỌNG + SẮP TRUYỀN CẢM LÊN TRÊN")
    print("=" * 72)
    for f in (ca1_bang_khop_phep_do, ca2_giong_ov_khong_chet,
              ca3_khoa_la_ma_giong_that, ca4_moi_giong_gon_co_so,
              ca5_nhan_va_thu_tu, ca6_nhan_tu_nhat_quan,
              ca7_bat_bien_khong_mat_giong, ca8_phep_do_dung_tieng,
              ca9_nhan_giong_ngoai):
        try:
            f()
        except Exception as e:                                # noqa: BLE001
            HONG += 1
            _HONG.append(f"{f.__name__} NỔ")
            print(f"  HỎNG {f.__name__} NỔ — {type(e).__name__}: {e}")
    print("\n" + "=" * 72)
    print(f"ĐẠT {DAT} · HỎNG {HONG}" + (f" · BỎ QUA {BOQUA}" if BOQUA else ""))
    if _HONG:
        print("HỎNG: " + " | ".join(_HONG))
    if _BOQUA:
        print("BỎ QUA: " + " | ".join(_BOQUA))
    sys.exit(1 if HONG else 0)
