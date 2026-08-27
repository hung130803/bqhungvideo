# -*- coding: utf-8 -*-
"""HẠ TẦNG ĐO DÙNG CHUNG cho mọi arm của lượt "dịch không chuẩn".

BẤT BIẾN: mọi arm phải đi qua ĐÚNG cửa app đi (`thay_giong._dich_loat` /
`dich.dich_theo_gio` / `dich.dich_va_soat`), không dựng đường dịch riêng —
dựng riêng là đo một thứ KHÔNG PHẢI thứ anh Hùng chạy.
"""
from __future__ import annotations
import json, re, sys, threading, time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
HOP = REPO / "_kq_dich"
HOP.mkdir(exist_ok=True)


# ---------------------------------------------------------------- SỔ LƯỢT GỌI
class SoGoi:
    """Bọc `llm.complete_json` để ghi HỒ SƠ THẬT từng lượt: model, max_tokens,
    finish_reason, số ký tự trả về, lỗi. Không có sổ này thì "vì sao dịch hỏng"
    chỉ là suy đoán."""

    def __init__(self) -> None:
        self.muc: list[dict] = []
        self._khoa = threading.Lock()
        self._cu = None

    def bat(self):
        from app.ai import llm
        if self._cu is not None:
            return
        self._cu = llm.complete_json
        so = self

        def bao(prompt, system="", provider=None, model=None):
            t0 = time.time()
            mt = llm.max_tokens_groq(prompt, system)
            # NHÃN gửi đi trong lượt này — không ghi cái này thì không trả lời
            # được câu "câu hỏng nằm ở lượt gọi thứ mấy", tức không truy được
            # vì sao hỏng.
            nhan = [int(x) for x in re.findall(r"^#(\d+)[ \[]", prompt, re.M)]
            m = {"giay": 0.0, "prompt_ky_tu": len(prompt),
                 "prompt_token_uoc": llm._uoc_token(prompt) + llm._uoc_token(system),
                 "max_tokens": mt, "model_xin": model or "",
                 "so_muc": len(nhan), "nhan": nhan,
                 "loi": "", "ket_thuc": "", "model_that": "",
                 "token_ra": 0, "than_ky_tu": 0}
            try:
                ra = so._cu(prompt, system=system, provider=provider, model=model)
                return ra
            except Exception as e:                       # noqa: BLE001
                m["loi"] = f"{type(e).__name__}: {str(e)[:200]}"
                raise
            finally:
                m["giay"] = round(time.time() - t0, 2)
                try:
                    cd = llm.chan_doan_lan()
                    m["ket_thuc"] = str(cd.get("ket_thuc", ""))
                    m["model_that"] = str(cd.get("model", ""))
                    m["token_ra"] = int(cd.get("token_ra", 0) or 0)
                    m["than_ky_tu"] = int(cd.get("so_ky_tu", 0) or 0)
                except Exception:                        # noqa: BLE001
                    pass
                with so._khoa:
                    so.muc.append(m)

        llm.complete_json = bao

    def tat(self):
        if self._cu is None:
            return
        from app.ai import llm
        llm.complete_json = self._cu
        self._cu = None

    def tom_tat(self) -> dict:
        n = len(self.muc)
        cat = sum(1 for m in self.muc if m["ket_thuc"] == "length")
        loi = sum(1 for m in self.muc if m["loi"])
        return {"so_luot": n, "so_bi_cat": cat, "so_loi": loi,
                "giay_tong": round(sum(m["giay"] for m in self.muc), 2),
                "token_ra_tong": sum(m["token_ra"] for m in self.muc),
                "prompt_token_max": max([m["prompt_token_uoc"] for m in self.muc] or [0]),
                "max_tokens_min": min([m["max_tokens"] for m in self.muc] or [0]),
                "model": sorted({m["model_that"] for m in self.muc if m["model_that"]})}


# ------------------------------------------------------------------ BỘ DÒ CHỮ
_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿]")
_HANGUL = re.compile(r"[가-힣]")
_CYRIL = re.compile(r"[Ѐ-ӿ]")
_ARAB = re.compile(r"[؀-ۿ]")
_THAI = re.compile(r"[฀-๿]")
_DEVA = re.compile(r"[ऀ-ॿ]")
_VN = re.compile(r"[ăâđêôơưĂÂĐÊÔƠƯáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩị"
                 r"óòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]", re.I)


def he_chu(t: str) -> str:
    """Hệ chữ LẠ xuất hiện trong `t` (rỗng = chỉ chữ Latin)."""
    t = str(t or "")
    for ten, rg in (("CJK", _CJK), ("hangul", _HANGUL), ("cyril", _CYRIL),
                    ("arab", _ARAB), ("thai", _THAI), ("deva", _DEVA)):
        if rg.search(t):
            return ten
    return ""


def co_dau_viet(t: str) -> bool:
    return bool(_VN.search(str(t or "")))


def so_chu_han(t: str) -> int:
    return len(_CJK.findall(str(t or "")))


# --------------------------------------------------------------- ĐỌC BỘ CÂU
def doc_cau(ma: str) -> tuple[list[dict], dict]:
    d = json.loads((HOP / f"cau_{ma}.json").read_text(encoding="utf-8"))
    return d["cau"], d


def ghi(ten: str, obj) -> Path:
    p = HOP / ten
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    return p
