"""
MODULE 2 — 🎙 REUP THUYẾT MINH (recap).

Đưa video vào -> AI đọc nội dung -> chọn các đoạn hay (TÁI DÙNG đường chọn
clip của M1) -> với MỖI clip, LLM "đạo diễn" (app/ai/recap.py) viết KỊCH BẢN
chia đoạn xen kẽ: GIỮ TIẾNG GỐC (khoảnh khắc đắt) / AI THUYẾT MINH (video tắt
tiếng, giọng AI kể — đúng NGÔN NGỮ video, theo PHONG CÁCH user chọn).

Kịch bản lưu vào clips.signals["recap"] (JSON sẵn có — không cần migration):
  {"style": "story", "lang": "en", "parts": [{"start","end","mode","text"}]}
Mốc part theo TIMELINE VIDEO GỐC (giây tuyệt đối, nằm trong segments của clip).

Xuất dùng lại job m1_export_clip: clip CÓ signals.recap -> m1 dựng track
thuyết minh (TTS) + tắt tiếng gốc trong các khoảng narrate (duck_ranges).
Clip KHÔNG có recap -> xuất y hệt cũ.

generate_recap KHÔNG đăng ký trực tiếp — được job "auto_recap"
(app/queue/jobs.py) gọi sau bước phân tích (như auto/auto_mixed).
"""
from __future__ import annotations

import os
import tempfile

from config import settings

from app.ai import llm, recap
from app.core.analysis import get_analysis
from app.core.ffmpeg_utils import extract_frame
from app.database import db
from app.modules.m1_highlight import (
    DEFAULTS, _delete_suggested, _llm_select_clips, load_used_ranges,
)
from app.queue.worker import JobContext

# Trần độ dài 1 clip recap khi user KHÔNG đặt Max (span liền mạch nên phải có
# trần cứng — thuyết minh clip 5 phút không phải mục tiêu short 9:16).
_HARD_MAX = 150.0
# Snap mốc part vào mép câu transcript trong phạm vi ±_SNAP_TOL giây
_SNAP_TOL = 1.5
# Tối đa số khung hình gửi model vision cho MỖI clip (tiết kiệm quota/băng thông)
_MAX_FRAMES = 6


def _clip_sentences(segs: list, start: float, end: float) -> list:
    """Các câu transcript GIAO với [start,end] -> [(s, e, text)]."""
    out = []
    for s in segs or []:
        try:
            a, b = float(s["start"]), float(s["end"])
        except (KeyError, TypeError, ValueError):
            continue
        txt = (s.get("text") or "").strip()
        if txt and b > start and a < end:
            out.append((max(a, start), min(b, end), txt))
    return out


# ------------------------------------------------------------------
# SNAP mốc cắt vào RANH GIỚI CÂU transcript (không cắt ngang câu nói)
# ------------------------------------------------------------------
def _sentence_edges(segs: list) -> list:
    """Tập mốc mép câu (start + end mỗi segment transcript), đã sort."""
    edges = set()
    for s in segs or []:
        try:
            edges.add(round(float(s["start"]), 2))
            edges.add(round(float(s["end"]), 2))
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(edges)


def _snap_time(t: float, edges: list, tol: float = _SNAP_TOL) -> float:
    """Dịch mốc t tới mép câu GẦN NHẤT trong ±tol giây; không có -> giữ nguyên."""
    best, bd = float(t), tol + 1e-9
    for b in edges:
        d = abs(b - t)
        if d < bd:
            bd, best = d, b
    return best


# ------------------------------------------------------------------
# SNAP CHUYỂN CẢNH: mốc chuyển kể<->gốc + mép window ưu tiên rơi vào mốc
# CHUYỂN CẢNH hình ảnh (phân tích "scenes" đã chạy trong pipeline auto) —
# cắt đúng nhịp hình chuyên nghiệp hơn. Mép câu vẫn là LUẬT CỨNG: mốc
# chuyển cảnh mà cắt ngang câu nói thì mép câu thắng.
# ------------------------------------------------------------------
_SCENE_TOL = 2.0        # tìm mốc chuyển cảnh trong ±2 giây quanh mốc cắt


def _scene_cuts(scenes) -> list:
    """Mốc CHUYỂN CẢNH (giây, sort tăng) từ kết quả phân tích 'scenes'
    (scene_detect: {"scenes": [{"start","end"}], "cut_points": [...]}).
    Ưu tiên cut_points; thiếu -> lấy mép start các scene. Không có phân
    tích scenes (LIGHT_MODE/skip) -> [] (mọi thứ chạy như cũ). Hàm thuần."""
    if not isinstance(scenes, dict):
        return []
    cuts = []
    for t in scenes.get("cut_points") or []:
        try:
            cuts.append(round(float(t), 2))
        except (TypeError, ValueError):
            continue
    if not cuts:
        for sc in scenes.get("scenes") or []:
            try:
                cuts.append(round(float(sc["start"]), 2))
            except (KeyError, TypeError, ValueError):
                continue
    return sorted(set(c for c in cuts if c > 0.01))


def _inside_sentence(t: float, spans: list, margin: float = 0.15) -> bool:
    """Mốc t có rơi vào GIỮA 1 câu nói không (spans = [(start, end)] câu
    transcript; margin = mép câu vẫn tính là ranh giới). Hàm thuần."""
    for a, b in spans or []:
        if a + margin < t < b - margin:
            return True
    return False


def _snap_time_scene(t: float, edges: list, cuts: list, spans: list,
                     tol: float = _SNAP_TOL,
                     scene_tol: float = _SCENE_TOL) -> float:
    """Snap mốc t: ƯU TIÊN mốc CHUYỂN CẢNH gần nhất trong ±scene_tol NẾU
    mốc đó cũng không cắt ngang câu nói (kiểm CẢ 2 điều kiện); xung đột
    (mốc cảnh nằm giữa câu) -> mép câu thắng (_snap_time như cũ). Không
    có cuts -> y hệt _snap_time. Hàm thuần — unit test được."""
    best, bd = None, scene_tol + 1e-9
    for c in cuts or []:
        d = abs(c - t)
        if d < bd:
            bd, best = d, c
    if best is not None and not _inside_sentence(best, spans):
        return float(best)
    return _snap_time(t, edges, tol)


