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


def _group(words: list, max_words: int = 3, max_dur: float = 1.3,
           gap: float = 0.6) -> list:
    """Gom 2-3 từ/cụm. KHÔNG gom qua ranh giới đoạn ghép (seg_idx đổi -> cụm mới)."""
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
    return [[ch[0][0], ch[-1][1], " ".join(c[2] for c in ch)] for ch in chunks]


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
        for w in ch:
            lead = int(round(max(0.0, w[0] - prev) * 100))
            if lead > 0:
                parts.append("{\\k%d}" % lead)        # chờ (chưa tô sáng)
            dur = int(round(max(0.08, w[1] - w[0]) * 100))
            parts.append("{\\kf%d}%s " % (dur, _esc(w[2])))
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


def _esc(text: str) -> str:
    return (text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")
                .replace("\n", " ").strip())


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
}
DEFAULT_PRESET = "Vàng nhảy (TikTok)"


def build_ass(words: list, segments: list, out_path,
              out_w: int = 1080, out_h: int = 1920,
              font: str = "Montserrat", size: int = 0,
              color: str = "", ny: float = 0.78,
              preset: str = DEFAULT_PRESET, delay: float = 0.0,
              hook: str = "", hook_dur: float = 6.0,
              hook_nx: float = 0.5, hook_ny: float = 0.10,
              hook_size: float = 0.0) -> bool:
    """Ghi file .ass phụ đề khớp lời theo KIỂU (preset). Trả True nếu có chữ.
    preset = tên kiểu trong CAPTION_PRESETS (vàng nhảy / karaoke / hộp đen / neon...).
    color = màu chữ TÙY CHỌN (ghi đè màu mặc định của kiểu); '' = dùng màu kiểu.
    delay = đẩy phụ đề TRỄ lại (giây) để khớp lời (whisper hay đánh dấu sớm);
            số âm = hiện sớm hơn. ny = vị trí dọc (0=trên, 1=dưới) do user KÉO.
    hook_nx/hook_ny = tâm-ngang/đỉnh ô HOOK (0..1, user kéo trong Chỉnh mẫu);
    hook_size = cỡ chữ hook theo tỉ lệ chiều cao (0 = mặc định 1.5x phụ đề).
    LƯU Ý: clip CÓ hook -> hook hiện trong hook_dur giây đầu, phụ đề chạy chữ
    bị ẨN trong lúc hook hiện (tránh chồng chữ), sau đó chạy bình thường."""
    has_hook = bool((hook or "").strip()) and hook_dur > 0
    remapped = _remap_words(words or [], segments or [])
    if not remapped and not has_hook:
        return False
    p = CAPTION_PRESETS.get(preset) or CAPTION_PRESETS[DEFAULT_PRESET]
    mode = p["mode"]
    main = color or p["color"]                 # màu chữ: user chọn hoặc của kiểu
    size = size or max(40, int(out_h * 0.05))
    side = int(out_w * 0.14)
    align = 8
    margin_v = int(max(0.02, min(0.9, ny)) * out_h)
    primary = _ass_color(main)
    outline = _ass_color(p.get("outline", "#000000"))
    ow = max(0, int(size * p.get("ow", 0.10)))
    shadow = p.get("shadow", 1)
    back = _alpha_color("#000000", 0x96)        # bóng đổ mặc định
    border_style = 1
    if p.get("box"):                            # KIỂU NỀN HỘP
        border_style = 3
        outline = _ass_color(p.get("box_color", "#000000"))
        ow = max(8, int(size * 0.20))           # = bề dày hộp ôm chữ
        shadow = 0
    elif p.get("glow"):                         # KIỂU NEON: bóng = màu viền (phát sáng)
        back = _alpha_color(p["glow"], 0x40)
    # secondary: karaoke = màu CHƯA nói (mờ); kiểu khác không dùng
    if mode == "karaoke":
        secondary = _alpha_color(p.get("unsung", "#FFFFFF"), 0x64)
        cues = _karaoke_cues(remapped)
        prefix = "{\\fad(60,40)}"               # cả cụm vào/ra mượt
    elif mode == "active":
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
        f"{style}\n{hook_style}\n\n"
        "[Events]\n"
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
    )
    lines = [head]
    if has_hook:                            # 1 dòng HOOK to ở đầu clip
        ht = _esc(hook)
        if p.get("upper"):
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
    # ---- KIỂU 'CẢ CÂU, TỪ ĐANG NÓI VÀNG' ----
    if mode == "active":
        rest_c = _ass_color(p.get("rest", "#FFFFFF"))
        act_c = primary                          # màu từ đang nói (vàng)
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
                    if j == i:                   # TỪ đang nói -> nhảy vàng (phồng nhẹ)
                        pop = ("\\t(0,90,\\fscx110\\fscy110)\\t(90,170,\\fscx100\\fscy100)"
                               if p.get("pop") else "")
                        parts.append(f"{{\\1c{act_c}{pop}}}{wt}{{\\1c{rest_c}}}")
                    else:
                        parts.append(wt)
                ev.append([wa, we, i == 0, i == n - 1, " ".join(parts)])
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
            if p.get("upper"):
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
        else:
            body = txt if mode == "karaoke" else _esc(txt)  # karaoke đã có tag
            body = prefix + body
        lines.append(
            f"Dialogue: 0,{_fmt(a2)},{_fmt(b2)},Default,,0,0,0,,{body}\n")
    Path(out_path).write_text("".join(lines), encoding="utf-8")
    return True
