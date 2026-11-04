# -*- coding: utf-8 -*-
"""PHIẾU ĐỢT + TRẠNG THÁI BẬN — giao kèo INTEGRATION.md mục 11, 12 (04/11/2026).

Phiếu CHỈ để BÁO CÁO và KÍCH HOẠT SỚM, KHÔNG BAO GIỜ là điều kiện bắt buộc:
nguồn sự thật vẫn là file trong thư mục kênh (mục 2). Phiếu mất / hỏng / đến
trễ thì video vẫn được cắt nhờ nhịp quét định kỳ của Tự chạy.

Mỗi loại file chỉ MỘT bên ghi:
  dot\\<dot_id>.json   — bqhungdown ghi, app này CHỈ ĐỌC.
  cat\\<dot_id>.json   — app này ghi (phiếu đợt cắt).
  ban_bqhungvideo.json — app này ghi (trạng thái bận, PCBot đọc).

KHÔNG BAO GIỜ đặt file ở đây trong thư mục kênh: `pipeline.collect_wipe` xoá
mọi file cấp 1 ở đó. Không ghi key/token/mật khẩu vào bất kỳ file nào.

Module THUẦN về logic (mọi tra cứu DB / đĩa được truyền vào) để test gọi thẳng
với đồng hồ giả; phần đọc DB thật nằm ở `ngu_canh_db()`.
"""
from __future__ import annotations

import html
import json
import os
import re
import threading
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

#: số `schema` lớn nhất app hiểu. Phiếu mang số lớn hơn -> bỏ qua + báo 1 lần.
SCHEMA_HIEU = 1
THU_MUC_MAC_DINH = r"C:\ProgramData\BQDayChuyen"
EXCHANGE_MAC_DINH = r"C:\ProgramData\PCBot\exchange"
TEN_FILE_BAN = "ban_bqhungvideo.json"
#: phiếu tải ghi `xong` mà sau chừng này phút không thấy file (và không có
#: trong sổ pipeline_files) -> `mat_file`.
MAT_FILE_PHUT = 10
#: phiếu tải đã đóng mà còn video chưa có kết quả cắt cuối -> sau chừng này
#: giờ thì đóng phiếu cắt `het_han` để vẫn có báo cáo nhóm (video trễ xong sau
#: đó vẫn được cắt và vẫn ghi vào phiếu cũ).
HAN_CAT_GIO = 6
#: mỗi bên tự xoá phiếu của mình cũ hơn chừng này ngày (luật 6).
GIU_NGAY = 14
#: JSON hỏng LIÊN TIẾP bấy nhiêu lần thì báo (luật 2).
HONG_BAO = 3

_TEN_DOT = re.compile(r"^\d{8}-\d{2,}\.json$")
#: trạng thái CẮT đã là kết quả cuối.
CUOI = ("xong", "loi", "trung", "mat_file", "kenh_tat", "khong_co_kenh")
#: video tải về với trạng thái này mới cần cắt (loi/bo_qua/cho... thì không).
CAN_CAT = ("xong", "tre")

_KHOA_CAT = threading.Lock()


def _h(x) -> str:
    """Tin Telegram gửi parse_mode=HTML: mọi chuỗi từ dữ liệu (tên nhóm, tên
    kênh/file, đường dẫn, lời lỗi) PHẢI thoát & < > — 'Tom & Jerry.mp4' đi thô
    là Telegram từ chối CẢ tin (và tin này còn gộp vào tin HẾT hàng chờ)."""
    return html.escape(str(x if x is not None else ""), quote=False)


# ------------------------------------------------------------ đường dẫn --
def chuan_hoa_duong(p) -> str:
    """Khoá so khớp thư mục kênh (luật 4): Unicode NFC, `/` -> `\\`, chữ
    thường, bỏ `\\` cuối. DB lưu `D:/video ssmatool/...`, tool tải lưu
    `D:\\video ssmatool\\...` — so nguyên chuỗi thì lệch 154/154 kênh."""
    s = unicodedata.normalize("NFC", str(p or "")).strip()
    s = s.replace("/", "\\")
    s = unicodedata.normalize("NFC", s.lower())
    return s.rstrip("\\")