def _unsplit_word(t: float, words: list) -> float:
    """Nếu mốc t rơi vào GIỮA 1 từ (word-level transcript) -> đẩy ra mép từ
    gần hơn (không cắt ngang từ). words = [(ws, we)]. Không words -> giữ t."""
    for ws, we in words or []:
        if ws + 0.01 < t < we - 0.01:
            return ws if (t - ws) <= (we - t) else we
    return t


def _snap_parts(parts: list, edges: list, tol: float = _SNAP_TOL,
                words: list | None = None, min_part: float = 1.5,
                cuts: list | None = None,
                spans: list | None = None) -> list:
    """Snap ranh giới GIỮA các part vào mép câu transcript (±tol giây).

    Ranh giới chung của part i và i+1 được dịch CÙNG NHAU (giữ phủ kín,
    không tạo hở/chồng lấn). Mốc MỞ ĐẦU part đầu + KẾT THÚC part cuối cũng
    snap (LLM hay lệch vài trăm ms so với mép câu -> validate sẽ chèn part
    orig vụn lên TRƯỚC hook, phá luật "part đầu là narrate"). Sau khi snap
    theo câu, nếu mốc vẫn nằm GIỮA 1 từ (transcript có words) -> đẩy ra mép
    từ. Snap nào làm 1 trong 2 part kề ngắn hơn min_part -> BỎ snap đó (giữ
    mốc cũ).

    cuts/spans != None: mốc CHUYỂN VAI narrate<->orig + mép đầu/cuối danh
    sách part ƯU TIÊN snap vào mốc CHUYỂN CẢNH gần nhất ±_SCENE_TOL nếu mốc
    đó không cắt ngang câu (_snap_time_scene — xung đột thì mép câu thắng);
    ranh giới cùng vai vẫn snap mép câu như cũ. Hàm thuần — test được."""
    if not parts:
        return []
    out = [dict(p) for p in parts]

    def snap_edge(t: float) -> float:
        """Mốc chuyển vai / mép danh sách: ưu tiên chuyển cảnh nếu có."""
        if cuts:
            return _snap_time_scene(t, edges, cuts, spans or [], tol)
        return _snap_time(t, edges, tol)

    # đầu part ĐẦU + cuối part CUỐI (validate_parts sẽ clamp vào span clip)
    s0 = _unsplit_word(snap_edge(float(out[0]["start"])), words)
    if (abs(s0 - float(out[0]["start"])) >= 0.01
            and float(out[0]["end"]) - s0 >= min_part):
        out[0]["start"] = round(s0, 2)
    e9 = _unsplit_word(snap_edge(float(out[-1]["end"])), words)
    if (abs(e9 - float(out[-1]["end"])) >= 0.01
            and e9 - float(out[-1]["start"]) >= min_part):
        out[-1]["end"] = round(e9, 2)
    for i in range(len(out) - 1):
        b0 = float(out[i]["end"])
        role_change = (str(out[i].get("mode") or "")
                       != str(out[i + 1].get("mode") or ""))
        b1 = snap_edge(b0) if role_change else _snap_time(b0, edges, tol)
        b1 = _unsplit_word(b1, words)
        if abs(b1 - b0) < 0.01:
            continue
        # không được làm part kề teo dưới min_part
        if (b1 - float(out[i]["start"]) < min_part
                or float(out[i + 1]["end"]) - b1 < min_part):
            continue
        out[i]["end"] = round(b1, 2)
        out[i + 1]["start"] = round(b1, 2)
    return out


# ------------------------------------------------------------------
# 📚 CHIA CHƯƠNG: K clip thuyết minh độc lập (Part 1..K)
# ------------------------------------------------------------------
# Video ngắn hơn ngưỡng này (hoặc transcript quá mỏng) -> tự hạ còn 1 clip
# (chia 3 chương cho video 2 phút chỉ ra clip vụn vô nghĩa).
_MIN_DUR_PER_EXTRA_CLIP = 150.0     # 2.5 phút
_MIN_SENTS_MULTI = 12


def _auto_recap_count(duration: float) -> int:
    """Số clip 'Tự động theo độ dài' (recap_count = 0, mặc định):
    < 4 phút -> 1 clip; 4-12 phút -> 2; > 12 phút -> 3.
    Hàm thuần — test được."""
    d = float(duration or 0)
    if d < 240.0:
        return 1
    if d <= 720.0:
        return 2
    return 3


def _win_bounds(preset: dict) -> tuple:
    """Min/Max SỐ CẢNH GHÉP mỗi clip -> (min, max, auto).

    Số cảnh ghép GIỜ LUÔN do AI tự quyết (bỏ hẳn phần "Cắt ghép" trong ⚙
    Cài đặt Reup) -> LUÔN trả bound RỘNG (2, 8) chỉ để chặn vô lý (prompt
    đạo diễn không gò cứng, validate_windows dùng max_n=8) + auto=True.
    preset không còn đọc key recap_win_* nữa. Hàm thuần — test được."""
    return 2, 8, True


def _resolve_count(preset: dict, duration: float) -> int:
    """recap_count trong preset -> số clip 1-3. 0/thiếu/hỏng = TỰ ĐỘNG theo
    độ dài (mặc định mới — user vẫn chọn tay 1-3 trong ⚙ Cài đặt Reup).
    Hàm thuần — test được."""
    try:
        c = int(preset.get("recap_count", 0))
    except (TypeError, ValueError):
        c = 0
    if c <= 0:
        c = _auto_recap_count(duration)
    return max(1, min(3, c))


