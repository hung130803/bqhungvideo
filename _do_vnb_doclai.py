# -*- coding: utf-8 -*-
"""ĐO GHÉP CẶP: DÒ CÂU LAN MAN RỒI ĐỌC LẠI — **TẮT vs BẬT**.

Trả lời đúng một câu: *bản vá đọc-lại có ăn thật không, và tốn thêm bao nhiêu
giây.* Giọng nhân bản VieNeu (`vnb:`) đọc tiếng Anh — đúng đường anh Hùng đi.

═══════════════════════════════════════════════════════════════════════════
GHÉP CẶP THẬT: **HAI ARM DÙNG CHUNG LƯỢT ĐỌC ĐẦU, TỪNG BYTE**
═══════════════════════════════════════════════════════════════════════════
VieNeu **KHÔNG tiền định** — cùng mã, cùng mẫu, cùng chữ mà hai lượt ra
`WER 3,1%` và `WER 12,7%` (lượt đo 26/08). So hai lượt chạy RỜI ở đây là đo
cái nhiễu đó chứ không đo bản vá; repo đã sai vì đúng chuyện này nhiều lần,
có lần lệch **1,81 lần** trên cùng bản mã.

Bản vá tác động ở **giữa** `giong_vieneu._doc`: sau lượt đọc đầu, trước
`_ep_khung`. Nên phép đo bọc `_chay_vieneu` lại và **CẤT lượt gọi ĐẦY ĐỦ đầu
tiên**: arm TẮT và arm BẬT nhận **y hệt một bộ file tiếng** cho lượt đọc đầu,
và chỉ khác nhau ở mấy lượt đọc LẠI. Mọi nhiễu chạy-khác-chạy bị triệt tiêu
**theo cấu tạo**, không phải nhờ đan xen.

Lượt đọc lại thì KHÔNG được lấy từ kho (khoá theo đúng bộ chữ, mà nhóm nghi
ngờ là bộ chữ khác) — nếu không thì arm BẬT "đọc lại" bằng chính file cũ và
phép đo tự cấp chứng nhận.

═══════════════════════════════════════════════════════════════════════════
CỘT ĐỐI CHỨNG BẮT BUỘC
═══════════════════════════════════════════════════════════════════════════
Arm **TẮT** phải ra **số câu bị bắt > 0**. Bằng 0 thì thước KHÔNG CÓ RĂNG và
mọi cột còn lại vô nghĩa — bảng sẽ ghi thẳng `THƯỚC KHÔNG CÓ RĂNG`.

═══════════════════════════════════════════════════════════════════════════
CANH ĐỘNG CƠ
═══════════════════════════════════════════════════════════════════════════
`dubbing._synth_all` **lùi êm về edge-tts** khi máy nhân bản hỏng cả loạt —
đúng cho người dùng, thảm hoạ cho phép đo (bảng sẽ khoe "0% sai chữ" trong
khi thứ vừa đọc là edge). Nên đếm số câu THẬT SỰ do `giong_vieneu` trả ra;
lệch là đánh dấu **KHÔNG HỢP LỆ**.

RANH GIỚI CỨNG: mẫu là **giọng MÁY** (edge-tts, dùng lại file của
`_do_vnb_en.py`). KHÔNG nhân bản giọng người thật nào.

Chạy:  .venv\\Scripts\\python -u _do_vnb_doclai.py
Env:   BQ_DL_VONG=2 · BQ_DL_ARM=TAT,BAT
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

import _do_adam_en as DA                                        # noqa: E402
import _do_vieneu_en as DV                                      # noqa: E402
import _do_vnb_en as VNB                                        # noqa: E402
from _do_doc_sai import tu_kiem_bo_cham                         # noqa: E402
from app.core import giong_vieneu as GV                         # noqa: E402

HOP = REPO / "_do_vnb_doclai"
KQ = REPO / "_kq_vnb_doclai.json"


# --------------------------------------------------- kho dùng chung lượt đầu
class KhoLuotDau:
    """Bọc `_chay_vieneu`: CẤT lượt gọi đầy đủ đầu tiên, phát lại cho arm sau.

    Chỉ cất theo **đúng bộ chữ** của lượt gọi. Lượt ĐỌC LẠI mang bộ chữ khác
    (chỉ mấy câu bị bắt) nên không bao giờ trúng kho — đó là điều kiện để arm
    BẬT thật sự đọc lại chứ không phát lại file cũ.
    """

    def __init__(self, goc: Path) -> None:
        self.goc = goc
        self.goc.mkdir(parents=True, exist_ok=True)
        self.kho: dict[tuple, dict] = {}
        self.that = None
        self.that_su_doc = 0          # số lượt gọi ĐỌC THẬT (không lấy kho)

    def __enter__(self) -> "KhoLuotDau":
        self.that = GV._chay_vieneu

        def _g(items, py, voice, ref_audio, han_giay, on_msg):
            khoa = tuple(str(it.get("text") or "") for it in items)
            cu = self.kho.get(khoa)
            if cu:
                ra = []
                for it in items:
                    nguon = cu["file"].get(int(it["i"]))
                    if not nguon or not Path(nguon).exists():
                        continue
                    dich = Path(it["raw"])
                    dich.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(nguon, dich)
                    ra.append({"i": int(it["i"]), "p": str(dich),
                               "giay": cu["giay"].get(int(it["i"]), 0.0)})
                r = dict(cu["ket"])
                r["ra"] = ra
                r["_sandbox"] = ""
                r["_tu_kho"] = True
                return r
            self.that_su_doc += 1
            r = self.that(items, py, voice, ref_audio, han_giay, on_msg)
            if r.get("ok"):
                bo = self.goc / f"k{len(self.kho):02d}"
                bo.mkdir(parents=True, exist_ok=True)
                fi, gi = {}, {}
                for x in r.get("ra") or []:
                    i = int(x.get("i", -1))
                    p = Path(x.get("p") or "")
                    if not p.exists():
                        continue
                    d = bo / f"c{i:04d}.wav"
                    shutil.copyfile(p, d)
                    fi[i] = str(d)
                    gi[i] = x.get("giay", 0.0)
                self.kho[khoa] = {
                    "ket": {k: v for k, v in r.items()
                            if k not in ("ra", "_sandbox")},
                    "file": fi, "giay": gi}
            return r

        GV._chay_vieneu = _g                                    # type: ignore
        return self

    def __exit__(self, *_a) -> None:
        GV._chay_vieneu = self.that                             # type: ignore


# ------------------------------------------------------------ báo cáo bản vá
class BatBaoCao:
    """Thu `ket["_lan_man"]` mà `_doc_lai_lan_man` để lại (đừng đọc log)."""

    def __init__(self) -> None:
        self.ds: list[dict] = []
        self._cu = None

    def __enter__(self) -> "BatBaoCao":
        self._cu = GV._doc_lai_lan_man

        def _g(*a, **k):
            r = self._cu(*a, **k)                    # type: ignore[misc]
            try:
                self.ds.append(dict(r.get("_lan_man") or {}))
            except Exception:                                    # noqa: BLE001
                pass
            return r

        GV._doc_lai_lan_man = _g                                # type: ignore
        return self

    def __exit__(self, *_a) -> None:
        GV._doc_lai_lan_man = self._cu                          # type: ignore

    def gop(self) -> dict:
        return {
            "bat": sum(int(x.get("bat") or 0) for x in self.ds),
            "doc_lai": sum(int(x.get("doc_lai") or 0) for x in self.ds),
            "an": sum(int(x.get("an") or 0) for x in self.ds),
            "giay": round(sum(float(x.get("giay") or 0.0) for x in self.ds), 1),
        }


def chay_arm(nhan: str, bat: bool, voice: str, thu: Path, kho: KhoLuotDau,
             ) -> dict:
    """Một arm: đọc 34 câu + 24 token rời qua CỬA THẬT rồi chép ngược, chấm."""
    os.environ["BQ_VN_DOC_LAI"] = "1" if bat else "0"
    ds = DV.cau_theo_nn("en")
    toks = DV.token_theo_nn("en")
    with BatBaoCao() as bc, VNB.CanhDongCo() as canh:
        t0 = time.time()
        ok_c = DV.doc_loat([c for _l, c, _t in ds], voice, thu, "c")
        ok_t = DV.doc_loat([t for _l, t in toks], voice, thu, "t")
        giay = time.time() - t0
        bao = bc.gop()
    n_can = len(ds) + len(toks)
    hop_le = canh.dem.get("vieneu", 0) >= n_can

    hang_c, hang_t = [], []
    for i, (loai, c, tks) in enumerate(ds):
        f = thu / f"c{i:03d}.mp3"
        if not (ok_c[i] and f.exists()):
            hang_c.append({"loai": loai, "cau": c, "tok": tks,
                           "chep": "[không đọc được]", "nn_tu_nhan": "",
                           "doc_duoc": False})
            continue
        txt, _ = DV.chep(f, "en")
        hang_c.append({"loai": loai, "cau": c, "tok": tks, "chep": txt,
                       "nn_tu_nhan": "", "doc_duoc": True})
    for i, (loai, tk) in enumerate(toks):
        f = thu / f"t{i:03d}.mp3"
        if not (ok_t[i] and f.exists()):
            hang_t.append({"loai": loai, "token": tk,
                           "chep": "[không đọc được]", "doc_duoc": False})
            continue
        txt, _ = DV.chep(f, "en")
        hang_t.append({"loai": loai, "token": tk, "chep": txt,
                       "doc_duoc": True})

    kq = {"arm": nhan, "voice": voice, "nn": "en", "vong": 1,
          "giay_cau": round(giay, 1), "giay_tok": 0.0,
          "cau": hang_c, "tok": hang_t}
    c = DV.cham(kq)
    chen = tong = 0
    for h in hang_c:
        if h["doc_duoc"]:
            _t, ch, _k, n = DA.dem_op(h["cau"], h["chep"])
            chen += ch
            tong += n
    c["chen"], c["tu"] = chen, tong
    c["giay"] = round(giay, 1)
    c["bao"] = bao
    c["hop_le"] = hop_le
    c["may_doc"] = dict(canh.dem)
    c["doc_that"] = kho.that_su_doc
    return c


def main() -> int:
    HOP.mkdir(parents=True, exist_ok=True)
    so_vong = int(os.environ.get("BQ_DL_VONG", "2"))
    chi = [x.strip() for x in (os.environ.get("BQ_DL_ARM") or "").split(",")
           if x.strip()]

    print("=" * 78)
    print("ĐỌC LẠI CÂU LAN MAN — ĐO GHÉP CẶP (TẮT vs BẬT), giọng `vnb:` x ANH")
    print("=" * 78)
    mau = VNB.lam_mau()
    voice = f"vnb:{mau}"
    print(f"mẫu (giọng MÁY edge-tts): {mau.name} · {mau.stat().st_size} byte")
    print(f"corpus: {len(DV.CORPUS['en'])} câu + {len(DV.token_theo_nn('en'))} "
          f"token rời · ngưỡng bộ dò {GV.doc_lan.NGUONG_LAN} · trần đọc lại "
          f"{GV.DOC_LAI_TOI_DA} lần/câu")

    print("\nTỰ KIỂM BỘ CHẤM (6 cặp đã biết đáp án)")
    if not bool(tu_kiem_bo_cham()):
        print("  DỪNG: bộ chấm lệch -> mọi số dưới đây vô nghĩa")
        return 2
    print("  -> bộ chấm KHỚP HẾT")

    tat: dict[str, list[dict]] = {}
    for vong in range(1, so_vong + 1):
        print(f"\n--- VÒNG {vong}/{so_vong} ---")
        with KhoLuotDau(HOP / f"kho_v{vong}") as kho:
            for nhan, bat in (("TAT", False), ("BAT", True)):
                if chi and nhan not in chi:
                    continue
                thu = HOP / f"{nhan}_v{vong}"
                if thu.exists():
                    shutil.rmtree(thu, ignore_errors=True)
                c = chay_arm(nhan, bat, voice, thu, kho)
                tat.setdefault(nhan, []).append(c)
                b = c["bao"]
                print(f"  [{nhan} v{vong}] bắt {b['bat']} · đọc lại "
                      f"{b['doc_lai']} · NHẬN {b['an']} · WER {c['wer']:.1f}% "
                      f"· bịa {c['chen']}/{c['tu']} · {c['giay']:.0f}s · "
                      f"máy {c['may_doc']} · "
                      f"{'HỢP LỆ' if c['hop_le'] else 'KHÔNG HỢP LỆ (lùi edge?)'}")

    # ------------------------------------------------------------- BẢNG
    print("\n" + "=" * 78)
    print("BẢNG — GHÉP CẶP, MỖI VÒNG DÙNG CHUNG LƯỢT ĐỌC ĐẦU")
    print("=" * 78)
    # **CỘT GIÂY PHẢI ĐỌC CHO ĐÚNG.** Arm BẬT nhận lượt đọc đầu TỪ KHO (đó
    # chính là chỗ ghép cặp), nên `giây` của nó KHÔNG phải chi phí cả lượt và
    # `giây(BẬT) − giây(TẮT)` ra số ÂM vô nghĩa. Chi phí thật của bản vá đo
    # THẲNG TẠI CHỖ VÁ: `_doc_lai_lan_man` tự bấm giờ và trả về `bao["giay"]`.
    print(f"{'vòng':>5}{'arm':>6}{'câu BẮT':>10}{'đọc lại':>9}{'NHẬN':>7}"
          f"{'tok sai%':>10}{'bịa %':>8}{'WER %':>8}"
          f"{'giây đọc ĐẦU':>14}{'+giây ĐỌC LẠI':>15}")
    for v in range(so_vong):
        cap = {}
        for nhan in ("TAT", "BAT"):
            rs = tat.get(nhan) or []
            if v < len(rs):
                cap[nhan] = rs[v]
        nen = (cap.get("TAT") or {}).get("giay", 0.0)
        for nhan in ("TAT", "BAT"):
            c = cap.get(nhan)
            if not c:
                continue
            b = c["bao"]
            co = "" if c["hop_le"] else " [KHÔNG HỢP LỆ]"
            print(f"{v + 1:>5}{nhan + co:>6}{b['bat']:>10}{b['doc_lai']:>9}"
                  f"{b['an']:>7}"
                  f"{100 * c['tc_sai'] / max(1, c['tc_n']):>9.1f}%"
                  f"{100 * c['chen'] / max(1, c['tu']):>7.1f}%"
                  f"{c['wer']:>7.1f}%{nen:>14.0f}{b['giay']:>+15.1f}")

    # ---------------------------------------------------- ĐỐI CHỨNG có răng
    print("\n" + "=" * 78)
    print("CHỐT CHỐNG-ĐẠT-OAN — arm TẮT phải BẮT > 0 thì thước mới CÓ RĂNG")
    print("=" * 78)
    tat_bat = sum(int(c["bao"]["bat"]) for c in (tat.get("TAT") or []))
    if tat_bat > 0:
        print(f"  arm TẮT bắt {tat_bat} câu (dò vẫn chạy, chỉ KHÔNG đọc lại)"
              f" -> **THƯỚC CÓ RĂNG**")
    else:
        print("  arm TẮT bắt 0 câu -> **THƯỚC KHÔNG CÓ RĂNG**: mọi cột trên "
              "vô nghĩa,\n     phải dựng lại corpus hoặc hạ ngưỡng rồi đo lại.")

    KQ.write_text(json.dumps(
        {"arm": {k: [{kk: vv for kk, vv in r.items() if kk not in ("tc", "tr")}
                     for r in v] for k, v in tat.items()},
         "nguong": GV.doc_lan.NGUONG_LAN, "mau": str(mau),
         "luc": time.strftime("%Y-%m-%d %H:%M")},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nSố thô: {KQ}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