def _la_sandbox() -> bool:
    return bool((os.environ.get("BQ_DATA_DIR") or "").strip()
                or (os.environ.get("BQ_QSETTINGS_INI") or "").strip())


def thu_muc_phieu(cai_dat: str | None = None) -> Path | None:
    """Thư mục phiếu đợt. env `BQ_DAYCHUYEN_DIR` thắng; đang chạy trong hộp
    cát test mà không đặt env thì KHÔNG đụng thư mục thật (trả None)."""
    env = (os.environ.get("BQ_DAYCHUYEN_DIR") or "").strip()
    if env:
        return Path(env)
    if _la_sandbox():
        return None
    return Path((cai_dat or "").strip() or THU_MUC_MAC_DINH)


def thu_muc_exchange() -> Path | None:
    """Thư mục trạng thái bận PCBot. Hộp cát test không đặt env -> None."""
    env = (os.environ.get("BQ_PCBOT_EXCHANGE") or "").strip()
    if env:
        return Path(env)
    if _la_sandbox():
        return None
    return Path(EXCHANGE_MAC_DINH)


# ------------------------------------------------------------- thời gian --
def gio_iso(ts: float | None = None) -> str:
    """ISO 8601 có múi giờ máy (`+07:00`) — luật 5."""
    return datetime.fromtimestamp(time.time() if ts is None else ts) \
        .astimezone().isoformat(timespec="seconds")


def doc_iso(s) -> float | None:
    """ISO 8601 -> epoch. Không đọc được -> None (KHÔNG đoán)."""
    if not s or not isinstance(s, str):
        return None
    try:
        d = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.astimezone()
    return d.timestamp()