def _split_chapters(duration: float, edges: list, k: int,
                    sentences: list | None = None) -> list:
    """Chia [0, duration] thành k CHƯƠNG, mốc chia SNAP vào mép câu transcript
    (không cắt ngang câu nói). k<=1/duration hỏng -> 1 chương cả video.

    CHIA THEO MẬT ĐỘ THOẠI (sửa lỗi 'số clip 3 -> ra 2'): nếu có `sentences`
    ([(start,end,text)]) -> mốc chia rơi vào chỗ MỖI CHƯƠNG có ~tổng_câu/k
    câu (thay vì chia đều thời gian -> chương giữa thưa thoại bị bỏ). Đoạn
    thoại dày -> chương ngắn; đoạn thưa -> chương dài, nhưng CHƯƠNG NÀO CŨNG
    có đủ câu để đạo diễn. Không có sentences -> chia đều thời gian như cũ.
    Snap làm chương teo (<20s) -> giữ mốc chia gốc. Hàm thuần — test được."""
    dur = float(duration or 0)
    if k <= 1 or dur <= 0:
        return [(0.0, dur)]
    # mốc chia THÔ: theo phân bố câu (đều SỐ CÂU/chương) nếu có transcript,
    # nếu không thì chia đều thời gian.
    raw_bounds = []
    sents = sorted(((float(a) + float(b)) / 2 for a, b, *_ in (sentences or [])))
    if len(sents) >= k:                  # đủ câu để chia theo mật độ
        for i in range(1, k):
            idx = int(round(len(sents) * i / k))
            idx = max(1, min(len(sents) - 1, idx))
            # mốc = giữa 2 câu quanh ranh giới nhóm câu (né cắt ngang câu)
            raw_bounds.append((sents[idx - 1] + sents[idx]) / 2)
    else:                                # thoại quá mỏng -> chia đều thời gian
        raw_bounds = [dur * i / k for i in range(1, k)]
    bounds = [0.0]
    for raw in raw_bounds:
        t = _snap_time(raw, edges, tol=15.0)
        if t - bounds[-1] < 20.0 or dur - t < 20.0:
            t = raw                      # snap phá chương -> giữ mốc gốc
        bounds.append(round(t, 2))
    bounds.append(round(dur, 2))
    out = [(bounds[i], bounds[i + 1]) for i in range(k)
           if bounds[i + 1] - bounds[i] >= 20.0]
    return out or [(0.0, dur)]


def _count_sents(sentences: list, c0: float, c1: float) -> int:
    """Số câu transcript có TÂM rơi trong chương [c0,c1]. Hàm thuần."""
    return sum(1 for a, b, *_ in (sentences or [])
               if c0 - 0.01 <= (float(a) + float(b)) / 2 <= c1 + 0.01)


def _merge_sparse_chapters(chapters: list, sentences: list,
                           min_sents: int = 3) -> list:
    """GỘP chương THƯA THOẠI (< min_sents câu) vào chương KỀ (ưu tiên chương
    kề THƯA hơn để cân bằng) — thay vì BỎ chương thưa (bỏ -> thiếu clip).
    Trả list chương [(c0,c1)] đã gộp, thứ tự thời gian giữ nguyên. Lặp tới
    khi mọi chương đủ dày HOẶC chỉ còn 1 chương. Hàm thuần — test được."""
    chs = [(float(c0), float(c1)) for c0, c1 in (chapters or [])]
    if len(chs) <= 1:
        return chs
    changed = True
    while changed and len(chs) > 1:
        changed = False
        for i, (c0, c1) in enumerate(chs):
            if _count_sents(sentences, c0, c1) >= min_sents:
                continue
            # chương thưa -> gộp với chương kề có ÍT câu hơn (né phình chương dày)
            left = chs[i - 1] if i > 0 else None
            right = chs[i + 1] if i + 1 < len(chs) else None
            if left and right:
                nl = _count_sents(sentences, *left)
                nr = _count_sents(sentences, *right)
                merge_left = nl <= nr
            else:
                merge_left = right is None
            if merge_left:
                chs[i - 1] = (chs[i - 1][0], c1)
                del chs[i]
            else:
                chs[i + 1] = (c0, chs[i + 1][1])
                del chs[i]
            changed = True
            break
    return chs


# ------------------------------------------------------------------
# 🚫 CHỐNG TRÙNG CẢNH GIỮA CÁC CLIP: mỗi giây video chỉ thuộc 1 clip.
# Dùng "used ranges" (các khoảng đã dùng ở clip TRƯỚC) — clip sau CẮT BỎ
# mọi phần giao với used (kèm khoảng đệm), cập nhật used sau mỗi clip.
# ------------------------------------------------------------------
_CLIP_GAP = 0.5           # đệm giữa 2 clip (giây) — clip sau bắt đầu sau
_MIN_WIN_KEEP = 3.0       # window còn lại dưới ngưỡng này sau khi cắt -> bỏ


def _merge_ranges(ranges: list, gap: float = 0.0) -> list:
    """Gộp các khoảng [s,e] chồng/sát nhau (cách <= gap) -> list rời rạc,
    sort tăng. Hàm thuần — test được."""
    norm = sorted(([float(s), float(e)] for s, e in ranges or []
                   if float(e) > float(s)), key=lambda x: x[0])
    out: list = []
    for s, e in norm:
        if out and s <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def _subtract_used(windows: list, used: list, gap: float = _CLIP_GAP,
                   min_keep: float = _MIN_WIN_KEEP) -> list:
    """Cắt khỏi mỗi window mọi phần GIAO với các khoảng `used` (đã dùng ở
    clip trước), nới `used` thêm `gap` đệm 2 bên. Trả các mảnh window còn
    lại (>= min_keep giây), sort tăng, KHÔNG giao với used. Hàm thuần —
    unit test được (nền tảng chống trùng cảnh giữa clip)."""
    blocked = [[s - gap, e + gap] for s, e in _merge_ranges(used)]
    out: list = []
    for ws, we in windows or []:
        ws, we = float(ws), float(we)
        pieces = [[ws, we]]
        for bs, be in blocked:
            nxt = []
            for ps, pe in pieces:
                if be <= ps or bs >= pe:       # không giao -> giữ nguyên
                    nxt.append([ps, pe])
                    continue
                if bs > ps:                    # giữ mảnh trước khối chặn
                    nxt.append([ps, min(bs, pe)])
                if be < pe:                    # giữ mảnh sau khối chặn
                    nxt.append([max(be, ps), pe])
            pieces = nxt
        for ps, pe in pieces:
            if pe - ps >= min_keep:
                out.append([round(ps, 2), round(pe, 2)])
    out.sort(key=lambda x: x[0])
    return out


