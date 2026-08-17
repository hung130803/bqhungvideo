"""
Tạo PHỤ ĐỀ CHẠY CHỮ khớp lời (kiểu TikTok) từ mốc-thời-gian-TỪNG-TỪ của whisper.
Xuất file .ass (libass) để ffmpeg "đốt" (burn) vào video.

Quan trọng: clip đã GHÉP nhiều đoạn (bỏ phần thừa) -> phải ÁNH XẠ thời gian của
từ về timeline ĐẦU RA (sau khi cắt ghép), bỏ các từ rơi vào đoạn bị cắt.
"""
from __future__ import annotations

from pathlib import Path


def _fmt(t: float) -> str:
    if t < 0:
        t = 0.0
    cs = int(round(t * 100))
    h = cs // 360000
    m = (cs // 6000) % 60
    s = (cs // 100) % 60
    c = cs % 100
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def _remap_words(words: list, segments: list) -> list:
    """Đưa mốc từ về timeline đầu ra (sau ghép); bỏ từ nằm trong đoạn bị cắt.
    Mỗi từ gắn seg_idx để KHÔNG gom chữ vắt qua chỗ cắt (tránh đọc linh tinh)."""
    out, offset = [], 0.0
    for si, (s, e) in enumerate(segments):
        s = float(s); e = float(e)
        for w in words:
            try:
                ws, we = float(w["start"]), float(w["end"])
            except (KeyError, ValueError, TypeError):
                continue
            if ws >= s and ws < e:
                a = offset + (ws - s)
                b = offset + (min(we, e) - s)
                txt = (w.get("word") or "").strip()
                if txt:
                    out.append([a, max(a + 0.06, b), txt, si])
        offset += (e - s)
    out.sort(key=lambda x: x[0])
    return out


#: SỐ KÝ TỰ tối đa của MỘT "từ ảo" CJK sau khi gom, theo MODE của preset. Mode
#: nào TỰ gom thêm ở dưới (group 3 · karaoke 4 · active/hlbox 3 cụm) thì gom ở
#: đây ÍT thôi, không thì dòng phụ đề dài 12-18 chữ -> tràn 3 dòng / cắt đáy.
#: `word` KHÔNG gom thêm nữa nên phải gom đủ đọc ngay tại đây.
#: Đo ở 1080x1920, cỡ chữ 0,055*h = 105 px: bề rộng dùng được 1080-2*151 = 778
#: px ≈ 7 chữ Hán/dòng -> 6 là vừa 1 dòng, còn dư chỗ cho viền.
_CJK_MAX = {"word": 6, "group": 2, "karaoke": 2, "active": 2, "hlbox": 2}


def _noi_cum(parts: list, tho: list | None = None) -> str:
    """Nối các từ của MỘT cụm thành chuỗi hiển thị. Giữa 2 từ CJK KHÔNG chèn
    dấu cách (Nhật/Trung/Hàn không dùng dấu cách — chèn vào ra
    'これは 誰も語 らなか った' / '他们 发现 东'), còn lại nối bằng 1 dấu cách.

    `parts` = chuỗi ĐÃ có tag ASS (nhánh 'active'); `tho` = chữ THÔ tương ứng
    để dò CJK (tag `{\\1c…}` không phải chữ nên phải dò trên bản thô).
    BẤT BIẾN: không có từ CJK nào -> trả Y HỆT `" ".join(parts)` (đường EN/VI
    không đổi 1 byte)."""
    tho = parts if tho is None else tho
    ra = ""
    for k, ps in enumerate(parts):
        if k:
            ra += "" if (_co_cjk(tho[k]) and _co_cjk(tho[k - 1])) else " "
        ra += ps
    return ra


def _gom_cjk(words: list, max_ky_tu: int = 6, max_dur: float = 1.8,
             gap: float = 0.45) -> list:
    """GOM các "từ" CJK 1 KÝ TỰ thành CỤM ĐỌC ĐƯỢC.

    LỖI THẬT (đo 14/08/2026 trên video tiếng Trung của anh Hùng
    `一只手表牵扯出一个巨大的秘密`): Groq whisper-large-v3 trả **MỐC TỪNG KÝ TỰ**
    cho tiếng Trung — 1.020/1.074 "từ" chỉ dài 1 ký tự. `_word_cues` cho mỗi từ
    1 dòng nên file .ass ra **1,07 ký tự/dòng, trung bình 0,175 s/dòng** (min
    0,05 s): người xem thấy MỘT chữ Hán nhấp nháy 6 lần/giây, KHÔNG ĐỌC ĐƯỢC.
    ffmpeg vẫn trả mã 0, khung vẫn đủ pixel -> cổng đếm pixel PASS OAN.

    Gom TRƯỚC khi dựng cue nên MỌI mode (word/group/karaoke/active/hlbox) đều
    hết bệnh, không phải vá 5 chỗ. Ngắt cụm khi: đủ `max_ky_tu` ký tự HIỂN THỊ ·
    quá `max_dur` giây · hở > `gap` giây (khoảng lặng = ý mới) · đổi đoạn ghép
    (`seg_idx`) · gặp dấu KẾT CÂU. Từ latin/số xen giữa KHÔNG bị gom vào chữ Hán.
    BẤT BIẾN: không có ký tự CJK nào -> trả Y HỆT list vào (đường EN/VI KHÔNG
    đổi 1 byte — cổng 21 so từng byte 18 preset cũ)."""
    if not any(_co_cjk(str(w[2])) for w in words or []):
        return words                       # bất biến: non-CJK y nguyên
    ket_cau = "。！？；…!?;、，,"
    ra: list = []
    for w in words or []:
        t = str(w[2])
        gop = bool(ra) and _co_cjk(ra[-1][2]) and (
            _co_cjk(t) or _chi_dau_cau(t))
        if gop:
            c = ra[-1]
            if (w[3] != c[3]                              # khác đoạn ghép
                    or len([x for x in c[2] if not _chi_dau_cau(x)])
                    >= max_ky_tu                          # đủ chữ
                    or (w[1] - c[0]) > max_dur            # cụm quá dài
                    or (w[0] - c[1]) > gap                # có khoảng lặng
                    or (c[2] and c[2][-1] in ket_cau)):   # vừa hết câu
                gop = False
        if gop:
            c = ra[-1]
            ra[-1] = [c[0], max(c[1], w[1]),
                      c[2] + ("" if _co_cjk(t) or _chi_dau_cau(t) else " ") + t,
                      c[3]]
        else:
            ra.append([w[0], w[1], t, w[3]])
    return ra


def _group(words: list, max_words: int = 3, max_dur: float = 2.4,
           gap: float = 0.6) -> list:
    """Gom 2-3 từ/cụm. KHÔNG gom qua ranh giới đoạn ghép (seg_idx đổi -> cụm mới).
    max_dur NỚI 1.3 -> 2.4s: whisper mỗi từ ~0.4-0.6s nên 3 từ ~1.5-1.8s hay
    vượt 1.3 -> cụm bị teo còn 1-2 từ (lỗi 'chọn cụm mà hiện 1-2 chữ'). Nới
    trần thời lượng cho cụm đủ 2-3 từ như tên gọi."""
    chunks, cur = [], []
    for w in words:
        if not cur:
            cur = [w]
            continue
        if (len(cur) >= max_words or (w[1] - cur[0][0]) > max_dur
                or (w[0] - cur[-1][1]) > gap or w[3] != cur[-1][3]):
            chunks.append(cur); cur = [w]
        else:
            cur.append(w)
    if cur:
        chunks.append(cur)
    return [[ch[0][0], ch[-1][1], _noi_cum([c[2] for c in ch])]
            for ch in chunks]


def group_word_cues(word_cues: list, max_words: int = 3,
                    max_dur: float = 2.4, gap: float = 0.6) -> list:
    """Gom danh sách cue TỪNG TỪ [(a,b,txt),...] (đã ở TIMELINE ĐẦU RA) thành
    CỤM 2-3 từ [(a,b,txt_cụm),...] — dùng cho phụ đề RECAP khi user chọn kiểu
    'cụm' (group): trước đây recap LUÔN tách từng từ dù chọn cụm (lỗi 'chọn
    chạy chữ theo cụm nhưng hiện 1 chữ'). Cắt cụm mới khi: đủ max_words từ,
    quá max_dur giây, hoặc hở > gap (khoảng lặng -> câu/ý mới). Hàm thuần."""
    chunks, cur = [], []
    for c in word_cues or []:
        try:
            a, b, txt = float(c[0]), float(c[1]), str(c[2]).strip()
        except (TypeError, ValueError, IndexError):
            continue
        if not txt:
            continue
        if not cur:
            cur = [[a, b, txt]]
            continue
        if (len(cur) >= max_words or (b - cur[0][0]) > max_dur
                or (a - cur[-1][1]) > gap):
            chunks.append(cur); cur = [[a, b, txt]]
        else:
            cur.append([a, b, txt])
    if cur:
        chunks.append(cur)
    return [[ch[0][0], ch[-1][1], _noi_cum([w[2] for w in ch])]
            for ch in chunks]


def preset_mode(preset: str) -> str:
    """Trả MODE của 1 preset phụ đề (word/karaoke/group/active). Không có ->
    mode của preset mặc định. Dùng để biết user chọn kiểu 'cụm' (group)."""
    p = CAPTION_PRESETS.get(preset) or CAPTION_PRESETS[DEFAULT_PRESET]
    return p.get("mode", "word")


def _word_cues(words: list) -> list:
    """TỪNG TỪ một cue -> khớp SÁT lúc nói nhất (kiểu CapCut auto-caption).
    Mỗi từ hiện đúng lúc bắt đầu nói, giữ tới khi từ KẾ bắt đầu (cùng đoạn, sát
    nhau) nên không nhấp nháy; im lặng dài thì tắt theo end của từ."""
    out = []
    n = len(words)
    for i, w in enumerate(words):
        a, b = w[0], w[1]
        if i + 1 < n and words[i + 1][3] == w[3] and words[i + 1][0] - b < 0.45:
            end = words[i + 1][0]          # giữ tới từ kế (liền mạch) -> khớp lời
        else:
            end = b + 0.15                 # cuối câu/trước khoảng lặng -> tắt sớm
        out.append([a, max(a + 0.05, end), w[2]])
    return out


def _karaoke_cues(words: list, max_words: int = 4, max_dur: float = 2.6,
                  gap: float = 0.55) -> list:
    """Karaoke: gom câu ngắn, mỗi từ 1 tag \\kf -> nói tới đâu chữ SÁNG tới đó
    (mượt). Không vắt qua chỗ ghép (seg_idx đổi -> cụm mới)."""
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or (w[1] - cur[0][0]) > max_dur
                    or (w[0] - cur[-1][1]) > gap or w[3] != cur[-1][3]):
            chunks.append(cur); cur = [w]
        else:
            cur.append(w)
    if cur:
        chunks.append(cur)
    out = []
    for ch in chunks:
        start, prev, parts = ch[0][0], ch[0][0], []
        for i, w in enumerate(ch):
            lead = int(round(max(0.0, w[0] - prev) * 100))
            if lead > 0:
                parts.append("{\\k%d}" % lead)        # chờ (chưa tô sáng)
            dur = int(round(max(0.08, w[1] - w[0]) * 100))
            # dấu cách SAU mỗi từ — trừ khi từ này VÀ từ kế đều là CJK (Nhật/
            # Trung/Hàn không dùng dấu cách; chèn vào ra '借助金 属探测 仪仔细').
            _sp = "" if (i + 1 < len(ch) and _co_cjk(str(w[2]))
                         and _co_cjk(str(ch[i + 1][2]))) else " "
            parts.append("{\\kf%d}%s%s" % (dur, _esc(w[2]), _sp))
            prev = w[1]
        out.append([start, ch[-1][1] + 0.25, "".join(parts).strip()])
    return out


def _chunks(words: list, max_words: int = 5, max_dur: float = 2.8,
            gap: float = 0.6) -> list:
    """Gom thành CỤM (cả câu ngắn) — dùng cho kiểu 'hiện cả câu'. Không vắt
    qua chỗ ghép (seg_idx đổi -> cụm mới). Trả list các cụm (list từ [a,b,txt,si])."""
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or (w[1] - cur[0][0]) > max_dur
                    or (w[0] - cur[-1][1]) > gap or w[3] != cur[-1][3]):
            chunks.append(cur); cur = [w]
        else:
            cur.append(w)
    if cur:
        chunks.append(cur)
    return chunks


