# -*- coding: utf-8 -*-
"""THƯỚC CHẤM "ĐỌC SAI CHỮ" CHO 5 THỨ TIẾNG — Việt · Anh · Hàn · Nhật · Trung.

═══════════════════════════════════════════════════════════════════════════
VÌ SAO PHẢI VIẾT THƯỚC MỚI: THƯỚC CŨ TỰ PHÁT CHỨNG NHẬN
═══════════════════════════════════════════════════════════════════════════
``_do_vieneu_en.wer`` (bản chép của ``_do_chatter.wer``, đang được
``_do_song_ngu.py`` dùng) chuẩn hoá chuỗi bằng::

    re.sub(r"[^0-9a-zà-ỹA-ZÀ-Ỹ\\s]", " ", s.lower())

Dải đó **chỉ có chữ latin và chữ Việt có dấu**. Mọi ký tự Hán · kana · Hangul
đều bị thay bằng dấu cách -> danh sách từ RỖNG -> hàm trả ``(0.0, 0)``.
**Đo thật trước khi viết file này** (không suy đoán):

    wer('역사상 한 번도 없었던 폭풍이', '완전히 다른 아무 말')  ->  (0.0, 0)
    wer('歴史上かつてない嵐が',        'まったく違う文')        ->  (0.0, 0)
    wer('一场史无前例的风暴',          '完全不同的句子')        ->  (0.0, 0)

Tức: chép ra **một câu hoàn toàn khác** vẫn ra **0,0% sai**. Đem thước đó đo
"giọng Multilingual có đọc được tiếng Hàn không" thì mọi giọng đều ĐẠT tuyệt
đối, kể cả giọng câm. Đây đúng họ bẫy ``astats`` (cổng 53) và ``startswith``
(cổng 44): **phép đo hỏng nguy hiểm hơn không đo, vì nó phát chứng nhận.**

═══════════════════════════════════════════════════════════════════════════
CÁCH TÁCH TỪ — MỖI TIẾNG MỘT KIỂU, VÀ NÓI RÕ VÌ SAO
═══════════════════════════════════════════════════════════════════════════
* ``vi`` ``en`` -> **theo TỪ** (dấu cách). Đây là WER đúng nghĩa.
* ``zh`` ``ja`` -> **theo KÝ TỰ** (CER). Hai tiếng này không có dấu cách nên
  không có "từ" để đếm; CER là thước chuẩn của giới nhận dạng tiếng nói cho
  chúng.
* ``ko`` -> **theo KÝ TỰ** (CER) dù tiếng Hàn CÓ dấu cách. Lý do: cách đặt
  dấu cách của máy nghe không ổn định (trợ từ dính/không dính vào danh từ),
  nên chấm theo từ sẽ tính một chỗ cách sai thành hai từ sai. CER là thước
  chuẩn cho tiếng Hàn, cùng lý do.

**HỆ QUẢ PHẢI NHỚ: CẤM SO CHÉO TIẾNG.** Cột ``vi``/``en`` là % TỪ sai, cột
``ko``/``ja``/``zh`` là % KÝ TỰ sai — hai đơn vị khác nhau. Vì vậy mọi kết
luận đều phải so với **TRẦN của CHÍNH tiếng đó** (giọng bản ngữ đọc tiếng
của nó), không bao giờ so số của tiếng này với tiếng kia. Đây cũng đúng luật
``nhan_nha`` giới hạn số 1 và ``giong_bang`` đã chốt.

═══════════════════════════════════════════════════════════════════════════
TỰ KIỂM BỘ DÒ LÀ BẮT BUỘC
═══════════════════════════════════════════════════════════════════════════
``tu_kiem()`` bắt thước phải kêu ĐÚNG CHIỀU ở CẢ 5 TIẾNG: giống hệt -> 0%,
khác hẳn -> gần 100%. Không có mục này thì bản thân file này lại là một cái
thước không ai kiểm — đúng cái nó vừa đi vạch mặt. Mọi phép đo dùng thước
này phải gọi ``tu_kiem()`` TRƯỚC và DỪNG nếu nó trả False.
"""
from __future__ import annotations