def _has_overlap(windows: list) -> bool:
    """Có cặp window nào GIAO nhau không (kiểm tra trong 1 clip). Hàm thuần."""
    ws = sorted(([float(s), float(e)] for s, e in windows or []),
                key=lambda x: x[0])
    for i in range(len(ws) - 1):
        if ws[i][1] > ws[i + 1][0] + 1e-6:
            return True
    return False


def _snap_up(t: float, edges: list, tol: float = 3.0) -> float:
    """Đẩy mốc CUỐI lên mép câu gần nhất trong [t, t+tol]; không có -> giữ t."""
    cands = [b for b in edges if t - 0.05 <= b <= t + tol]
    return max(cands) if cands else t


def _snap_down(t: float, edges: list, tol: float = 3.0) -> float:
    """Đẩy mốc ĐẦU xuống mép câu gần nhất trong [t-tol, t]; không có -> giữ t."""
    cands = [b for b in edges if t - tol <= b <= t + 0.05]
    return min(cands) if cands else t


def _enforce_recap_len(windows: list, min_len: float, max_len: float,
                       edges: list, chapter: tuple, used: list,
                       duration: float,
                       gap: float = _CLIP_GAP) -> list:
    """ÉP TỔNG độ dài các window của 1 clip recap vào [min_len, max_len].

    SỬA LỖI 'clip recap 46s khi min 60': validate_windows chỉ cắt TRẦN từng
    khung, KHÔNG ép SÀN tổng -> AI chọn windows tổng < min vẫn lọt. Hàm này
    chạy cho MỖI clip trước khi lưu:
      - Tổng < min_len -> NỚI: kéo dài window CUỐI về sau (bám mép câu, KHÔNG
        tràn ranh giới chương/video, né `used` + đệm gap). Không đủ trong
        chương -> nới window ĐẦU về trước; vẫn thiếu -> nới CUỐI ra NGOÀI
        chương (tới hết video) né used.
      - Tổng > max_len -> CẮT bớt: rút window cuối (bám mép câu), khung teo
        dưới _MIN_WIN_KEEP thì bỏ hẳn.
    edges = mép câu transcript; chapter = (c0,c1) ranh giới chương; used =
    các khoảng clip trước đã dùng (né trùng cảnh). Hàm thuần — test được."""
    ws = [[float(s), float(e)] for s, e in (windows or [])]
    if not ws:
        return ws
    ws.sort(key=lambda x: x[0])
    c0, c1 = float(chapter[0]), float(chapter[1])
    dur = float(duration or 0) or (ws[-1][1])
    blocked = [[b0 - gap, b1 + gap] for b0, b1 in _merge_ranges(used)]

    def _room_end(t: float, hard: float) -> float:
        """Mốc xa nhất window cuối nới tới được (<= hard, né khối `used`)."""
        limit = hard
        for b0, b1 in blocked:
            if b0 >= t and b0 < limit:      # khối chặn phía sau -> dừng trước nó
                limit = b0
        return max(t, limit)

    def _room_start(t: float, hard: float) -> float:
        """Mốc gần nhất window đầu lùi tới được (>= hard, né khối `used`)."""
        limit = hard
        for b0, b1 in blocked:
            if b1 <= t and b1 > limit:
                limit = b1
        return min(t, limit)

    def _total():
        return sum(e - s for s, e in ws)

    # ---- CẮT nếu quá max ----
    if max_len and max_len > 0 and _total() > max_len + 1.0:
        cut, tot = [], 0.0
        for s, e in ws:
            if tot >= max_len - 0.01:
                break
            if tot + (e - s) > max_len:
                ne = round(s + (max_len - tot), 2)
                ne = _snap_down(ne, edges, tol=2.0)
                if ne - s < _MIN_WIN_KEEP:
                    break
                cut.append([s, ne]); tot += ne - s
                break
            cut.append([s, e]); tot += e - s
        ws = cut or ws[:1]

    # ---- NỚI nếu dưới min ----
    if min_len and min_len > 0 and _total() < min_len - 1.0:
        # 1) nới CUỐI về sau, tối đa tới hết chương (né used)
        deficit = min_len - _total()
        hard = _room_end(ws[-1][1], c1)
        room = max(0.0, hard - ws[-1][1])
        add = min(room, deficit)
        if add > 0.05:
            ne = _snap_up(ws[-1][1] + add, edges, tol=3.0)
            ne = min(ne, hard)
            if ne < ws[-1][1] + add - 0.5:  # snap kéo ngắn -> bỏ snap
                ne = ws[-1][1] + add
            ws[-1][1] = round(min(ne, hard), 2)
        # 2) còn thiếu -> nới ĐẦU về trước (tới đầu chương, né used)
        deficit = min_len - _total()
        if deficit > 0.5:
            hard = _room_start(ws[0][0], c0)
            room = max(0.0, ws[0][0] - hard)
            add = min(room, deficit)
            if add > 0.05:
                ns = _snap_down(ws[0][0] - add, edges, tol=3.0)
                ns = max(ns, hard)
                if ws[0][0] - ns < add - 0.5:
                    ns = ws[0][0] - add
                ws[0][0] = round(max(ns, hard), 2)
        # 3) vẫn thiếu -> nới CUỐI ra NGOÀI chương tới hết video (né used)
        deficit = min_len - _total()
        if deficit > 0.5:
            hard = _room_end(ws[-1][1], dur)
            room = max(0.0, hard - ws[-1][1])
            add = min(room, deficit)
            if add > 0.05:
                ne = _snap_up(ws[-1][1] + add, edges, tol=3.0)
                ne = min(ne, hard)
                if ne < ws[-1][1] + add - 0.5:
                    ne = ws[-1][1] + add
                ws[-1][1] = round(min(ne, hard), 2)
    return [[round(s, 2), round(e, 2)] for s, e in ws]