def apply_case(text: str, mode: str) -> str:
    """Đổi KIỂU CHỮ HIỂN THỊ (không đổi mốc/timing). mode:
      "" / "keep" -> giữ nguyên
      "upper"     -> HOA (unicode-safe, tiếng Việt có dấu OK)
      "lower"     -> thường
      "title"     -> Hoa Đầu Từ (tách theo dấu cách, chữ đầu mỗi từ viết hoa)
    Dùng chung cho phụ đề gốc (cap_case), AI kể (narr_case), hook (hook_case),
    và lớp chữ overlay title/part (hook_case/part_case)."""
    if not text:
        return text
    m = (mode or "").strip().lower()
    if m == "upper":
        return text.upper()
    if m == "lower":
        return text.lower()
    if m == "title":
        # tách theo dấu cách (giữ nguyên khoảng trắng gốc) — chữ đầu mỗi từ HOA,
        # phần còn lại thường. .title() của python vỡ ở dấu ' / số (it's->It'S)
        # nên tự tách bằng space cho tiếng Việt/Anh đúng.
        return " ".join(
            (w[:1].upper() + w[1:].lower()) if w else w
            for w in text.split(" "))
    return text


def _esc(text: str) -> str:
    return (text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")
                .replace("\n", " ").strip())


def _chi_dau_cau(t: str) -> bool:
    """Chuỗi CHỈ có dấu câu/khoảng trắng (whisper hay tách ra ',' '.' '…' riêng).
    Dùng để KHÔNG chiếu ô nền sáng lên một dấu phẩy (nhìn rất vô nghĩa)."""
    return not any(c.isalnum() for c in (t or ""))


def _co_cjk(t: str) -> bool:
    """Có chữ Nhật/Trung/Hàn? -> nối các cụm KHÔNG chèn dấu cách (những thứ
    tiếng này không dùng dấu cách; chèn vào là ra 'これは 誰も語 らなか った')."""
    for c in t or "":
        o = ord(c)
        if (0x3040 <= o <= 0x30FF or 0x3400 <= o <= 0x4DBF
                or 0x4E00 <= o <= 0x9FFF or 0xAC00 <= o <= 0xD7AF
                or 0xF900 <= o <= 0xFAFF):
            return True
    return False


#: FONT CHO CHỮ CJK, theo thứ tự ƯU TIÊN — (tên họ font khai trong .ass,
#: các tên FILE để kiểm "máy này có thật không").
#: ĐO 14/08/2026 trên máy anh Hùng: 12/12 font đóng gói trong
#: `app/assets/fonts` có **0 glyph CJK**. Chữ Hán hiện được là nhờ libass TỰ
#: LÙI sang font hệ điều hành — thứ tự lùi do fontconfig quyết định, app không
#: kiểm soát: khai 'Montserrat' thì nó đi
#: `Montserrat-Bold -> YuGothicUI-Semibold (NHẬT) -> MicrosoftJhengHeiUIBold
#: (Trung PHỒN THỂ)`, tức phụ đề tiếng Trung GIẢN THỂ đang vẽ bằng font Nhật.
#: Khai thẳng 'Microsoft YaHei' -> libass chọn `MicrosoftYaHei-Bold` NGAY, 0
#: lượt lùi. Máy KHÔNG có font nào trong danh sách -> giữ nguyên font user
#: chọn, libass lùi y như cũ (KHÔNG làm xấu đi máy nhân viên).
_CJK_FONT_UNG = {
    "trung": (("Microsoft YaHei", ("msyh.ttc", "msyh.ttf")),
              ("Microsoft JhengHei", ("msjh.ttc", "msjh.ttf")),
              ("SimSun", ("simsun.ttc",)),
              ("SimHei", ("simhei.ttf",))),
    "nhat": (("Yu Gothic UI", ("YuGothR.ttc", "YuGothM.ttc")),
             ("Meiryo", ("meiryo.ttc",)),
             ("MS Gothic", ("msgothic.ttc",))),
    "han": (("Malgun Gothic", ("malgun.ttf",)),
            ("Batang", ("batang.ttc",)),
            ("Gulim", ("gulim.ttc",))),
}
_CJK_FONT_NHO: dict = {}


def _thu_muc_font_he() -> list:
    """Thư mục font của Windows (máy + hồ sơ user). Không phải Windows -> []."""
    import os
    ra = []
    w = os.environ.get("WINDIR") or os.environ.get("SystemRoot")
    if w:
        ra.append(os.path.join(w, "Fonts"))
    la = os.environ.get("LOCALAPPDATA")
    if la:
        ra.append(os.path.join(la, "Microsoft", "Windows", "Fonts"))
    return [d for d in ra if os.path.isdir(d)]