import re
import unicodedata

#: Tiếng chấm theo KÝ TỰ (CER) thay vì theo TỪ. Xem docstring.
THEO_KY_TU = frozenset({"zh", "ja", "ko"})

#: Ký tự đáng kể khi chấm theo KÝ TỰ: chữ Hán · kana · Hangul · chữ-số latin.
#: Viết bằng ``\u`` chứ KHÔNG dán ký tự thật vào dải regex — bài học cổng 54:
#: dòng ``"豈-﫿"`` chép từ chú thích "U+F900-U+FAFF" hoá ra là **U+8C48**, dải
#: thật nuốt trọn hangul mà đọc bằng mắt không thấy.
_GIU_KY_TU = re.compile(
    "[^"
    "一-鿿"        # CJK thống nhất (chữ Hán)
    "㐀-䶿"        # CJK mở rộng A
    "぀-ヿ"        # hiragana + katakana (+ dấu chấm câu Nhật)
    "가-힣"        # Hangul âm tiết
    "ᄀ-ᇿ"        # Hangul jamo
    "0-9a-z"
    "]")

#: Bỏ dấu câu khi chấm theo TỪ. Giữ chữ-số và chữ Việt có dấu.
_BO_DAU_CAU = re.compile(r"[^0-9a-zÀ-ɏḀ-ỿ\s]")


def tach_tu(s: str, nn: str) -> list[str]:
    """Chuỗi -> danh sách đơn vị chấm. **HAI BÊN PHẢI QUA CÙNG HÀM NÀY.**"""
    s = unicodedata.normalize("NFC", str(s or "")).lower()
    if nn in THEO_KY_TU:
        return list(_GIU_KY_TU.sub("", s))
    s = _BO_DAU_CAU.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip().split()


def _lev(a: list[str], b: list[str]) -> int:
    """Khoảng cách Levenshtein trên danh sách đơn vị."""
    if not a:
        return len(b)
    tr = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        moi = [i]
        for j in range(1, len(b) + 1):
            moi.append(min(tr[j] + 1, moi[-1] + 1,
                           tr[j - 1] + (a[i - 1] != b[j - 1])))
        tr = moi
    return tr[len(b)]


def ty_le_sai(goc: str, nghe: str, nn: str) -> tuple[float, int]:
    """(tỉ lệ sai 0..1+, số đơn vị của bản GỐC).

    Số đơn vị **0** nghĩa là câu gốc không có gì để chấm -> trả ``(0.0, 0)``
    và người gọi PHẢI bỏ mẫu đó đi, đừng cộng vào trung bình như một mẫu
    "0% sai". Đó chính là chỗ thước cũ chết.
    """
    a = tach_tu(goc, nn)
    b = tach_tu(nghe, nn)
    if not a:
        return 0.0, 0
    return _lev(a, b) / len(a), len(a)


def co_trong(token: str, ban_chep: str, nn: str) -> bool:
    """Bản chép có chứa `token` không — dùng cho phép chấm TỪNG TOKEN.

    So trên chuỗi ĐÃ CHUẨN HOÁ của cùng bộ tách, nên không lệ thuộc dấu câu
    / dấu cách / chữ hoa. Với tiếng chấm-theo-ký-tự thì đây là phép tìm
    chuỗi con trên chuỗi ký tự đã lọc — đúng thứ cần hỏi ("máy có phát ra
    đúng mấy chữ đó không").
    """
    a = tach_tu(token, nn)
    b = tach_tu(ban_chep, nn)
    if not a:
        return False
    if nn in THEO_KY_TU:
        return "".join(a) in "".join(b)
    return " " + " ".join(a) + " " in " " + " ".join(b) + " "