# ------------------------------------------------------------------
# 🎬 MULTI-WINDOW: rút gọn transcript cho prompt đạo diễn
# ------------------------------------------------------------------
def _condense_listing(segs: list, duration: float,
                      max_chars: int = 11000) -> str:
    """Transcript cho prompt ĐẠO DIỄN. Video ngắn (<=8 phút) -> nguyên từng
    câu; dài hơn -> GỘP các câu liền kề thành dòng ~10s (đủ hiểu mạch chuyện,
    tiết kiệm token); vẫn quá max_chars -> gộp thô 20s; chốt cắt max_chars."""
    def build(step: float) -> str:
        lines, cur_s, cur_e, buf = [], None, 0.0, []
        for s in segs or []:
            try:
                a, b = float(s["start"]), float(s["end"])
            except (KeyError, TypeError, ValueError):
                continue
            t = (s.get("text") or "").strip()
            if not t:
                continue
            if cur_s is None:
                cur_s = a
            buf.append(t)
            cur_e = max(cur_e, b)
            if step <= 0 or cur_e - cur_s >= step:
                lines.append(f"{cur_s:.1f} {cur_e:.1f} | {' '.join(buf)}")
                cur_s, buf = None, []
        if buf:
            lines.append(f"{cur_s:.1f} {cur_e:.1f} | {' '.join(buf)}")
        return "\n".join(lines)

    txt = build(0.0 if (duration or 0) <= 480 else 10.0)
    if len(txt) > max_chars:
        txt = build(20.0)
    return txt[:max_chars]


# ------------------------------------------------------------------
# NGỮ CẢNH THỊ GIÁC: trích khung hình cho model vision "nhìn" clip
# ------------------------------------------------------------------
def _clip_frames(src: str, start: float, end: float, tmp_dir: str,
                 tag: str) -> list:
    """Trích tối đa _MAX_FRAMES khung hình RẢI ĐỀU clip (1 frame giữa mỗi
    cửa sổ con ~12-15s — cỡ 1 part ứng viên) -> [(giây, đường_dẫn_jpg)].
    Ảnh nhỏ ~360px (tiết kiệm token vision). Frame trích lỗi -> bỏ riêng."""
    dur = end - start
    if dur <= 1.0 or not src or not os.path.exists(src):
        return []
    n = max(2, min(_MAX_FRAMES, int(round(dur / 12.0))))
    out = []
    for k in range(n):
        t = start + (k + 0.5) * dur / n        # giữa mỗi cửa sổ con
        fp = os.path.join(tmp_dir, f"_recapf_{tag}_{k}.jpg")
        if extract_frame(src, t, fp, width=360):
            out.append((round(t, 1), fp))
    return out