def _chu_gi(t: str) -> str:
    """Chữ này là TRUNG / NHẬT / HÀN? '' = không phải CJK.
    Kana -> Nhật · Hangul -> Hàn · chỉ chữ Hán -> Trung (tiếng Nhật viết THUẦN
    kanji gần như không có, còn tiếng Trung thì KHÔNG BAO GIỜ có kana)."""
    kana = hangul = han = False
    for c in t or "":
        o = ord(c)
        if 0x3040 <= o <= 0x30FF:
            kana = True
        elif 0xAC00 <= o <= 0xD7AF:
            hangul = True
        elif (0x3400 <= o <= 0x4DBF or 0x4E00 <= o <= 0x9FFF
                or 0xF900 <= o <= 0xFAFF):
            han = True
    if kana:
        return "nhat"
    if hangul:
        return "han"
    return "trung" if han else ""


def font_cjk(text: str, font: str = "") -> str:
    """FONT nên khai trong .ass cho chuỗi `text`.

    BẤT BIẾN: `text` KHÔNG có ký tự CJK nào -> trả Y HỆT `font` (đường EN/VI
    không đổi 1 byte). Có CJK -> trả font CJK ĐẦU TIÊN mà MÁY NÀY CÓ THẬT;
    không có cái nào -> vẫn trả `font` (giữ nguyên hành vi cũ)."""
    ngon = _chu_gi(text)
    if not ngon:
        return font
    if ngon not in _CJK_FONT_NHO:
        import os
        thu = _thu_muc_font_he()
        chon = ""
        for ho, files in _CJK_FONT_UNG[ngon]:
            if any(os.path.isfile(os.path.join(d, f))
                   for d in thu for f in files):
                chon = ho
                break
        _CJK_FONT_NHO[ngon] = chon
    return _CJK_FONT_NHO[ngon] or font


def _ass_color(hexv: str) -> str:
    """#RRGGBB -> &H00BBGGRR (ASS dùng BGR)."""
    h = (hexv or "#FFFFFF").lstrip("#")
    if len(h) != 6:
        return "&H00FFFFFF"
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}".upper()


def _alpha_color(hexv: str, alpha: int) -> str:
    """#RRGGBB + alpha (0=đặc..255=trong) -> &HAABBGGRR."""
    h = (hexv or "#000000").lstrip("#")
    if len(h) != 6:
        h = "000000"
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


# ---- NEON + chọn TỪ KHÓA để tô nổi (Selective Keyword Highlight) ----
NEON_PALETTE = ["#39FF14", "#FF2D95", "#FFE000", "#16E0FF", "#FF6A00"]
_STOP = set((
    # English (từ nối/đệm + đại từ)
    "the a an and or but of to in on at is are was were be been am i you he she "
    "it we they me my your his her our their this that these those for with as so "
    "do does did have has had will would can could just not no yes if then than "
    "out up off get got too very also "
    # Tiếng Việt: từ nối/đệm
    "là và của một các có không được người này đó cho khi với thì mà ở ra vào "
    "rồi đã đang sẽ bị cũng nữa lại nên cứ chỉ đi nhé ạ à ơi cái con những "
    "rất quá thôi luôn vẫn còn từ về theo cùng hay hoặc nhưng vì do bởi "
    # Tiếng Việt: đại từ (không nổi bật)
    "tôi tao tớ mình em anh chị mày nó họ ta chúng ông bà cô chú bác ai gì "
).split())


def _is_keyword(word: str) -> bool:
    """Từ 'đáng nổi bật' = từ có NGHĨA (không phải từ nối/đệm/đại từ)."""
    t = word.strip().strip(".,!?;:\"'…-").lower()
    return len(t) >= 2 and t not in _STOP


# ---- BỘ KIỂU PHỤ ĐỀ (chọn được, chỉnh màu) ----
# mode: word (từng từ + nhảy) | karaoke (sáng dần) | group (2-3 từ)
CAPTION_PRESETS = {
    "Vàng nhảy (TikTok)": {"mode": "word", "color": "#FFD83D",
                           "outline": "#241900", "ow": 0.12, "shadow": 2,
                           "animate": True},
    "Karaoke sáng dần": {"mode": "karaoke", "color": "#FFE23D",
                         "unsung": "#FFFFFF", "outline": "#241900",
                         "ow": 0.11, "shadow": 2},
    "Trắng đơn giản": {"mode": "word", "color": "#FFFFFF", "outline": "#000000",
                       "ow": 0.11, "shadow": 1},   # trắng, chạy từng từ, KHÔNG nhảy
    "Trắng viền đen": {"mode": "word", "color": "#FFFFFF", "outline": "#000000",
                       "ow": 0.14, "shadow": 1, "animate": True},
    "Nền hộp đen": {"mode": "group", "color": "#FFFFFF", "outline": "#000000",
                    "ow": 0.0, "shadow": 0, "box": True, "box_color": "#000000"},
    "Viền neon": {"mode": "word", "color": "#FFFFFF", "outline": "#19E3FF",
                  "ow": 0.12, "shadow": 6, "glow": "#19E3FF", "animate": True},
    "Neon nổi từ khóa": {"mode": "word", "color": "#FFFFFF", "outline": "#0A0A0A",
                         "ow": 0.07, "shadow": 0, "highlight": True,
                         "upper": True},
    # CẢ CÂU hiện sẵn (trắng) — từ ĐANG NÓI nhảy sang VÀNG, chạy theo lời.
    "Cả câu, từ đang nói vàng": {"mode": "active", "color": "#FFE23D",
                                 "rest": "#FFFFFF", "outline": "#1A1200",
                                 "ow": 0.12, "shadow": 2, "pop": True},
    # ---- Bộ kiểu MỚI (đa dạng cho nhiều thể loại kênh) ----
    "Hồng nổi (Reels)": {"mode": "word", "color": "#FF2D95",
                         "outline": "#3D0022", "ow": 0.13, "shadow": 3,
                         "animate": True, "upper": True},
    "Xanh neon điện": {"mode": "word", "color": "#16E0FF",
                       "outline": "#001A20", "ow": 0.12, "shadow": 6,
                       "glow": "#16E0FF", "animate": True},
    "Đậm bóng đổ (gym/motivation)": {"mode": "word", "color": "#FFFFFF",
                                     "outline": "#000000", "ow": 0.16,
                                     "shadow": 8, "upper": True,
                                     "animate": True},
    "Nền hộp trắng, chữ đen": {"mode": "group", "color": "#111111",
                               "outline": "#000000", "ow": 0.0, "shadow": 0,
                               "box": True, "box_color": "#FFFFFF"},
    "Vàng hộp đen (podcast)": {"mode": "group", "color": "#FFD83D",
                               "outline": "#000000", "ow": 0.0, "shadow": 0,
                               "box": True, "box_color": "#000000"},
    "Karaoke hồng": {"mode": "karaoke", "color": "#FF5CA8",
                     "unsung": "#FFFFFF", "outline": "#2A0016",
                     "ow": 0.11, "shadow": 2},
    "Cả câu, từ đang nói xanh": {"mode": "active", "color": "#16E0FF",
                                 "rest": "#FFFFFF", "outline": "#00161A",
                                 "ow": 0.12, "shadow": 2, "pop": True},
    # ---- CỤM 2-3 chữ, KHÔNG nền hộp (box=False -> BorderStyle=1, chỉ viền) ----
    # Hiện nguyên cụm, hết cụm nhảy cụm mới; không có nền chữ nhật ôm chữ.
    "Cụm chữ trắng": {"mode": "group", "color": "#FFFFFF", "outline": "#000000",
                      "ow": 0.13, "shadow": 2},
    "Cụm chữ vàng": {"mode": "group", "color": "#FFD83D", "outline": "#241900",
                     "ow": 0.13, "shadow": 2},
    "Cụm chữ viền neon": {"mode": "group", "color": "#FFFFFF",
                          "outline": "#19E3FF", "ow": 0.12, "shadow": 6,
                          "glow": "#19E3FF"},
    # ---- CẢ CÂU, TỪ ĐANG NÓI ĐỔI MÀU — kiểu CapCut "chữ trắng viền đen dày,
    # 1 từ ĐỎ" (anh Hùng gửi ảnh mẫu 05/08/2026). Khác 2 kiểu 'active' cũ ở:
    # viền DÀY hơn (0.16 vs 0.12) + chữ HOA + màu nhấn nóng -> đọc được trên
    # mọi nền, đúng cái nhìn "sạch mà mạnh" của CapCut.
    "Cả câu, từ đang nói ĐỎ (CapCut)": {
        "reveal": 1,  # từ chưa nói MỜ 30%
        "mode": "active", "color": "#FF2020", "rest": "#FFFFFF",
        "outline": "#000000", "ow": 0.16, "shadow": 3, "pop": True,
        "upper": True},
    "Cả câu, từ đang nói CAM (CapCut)": {
        "reveal": 1,
        "mode": "active", "color": "#FF8A00", "rest": "#FFFFFF",
        "outline": "#000000", "ow": 0.16, "shadow": 3, "pop": True,
        "upper": True},
    "Cả câu, từ đang nói XANH LÁ (CapCut)": {
        "reveal": 1,
        "mode": "active", "color": "#39FF14", "rest": "#FFFFFF",
        "outline": "#000000", "ow": 0.16, "shadow": 3, "pop": True,
        "upper": True},
    # ---- Ô NỀN SÁNG CHẠY THEO TỪ ĐANG NÓI (kiểu Submagic/Hormozi) ----
    # Cả cụm hiện sẵn (trắng viền đen); TỪ đang nói được bọc 1 Ô NỀN màu, ô này
    # NHẢY sang từ kế theo mốc lời -> mắt bị kéo theo từng chữ. hl_palette =
    # danh sách màu ô; nhiều màu -> mỗi từ 1 màu (đa dạng, đỡ nhàm 200 kênh).
    "Ô sáng chạy từ (đa màu)": {
        "reveal": 2,  # chữ chưa nói thì CHƯA hiện
        "mode": "hlbox", "color": "#FFFFFF", "rest": "#FFFFFF",
        "outline": "#000000", "ow": 0.13, "shadow": 2, "pop": True,
        "upper": True, "box_text": "#0B0B0B",
        "hl_palette": ["#FFE23D", "#16E0FF", "#39FF14", "#FF2D95", "#FF8A00",
                       "#B36BFF"]},
    "Ô sáng chạy từ (vàng)": {
        "reveal": 2,  # chữ chưa nói thì CHƯA hiện
        "mode": "hlbox", "color": "#FFFFFF", "rest": "#FFFFFF",
        "outline": "#000000", "ow": 0.13, "shadow": 2, "pop": True,
        "upper": True, "box_text": "#0B0B0B", "hl_palette": ["#FFE23D"]},
    "Ô sáng chạy từ (xanh neon)": {
        "reveal": 2,  # chữ chưa nói thì CHƯA hiện
        "mode": "hlbox", "color": "#FFFFFF", "rest": "#FFFFFF",
        "outline": "#000000", "ow": 0.13, "shadow": 2, "pop": True,
        "upper": True, "box_text": "#00201A", "hl_palette": ["#16E0FF"]},
    "Ô sáng chạy từ (xanh lá)": {
        "reveal": 2,  # chữ chưa nói thì CHƯA hiện
        "mode": "hlbox", "color": "#FFFFFF", "rest": "#FFFFFF",
        "outline": "#000000", "ow": 0.13, "shadow": 2, "pop": True,
        "upper": True, "box_text": "#06210A", "hl_palette": ["#39FF14"]},
    "Ô sáng chạy từ (hồng)": {
        "reveal": 2,  # chữ chưa nói thì CHƯA hiện
        "mode": "hlbox", "color": "#FFFFFF", "rest": "#FFFFFF",
        "outline": "#000000", "ow": 0.13, "shadow": 2, "pop": True,
        "upper": True, "box_text": "#FFFFFF", "hl_palette": ["#FF2D95"]},
    "Ô sáng chạy từ (đỏ)": {
        "reveal": 2,  # chữ chưa nói thì CHƯA hiện
        "mode": "hlbox", "color": "#FFFFFF", "rest": "#FFFFFF",
        "outline": "#000000", "ow": 0.13, "shadow": 2, "pop": True,
        "upper": True, "box_text": "#FFFFFF", "hl_palette": ["#FF2E2E"]},
}
#: Màu ô mặc định khi preset khai mode 'hlbox' mà thiếu hl_palette.
HL_PALETTE = ["#FFE23D", "#16E0FF", "#39FF14", "#FF2D95", "#FF8A00", "#B36BFF"]
DEFAULT_PRESET = "Vàng nhảy (TikTok)"
# Mục ĐẦU combo "Kiểu chạy chữ" của khu CHỮ AI ĐỌC: dùng Y HỆT phụ đề gốc
# (Style Default) — tương đương narr_same=True cũ. Chọn 1 preset khác -> đoạn
# AI kể render bằng MODE + màu/viền của preset đó (Style Narrate riêng).
NARR_SAME_LABEL = "(giống phụ đề gốc)"