# ---------------------------------------------------------------------------
# TỰ KIỂM — thước phải KÊU, không được là con dấu
# ---------------------------------------------------------------------------
#: (nn, câu gốc, câu KHÁC HẲN cùng tiếng). Câu khác phải cùng tiếng, nếu
#: không thì phép thử chỉ chứng minh "chữ Hàn khác chữ Anh" (chuyện hiển
#: nhiên) chứ không chứng minh thước phân biệt được NỘI DUNG.
_CA_TU_KIEM: tuple[tuple[str, str, str], ...] = (
    ("vi", "Một cơn bão chưa từng có trong lịch sử đang ập tới thành phố này.",
     "Con mèo nhỏ nằm ngủ trên chiếc ghế gỗ cạnh cửa sổ buổi trưa."),
    ("en", "A storm unlike anything in recorded history is closing in.",
     "The small cat was sleeping on a wooden chair beside the window."),
    ("ko", "역사상 한 번도 없었던 폭풍이 이 도시로 다가오고 있습니다.",
     "작은 고양이가 창가의 나무 의자 위에서 자고 있었습니다."),
    ("ja", "歴史上かつてない嵐がこの街に近づいています。",
     "小さな猫が窓辺の木の椅子の上で眠っていました。"),
    ("zh", "一场史无前例的风暴正在逼近这座城市。",
     "一只小猫在窗边的木椅子上睡着了。"),
)

#: Ca CHÉP SAI HẲN của Chatterbox — ca thật, lấy nguyên văn từ nhật ký app.
#: Giữ ở đây vì nó là hình dạng của một ca HỎNG THẬT (giọng tự nhận đa ngôn
#: ngữ đọc ra chữ vô nghĩa, mã thoát 0, không một dòng báo).
CA_CHATTERBOX = ("vi", "Một cơn bão chưa từng có",
                 "Mokonbel, Chutanko, Tronglaichsatanglaich")


def tu_kiem(in_ra: bool = True) -> bool:
    """Bắt thước kêu đúng chiều ở CẢ 5 TIẾNG. False = KHÔNG được đo tiếp."""
    ok = True
    dong = []
    for nn, a, b in _CA_TU_KIEM:
        giong, n1 = ty_le_sai(a, a, nn)
        khac, n2 = ty_le_sai(a, b, nn)
        dat = (n1 >= 5) and (giong == 0.0) and (khac >= 0.5)
        ok = ok and dat
        dong.append(f"  {nn}: {n1:3d} đơn vị · giống hệt {giong*100:5.1f}% · "
                    f"khác hẳn {khac*100:5.1f}%  {'ĐẠT' if dat else 'HỎNG'}")
    nn, a, b = CA_CHATTERBOX
    cb, _ = ty_le_sai(a, b, nn)
    dat_cb = cb >= 0.5
    ok = ok and dat_cb
    dong.append(f"  ca THẬT Chatterbox (vi): {cb*100:5.1f}% sai  "
                f"{'ĐẠT' if dat_cb else 'HỎNG'}")
    # Chốt ngược: thước CŨ phải TRƯỢT đúng 3 tiếng — nếu nó không trượt thì
    # lý do tồn tại của file này đã sai, và phải đọc lại trước khi tin số.
    try:
        from _do_vieneu_en import wer
        truot = [nn for nn, a, b in _CA_TU_KIEM
                 if nn in THEO_KY_TU and wer(a, b)[0] == 0.0]
        dat_cu = sorted(truot) == ["ja", "ko", "zh"]
        ok = ok and dat_cu
        dong.append(f"  thước CŨ (`_do_vieneu_en.wer`) trả 0% oan cho: "
                    f"{truot}  {'ĐẠT' if dat_cu else 'HỎNG'}")
    except Exception as e:                                    # noqa: BLE001
        dong.append(f"  (không nạp được thước cũ để đối chiếu: {e})")
    if in_ra:
        print("TỰ KIỂM THƯỚC 5 TIẾNG" + (" — ĐẠT" if ok else " — HỎNG"))
        print("\n".join(dong))
    return ok


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(0 if tu_kiem() else 2)