def generate_recap(payload: dict, ctx: JobContext) -> dict:
    """Bước 'reup thuyết minh' — job 'auto_recap' gọi sau khi phân tích.

    payload: {video_id, preset: {..., recap_style, recap_ratio,
    recap_count, min_len, max_len}}.
    Số CẢNH ghép mỗi clip GIỜ LUÔN do AI tự quyết (bound rộng 2-8, prompt
    không gò cứng). min_len/max_len = ĐỘ DÀI mỗi clip (giây) từ ⚙ Cài đặt
    Reup (recap_min_sec/max_sec) — studio_page override 'Tùy chỉnh cắt'
    chung; thiếu -> lùi cut_min/cut_max cũ. recap_count = số clip thuyết
    minh: 0/thiếu = TỰ ĐỘNG
    theo độ dài (<4 phút 1 clip, 4-12 phút 2, >12 phút 3 — mặc định), hoặc
    chọn tay 1-3 — chia video thành K CHƯƠNG, mỗi chương 1 clip độc lập.
    Kết quả: các dòng clips status='suggested' kèm signals.recap (kịch
    bản). Lỗi LLM -> ném lỗi rõ.
    """
    video_id = int(payload["video_id"])
    preset = payload.get("preset") or {}
    cfg = {**DEFAULTS, **preset}
    style = str(preset.get("recap_style") or recap.DEFAULT_STYLE)
    try:                              # tỉ lệ AI kể (15-80%) từ Cài đặt Reup
        ratio = float(preset.get("recap_ratio") or 45)
    except (TypeError, ValueError):
        ratio = 45.0
    # 🎭 Giọng cảm xúc (audio tag v3): BẬT -> prompt dặn AI chèn tag cảm xúc
    # ([excited]/[whispers]/[dramatic pause]) + nhấn CAPS vào lời narrate.
    # MẶC ĐỊNH BẬT; tag chỉ phát huy khi export bằng giọng ElevenLabs v3,
    # nhưng chèn sẵn KHÔNG hại (build_recap_track tự strip cho giọng khác).
    emotion = str(preset.get("recap_emotion", True)).strip().lower() \
        not in ("false", "0", "no", "off")

    if not llm.is_configured():
        raise RuntimeError(
            "Reup thuyết minh cần AI viết kịch bản — hãy dán key Groq/Gemini "
            "trong 'Cài đặt AI' rồi thử lại.")

    ctx.progress(0.02, "Đọc kết quả phân tích...")
    transcript = get_analysis(video_id, "transcript") or {}
    scenes = get_analysis(video_id, "scenes") or {}
    segs = transcript.get("segments") or []
    if not segs:
        raise RuntimeError(
            "Video chưa có lời thoại (transcript) — không viết được kịch bản "
            "thuyết minh. Hãy chạy phân tích trước.")
    vrow = db.query_one("SELECT duration, src_path FROM videos WHERE id=?",
                        (video_id,))
    duration = float(vrow["duration"] or 0) if vrow else 0.0
    src_path = (vrow["src_path"] or "") if vrow else ""
    # 🚫 CHỐNG TRÙNG QUA CÁC LẦN TẠO: các đoạn ĐÃ dùng ở clip trước của video
    # này (đọc TRƯỚC _delete_suggested — giữ cả lần bấm trước còn treo
    # suggested). Reup lần sau (hoặc sau khi đã Tạo clip thường) né các đoạn cũ.
    prev_used = load_used_ranges(video_id)
    # Tên ngôn ngữ CHUẨN TIẾNG ANH ("English"/"Vietnamese") cho prompt —
    # tên kiểu "tiếng Anh" từng làm model viết kịch bản tiếng Việt cho
    # video EN (model tuân "write in English" tốt hơn hẳn).
    lang_name = recap.lang_en_name(transcript.get("language", ""))
    edges = _sentence_edges(segs)          # mép câu -> snap mốc cắt
    tr_words = []                          # (ws, we) word-level nếu whisper trả
    for w in (transcript.get("words") or []):
        try:
            tr_words.append((float(w["start"]), float(w["end"])))
        except (KeyError, TypeError, ValueError):
            continue
    # Mốc CHUYỂN CẢNH từ phân tích "scenes" (đã chạy trong pipeline auto;
    # LIGHT_MODE/skip -> rỗng, snap chạy như cũ) + khoảng từng câu để kiểm
    # "mốc cảnh có cắt ngang câu không" (mép câu là luật cứng, cảnh chỉ ưu
    # tiên khi không phạm câu).
    scene_cuts = _scene_cuts(scenes)
    sent_spans = []
    for s in segs:
        try:
            sent_spans.append((float(s["start"]), float(s["end"])))
        except (KeyError, TypeError, ValueError):
            continue

    # ---- 0) 🎬 ĐẠO DIỄN MULTI-WINDOW THEO CHƯƠNG (mặc định): chia video
    # thành K CHƯƠNG thời lượng ~bằng nhau (user chọn 1-3 trong ⚙ Cài đặt
    # Reup, mặc định 2) rồi chạy đạo diễn RIÊNG từng chương -> K clip recap
    # ĐỘC LẬP Part 1..K, mỗi clip có hook + mạch chuyện + kết RIÊNG của
    # chương đó (sửa lỗi user 'chỉ làm được 1 video'). Video ngắn (<2.5
    # phút) / transcript mỏng -> tự hạ còn 1 clip (không chia vụn).
    # Mọi chương hỏng hoặc LLM lỗi -> FALLBACK đường 1-span cũ bên dưới.
    prov = llm.active_provider()
    min_total = float(cfg.get("min_len") or 0) or 60.0
    max_total = float(cfg.get("max_len") or 0) or _HARD_MAX
    # min/max SỐ CẢNH ghép mỗi clip (win_auto=True -> AI tự chọn, bound rộng)
    win_lo, win_hi, win_auto = _win_bounds(preset)
    sents_all = []
    for s in segs:
        try:
            a, b = float(s["start"]), float(s["end"])
        except (KeyError, TypeError, ValueError):
            continue
        t = (s.get("text") or "").strip()
        if t:
            sents_all.append((a, b, t))
    # duration DB có thể trống -> lấy mép câu cuối transcript làm độ dài
    dur_hint = duration or (sents_all[-1][1] if sents_all else 0.0)
    count = _resolve_count(preset, dur_hint)   # 0 = tự động theo độ dài
    if (duration < _MIN_DUR_PER_EXTRA_CLIP
            or len(sents_all) < _MIN_SENTS_MULTI):
        count = 1                       # video ngắn/thoại mỏng -> 1 clip
    else:
        # mỗi chương phải đủ dày (>=60s) để đạo diễn có cái mà cắt ghép
        count = min(count, max(1, int(duration // 60.0)))

    chapters = _split_chapters(duration, edges, count, sents_all)
    # 🚫 SỬA LỖI 'số clip N -> ra ít hơn': chương THƯA THOẠI (<3 câu) KHÔNG
    # bị bỏ trống nữa (bỏ -> thiếu clip). Chia đã theo mật độ câu nên hiếm
    # khi còn chương thưa; nếu vẫn còn (đoạn video gần như không lời) -> GỘP
    # vào chương KỀ để cả 2 gộp lại vẫn đủ câu, giữ đúng tinh thần "cố ra đủ
    # N khi video đủ nội dung". Gộp xong count thực tế có thể < N -> log rõ.
    chapters = _merge_sparse_chapters(chapters, sents_all, min_sents=3)
    if len(chapters) < count:
        ctx.progress(0.05,
                     f"⚠ Video không đủ nội dung cho {count} clip — sau khi "
                     f"gộp chương thưa thoại chỉ tạo được tối đa "
                     f"{len(chapters)} clip.")
    ch_scripts: list[tuple[int, float, float, dict]] = []
    for ci, (c0, c1) in enumerate(chapters):
        ctx.progress(0.06 + 0.34 * ci / max(1, len(chapters)),
                     f"AI [{prov}] viết kịch bản chương "
                     f"{ci + 1}/{len(chapters)} (chọn khung cảnh + cầu "
                     "nối)...")
        ch_sents = [(a, b, t) for a, b, t in sents_all
                    if c0 - 0.01 <= (a + b) / 2 <= c1 + 0.01]
        ch_segs = [s for s in segs
                   if c0 - 0.01 <= (float(s.get("start", 0))
                                    + float(s.get("end", 0))) / 2 <= c1 + 0.01]
        try:
            sc = recap.write_director_script(
                ch_sents, lang_name, style, c1,
                min(min_total, max(30.0, 0.6 * (c1 - c0))),
                min(max_total, c1 - c0), ratio=ratio,
                listing=_condense_listing(ch_segs, c1 - c0),
                win_min=win_lo, win_max=win_hi, emotion=emotion,
                win_auto=win_auto)
        except llm.LLMError:
            sc = None                  # chương lỗi -> bỏ riêng chương đó
        if sc:
            ch_scripts.append((ci, c0, c1, sc))
            # LOG RÕ ĐƯỜNG ĐI: user nhìn queue biết ngay chương này dùng
            # kịch bản mấy cảnh (vs "1 mạch (dự phòng)" bên dưới).
            ctx.progress(0.06 + 0.34 * (ci + 1) / max(1, len(chapters)),
                         f"Chương {ci + 1}: kịch bản "
                         f"{len(sc['windows'])} cảnh ✔")
            if sc.get("lang_warn"):    # hậu kiểm ngôn ngữ bắt lỗi -> báo user
                ctx.progress(0.06 + 0.34 * (ci + 1) / max(1, len(chapters)),
                             f"⚠ Chương {ci + 1}: {sc['lang_warn']}")

    if ch_scripts:
        _delete_suggested(video_id)
        lang0 = (transcript.get("language") or "").strip()
        clip_ids: list = []
        # 🚫 khoảng ĐÃ dùng: SEED bằng các clip lần trước (prev_used) + cập nhật
        # dần sau mỗi chương -> windows mới né cả clip cũ lẫn chương trước.
        used_ranges: list = list(prev_used)
        for ci, c0, c1, script in ch_scripts:
            # SNAP mép khung vào CHUYỂN CẢNH (ưu tiên, nếu không cắt ngang
            # câu) / mép câu + KẸP CỨNG vào chương [c0,c1] (snap KHÔNG được
            # vượt ranh giới chương) rồi VALIDATE LẠI; part snap + validate
            # TỪNG khung (không vắt khung).
            snapped_w = [[max(c0, min(c1, _snap_time_scene(
                                  s, edges, scene_cuts, sent_spans))),
                          max(c0, min(c1, _snap_time_scene(
                                  e, edges, scene_cuts, sent_spans)))]
                         for s, e in script["windows"]]
            # 🚫 CHỐNG TRÙNG CẢNH: cắt bỏ phần giao với các clip TRƯỚC (mỗi
            # giây video chỉ thuộc 1 clip). Snap có thể nới window tràn sang
            # chương/clip kế -> _subtract_used dồn về khoảng chưa dùng.
            snapped_w = _subtract_used(snapped_w, used_ranges)
            ch_sents = _clip_sentences(segs, c0, c1)
            windows = recap.validate_windows(snapped_w, duration,
                                             max_n=win_hi,
                                             sentences=ch_sents)
            # 🔒 ÉP ĐỘ DÀI CLIP VÀO [min_total, max_total] (sửa lỗi 'clip
            # recap 46s khi min 60'): validate_windows chỉ clamp TRẦN từng
            # khung, KHÔNG ép SÀN tổng -> AI chọn windows tổng < min vẫn lọt.
            # _enforce_recap_len nới/cắt tổng windows về đúng khoảng user đặt,
            # bám mép câu, né used_ranges + ranh giới chương/video.
            windows = _enforce_recap_len(
                windows, min_total, max_total, edges,
                (c0, c1), used_ranges, duration)
            snapped_parts: list = []
            for ws, we in windows or []:
                sub = [p for p in script["parts"]
                       if ws - 0.01
                       <= (float(p["start"]) + float(p["end"])) / 2
                       <= we + 0.01]
                snapped_parts.extend(
                    _snap_parts(sub, edges, words=tr_words,
                                cuts=scene_cuts, spans=sent_spans))
            # validate TỪNG khung + RELEVANCE (lời narrate phải dính chi
            # tiết transcript khung đó/kề — validate_parts_windows lo)
            parts = recap.validate_parts_windows(snapped_parts, windows,
                                                 sentences=ch_sents)
            # ÉP CỨNG tỉ lệ AI kể (prompt xin thôi chưa đủ — LLM hay nói
            # tràn ~80%): vượt ratio+12% -> chuyển part kể giữa dài nhất
            # về orig, giữ hook + chốt (recap.enforce_narrate_ratio).
            parts = recap.enforce_narrate_ratio(parts, ratio)
            if not windows or not any(p["mode"] == "narrate" for p in parts):
                continue                # chương snap hỏng -> bỏ riêng chương
            total = round(sum(e - s for s, e in windows), 1)
            title = script.get("title") or "Clip thuyết minh"
            wlist = [[round(s, 2), round(e, 2)] for s, e in windows]
            signals = {
                "segments": wlist, "n_seg": len(wlist), "llm_used": True,
                "ai": prov, "dur": total,
                "title_en": script.get("title") or "",
                "recap": {"style": style, "lang": lang0, "parts": parts,
                          "windows": wlist, "chapter": [c0, c1]},
            }
            chap_note = (f"Chương {ci + 1}/{len(chapters)}: "
                         if len(chapters) > 1 else "")
            cid = db.insert(
                """INSERT INTO clips (video_id, start_sec, end_sec, score,
                                      reason, title, transcript, signals,
                                      status)
                   VALUES (?,?,?,?,?,?,?,?, 'suggested')""",
                (video_id, wlist[0][0], wlist[-1][1], 80.0,
                 f"{chap_note}đạo diễn ghép {len(wlist)} khung cảnh "
                 f"(~{total:.0f}s), thuyết minh "
                 + recap.style_label(style) + ".",
                 title, "", db.dumps(signals)))
            clip_ids.append(cid)
            used_ranges.extend(wlist)   # 🚫 clip sau né các khung này
        if clip_ids:
            ctx.progress(1.0, f"AI [{prov}] dựng {len(clip_ids)} clip recap "
                              f"theo {len(chapters)} chương "
                              f"({recap.style_label(style)})")
            return {"count": len(clip_ids), "clip_ids": clip_ids,
                    "scripts": len(clip_ids), "style": style,
                    "llm_used": True, "chapters": len(chapters)}

    # ---- 1) FALLBACK 1-SPAN: chọn các đoạn hay (đường chọn clip của auto) ----
    # LOG RÕ ĐƯỜNG ĐI: đạo diễn multi-window hỏng -> kịch bản 1 mạch dự phòng
    ctx.progress(0.05, f"AI [{prov}] kịch bản 1 mạch (dự phòng) — đang đọc "
                       "nội dung & chọn đoạn hay...")

    class _Sel:                       # map tiến độ chọn clip về 0.05..0.45
        profile = ctx.profile
        def progress(self, p, m=""):
            ctx.progress(0.05 + 0.40 * max(0.0, min(1.0, (p - 0.3) / 0.3)), m)
        def check_canceled(self):
            ctx.check_canceled()

    clips, warns = _llm_select_clips(transcript, duration, _Sel(), scenes, cfg)
    if not clips:
        return {"count": 0, "clip_ids": [],
                "note": "AI không chọn được đoạn nào đủ hay để thuyết minh."}

    # Recap dùng SPAN LIỀN MẠCH (thuyết minh phủ cả đoạn, không cắt khúc giữa).
    # Đầu/cuối span SNAP vào CHUYỂN CẢNH (ưu tiên, nếu không cắt ngang câu)
    # hoặc mép câu transcript (±_SNAP_TOL) -> không mở/đóng clip giữa chừng
    # 1 câu nói.
    max_len = float(cfg.get("max_len") or 0) or _HARD_MAX
    # clips đã sort theo thời gian; giữ mốc KẾT của span TRƯỚC để span sau
    # bắt đầu SAU nó + đệm (🚫 chống trùng cảnh: các span PHẢI rời nhau —
    # snap có thể kéo mép span sau lùi về trước mép span trước -> chồng).
    # 🚫 CHỐNG TRÙNG QUA CÁC LẦN TẠO: các đoạn đã dùng ở clip trước làm khối
    # chặn -> span mới né (mảnh còn lại dài nhất). span[i] sau đó cũng thành
    # khối chặn cho span[i+1] (giữ các span rời nhau như cũ).
    span_used = list(prev_used)
    spans = []
    prev_end = 0.0
    for c in clips:
        s0 = float(c["segments"][0][0])
        e1 = float(c["segments"][-1][1])
        s0 = max(0.0, _snap_time_scene(s0, edges, scene_cuts, sent_spans))
        e1 = _snap_time_scene(e1, edges, scene_cuts, sent_spans)
        s0 = max(s0, prev_end + _CLIP_GAP if prev_end > 0 else s0)
        e1 = min(e1, s0 + max_len, duration or e1)
        if e1 - s0 < 10.0:
            continue
        # né đoạn đã dùng: giữ MẢNH còn lại DÀI NHẤT (>=10s) sau khi trừ used
        pieces = _subtract_used([[s0, e1]], span_used, min_keep=10.0)
        if not pieces:
            continue                         # toàn bộ span trùng -> bỏ clip này
        ps, pe = max(pieces, key=lambda p: p[1] - p[0])
        pe = min(pe, ps + max_len, duration or pe)
        if pe - ps >= 10.0:
            spans.append((round(ps, 2), round(pe, 2), c))
            prev_end = pe
            span_used.append([ps, pe])

    # ---- 2) LLM đạo diễn viết kịch bản từng clip ----
    # NGỮ CẢNH THỊ GIÁC: nếu bật USE_VISION + model vision sẵn sàng -> trích
    # tối đa _MAX_FRAMES khung hình/clip cho AI NHÌN cảnh rồi viết lời bám
    # hình. Không vision -> prompt tự dặn bám transcript theo mốc thời gian.
    use_vision = bool(getattr(settings, "USE_VISION", False)
                      and llm.vision_available())
    scripts = []
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="recapf_") as ftd:
        for i, (s0, e1, c) in enumerate(spans):
            ctx.progress(0.45 + 0.5 * i / max(1, len(spans)),
                         f"Viết kịch bản {i + 1}/{len(spans)}"
                         + (" (AI xem hình)" if use_vision else "") + "...")
            sents = _clip_sentences(segs, s0, e1)
            frames = (_clip_frames(src_path, s0, e1, ftd, str(i))
                      if use_vision else None)
            try:
                sc = recap.write_script(sents, lang_name, style, s0, e1,
                                        title=c.get("title", ""),
                                        frames=frames, ratio=ratio,
                                        emotion=emotion)
            except llm.LLMError as e:
                errors.append(str(e))
                sc = None
            if sc:
                # SNAP mốc part vào mép câu (±_SNAP_TOL, không cắt ngang
                # câu/từ; mốc chuyển vai ưu tiên CHUYỂN CẢNH) rồi validate
                # lại cho phủ kín sạch sẽ.
                snapped = _snap_parts(sc["parts"], edges, words=tr_words,
                                      cuts=scene_cuts, spans=sent_spans)
                sc["parts"] = recap.validate_parts(snapped, s0, e1,
                                                   sentences=sents)
                # ÉP CỨNG tỉ lệ AI kể (như đường đạo diễn ở trên)
                sc["parts"] = recap.enforce_narrate_ratio(sc["parts"], ratio)
                if sc.get("lang_warn"):  # hậu kiểm ngôn ngữ -> báo user
                    ctx.progress(0.45 + 0.5 * i / max(1, len(spans)),
                                 f"⚠ Kịch bản {i + 1}: {sc['lang_warn']}")
            scripts.append(sc)
    if spans and not any(scripts):
        raise RuntimeError(
            "AI không viết được kịch bản thuyết minh cho clip nào"
            + (f" — lỗi: {errors[0][:200]}" if errors else
               " (kịch bản trả về không hợp lệ)."))

    # ---- 3) Lưu clip + kịch bản (signals.recap) ----
    _delete_suggested(video_id)
    lang = (transcript.get("language") or "").strip()
    clip_ids = []
    n_script = 0
    for (s0, e1, c), sc in zip(spans, scripts):
        signals = {
            "segments": [[s0, e1]], "n_seg": 1, "llm_used": True,
            "ai": prov, "dur": round(e1 - s0, 1),
            "title_en": (sc or {}).get("title") or c.get("title_en", ""),
            "hook": c.get("hook", ""),
        }
        if sc:
            n_script += 1
            signals["recap"] = {"style": style, "lang": lang,
                                "parts": sc["parts"]}
        cid = db.insert(
            """INSERT INTO clips (video_id, start_sec, end_sec, score, reason,
                                  title, transcript, signals, status)
               VALUES (?,?,?,?,?,?,?,?, 'suggested')""",
            (video_id, s0, e1, round(float(c.get("score", 60)), 1),
             ("Thuyết minh " + recap.style_label(style) + ". "
              + (c.get("reason") or "")).strip(),
             c.get("title") or "Clip thuyết minh", "", db.dumps(signals)))
        clip_ids.append(cid)

    msg = (f"AI [{prov}] tạo {len(clip_ids)} clip thuyết minh 1 mạch "
           f"(dự phòng — {n_script} có kịch bản, phong cách "
           f"{recap.style_label(style)})")
    if errors:
        msg += f" — {len(errors)} clip viết kịch bản lỗi (giữ tiếng gốc)"
    if warns:
        msg += " — CẢNH BÁO: " + "; ".join(warns)
    ctx.progress(1.0, msg)
    return {"count": len(clip_ids), "clip_ids": clip_ids,
            "scripts": n_script, "style": style, "llm_used": True}