#: Vị trí dọc đặt sẵn cho chữ (nhãn UI -> mã). "" = giữ chỗ mặc định của
#: đường gọi (đường thay giọng: CHÍNH GIỮA DẢI CHỮ CŨ vừa che).
VI_TRI_CHU = (("(theo chỗ chữ cũ)", ""), ("Trên", "tren"),
              ("Giữa", "giua"), ("Dưới", "duoi"))
#: Neo ASS + vị trí dọc (tỉ lệ chiều cao khung) cho từng mã ở trên.
_VI_TRI_ASS = {"tren": (8, 0.10), "giua": (5, 0.50), "duoi": (2, 0.88)}


def kieu_chu_ass(preset: str = "", size: int = 0, color: str = "",
                 outline: str = "", ow: float = 0.0, out_h: int = 1920,
                 dam: bool | None = None,
                 nghieng: bool | None = None) -> dict:
    """Quy 1 tên KIỂU (preset) + các ô user ghi đè ra TRƯỜNG KIỂU CHỮ của .ass.

    ĐÂY LÀ CỬA DUY NHẤT quy preset ra kiểu chữ — `build_ass` (đường CẮT
    THƯỜNG) và `che_chu.ghi_ass` (đường THAY GIỌNG) đều gọi vào đây, nên đặt
    cùng tham số thì HAI ĐƯỜNG RA CÙNG MỘT KIỂU CHỮ. Tách ra từ chính thân
    `build_ass` chứ không viết lại: bất biến cổng 21 ("18 preset CŨ × 4 bộ
    tham số ra .ass giống TỪNG BYTE") canh đúng điều đó.

    `size` = CỠ CHỮ tính bằng ĐIỂM ẢNH (0 -> tự theo `out_h`). Nhắc lại bẫy
    cổng 45(c): truyền TỈ LỆ (0,055) vào đây thì .ass ghi `Fontsize: 0.055`,
    chữ dưới 1 điểm ảnh = KHÔNG THẤY GÌ mà ffmpeg vẫn trả mã 0.
    `ow` = độ dày viền theo TỈ LỆ cỡ chữ (0 -> theo preset).
    `dam` / `nghieng` = None -> giữ mặc định (đậm, không nghiêng) như cũ.
    """
    p = CAPTION_PRESETS.get(preset) or CAPTION_PRESETS[DEFAULT_PRESET]
    main = color or p["color"]                 # màu chữ: user chọn hoặc của kiểu
    size = size or max(40, int(out_h * 0.05))
    primary = _ass_color(main)
    vien = _ass_color(p.get("outline", "#000000"))
    dovien = max(0, int(size * p.get("ow", 0.10)))
    shadow = p.get("shadow", 1)
    back = _alpha_color("#000000", 0x96)        # bóng đổ mặc định
    border_style = 1
    if p.get("box"):                            # KIỂU NỀN HỘP
        border_style = 3
        vien = _ass_color(p.get("box_color", "#000000"))
        dovien = max(8, int(size * 0.20))       # = bề dày hộp ôm chữ
        shadow = 0
    elif p.get("glow"):                         # KIỂU NEON: bóng = màu viền (phát sáng)
        back = _alpha_color(p["glow"], 0x40)
    # OVERRIDE user (Chỉnh mẫu, khu Phụ đề): màu viền / độ dày viền. Thiếu ->
    # giữ theo preset như trên. `ow` theo tỉ lệ chiều cao (như 'ow' của
    # preset) -> quy ra px theo size.
    if outline:
        vien = _ass_color(outline)
    if ow and ow > 0:
        dovien = max(0, int(size * ow))
    return {"size": int(size), "primary": primary, "outline": vien,
            "back": back, "ow": dovien, "shadow": shadow,
            "border_style": border_style,
            # ASS: -1 = BẬT, 0 = TẮT. Mặc định giữ nguyên hành vi cũ của
            # `build_ass` (Bold=-1, Italic=0).
            "bold": -1 if (True if dam is None else dam) else 0,
            "italic": -1 if (False if nghieng is None else nghieng) else 0,
            "upper": bool(p.get("upper")), "mode": p.get("mode", "word")}


