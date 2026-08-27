"""ĐO CHẬM ĐƯỜNG THAY GIỌNG — bổ đồng hồ TỪNG BƯỚC trên ĐÚNG cấu hình anh Hùng.

Anh Hùng 27/08/2026: *"2 tiếng mới được 1 video lồng tiếng 3 phút"* = **40 lần
thời gian thật**. Mọi số đo trong repo nói con số đó không thể đúng nếu đường
chạy lành, nên việc số một là ĐO chứ không phải tối ưu mò.

CẤU HÌNH ĐO (đọc từ ảnh màn hình anh Hùng gửi):
  · giọng `vnb:` (nhân bản, VieNeu) · đích `en` · TÁCH NHẠC (`de_giong=False`)
  · "Chỉnh video theo giọng" (`hinh_theo_giong=True`, `doc_deu=False` — MỤC 2)
  · che chữ BẬT (làm mờ, mức 1.00)

MẪU GIỌNG LÀ **GIỌNG MÁY** (edge-tts) — luật repo cấm dùng `adam_clone.wav`
(bản sao một giọng ElevenLabs thương mại) và cấm nhân bản giọng người thật.
Vì thế mọi số ở đây là số của ĐƯỜNG CHẠY, không phải của giọng anh Hùng.

GHI RA ĐĨA NGAY SAU MỖI BƯỚC — lượt đo trước bị giết giữa chừng và mất sạch
vì gom tới cuối.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO = Path(__file__).resolve().parent
HOP = REPO / "_kq_cham_tg"
KQ = REPO / "_kq_cham_tg.json"

#: Nguồn THẬT của anh Hùng. **CHỈ ĐỌC — copy ra hộp cát, không đụng bản gốc.**
NGUON = Path(os.environ.get(
    "BQ_TG_NGUON",
    r"C:\Users\Admin\Downloads\longtieng"
    r"\#强烈推荐 #原创 #高分电影 #我在抖音看电影 #好片推荐.mp4"))


# ==========================================================================
# SỔ GHI — ghi ra đĩa NGAY SAU MỖI BƯỚC
# ==========================================================================
class So:
    def __init__(self, duong: Path):
        self.duong = duong
        self.d: dict = {"bat_dau": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "luot": []}
        self.ghi()

    def dat(self, **kw):
        self.d.update(kw)
        self.ghi()

    def them_luot(self, luot: dict):
        self.d["luot"].append(luot)
        self.ghi()

    def ghi(self):
        try:
            self.duong.write_text(
                json.dumps(self.d, ensure_ascii=False, indent=1),
                encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass


# ==========================================================================
# POLL VRAM/RAM TRONG LÚC CHẠY
# ==========================================================================
# BẪY ĐÃ SẬP HAI LẦN (cổng 71 · 73): lấy mẫu TRƯỚC và SAU tiến trình con thì
# tiến trình thoát là trả sạch VRAM -> ra đúng mức NỀN, tức KHÔNG đo gì cả.
class Doi:
    def __init__(self, nhip: float = 1.0):
        self.nhip = nhip
        self.chay = False
        self.vram_max = 0
        self.vram_nen = 0
        self.ram_max = 0.0
        self.cpu: list[float] = []
        self.mau = 0
        self._t = None

    def _vram(self) -> int:
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10)
            return int((r.stdout or "0").strip().splitlines()[0])
        except Exception:  # noqa: BLE001
            return 0

    def _vong(self):
        import psutil
        while self.chay:
            v = self._vram()
            self.vram_max = max(self.vram_max, v)
            try:
                m = psutil.virtual_memory()
                self.ram_max = max(self.ram_max,
                                   float(m.total - m.available) / (1024 ** 3))
                self.cpu.append(psutil.cpu_percent(interval=None))
            except Exception:  # noqa: BLE001
                pass
            self.mau += 1
            time.sleep(self.nhip)

    def bat(self):
        self.vram_nen = self._vram()
        self.vram_max = self.vram_nen
        self.chay = True
        self._t = threading.Thread(target=self._vong, daemon=True)
        self._t.start()

    def tat(self) -> dict:
        self.chay = False
        if self._t:
            self._t.join(timeout=5)
        return {"vram_nen_mib": self.vram_nen, "vram_dinh_mib": self.vram_max,
                "vram_them_mib": self.vram_max - self.vram_nen,
                "ram_dinh_gb": round(self.ram_max, 2),
                "cpu_tb_%": round(sum(self.cpu) / max(1, len(self.cpu)), 1),
                "cpu_max_%": round(max(self.cpu or [0]), 1),
                "so_mau": self.mau}


# ==========================================================================
# ĐẾM: spawn VieNeu · lượt Groq · câu bị doc_lan bắt
# ==========================================================================
class Dem:
    """Bọc các cửa THẬT rồi đếm. KHÔNG dựng đường riêng cho phép đo."""

    def __init__(self):
        self.vieneu: list[dict] = []      # mỗi lần spawn tiến trình VieNeu
        self.groq: list[dict] = []        # mỗi lượt gọi LLM
        self.doc_lai: list[dict] = []     # doc_lan bắt + đọc lại
        self._goc: list = []

    def nhap(self):
        from app.core import giong_vieneu as VN
        from app.ai import llm as LLM

        goc_chay = VN._chay_vieneu

        def _chay(items, py, voice, ref_audio, han_giay, on_msg):
            t0 = time.time()
            k = goc_chay(items, py, voice, ref_audio, han_giay, on_msg)
            self.vieneu.append({
                "so_cau": len(items), "giay": round(time.time() - t0, 2),
                "nap_s": k.get("nap"), "gen_s": k.get("gen"),
                "ok": bool(k.get("ok")), "nhan_ban": bool(ref_audio)})
            return k

        VN._chay_vieneu = _chay
        self._goc.append((VN, "_chay_vieneu", goc_chay))

        goc_lan = VN._doc_lai_lan_man

        def _lan(items, ket, tt, voice, nb, han_giay, on_msg, sb, lang):
            truoc = len(self.vieneu)
            t0 = time.time()
            k = goc_lan(items, ket, tt, voice, nb, han_giay, on_msg, sb, lang)
            self.doc_lai.append({
                "so_cau_loat": len(items),
                "spawn_them": len(self.vieneu) - truoc,
                "giay": round(time.time() - t0, 2)})
            return k

        VN._doc_lai_lan_man = _lan
        self._goc.append((VN, "_doc_lai_lan_man", goc_lan))

        for ten in ("complete_json", "complete_text", "complete_vision_json"):
            f = getattr(LLM, ten, None)
            if f is None:
                continue
            self._goc.append((LLM, ten, f))
            setattr(LLM, ten, self._boc(f, ten))

    def _boc(self, f, ten):
        def g(*a, **kw):
            t0 = time.time()
            try:
                return f(*a, **kw)
            finally:
                self.groq.append({"ham": ten,
                                  "giay": round(time.time() - t0, 2)})
        return g

    def tra(self):
        for mod, ten, f in reversed(self._goc):
            setattr(mod, ten, f)
        self._goc.clear()

    def bang(self) -> dict:
        return {
            "spawn_vieneu": len(self.vieneu),
            "spawn_vieneu_chi_tiet": self.vieneu,
            "giay_vieneu_tong": round(sum(x["giay"] for x in self.vieneu), 2),
            "giay_nap_model_tong": round(
                sum(float(x.get("nap_s") or 0) for x in self.vieneu), 2),
            "luot_groq": len(self.groq),
            "giay_groq_tong": round(sum(x["giay"] for x in self.groq), 2),
            "doc_lan": self.doc_lai,
        }


# ==========================================================================
# ĐỒNG HỒ TỪNG BƯỚC — bám 9 mốc `prog()` CÓ SẴN của `thay_giong_video`
# ==========================================================================
class DongHo:
    """Ghi mốc theo LỜI NHẮN của `prog`, không chép tay nhãn vào đây.

    Chép tay nhãn là đo bản chữ CŨ: mã đổi thì ngoài đời sai mà bảng vẫn đẹp
    (đúng cách cổng 57 đọc 9 mốc thẳng từ mã nguồn).
    """

    def __init__(self):
        self.t0 = time.time()
        self.moc: list[tuple[float, float, str]] = []
        self.cuoi = ""

    def __call__(self, p: float, m: str):
        t = time.time()
        m = (m or "").strip()
        # Chỉ ghi khi ĐỔI BƯỚC: `prog` còn được gọi hàng trăm lần cho tiến
        # trình con bên trong một bước.
        goc = m.split("...")[0][:60]
        if goc != self.cuoi:
            self.moc.append((round(t - self.t0, 2), round(p, 4), m[:120]))
            self.cuoi = goc
            print(f"  [{t - self.t0:7.1f}s] {p:5.1%}  {m[:90]}", flush=True)

    def bang(self, tong: float) -> list[dict]:
        r = []
        for k, (t, p, m) in enumerate(self.moc):
            het = self.moc[k + 1][0] if k + 1 < len(self.moc) else tong
            giay = round(het - t, 2)
            r.append({"bat_dau_s": t, "giay": giay,
                      "%_tong": round(100.0 * giay / max(1e-9, tong), 1),
                      "p": p, "loi_nhan": m})
        return r


# ==========================================================================
# MẪU GIỌNG MÁY — edge-tts, KHÔNG đụng `adam_clone.wav`
# ==========================================================================
CAU_MAU = ("Hôm nay tôi thử giọng đọc mới của phần mềm, "
           "nghe xem có tự nhiên và rõ ràng không nhé.")


def lam_mau(dich: Path) -> Path:
    """Sinh mẫu ~7-10 giây bằng edge-tts rồi ép về WAV 24 kHz mono."""
    if dich.is_file() and dich.stat().st_size > 50_000:
        return dich
    import asyncio
    import edge_tts
    mp3 = dich.with_suffix(".mp3")
    dich.parent.mkdir(parents=True, exist_ok=True)

    async def _ch():
        c = edge_tts.Communicate(CAU_MAU, "vi-VN-NamMinhNeural")
        await c.save(str(mp3))

    asyncio.run(_ch())
    from config import settings
    subprocess.run([settings.FFMPEG_PATH, "-y", "-v", "error", "-i", str(mp3),
                    "-ac", "1", "-ar", "24000", str(dich)],
                   check=True, capture_output=True)
    return dich


# ==========================================================================
# MỘT LƯỢT
# ==========================================================================
def mot_luot(so: So, video: Path, voice: str, ten: str, **kw) -> dict:
    from app.core.thay_giong import thay_giong_video

    lam = HOP / f"lam_{ten}"
    if lam.exists():
        shutil.rmtree(lam, ignore_errors=True)
    lam.mkdir(parents=True, exist_ok=True)

    dh = DongHo()
    dem = Dem()
    doi = Doi(nhip=1.0)
    print(f"\n=== LƯỢT {ten} · {video.name} ===", flush=True)
    dem.nhap()
    doi.bat()
    t0 = time.time()
    try:
        kq = thay_giong_video(
            video, dich_sang="en", thu_muc_lam=str(lam), voice=voice,
            on_progress=dh, **kw)
    except Exception as e:  # noqa: BLE001
        kq = {"ok": False, "loi": f"{type(e).__name__}: {e}"}
    tong = time.time() - t0
    dem.tra()
    may = doi.tat()

    luot = {
        "ten": ten, "video": video.name, "voice": voice[:60],
        "cau_hinh": {k: v for k, v in kw.items()},
        "giay_tong": round(tong, 2),
        "do_dai_video_s": kq.get("do_dai"),
        "lan_thoi_gian_that": (round(tong / kq["do_dai"], 2)
                               if kq.get("do_dai") else None),
        "ok": bool(kq.get("ok")), "loi": kq.get("loi", ""),
        "so_cau": (kq.get("chep") or {}).get("so_cau"),
        "buoc": dh.bang(tong),
        **dem.bang(),
        "may": may,
        "doc": kq.get("doc"), "rut_gon": kq.get("rut_gon"),
        "doc_nhanh": kq.get("doc_nhanh"), "hinh": kq.get("hinh"),
        "che_chu": kq.get("che_chu"), "tach": kq.get("tach"),
    }
    so.them_luot(luot)
    print(f"--- {ten}: {tong:.1f}s · ok={luot['ok']} · "
          f"spawn VieNeu={luot['spawn_vieneu']} · Groq={luot['luot_groq']} "
          f"· VRAM +{may['vram_them_mib']} MiB", flush=True)
    shutil.rmtree(lam, ignore_errors=True)
    return luot


def don():
    if HOP.exists():
        shutil.rmtree(HOP, ignore_errors=True)


def main():
    so = So(KQ)
    try:
        HOP.mkdir(parents=True, exist_ok=True)
        if not NGUON.is_file():
            print(f"KHÔNG THẤY NGUỒN: {NGUON}")
            so.dat(loi=f"không thấy nguồn {NGUON}")
            return 2
        # COPY ra hộp cát — luật: không đụng video trong `Downloads\longtieng`.
        vid = HOP / "nguon.mp4"
        if not vid.is_file():
            shutil.copy2(NGUON, vid)
        mau = lam_mau(HOP / "mau_may.wav")
        from app.core import giong_vieneu as VN
        voice = VN.ma_nhan_ban(str(mau))
        tt = VN.tinh_trang_vieneu()
        so.dat(nguon=str(NGUON), mau=str(mau), voice=voice,
               vieneu={"co": tt.get("co"), "thieu": tt.get("thieu")},
               ghi_chu="mẫu là GIỌNG MÁY edge-tts, không dùng adam_clone.wav")
        print(f"nguồn: {vid.name} · mẫu: {mau.name} · VieNeu co={tt.get('co')}")

        mot_luot(so, vid, voice, "A_muc2",
                 cach_tach="auto", che_chu=True, che_chu_cach="mo",
                 che_chu_muc=1.0, hinh_theo_giong=True, doc_deu=False,
                 de_giong=False, viet_chu=True)
    finally:
        so.dat(xong=time.strftime("%Y-%m-%d %H:%M:%S"))
        don()
    print(f"\nGhi: {KQ}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