# --------------------------------------------------------- ghi nguyên tử --
def ghi_nguyen_tu(path, obj, thu_lai: int = 5, cho: float = 0.2) -> None:
    """Luật 1: ghi `<tên>.json.tmp` cùng thư mục -> flush + fsync -> đổi tên
    đè. Đổi tên vướng khoá (bên kia đang đọc) thì thử lại 5 lần × 200 ms.
    File tạm KHÔNG mang đuôi video / `.part` / `.ytdl`. Hỏng hẳn thì NÉM."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    data = json.dumps(obj, ensure_ascii=False, indent=1)
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(data)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass
    loi = None
    for i in range(max(1, thu_lai)):
        try:
            os.replace(tmp, path)
            return
        except PermissionError as e:   # Windows: bên kia đang mở đọc
            loi = e
            time.sleep(cho)
    try:
        tmp.unlink()
    except OSError:
        pass
    raise loi or OSError("không đổi tên được file phiếu")


def doc_json(path) -> tuple[object, str]:
    """Đọc HẾT rồi đóng ngay (luật 2). Trả (dữ liệu, '') | (None, lý do)."""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            raw = f.read()
    except FileNotFoundError:
        return None, "mat"
    except OSError as e:
        return None, f"không đọc được: {e}"
    try:
        return json.loads(raw), ""
    except ValueError as e:
        return None, f"JSON hỏng: {e}"


class BoDoc:
    """Đọc phiếu tải theo luật 2-3: JSON hỏng -> GIỮ BẢN ĐỌC ĐƯỢC LẦN TRƯỚC
    (không coi là rỗng); hỏng 3 lần LIÊN TIẾP thì báo; `schema` lạ -> bỏ qua
    phiếu + báo 1 lần."""

    def __init__(self):
        self._tot: dict[str, dict] = {}
        self._hong: dict[str, int] = {}
        self._da_bao: set = set()

    def doc(self, path) -> tuple[dict | None, list[str]]:
        k = str(path)
        bao: list[str] = []
        data, loi = doc_json(path)
        if loi == "mat":
            return self._tot.get(k), bao
        if data is None or not isinstance(data, dict):
            n = self._hong.get(k, 0) + 1
            self._hong[k] = n
            if n == HONG_BAO and ("hong", k) not in self._da_bao:
                self._da_bao.add(("hong", k))
                bao.append(f"phiếu {Path(k).name} đọc hỏng {n} lần liên tiếp "
                           f"({(loi or 'không phải object')[:80]}) — vẫn cắt theo "
                           "quét thư mục")
            return self._tot.get(k), bao
        self._hong[k] = 0
        self._da_bao.discard(("hong", k))
        try:
            sch = int(data.get("schema") or 0)
        except (TypeError, ValueError):
            sch = 0
        if sch > SCHEMA_HIEU:
            if ("schema", k) not in self._da_bao:
                self._da_bao.add(("schema", k))
                bao.append(f"phiếu {Path(k).name} có schema {sch} (app hiểu tới "
                           f"{SCHEMA_HIEU}) — bỏ qua phiếu, vẫn cắt theo quét")
            return None, bao
        self._tot[k] = data
        return data, bao


def ds_phieu(thu_muc_con) -> list[Path]:
    """Phiếu đúng mẫu tên `YYYYMMDD-NN.json` (không lấy `.tmp`)."""
    try:
        return sorted(p for p in Path(thu_muc_con).iterdir()
                      if p.is_file() and _TEN_DOT.match(p.name))
    except OSError:
        return []


def don_phieu_cu(thu_muc_cat, now: float | None = None) -> int:
    """Luật 6: xoá phiếu CẮT của mình cũ hơn 14 ngày, CHỈ file đúng mẫu tên."""
    now = time.time() if now is None else now
    n = 0
    for p in ds_phieu(thu_muc_cat):
        try:
            if now - p.stat().st_mtime > GIU_NGAY * 86400:
                p.unlink()
                n += 1
        except OSError:
            continue
    return n


# ------------------------------------------------------------ phiếu cắt --
def _tt_tu_so(so: dict | None) -> tuple[str, int, str]:
    """Dòng sổ pipeline_files -> (trạng thái cắt, số Part, lý do lỗi)."""
    if not so:
        return "", 0, ""
    st = so.get("status") or ""
    if st == "taken":
        return "dang_lam", 0, ""
    if st == "done":
        return "xong", int(so.get("parts") or 0), ""
    if st == "dup":
        return "trung", 0, str(so.get("note") or "")[:200]
    if st == "bad":
        # file hỏng / không đọc được: app KHÔNG thử lại -> kết quả CUỐI
        return "loi", 0, ("file hỏng/không đọc được: " + str(so.get("note") or ""))[:200]
    if st == "error":
        return "loi", 0, str(so.get("note") or st)[:200]
    return "", 0, ""


def dung_phieu_cat(ptai: dict, cu: dict | None, nc: dict,
                   now: float | None = None) -> tuple[dict, list[tuple]]:
    """Dựng phiếu CẮT từ phiếu TẢI + sổ của app. Hàm thuần.

    `nc` (ngữ cảnh tra cứu):
      kenh:  {khoá_thư_mục: {"pid", "ten", "on"}}  (khoá = chuan_hoa_duong)
      so:    fn(pid, file_name) -> dòng sổ mới nhất {status, note, parts} | None
      moi:   fn(pid, ts) -> [dòng sổ nhận SAU mốc ts] (gán video `tre` chưa
             biết tên file)
      co_file: fn(thư_mục, file_name) -> bool
    Trả (phiếu cắt, sự kiện). Sự kiện: ("mat_file", tên kênh, file),
    ("dong", dot_id)."""
    now = time.time() if now is None else now
    su: list[tuple] = []
    cu_v: dict = {}
    for k in (cu or {}).get("kenh") or []:
        for v in k.get("video") or []:
            cu_v[(chuan_hoa_duong(k.get("thu_muc")), str(v.get("id")))] = v
    mo_luc = doc_iso(ptai.get("mo_luc"))
    kenh_ra = []
    for k in ptai.get("kenh") or []:
        if not isinstance(k, dict):
            continue
        tm = str(k.get("thu_muc") or "")
        kh = chuan_hoa_duong(tm)
        ch = (nc.get("kenh") or {}).get(kh)
        da_ten = {str(v.get("file")) for v in k.get("video") or []
                  if isinstance(v, dict) and v.get("file")}
        moi_sd = None
        ds_v = []
        for v in k.get("video") or []:
            if not isinstance(v, dict):
                continue
            vid = str(v.get("id") or v.get("file") or "")
            tai = str(v.get("trang_thai") or "")
            fname = str(v.get("file") or "")
            old = cu_v.get((kh, vid)) or {}
            tt, part, loi = "chua_thay", 0, ""
            tam = False
            if ch is None:
                tt = "khong_co_kenh"
            elif not ch.get("on"):
                tt = "kenh_tat"
            elif tai in CAN_CAT:
                so = nc["so"](ch["pid"], fname) if fname else None
                if so is None and not fname and tai == "tre":
                    # trễ, phiếu đã đóng nên không bao giờ có tên file: nhận
                    # dòng sổ MỚI (sau mo_luc) chưa thuộc video nào của phiếu.
                    if moi_sd is None:
                        moi_sd = [r for r in (nc["moi"](ch["pid"], mo_luc or 0) or [])
                                  if str(r.get("file_name")) not in da_ten]
                    if moi_sd:
                        so = moi_sd.pop(0)
                        fname = str(so.get("file_name") or "")
                tt, part, loi = _tt_tu_so(so)
                if (tt == "loi" and (so or {}).get("status") != "bad"
                        and fname and nc["co_file"](tm, fname)):
                    tam = True           # gốc còn trong thư mục -> lượt sau thử lại
                if not tt:
                    tt = "chua_thay"
                    xl = doc_iso(v.get("xong_luc"))
                    if (tai == "xong" and fname and xl is not None
                            and now - xl >= MAT_FILE_PHUT * 60
                            and not nc["co_file"](tm, fname)):
                        tt = "mat_file"
            if tt == "mat_file" and old.get("trang_thai") != "mat_file":
                su.append(("mat_file", (ch or {}).get("ten") or tm, fname))
            rec = {"id": vid, "file": fname or None, "tai": tai, "trang_thai": tt,
                   "part": part, "loi": loi or None, "tam": tam,
                   "cap_nhat": old.get("cap_nhat") if old.get("trang_thai") == tt
                   and old.get("part") == part else gio_iso(now)}
            ds_v.append(rec)
        kenh_ra.append({"thu_muc": tm, "pid": (ch or {}).get("pid"),
                        "ten": (ch or {}).get("ten"), "video": ds_v})
    pc = {"schema": 1, "dot_id": ptai.get("dot_id"), "nhom": ptai.get("nhom"),
          "tao_luc": (cu or {}).get("tao_luc") or gio_iso(now),
          "trang_thai": (cu or {}).get("trang_thai") or "dang_cat",
          "dong_luc": (cu or {}).get("dong_luc"),
          "ly_do_dong": (cu or {}).get("ly_do_dong"),
          "bao_cao_luc": (cu or {}).get("bao_cao_luc"),
          "kenh": kenh_ra,
          "kenh_khong_co_video": list(ptai.get("kenh_khong_co_video") or [])}
    if pc["trang_thai"] != "da_dong" and ptai.get("trang_thai") == "da_dong":
        can = [v for k in kenh_ra for v in k["video"]
               if v["tai"] in CAN_CAT or v["trang_thai"] in ("kenh_tat", "khong_co_kenh")]
        # `loi` mà gốc còn trong thư mục (lỗi tạm, app sẽ thử lại) CHƯA là kết
        # quả cuối; chỉ lỗi đã dời khỏi thư mục (_Loi / quarantine) mới cuối.
        het = all(v["trang_thai"] in CUOI and not v.get("tam") for v in can)
        dl = doc_iso(ptai.get("dong_luc")) or now
        if het or now - dl >= HAN_CAT_GIO * 3600:
            pc["trang_thai"] = "da_dong"
            pc["dong_luc"] = gio_iso(now)
            pc["ly_do_dong"] = "xong" if het else "het_han"
            su.append(("dong", pc["dot_id"]))
    return pc, su


def _ruot(pc: dict) -> str:
    """Phần so sánh 'có đổi không' (bỏ dấu thời gian cập nhật)."""
    return json.dumps({k: v for k, v in pc.items()}, ensure_ascii=False, sort_keys=True)


def bao_cao_nhom(ptai: dict, pc: dict) -> str:
    """Tin báo cáo NHÓM (gửi đúng 1 lần khi cả 2 phiếu đã đóng)."""
    vs = [v for k in pc.get("kenh") or [] for v in k.get("video") or []]
    tong = [v for v in vs if v.get("tai") != "bo_qua"]
    n_tai = sum(1 for v in tong if v.get("tai") == "xong")
    n_tre = sum(1 for v in tong if v.get("tai") == "tre")
    n_bq = sum(1 for v in vs if v.get("tai") == "bo_qua")
    n_tl = sum(1 for v in tong if v.get("tai") == "loi")
    xong = [v for v in vs if v.get("trang_thai") == "xong"]
    loi = [v for v in vs if v.get("trang_thai") == "loi"]
    part = sum(int(v.get("part") or 0) for v in xong)
    dong = [f"📦 <b>Nhóm «{_h(ptai.get('nhom') or '?')}»</b> (đợt {_h(pc.get('dot_id'))}): "
            f"tải {n_tai}/{len(tong)}"
            + (f" ({n_tre} trễ)" if n_tre else "")
            + (f" · tải lỗi {n_tl}" if n_tl else "")
            + f" · cắt xong {len(xong)}"
            + (f" · lỗi {len(loi)} ({_h((loi[0].get('loi') or '')[:60])})" if loi else "")
            + f" · Part mới {part}"]
    phu = []
    for tt, nhan in (("trung", "trùng"), ("mat_file", "MẤT FILE"),
                     ("kenh_tat", "kênh tắt dây chuyền"),
                     ("khong_co_kenh", "không có kênh cắt"),
                     ("chua_thay", "chưa cắt"), ("dang_lam", "đang cắt")):
        n = sum(1 for v in vs if v.get("trang_thai") == tt
                and (tt not in ("chua_thay",) or v.get("tai") in CAN_CAT))
        if n:
            phu.append(f"{nhan} {n}")
    if n_bq:
        phu.append(f"bỏ qua khi tải {n_bq}")
    if pc.get("ly_do_dong") == "het_han":
        phu.append(f"đóng vì quá {HAN_CAT_GIO} giờ")
    if phu:
        dong.append("· " + " · ".join(phu))
    return "\n".join(dong)


def cap_nhat_tat_ca(goc: Path, bo_doc: BoDoc, nc: dict,
                    now: float | None = None) -> dict:
    """1 lượt (LUỒNG NỀN): đọc mọi phiếu tải -> ghi phiếu cắt đổi khác.
    Trả {"xong_moi": [(dot_id, id, xong_ts)], "su_kien": [...], "bao": [...],
    "bao_cao": [(dot_id, text)], "kck": [thư mục], "loi_ghi": str}."""
    now = time.time() if now is None else now
    ra: dict = {"xong_moi": [], "su_kien": [], "bao": [], "bao_cao": [],
                "kck": [], "loi_ghi": ""}
    d_dot, d_cat = Path(goc) / "dot", Path(goc) / "cat"
    hom_nay = datetime.fromtimestamp(now).strftime("%Y%m%d")
    for p in ds_phieu(d_dot):
        ptai, bao = bo_doc.doc(p)
        ra["bao"].extend(bao)
        if not isinstance(ptai, dict) or not ptai.get("dot_id"):
            continue
        for k in ptai.get("kenh") or []:
            for v in (k.get("video") or []) if isinstance(k, dict) else []:
                if isinstance(v, dict) and v.get("trang_thai") == "xong":
                    xl = doc_iso(v.get("xong_luc"))
                    if xl is not None:
                        ra["xong_moi"].append((ptai["dot_id"], str(v.get("id")), xl))
        fcat = d_cat / p.name
        with _KHOA_CAT:
            cu, _ = doc_json(fcat)
            cu = cu if isinstance(cu, dict) and cu.get("dot_id") == ptai["dot_id"] else None
            pc, su = dung_phieu_cat(ptai, cu, nc, now)
            ra["su_kien"].extend(su)
            if cu is None or _ruot(pc) != _ruot(cu):
                try:
                    d_cat.mkdir(parents=True, exist_ok=True)
                    ghi_nguyen_tu(fcat, pc)
                except OSError as e:
                    ra["loi_ghi"] = f"không ghi được phiếu cắt {fcat.name}: {e}"
                    continue
        if pc.get("trang_thai") == "da_dong" and not pc.get("bao_cao_luc"):
            ra["bao_cao"].append((ptai["dot_id"], bao_cao_nhom(ptai, pc)))
        if str(ptai["dot_id"]).startswith(hom_nay):
            for k in pc.get("kenh") or []:
                if any(v.get("trang_thai") == "khong_co_kenh" for v in k.get("video") or []):
                    ra["kck"].append(k.get("thu_muc"))
    return ra


def danh_dau_da_bao(goc: Path, dot_id: str, now: float | None = None) -> bool:
    """Ghi `bao_cao_luc` vào phiếu cắt -> mở lại app KHÔNG gửi lại (V20)."""
    f = Path(goc) / "cat" / f"{dot_id}.json"
    with _KHOA_CAT:
        pc, loi = doc_json(f)
        if not isinstance(pc, dict):
            return False
        if pc.get("bao_cao_luc"):
            return True
        pc["bao_cao_luc"] = gio_iso(now)
        try:
            ghi_nguyen_tu(f, pc)
        except OSError:
            return False
    return True


# ------------------------------------------------------- tra cứu DB thật --
def ngu_canh_db(root: str) -> dict:
    """Ngữ cảnh tra cứu từ DB (gọi ở LUỒNG NỀN). Khớp kênh THEO THƯ MỤC."""
    from app.core import pipeline as P
    from app.database.db import db
    kenh: dict = {}
    for r in db.query("SELECT id, name, pipe_on, pipe_hidden, pipe_src, export_dir "
                      "FROM projects"):
        try:
            d = P.resolve_src_dir(root, r["name"], (r["pipe_src"] or "").strip()
                                  or (r["export_dir"] or "").strip())
        except Exception:  # noqa: BLE001
            continue
        k = chuan_hoa_duong(d)
        bat = bool(r["pipe_on"]) and not bool(r["pipe_hidden"])
        # 2 kênh trỏ cùng thư mục (không nên có): kênh BẬT thắng.
        if k not in kenh or (bat and not kenh[k]["on"]):
            kenh[k] = {"pid": int(r["id"]), "ten": r["name"], "on": bat}

    def so(pid, fname):
        r = db.query_one("SELECT status, note, video_id FROM pipeline_files "
                         "WHERE project_id=? AND file_name=? ORDER BY id DESC LIMIT 1",
                         (pid, fname))
        if not r:
            return None
        d = dict(r)
        d["parts"] = 0
        if r["video_id"]:
            c = db.query_one("SELECT COUNT(*) n FROM clips WHERE video_id=? "
                             "AND status='exported'", (int(r["video_id"]),))
            d["parts"] = int(c["n"]) if c else 0
        return d

    def moi(pid, ts):
        moc = datetime.fromtimestamp(float(ts or 0), timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        ra = []
        for r in db.query("SELECT file_name, status, note, video_id FROM pipeline_files "
                          "WHERE project_id=? AND taken_at>=? ORDER BY id", (pid, moc)):
            d = dict(r)
            d["parts"] = 0
            if r["video_id"]:
                c = db.query_one("SELECT COUNT(*) n FROM clips WHERE video_id=? "
                                 "AND status='exported'", (int(r["video_id"]),))
                d["parts"] = int(c["n"]) if c else 0
            ra.append(d)
        return ra

    def co_file(tm, fname):
        try:
            return (Path(tm) / fname).is_file()
        except OSError:
            return False

    return {"kenh": kenh, "so": so, "moi": moi, "co_file": co_file}


# -------------------------------------------------------- trạng thái bận --
def noi_dung_ban(cho: int, dang_lam: int, dang_nhan: int, dang_quet: bool,
                 pid: int, phien_ban: str, ly_do=None,
                 now: float | None = None, dang_thoat: bool = False) -> dict:
    """Mục 12: bận khi còn job pending/running, còn file trong hàng nhận, hoặc
    đang quét nền. `dang_thoat` = lần ghi cuối khi thoát êm (ban=false)."""
    ban = (not dang_thoat) and (cho + dang_lam + dang_nhan > 0 or bool(dang_quet))
    return {"app": "bqhungvideo", "ban": bool(ban), "cho": int(cho + dang_nhan),
            "dang_lam": int(dang_lam), "cap_nhat": gio_iso(now), "pid": int(pid),
            "phien_ban": str(phien_ban), "ly_do": ly_do}