def build_ass(words: list, segments: list, out_path,
              out_w: int = 1080, out_h: int = 1920,
              font: str = "Montserrat", size: int = 0,
              color: str = "", ny: float = 0.78,
              preset: str = DEFAULT_PRESET, delay: float = 0.0,
              hook: str = "", hook_dur: float = 6.0,
              hook_nx: float = 0.5, hook_ny: float = 0.10,
              hook_size: float = 0.0,
              extra_cues: list | None = None,
              narr_color: str = "", narr_italic: bool | None = None,
              narr_same: bool = False,
              narr_ny: float = 0.0, narr_size: float = 0.0,
              cap_case: str = "", narr_case: str = "",
              hook_case: str = "",
              cap_outline: str = "", cap_ow: float = 0.0,
              narr_preset: str = "", narr_outline: str = "",
              narr_ow: float = 0.0, narr_font: str = "") -> bool:
    """Ghi file .ass phụ đề khớp lời theo KIỂU (preset). Trả True nếu có chữ.
    preset = tên kiểu trong CAPTION_PRESETS (vàng nhảy / karaoke / hộp đen / neon...).
    color = màu chữ TÙY CHỌN (ghi đè màu mặc định của kiểu); '' = dùng màu kiểu.
    delay = đẩy phụ đề TRỄ lại (giây) để khớp lời (whisper hay đánh dấu sớm);
            số âm = hiện sớm hơn. ny = vị trí dọc (0=trên, 1=dưới) do user KÉO.
    hook_nx/hook_ny = tâm-ngang/đỉnh ô HOOK (0..1, user kéo trong Chỉnh mẫu);
    hook_size = cỡ chữ hook theo tỉ lệ chiều cao (0 = mặc định 1.5x phụ đề).
    extra_cues = [(start, end, text[, kind])] — cue THÊM đã ở TIMELINE ĐẦU RA
    (không remap, không delay). Recap dùng CẢ 2 loại cue đồng thời (render
    KHÔNG đè nhau vì mốc part orig/narrate rời nhau):
      - narrate (lời KỂ AI): kind="word" (mốc WordBoundary TTS, chạy từng từ)
        / "sent" (cả câu, fade nhẹ) -> Style Narrate (italic + accent vàng).
      - orig (LỜI GỐC nhân vật đoạn mode="orig"): kind="orig_word" (word-level)
        / "orig_sent" (fallback chia câu) -> Style Default (GIỐNG phụ đề clip
        thường) — sửa lỗi 'đoạn gốc không có phụ đề'.
    narr_color = màu hex CHỮ AI KỂ (Style Narrate) do user chọn trong CHỈNH
    MẪU phần "Chữ AI đọc"; ""/None -> #FFD966 (vàng mặc định cũ, có logic
    tránh trùng màu chữ chính như trước). narr_italic = in nghiêng lời AI kể
    (None -> True mặc định). narr_same=True -> đoạn AI kể dùng LUÔN Style
    Default (render cue narrate "word"/"sent" bằng Default như đoạn gốc,
    không phân biệt) — bỏ qua narr_color/narr_italic.
    narr_ny = vị trí dọc RIÊNG (0..1) cho Style Narrate (MarginV theo neo an8);
    0/thiếu -> dùng ny của phụ đề gốc như cũ. narr_size = cỡ chữ RIÊNG cho
    Narrate theo tỉ lệ chiều cao; 0/thiếu -> = cỡ phụ đề gốc.
    cap_case / narr_case / hook_case = kiểu chữ HIỂN THỊ ("upper"/"lower"/
    "title"/""=giữ nguyên) áp cho cue gốc / cue AI kể / hook (không đổi mốc).
    cap_outline / cap_ow = màu viền / độ dày viền TÙY CHỌN cho Style Default
    (khu Phụ đề gốc); ""/0 -> theo preset. cap_ow theo tỉ lệ chiều cao (như 'ow'
    của preset). narr_preset = tên KIỂU riêng cho đoạn AI kể (Style Narrate) —
    rỗng / NARR_SAME_LABEL "(giống phụ đề gốc)" -> dùng Style Default y hệt gốc
    (tương đương narr_same cũ); chọn preset khác -> Narrate lấy màu/viền/glow của
    preset đó + chạy hiệu ứng theo mode. narr_outline / narr_ow = màu viền / độ
    dày viền TÙY CHỌN cho Style Narrate (thiếu -> theo narr_preset).
    narr_font = FONT riêng cho Style Narrate (Chỉnh mẫu khu "Chữ AI đọc");
    rỗng / NARR_SAME_LABEL "(giống phụ đề gốc)" -> dùng font phụ đề gốc (`font`).
    (đoạn narrate tiếng gốc bị tắt nên không có words; recap KHÔNG truyền
    `words` — mọi phụ đề recap đi qua extra_cues cho nhất quán timeline.)
    LƯU Ý: clip CÓ hook -> hook hiện trong hook_dur giây đầu, phụ đề chạy chữ
    bị ẨN trong lúc hook hiện (tránh chồng chữ), sau đó chạy bình thường."""
    has_hook = bool((hook or "").strip()) and hook_dur > 0
    remapped = _remap_words(words or [], segments or [])
    extra_cues = [c for c in (extra_cues or [])
                  if len(c) >= 3 and str(c[2]).strip() and c[1] > c[0]]
    if not remapped and not has_hook and not extra_cues:
        return False
    p = CAPTION_PRESETS.get(preset) or CAPTION_PRESETS[DEFAULT_PRESET]
    mode = p["mode"]
    # 🈶 CJK (Trung/Nhật/Hàn): whisper trả MỐC TỪNG KÝ TỰ -> gom thành cụm đọc
    # được TRƯỚC khi dựng cue, nếu không phụ đề là 1 chữ nhấp nháy 0,17 s/lần
    # (xem `_gom_cjk`). Non-CJK trả y nguyên nên đường EN/VI KHÔNG đổi 1 byte.
    remapped = _gom_cjk(remapped, _CJK_MAX.get(mode, 6))
    # 🈶 FONT cho chữ CJK: font đóng gói của app có 0 glyph chữ Hán (đo 12/12
    # file), chữ hiện được là do libass TỰ LÙI sang font hệ điều hành — thứ tự
    # lùi app không kiểm soát và máy thiếu font thì ra Ô VUÔNG mà ffmpeg VẪN
    # trả mã 0. Khai thẳng font CJK CÓ THẬT trên máy này (xem `font_cjk`).
    # Non-CJK -> trả y nguyên `font` nên đường EN/VI KHÔNG đổi 1 byte.
    _chu_ht = "".join(str(w[2]) for w in remapped[:400]) + str(hook or "") \
        + "".join(str(c[2]) for c in extra_cues[:200])
    font = font_cjk(_chu_ht, font)
    # Kiểu chữ Style Default: quy qua CỬA DUY NHẤT `kieu_chu_ass` (đường THAY
    # GIỌNG gọi đúng hàm này) — thân cũ nằm nguyên trong đó, cổng 21 canh
    # ".ass giống TỪNG BYTE" nên phần này không được đổi hành vi.
    _k = kieu_chu_ass(preset, size, color, cap_outline, cap_ow, out_h)
    size = _k["size"]
    side = int(out_w * 0.14)
    align = 8
    margin_v = int(max(0.02, min(0.9, ny)) * out_h)
    primary, outline, back = _k["primary"], _k["outline"], _k["back"]
    ow, shadow, border_style = _k["ow"], _k["shadow"], _k["border_style"]
    # secondary: karaoke = màu CHƯA nói (mờ); kiểu khác không dùng
    if mode == "karaoke":
        secondary = _alpha_color(p.get("unsung", "#FFFFFF"), 0x64)
        # karaoke nhúng \kf theo TỪNG TỪ -> áp case trên TỪ trước khi dựng tag
        # (không thể áp lên cả body vì lẫn tag). cap_case rỗng -> theo cờ
        # 'upper' của preset (nếu có); không có nữa -> giữ nguyên.
        _kcase = cap_case or ("upper" if p.get("upper") else "")
        kw_src = ([[a, b, apply_case(t, _kcase), si]
                   for a, b, t, si in remapped] if _kcase else remapped)
        cues = _karaoke_cues(kw_src)
        prefix = "{\\fad(60,40)}"               # cả cụm vào/ra mượt
    elif mode in ("active", "hlbox"):
        secondary = "&H000000FF"
        cues = []                               # vẽ riêng bên dưới (mỗi từ 1 dòng)
        prefix = ""
    elif p.get("highlight"):
        secondary = "&H000000FF"
        cues = _word_cues(remapped)             # từng từ -> tô màu riêng được
        prefix = ""
    else:
        secondary = "&H000000FF"
        cues = _word_cues(remapped) if mode == "word" else _group(remapped)
        prefix = ("{\\fad(40,0)\\t(0,90,\\fscx118\\fscy118)"
                  "\\t(90,200,\\fscx100\\fscy100)}" if p.get("animate") else "")
    style = (f"Style: Default,{font},{size},{primary},{secondary},{outline},"
             f"{back},-1,0,0,0,100,100,0,0,{border_style},{ow},{shadow},"
             f"{align},{side},{side},{margin_v},1")
    # STYLE RIÊNG "Narrate" cho phụ đề THUYẾT MINH (recap): NGHIÊNG + màu
    # ACCENT khác hẳn màu preset -> người xem phân biệt ngay lời KỂ của AI
    # với lời THOẠI gốc (trước đây 2 loại giống hệt nhau -> 'sub linh tinh').
    # Màu: user chọn ở ⚙ Cài đặt Reup (narr_color) -> dùng THẲNG (đã là 1
    # trong 5 màu định sẵn, phân biệt tốt); KHÔNG chọn -> accent = màu glow
    # của preset (neon) nếu có, không thì VÀNG NHẠT #FFD966, trùng màu chữ
    # chính -> lùi về trắng (vẫn phân biệt nhờ nghiêng + fade).
    # narr_italic (None -> True): 1 = nghiêng, 0 = thẳng. narr_same=True ->
    # đoạn AI kể render Style Default (không cần Narrate) — vẫn dựng style
    # cho an toàn nhưng cue narrate sẽ dùng Default (xem vòng extra_cues).
    # narr_preset (khu CHỮ AI ĐỌC): chọn KIỂU riêng cho đoạn AI kể. Rỗng /
    # NARR_SAME_LABEL -> "giống phụ đề gốc" (Style Default, như narr_same cũ).
    # Chọn preset khác -> Style Narrate lấy màu/viền/glow/box của preset ĐÓ,
    # cue narrate chạy theo MODE preset đó (xem vòng extra_cues bên dưới).
    narr_same = narr_same or (not narr_preset) or (
        narr_preset == NARR_SAME_LABEL)
    np = (CAPTION_PRESETS.get(narr_preset) if not narr_same else None) or p
    narr_mode = np["mode"]
    # màu chữ Narrate: user chọn (narr_color) ghi đè; thiếu -> màu của np, tránh
    # trùng màu chữ chính (giữ logic phân biệt cũ khi dùng chung preset gốc).
    if narr_color:
        narr_primary = _ass_color(narr_color)
    elif not narr_same:
        # kiểu 'ô sáng chạy từ' khai color=trắng (chữ nền trắng) -> nếu lấy
        # nguyên thì chữ AI kể ra TRẮNG, lẫn hẳn với lời gốc. Lấy màu ô đầu
        # bảng làm màu nhấn để vẫn phân biệt được lời AI.
        narr_primary = _ass_color(
            (np.get("hl_palette") or [np.get("color", "#FFFFFF")])[0]
            if np.get("mode") == "hlbox" else np.get("color", "#FFFFFF"))
    else:
        narr_accent = p.get("glow") or "#FFD966"
        if _ass_color(narr_accent) == primary:
            narr_accent = ("#FFFFFF" if primary != _ass_color("#FFFFFF")
                           else "#FFD966")
        narr_primary = _ass_color(narr_accent)
    # viền / bóng / hộp Narrate: theo np; narr_outline/narr_ow ghi đè viền.
    narr_outline_c = _ass_color(np.get("outline", "#000000"))
    narr_shadow = np.get("shadow", 1)
    narr_border = 1
    narr_back = _alpha_color("#000000", 0x96)
    narr_ital = -1 if (True if narr_italic is None else narr_italic) else 0
    # Cỡ + vị trí dọc RIÊNG cho Narrate (thiếu -> = phụ đề gốc). narr_size
    # theo tỉ lệ chiều cao (như size phụ đề); narr_ny theo neo an8 (đỉnh).
    nsize = int(narr_size * out_h) if narr_size and narr_size > 0 else size
    now = max(0, int(nsize * np.get("ow", 0.10)))
    if np.get("box"):
        narr_border = 3
        narr_outline_c = _ass_color(np.get("box_color", "#000000"))
        now = max(8, int(nsize * 0.20))
        narr_shadow = 0
    elif np.get("glow"):
        narr_back = _alpha_color(np["glow"], 0x40)
    if narr_outline:
        narr_outline_c = _ass_color(narr_outline)
    if narr_ow and narr_ow > 0:
        now = max(0, int(nsize * narr_ow))
    # narr_same -> đồng bộ HẲN với Default (viền/bóng/hộp) để trông y hệt gốc.
    if narr_same:
        narr_outline_c, narr_shadow, narr_border, narr_back = (
            outline, shadow, border_style, back)
        now = max(0, int(nsize * p.get("ow", 0.10)))
        if p.get("box"):
            now = max(8, int(nsize * 0.20))
        if narr_outline:
            narr_outline_c = _ass_color(narr_outline)
        if narr_ow and narr_ow > 0:
            now = max(0, int(nsize * narr_ow))
    narr_mv = (int(max(0.02, min(0.9, narr_ny)) * out_h)
               if narr_ny and narr_ny > 0 else margin_v)
    # FONT Style Narrate: narr_font user chọn (Chỉnh mẫu khu "Chữ AI đọc");
    # rỗng / NARR_SAME_LABEL -> dùng font phụ đề gốc (giữ hành vi cũ).
    nfont = (font if (not narr_font or narr_font == NARR_SAME_LABEL)
             else font_cjk(_chu_ht, narr_font))   # CJK: font riêng cũng phải đổi
    narr_style = (f"Style: Narrate,{nfont},{nsize},{narr_primary},{secondary},"
                  f"{narr_outline_c},{narr_back},-1,{narr_ital},0,0,100,100,0,0,"
                  f"{narr_border},{now},{narr_shadow},{align},{side},{side},"
                  f"{narr_mv},1")
    # HOOK: câu giật tít TO ở ĐẦU clip (an8 = trên, neo đỉnh); vàng nổi + viền dày
    # vị trí/cỡ theo Ô HOOK user kéo trong Chỉnh mẫu (thiếu -> mặc định như cũ)
    hsize = int(hook_size * out_h) if hook_size > 0 else int(size * 1.5)
    hmv = int(max(0.0, min(0.9, hook_ny)) * out_h)
    hook_style = (f"Style: Hook,{font},{hsize},{primary},&H000000FF,{outline},"
                  f"{back},-1,0,0,0,100,100,0,0,1,{max(4, int(hsize*0.11))},2,"
                  f"8,{side},{side},{hmv},1")
    head = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {out_w}\nPlayResY: {out_h}\nWrapStyle: 0\n\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,"
        "OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,"
        "Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,"
        "MarginV,Encoding\n"
        f"{style}\n{hook_style}\n{narr_style}\n\n"
        "[Events]\n"
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
    )
    lines = [head]
    if has_hook:                            # 1 dòng HOOK to ở đầu clip
        ht = _esc(hook)
        if hook_case:                       # user chọn kiểu chữ hoa -> ưu tiên
            ht = apply_case(ht, hook_case)
        elif p.get("upper"):
            ht = ht.upper()
        han = ("\\fad(150,250)\\t(0,160,\\fscx112\\fscy112)"
               "\\t(160,320,\\fscx100\\fscy100)")
        if abs(hook_nx - 0.5) > 0.01:       # user kéo lệch ngang -> neo bằng \pos
            han = f"\\pos({int(hook_nx * out_w)},{hmv})" + han
        lines.append(f"Dialogue: 1,{_fmt(0)},{_fmt(hook_dur)},Hook,,0,0,0,,"
                     f"{{{han}}}{ht}\n")
    # CÓ HOOK -> ẨN phụ đề chạy chữ TRONG lúc hook hiện (tránh chồng chữ):
    # bỏ cue nằm hẳn trong [0, hook_dur); cue vắt qua mốc -> cắt start = hook_dur.
    # Hook và phụ đề chạy CÙNG NHAU (user chốt 2026-07): không ẩn phụ đề lúc
    # hook hiện nữa — tắt hook thì chỉ hook biến mất, phụ đề luôn chạy từ 0s.
    min_start = 0.0
    # Cue THUYẾT MINH (recap): mốc đã ở timeline đầu ra — không remap/delay.
    # Phần tử thứ 4 (tuỳ chọn) = kind: "word" -> cue TỪNG TỪ (word boundary
    # thật của edge-tts); mặc định/"sent" -> hiện CẢ CÂU. Dùng Style Narrate
    # (nghiêng + màu accent) và KHÔNG dùng pop/karaoke của preset gốc — từng
    # từ chỉ FADE NHẸ (50/30ms) -> nhìn là biết lời KỂ, không lẫn với thoại.
    # kind:
    #   "word"/"sent"       -> Style Narrate (lời KỂ của AI — italic + accent)
    #   "orig_word"/"orig_sent" -> Style Default (LỜI GỐC nhân vật đoạn orig —
    #                          GIỐNG phụ đề clip thường, KHÁC hẳn Narrate) — sửa
    #                          lỗi 'đoạn gốc không có phụ đề'. Cue đã ở TIMELINE
    #                          ĐẦU RA (m1._recap_orig_caption_cues đã map + trừ
    #                          offset segment) nên KHÔNG remap/delay ở đây.
    extra_lines = []
    word_pre = "{\\fad(50,30)}"
    orig_anim = ("{\\fad(30,0)\\t(0,90,\\fscx116\\fscy116)"
                 "\\t(90,190,\\fscx100\\fscy100)}" if p.get("animate")
                 else "{\\fad(40,0)}")
    # ANIMATION cue AI kể (Style Narrate) theo MODE của narr_preset: preset có
    # animate/pop/karaoke -> phồng nhẹ khi vào (chạy giống kiểu đã chọn); preset
    # tĩnh -> chỉ fade nhẹ. Cue narrate là chữ đã gom sẵn (word/sent) nên không
    # nhúng \\kf từng-từ; dùng scale-pop cho cả cụm là gần nhất & không lỗi.
    _narr_active = (not narr_same) and (
        np.get("animate") or np.get("pop") or narr_mode == "karaoke")
    narr_word_pre = ("{\\fad(40,0)\\t(0,90,\\fscx116\\fscy116)"
                     "\\t(90,190,\\fscx100\\fscy100)}" if _narr_active
                     else word_pre)
    narr_sent_pre = "{\\fad(80,80)}"
    for c in extra_cues:
        ea, eb, etxt = c[0], c[1], c[2]
        kind = str(c[3]) if len(c) > 3 else "sent"
        et = _esc(str(etxt))
        # case: cue gốc (orig_*) theo cap_case; cue AI kể (word/sent) theo
        # narr_case. narr_same=True -> AI kể render Style Default -> vẫn dùng
        # narr_case cho đúng lựa chọn phần "Chữ AI đọc".
        # Fallback cờ 'upper': cue GỐC theo preset phụ đề (p); cue AI KỂ theo
        # preset của CHÍNH NÓ (np — narr_same thì np=p). Trước đây luôn dùng p
        # -> chọn kiểu AI kể có 'upper' không ra HOA, hoặc bị HOA oan theo kiểu
        # phụ đề gốc (lỗi 'chọn kiểu này ra kiểu khác').
        _is_orig = kind.startswith("orig")
        _ecase = cap_case if _is_orig else narr_case
        if _ecase:
            et = apply_case(et, _ecase)
        elif (p if _is_orig else np).get("upper"):
            et = et.upper()
        if kind.startswith("orig"):
            # LỜI GỐC nhân vật -> Style Default (như clip thường)
            pre = orig_anim if kind == "orig_word" else "{\\fad(60,40)}"
            style_name = "Default"
        elif narr_same:
            # user chọn "giống hệt phụ đề mẫu" -> đoạn AI kể dùng LUÔN Style
            # Default (không phân biệt) — dùng đúng animation kiểu orig để
            # trông y hệt phụ đề đoạn gốc.
            pre = orig_anim if kind == "word" else "{\\fad(60,40)}"
            style_name = "Default"
        else:
            pre = narr_word_pre if kind == "word" else narr_sent_pre
            style_name = "Narrate"
        extra_lines.append(
            f"Dialogue: 0,{_fmt(max(0.0, ea))},{_fmt(eb)},{style_name},,"
            f"0,0,0,,{pre}{et}\n")
    # ---- KIỂU 'Ô NỀN SÁNG CHẠY THEO TỪ ĐANG NÓI' (Submagic) ----
    # Mỗi từ sinh 2 dòng: LỚP 0 = miếng ô nền (chữ tô ĐẶC cùng màu viền dày ->
    # thành viên thuốc bo góc ôm chữ), LỚP 1 = CHỮ vẽ đè lên. Vì sao phải 2 lớp:
    # bản đầu nhúng ô GIỮA DÒNG chung với chữ thì viền đen của từ BÊN CẠNH vẽ
    # đè lên ô (libass gộp mọi viền của 1 dòng vào cùng 1 lớp) -> ô bị "chặt"
    # phẳng một cạnh, và cỡ chữ lớn thì 2 từ dính liền nhau (đo 05/08/2026).
    # Hai lớp có CÙNG chữ/cỡ/lề nên bố cục y hệt -> ô luôn nằm đúng sau từ.
    if mode == "hlbox":
        # màu chữ nền: user chọn trong Chỉnh mẫu (color) ĐƯỢC ƯU TIÊN — bản đầu
        # bỏ qua `color` nên "chọn màu ra màu khác" (lỗi cũ 110 tái diễn).
        rest_c = _ass_color(color or p.get("rest", "#FFFFFF"))
        _pal = [c for c in (p.get("hl_palette") or HL_PALETTE) if str(c).strip()]
        pal = [_ass_color(c) for c in _pal] or [_ass_color("#FFE23D")]
        box_txt = _ass_color(p.get("box_text", "#0B0B0B"))
        # bề dày ô PHẢI dày hơn viền chữ (ow), không thì user kéo "độ dày viền"
        # lên 0,2-0,3 là viền đen nuốt hết ô, chữ thành cục đen (đo 05/08/2026).
        bord_box = max(6, int(size * 0.17), ow + max(4, int(size * 0.05)))
        pop = ("\\t(0,80,\\fscy105)\\t(80,160,\\fscy100)"
               if p.get("pop") else "")   # CHỈ phồng dọc: phồng ngang làm cả
        #                                   khối chữ xuống dòng lại trong 160ms
        an = "{\\alpha&HFF&}"            # từ không được chiếu -> ẩn ở lớp ô
        # CHỮ CHƯA NÓI (anh Hùng 06/08/2026: "chữ hiện trước khi nói"). Đo thật:
        # kiểu hiện-cả-cụm bày sẵn cả cụm ngay từ từ ĐẦU TIÊN nên từ cuối hiện
        # TRƯỚC TIẾNG tới 1,44s. reveal: 0 = hiện hết (như cũ) · 1 = từ chưa nói
        # MỜ ~30% · 2 = ẨN hẳn (sớm 0,00s). Dùng \alpha nên KHÔNG đổi bề rộng
        # chữ -> chỗ đứng của chữ y nguyên, không giật layout.
        _reveal = int(p.get("reveal", 0) or 0)
        _mo, _an_chu = "{\\alpha&HB4&}", "{\\alpha&HFF&}"
        ev = []            # [start, end, first, last, body_ô, body_chữ]
        gi = 0                                   # số thứ tự từ trong CẢ clip
        for ch in _chunks(remapped, max_words=3):   # cụm 3 từ: cụm 5 từ + chữ
            cend = ch[-1][1] + 0.25                 # HOA hay tràn 3-4 dòng
            n = len(ch)
            chu_ch, cjk_ch = [], []
            for ww in ch:                        # chữ hiển thị của cả cụm
                wt = _esc(ww[2])
                if cap_case:
                    wt = apply_case(wt, cap_case)
                elif p.get("upper"):
                    wt = wt.upper()
                chu_ch.append(wt)
                cjk_ch.append(_co_cjk(wt))
            for i, w in enumerate(ch):
                gi_tu = gi + i
                if _chi_dau_cau(chu_ch[i]):
                    continue     # KHÔNG chiếu ô lên dấu câu đứng lẻ (","/"...")
                wa = max(0.0, w[0] + delay)
                we = ((ch[i + 1][0] + delay) if i + 1 < n else (cend + delay))
                col = pal[gi_tu % len(pal)]      # màu theo THỨ TỰ TỪ cả clip ->
                #                                  1 từ = 1 màu ở mọi dòng
                o, chu = [], []
                for j, wt in enumerate(chu_ch):
                    if j == i:
                        o.append(f"{{\\alpha&H00&\\1c{col}\\3c{col}"
                                 f"\\bord{bord_box}\\shad0\\blur0.7{pop}}}{wt}")
                        chu.append(f"{{\\1c{box_txt}\\bord0\\shad0{pop}}}{wt}"
                                   f"{{\\1c{rest_c}\\bord{ow}\\shad{shadow}"
                                   "\\fscy100}")
                    else:
                        o.append(an + wt)
                        if _reveal and j > i:      # từ CHƯA được nói tới
                            chu.append((_an_chu if _reveal >= 2 else _mo)
                                       + wt + "{\\alpha&H00&}")
                        else:
                            chu.append(wt)
                # CJK (Nhật/Trung/Hàn) không có dấu cách -> nối liền, đừng chèn
                # khoảng trắng lạ giữa các cụm ký tự.
                def _noi(ps):
                    ra = ps[0]
                    for k in range(1, len(ps)):
                        ra += ("" if (cjk_ch[k] and cjk_ch[k - 1]) else " ") + ps[k]
                    return ra
                ev.append([wa, we, i == 0, i == n - 1, _noi(o), _noi(chu)])
            gi += n
        ev.sort(key=lambda e: e[0])
        # 1) ép không chồng nhau  2) GOM từ nói quá dày + LẤP LỖ: bản đầu chỉ
        # "bỏ dòng < 60ms" nên transcript nói nhanh mất 4-6% chữ, còn bản chép
        # lời không có mốc từng-từ (recap/lồng tiếng, bước 0,05s) thì mất gần
        # hết chữ (đo: 1/20 dòng). Nay giữ ô ở từ trước lâu hơn thay vì bỏ.
        for k in range(len(ev) - 1):
            if ev[k][1] > ev[k + 1][0]:
                ev[k][1] = ev[k + 1][0]
        gon, i = [], 0
        while i < len(ev):
            cur = ev[i]
            j = i + 1
            while j < len(ev) and ev[j][0] - cur[0] < 0.12:
                cur[3] = cur[3] or ev[j][3]      # giữ cờ 'cuối cụm' để có fade
                j += 1
            if j < len(ev) and ev[j][0] - cur[1] < 0.35:
                cur[1] = ev[j][0]                # lấp lỗ -> không nhấp nháy
            cur[1] = max(cur[1], cur[0] + 0.08)  # delay âm không làm co về 0
            gon.append(cur)
            i = j
        for wa, we, first, last, b_o, b_chu in gon:
            if we <= min_start:
                continue
            wa = max(wa, min_start)
            if we - wa < 0.06:
                continue
            fad = "\\fad(80,0)" if first else ("\\fad(0,90)" if last else "")
            lines.append(f"Dialogue: 0,{_fmt(wa)},{_fmt(we)},Default,,0,0,0,,"
                         f"{{{fad}}}{b_o}\n")
            lines.append(f"Dialogue: 1,{_fmt(wa)},{_fmt(we)},Default,,0,0,0,,"
                         f"{{{fad}\\1c{rest_c}}}{b_chu}\n")
        lines.extend(extra_lines)
        Path(out_path).write_text("".join(lines), encoding="utf-8")
        return True

    # ---- KIỂU 'CẢ CÂU, TỪ ĐANG NÓI VÀNG' ----
    if mode == "active":
        rest_c = _ass_color(p.get("rest", "#FFFFFF"))
        act_c = primary                          # màu từ đang nói (vàng)
        _reveal = int(p.get("reveal", 0) or 0)   # xem chú thích ở nhánh hlbox
        _mo, _an_chu = "{\\alpha&HB4&}", "{\\alpha&HFF&}"
        ev = []                                  # (start, end, is_first, is_last, body)
        for ch in _chunks(remapped):
            cend = ch[-1][1] + 0.25
            n = len(ch)
            for i, w in enumerate(ch):
                wa = max(0.0, w[0] + delay)
                we = ((ch[i + 1][0] + delay) if i + 1 < n else (cend + delay))
                parts = []
                for j, ww in enumerate(ch):
                    wt = _esc(ww[2])
                    if cap_case:                 # kiểu chữ hoa cho phụ đề gốc
                        wt = apply_case(wt, cap_case)
                    elif p.get("upper"):         # preset khai 'upper' -> HOA
                        wt = wt.upper()
                    if j == i:                   # TỪ đang nói -> nhảy vàng (phồng nhẹ)
                        pop = ("\\t(0,90,\\fscx110\\fscy110)\\t(90,170,\\fscx100\\fscy100)"
                               if p.get("pop") else "")
                        parts.append(f"{{\\1c{act_c}{pop}}}{wt}{{\\1c{rest_c}}}")
                    elif _reveal and j > i:      # từ CHƯA được nói tới
                        parts.append((_an_chu if _reveal >= 2 else _mo) + wt
                                     + "{\\alpha&H00&}")
                    else:
                        parts.append(wt)
                ev.append([wa, we, i == 0, i == n - 1,
                           _noi_cum(parts, [ww[2] for ww in ch])])
        # CHỐNG CHÈN NHAU: sắp theo giờ, ép mỗi dòng kết thúc TRƯỚC khi dòng kế bắt đầu
        ev.sort(key=lambda e: e[0])
        for k in range(len(ev) - 1):
            if ev[k][1] > ev[k + 1][0]:
                ev[k][1] = ev[k + 1][0]
        for wa, we, first, last, parts in ev:
            if we <= min_start:                  # cue nằm hẳn trong lúc hook hiện -> bỏ
                continue
            wa = max(wa, min_start)              # vắt qua mốc hook -> cắt start
            if we - wa < 0.06:                   # bỏ dòng quá ngắn (đỡ nhấp nháy)
                continue
            # fade chỉ ở ĐẦU/CUỐI cụm (giữa cụm chữ đứng yên, chỉ đổi màu) -> không chớp
            fad = "\\fad(80,0)" if first else ("\\fad(0,90)" if last else "")
            body = ("{%s\\1c%s}" % (fad, rest_c)) + parts
            lines.append(
                f"Dialogue: 0,{_fmt(wa)},{_fmt(we)},Default,,0,0,0,,{body}\n")
        lines.extend(extra_lines)
        Path(out_path).write_text("".join(lines), encoding="utf-8")
        return True

    anim = ("\\fad(30,0)\\t(0,90,\\fscx116\\fscy116)\\t(90,190,\\fscx100\\fscy100)")
    kw_i, prev_kw = -1, False
    bord_kw = max(4, int(size * 0.06))
    for a, b, txt in cues:
        a2, b2 = max(0.0, a + delay), max(0.05, b + delay)   # đẩy trễ cho khớp lời
        if b2 <= min_start:               # cue nằm hẳn trong lúc hook hiện -> bỏ
            continue
        a2 = max(a2, min_start)           # vắt qua mốc hook -> cắt start
        if p.get("highlight"):
            # CHỮ HOA + tô NEON cho TỪ KHÓA + phát sáng (glow qua \blur)
            word = _esc(txt)
            if cap_case:                  # user chọn kiểu chữ hoa -> ưu tiên
                word = apply_case(word, cap_case)
            elif p.get("upper"):
                word = word.upper()
            is_kw = _is_keyword(txt)
            if is_kw and not prev_kw:     # cụm từ-khóa LIỀN nhau dùng CÙNG màu
                kw_i += 1
            prev_kw = is_kw
            if is_kw:
                col = _ass_color(NEON_PALETTE[kw_i % len(NEON_PALETTE)])
                inl = (f"{{\\1c{col}\\3c{col}\\bord{bord_kw}\\blur5\\shad0{anim}}}")
            else:
                inl = (f"{{\\1c&H00FFFFFF\\3c{outline}\\bord{ow}\\blur0.6{anim}}}")
            body = inl + word
        elif mode == "karaoke":
            body = prefix + txt                 # karaoke đã có tag \kf — không đụng
        else:
            wtxt = _esc(txt)
            if cap_case:                        # phụ đề gốc word/group -> áp case
                wtxt = apply_case(wtxt, cap_case)
            elif p.get("upper"):                # preset khai 'upper' (vd Hồng nổi,
                wtxt = wtxt.upper()             # Đậm bóng đổ) -> HOA như đã hứa
            body = prefix + wtxt
        lines.append(
            f"Dialogue: 0,{_fmt(a2)},{_fmt(b2)},Default,,0,0,0,,{body}\n")
    lines.extend(extra_lines)
    Path(out_path).write_text("".join(lines), encoding="utf-8")
    return True
