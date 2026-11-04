# -*- coding: utf-8 -*-
"""TỰ CHẠY DÂY CHUYỀN — phần nối giao diện (INTEGRATION.md mục 5, 11, 12).

Thuộc MainWindow (KHÔNG treo vào `StudioPage._poll_tick`: nó dừng hẳn khi mở
hộp chọn file và khi DB vỡ). Hai nhịp QTimer riêng:

  15 s — `nhip()`: chỉ đọc RAM (+1 truy vấn đếm việc khi TỚI nhịp), quyết định
         có chạy không (tu_chay.LichTuChay) rồi gọi ĐÚNG
         `StudioPage._bot_chay_day_chuyen(nhóm đã lưu, tu_dong=True)` — hàm
         của nút ▶ / bot. Lượt tự chạy KHÔNG nhảy màn hình. Kèm canh quét /
         nhận bị TREO (1b-V4).
  60 s — `nhip_60()`: dựng + ghi file TRẠNG THÁI BẬN (dựng ở luồng giao diện
         -> app treo thì file cũ đi, đúng mục 12), rồi ở LUỒNG NỀN (_chay_nen):
         đo ổ đĩa từng ổ chứa thư mục kênh + hỏi hạn mức AI + đọc phiếu tải +
         ghi phiếu cắt.

Đợt 1b (04/11/2026, anh Hùng: "mọi thứ có nút, chỉnh được giờ, lỗi phải báo
lên bot"): nút Chạy ngay / Dừng lượt / Bỏ qua hôm nay + trạng thái TỰ CẬP NHẬT
trong hộp, và cùng các lệnh đó qua bot (`lenh()` — tele_bot gọi qua goi_ui).
QUY TẮC BÁO: mỗi loại lỗi tối đa 1 lần/giờ, hết lỗi báo "đã ổn lại", chỉ đánh
dấu "đã báo" khi gửi THÀNH CÔNG, chuỗi dữ liệu luôn qua `PD._h()`.

Không hộp thoại, không gọi mạng trên luồng giao diện ở đường tự chạy; Telegram
gửi qua `tele_bot._bot._viec` (luồng nền của bot). Công tắc mặc định TẮT; tắt
= app chạy y như trước 04/11/2026 (trừ file trạng thái bận, ghi luôn).
"""
from __future__ import annotations

import os
import threading

from PyQt6.QtCore import QObject, QTimer

from app.core import phieu_dot as PD
from app.core import tu_chay as TC


#: lượt nền (đo ổ + phiếu) chạy quá chừng này giây thì coi là treo, cho đo lại.
NEN_TOI_DA_GIAY = 300
#: 1b-V4: quét / nhận đứng yên quá chừng này giây = treo -> báo bot + gỡ cờ.
TREO_GIAY = 1200
#: phiếu cắt ghi lỗi liên tục quá chừng này giây -> báo bot.
GHI_LOI_GIAY = 600
TEN_LOI = {
    "loi_nhip": "Tự chạy lỗi trong nhịp chạy",
    "loi_60": "Tự chạy lỗi trong nhịp 60 s (trạng thái bận / chuẩn bị đo)",
    "loi_nen": "Tự chạy lỗi khi đo ổ / đọc phiếu (luồng nền)",
    "nhom_rong": "nhóm Tự chạy đã chọn không còn kênh nào BẬT",
    "thu_muc_phieu": "không có thư mục phiếu đợt",
    "ghi_phieu": "không ghi được phiếu cắt",
    "db_hong": "cơ sở dữ liệu hỏng — Tự chạy ngừng cập nhật phiếu",
    "o_day": "ổ đĩa sắp đầy — Tự chạy DỪNG",
    "khong_key": "chưa có key AI — Tự chạy không chạy",
    "het_luot_ai": "mọi key AI hết lượt kéo dài — Tự chạy ngừng nhận thêm",
    "treo_quet": "lượt QUÉT thư mục bị treo — đã gỡ cờ",
    "treo_nhan": "hàng NHẬN video đứng im — đã dừng lượt",
}


class TuChayUI(QObject):
    def __init__(self, parent, studio, state, dong_ho=None):
        super().__init__(parent)
        self.studio = studio
        self.state = state
        self._dong_ho = dong_ho or TC.bay_gio
        self.lich = TC.LichTuChay()
        self._mo_app = True
        self.o_dia = None                 # (ok, lời) của lần đo gần nhất
        self.het_luot_ai = False
        self.cho_phan_tich = 0
        self.dot_mo: list = []            # [(dot_id, nhóm, tải, cắt)] chưa đóng
        self._nen_dang = False
        self._bo_doc = PD.BoDoc()
        self._da_dua_bao: set = set()     # dot_id đã đưa bot trong phiên này
        self._ghi_log_bc: set = set()
        self._ban_loi_da_ghi = False
        self.so_ghi_ban = 0
        self.lan_nen = 0
        self._t15 = self._t60 = None
        self._nen_tu = 0.0
        self._nen_the = 0
        self._loi: dict = {}              # loại -> {"tu", "gui"} (lỗi ĐANG có)
        #: loại -> lúc GỬI ĐƯỢC gần nhất. KHÔNG xoá khi hết lỗi: lỗi chập chờn
        #: (lỗi - ổn - lỗi) vẫn chỉ báo 1 lần/giờ.
        self._gui_cuoi: dict = {}
        self._kck_log = ""
        self._kck_dang = ""
        self._quet_thay = None
        self._nhan_sig = None
        self._nhan_tu = None
        self._ghi_loi_tu = None

    # ------------------------------------------------------------ nhịp --
    def bat_dau(self) -> None:
        self._t15 = QTimer(self)
        self._t15.timeout.connect(self.nhip)
        self._t15.start(15_000)
        self._t60 = QTimer(self)
        self._t60.timeout.connect(self.nhip_60)
        self._t60.start(60_000)
        self._t20 = QTimer(self)                # lượt đo đầu (huỷ được khi dựng hỏng)
        self._t20.setSingleShot(True)
        self._t20.timeout.connect(self.nhip_60)
        self._t20.start(20_000)

    def dung(self) -> None:
        for t in (self._t15, self._t60, getattr(self, "_t20", None)):
            if t is not None:
                t.stop()

    def cau_hinh(self) -> TC.CauHinh:
        from app.ui.appsettings import app_settings
        return TC.doc_cau_hinh(app_settings())

    def _dem_cho(self) -> int:
        """Số việc PHÂN TÍCH đang chờ (1 truy vấn GROUP BY có chỉ mục)."""
        try:
            from app import services
            c = services.queue_counts() or {}
            return int(c.get("wait_analyze", 0) or 0)
        except Exception:  # noqa: BLE001
            return 0

    def tinh_trang(self, dem: bool = False) -> TC.TinhTrang:
        S = self.studio
        try:
            from app.ai import llm as _llm
            co_key = bool(_llm.is_configured())
        except Exception:  # noqa: BLE001
            co_key = True
        try:
            from app.database.db import db
            db_hong = bool(getattr(db, "corrupt_live", False))
        except Exception:  # noqa: BLE001
            db_hong = False
        pool = getattr(self.state, "pool", None)
        try:
            tam = bool(pool is not None and pool.dang_tam_dung())
        except Exception:  # noqa: BLE001
            tam = False
        if dem:
            self.cho_phan_tich = self._dem_cho()
        return TC.TinhTrang(
            modal_busy=bool(getattr(S, "_modal_busy", False)),
            dang_quet=S._pipe_dang_quet_n() > 0,
            dang_nhan=int(S._bot_dang_nhan() or 0),
            tam_dung=tam, co_key=co_key, db_hong=db_hong, o_dia=self.o_dia,
            cho_phan_tich=self.cho_phan_tich, het_luot_ai=self.het_luot_ai)

    def nhip(self, now: float | None = None) -> str:
        """1 nhịp quyết định. Trả việc đã làm (test đọc). Không bao giờ ném."""
        now = self._dong_ho() if now is None else now
        try:
            r = self._nhip(now)
            self.het_loi("loi_nhip", now)
            return r
        except Exception as e:  # noqa: BLE001 - tự chạy là phụ, không làm sập app
            self.bao_loi("loi_nhip", f"{TEN_LOI['loi_nhip']}: {type(e).__name__}: {e}", now)
            return "loi"

    def _toi(self, now: float) -> bool:
        l_ = self.lich
        return l_.ep or (l_.hen is not None and now >= l_.hen) or l_._toi_kich(now)

    def _nhip(self, now: float) -> str:
        cfg = self.cau_hinh()
        self.lich.dong_bo(cfg, now, luc_mo_app=self._mo_app)
        self._mo_app = False
        if not cfg.bat:
            return "tat"
        self._canh_treo(now)
        tt = self.tinh_trang(dem=self._toi(now))
        viec, ly = self.lich.quyet_dinh(cfg, tt, now)
        if viec in ("chay", "bo"):
            # trạng thái kéo dài: lỗi thì báo (1/giờ), hết thì báo "đã ổn"
            # db_hong KHÔNG báo ở đây: bot đã có tin "Cơ sở dữ liệu báo hỏng"
            # (_bao_db, 1 lần) — gộp chung, không lặp mỗi giờ (S1).
            for loai, co in (("o_day", tt.o_dia is not None and not tt.o_dia[0]),
                             ("khong_key", not tt.co_key),
                             ("het_luot_ai", tt.het_luot_ai)):
                if co:
                    them = (f": {self.o_dia[1]}" if loai == "o_day" and self.o_dia else "")
                    self.bao_loi(loai, TEN_LOI[loai] + them, now)
                else:
                    self.het_loi(loai, now)
        if viec == "chay":
            toi_da = max(1, cfg.nguong_cho - tt.cho_phan_tich)
            kq = self.studio._bot_chay_day_chuyen(cfg.nhom, tu_dong=True,
                                                  toi_da=toi_da) or {}
            self.lich.da_chay(cfg, now)
            if not kq.get("ok"):
                ld = str(kq.get("ly_do") or "")
                if "không có kênh" in ld.lower():
                    ten = "tất cả" if cfg.nhom == "__ALL__" else (cfg.nhom or "Chưa phân nhóm")
                    self.bao_loi("nhom_rong", f"{TEN_LOI['nhom_rong']} (nhóm «{ten}»)", now)
                elif self.lich.nen_noi("kq:" + ld, now):
                    self.studio._pipe_log(f"⏸ Tự chạy: không chạy được — {ld}")
            else:
                self.het_loi("nhom_rong", now)
            return "chay"
        if viec in ("bo", "hoan") and ly not in ("ngoai_gio", "bo_qua_ngay"):
            loi = TC.LOI_NOI.get(ly, ly)
            if ly == "o_day" and self.o_dia:
                loi += f": {self.o_dia[1]}"
            if self.lich.nen_noi(ly, now):
                self.studio._pipe_log(
                    ("⏸ Tự chạy: đang HOÃN — " if viec == "hoan"
                     else "⏸ Tự chạy: không chạy lượt mới — ") + loi)
        return viec

    # ------------------------------------------------ 1b-V4: canh treo --
    def _canh_treo(self, now: float) -> None:
        S = self.studio
        vua_go = False
        if S._pipe_dang_quet_n() > 0:
            if self._quet_thay is None:
                self._quet_thay = now
            elif now - self._quet_thay >= TREO_GIAY:
                self._quet_thay = None
                vua_go = True
                S._pipe_dung_luot(go_co_quet=True)
                self.bao_loi("treo_quet", f"{TEN_LOI['treo_quet']} sau "
                             f"{TREO_GIAY // 60} phút (ổ chậm / ổ mạng chết?)", now)
        else:
            self._quet_thay = None
        q = getattr(S, "_pipe_intake_q", None) or []
        if q:
            sig = (len(q), getattr(S, "_pipe_intake_taken", 0))
            if sig != self._nhan_sig:
                self._nhan_sig, self._nhan_tu = sig, now
            elif now - (self._nhan_tu or now) >= TREO_GIAY:
                self._nhan_sig = self._nhan_tu = None
                vua_go = True
                S._pipe_dung_luot(chi_tu_chay=False)   # treo: bỏ HẾT hàng nhận
                self.bao_loi("treo_nhan", f"{TEN_LOI['treo_nhan']} ({len(q)} video "
                             f"không nhích trong {TREO_GIAY // 60} phút)", now)
        else:
            self._nhan_sig = self._nhan_tu = None
        # "đã ổn lại" chỉ ở nhịp SAU (nhịp vừa gỡ cờ thì chưa biết đã ổn chưa)
        if not vua_go and not q and not S._pipe_dang_quet_n():
            self.het_loi("treo_quet", now)
            self.het_loi("treo_nhan", now)

    # -------------------------------------------------- 60 s: bận + phiếu --
    def nhip_60(self, now: float | None = None) -> None:
        now = self._dong_ho() if now is None else now
        try:
            self._nhip_60(now)
        except Exception as e:  # noqa: BLE001
            loi = f"{TEN_LOI['loi_60']}: {type(e).__name__}: {e}"
            try:
                bat = self.cau_hinh().bat
            except Exception:  # noqa: BLE001
                bat = False
            if not bat:
                # Tự chạy TẮT (chỉ còn ghi file bận): im lặng như cũ — log 1
                # lần, KHÔNG gửi Telegram (N6).
                if self.lich.nen_noi("log:loi_60_tat", now):
                    self.studio._pipe_log("⚠ " + loi)
                return
            # khoá RIÊNG cho phần ĐỒNG BỘ của đường 60 s; lỗi phần NỀN dùng
            # "loi_nen" và chỉ _nen_xong thành công mới gỡ (B1/N3).
            self.bao_loi("loi_60", loi, now)
            return
        self.het_loi("loi_60", now)

    def _nhip_60(self, now: float) -> None:
        # Trạng thái bận ghi LUÔN khi app chạy (kể cả Tự chạy TẮT) để PCBot biết
        # app bận cả khi anh Hùng bấm cắt tay. Hộp cát test / chưa cài PCBot
        # (không có thư mục exchange) -> im lặng bỏ qua.
        self.ghi_ban(now)
        cfg = self.cau_hinh()
        if not cfg.bat:
            return
        if self._nen_dang:
            if now - self._nen_tu < NEN_TOI_DA_GIAY:
                return                   # lượt nền trước chưa xong (ổ mạng chậm)
            if self.lich.nen_noi("nen_treo", now):
                self.studio._pipe_log("⚠ Tự chạy: đo ổ / đọc phiếu treo quá "
                                      f"{NEN_TOI_DA_GIAY // 60} phút — đo lại")
        from app.database.db import db
        db_hong = bool(getattr(db, "corrupt_live", False))
        self._nen_dang = True
        self._nen_tu = now
        self._nen_the += 1
        the = self._nen_the
        S = self.studio
        root = S._pipe_root()
        goc = PD.thu_muc_phieu(cfg.thu_muc)
        bo_doc = self._bo_doc

        def viec():
            ra = {"o": TC.kiem_o_dia(TC.thu_muc_kenh_bat(root),
                                     cfg.o_video_gb, cfg.o_c_gb),
                  "phieu": None, "goc": goc, "co_dot": None, "db_hong": db_hong,
                  "het_ai": None}
            try:
                from app.ai import llm as _llm
                if _llm.is_configured():
                    w = _llm.soonest_ready_wait(_llm.active_provider())
                    # None = MỌI key bị chặn / không dùng được -> cũng là hết
                    # lượt (S3); chưa có key nào thì đường "khong_key" lo.
                    ra["het_ai"] = w is None or float(w) > TC.HET_LUOT_AI_GIAY
            except Exception:  # noqa: BLE001
                ra["het_ai"] = None
            if goc is not None:
                ra["co_dot"] = (goc / "dot").is_dir()
            # 1b-V1: DB HỎNG -> mọi truy vấn trả rỗng -> mọi video thành
            # `khong_co_kenh` (là kết quả CUỐI) -> đóng phiếu + báo cáo SAI. Dừng.
            if db_hong or getattr(db, "corrupt_live", False):
                ra["db_hong"] = True
                return ra
            if ra["co_dot"]:
                nc = PD.ngu_canh_db(root)
                if getattr(db, "corrupt_live", False) or not nc["kenh"]:
                    ra["db_hong"] = bool(getattr(db, "corrupt_live", False))
                    ra["khong_kenh"] = True
                    return ra
                ra["phieu"] = PD.cap_nhat_tat_ca(goc, bo_doc, nc, now)
                if ra["phieu"].get("db_hong"):
                    ra["db_hong"] = True
                    ra["phieu"] = None
                    return ra
                PD.don_phieu_cu(goc / "cat", now)
            return ra
        S._chay_nen(viec, lambda kq, g=the: self._nen_xong(kq, g), "bq-tu-chay")

    def _nen_xong(self, kq, the: int | None = None) -> None:
        # Lượt nền CŨ (bị coi là treo, đã có lượt mới thay) về muộn: bỏ qua,
        # KHÔNG được xoá cờ đang-chạy của lượt mới.
        if the is not None and the != self._nen_the:
            return
        self._nen_dang = False
        self.lan_nen += 1
        ok, val = kq
        now = self._dong_ho()
        if not ok:
            self.bao_loi("loi_nen", f"{TEN_LOI['loi_nen']} — {val}", now)
            return
        self.het_loi("loi_nen", now)
        self.o_dia = val["o"]
        if val.get("het_ai") is not None:
            self.het_luot_ai = bool(val["het_ai"])
        if val.get("db_hong"):
            # chỉ GHI LOG (1/giờ); tin Telegram do bot gửi (_bao_db) — S1
            if self.lich.nen_noi("log:db_hong", now):
                self.studio._pipe_log("⚠ Tự chạy: " + TEN_LOI["db_hong"]
                                      + " (khởi động lại app để tự chữa)")
            return
        if val.get("co_dot") is False:
            self.bao_loi("thu_muc_phieu", f"{TEN_LOI['thu_muc_phieu']} {val['goc']} — "
                         "vẫn cắt theo quét thư mục, chỉ mất báo cáo nhóm", now)
        elif val.get("co_dot"):
            self.het_loi("thu_muc_phieu", now)
        ra, goc = val.get("phieu"), val.get("goc")
        if not ra:
            return
        self.dot_mo = ra.get("mo") or []
        for dot, vid, ts in ra["xong_moi"]:
            self.lich.them_kich(dot, vid, ts, now)
        for s in ra["bao"]:
            self.studio._pipe_log("⚠ Phiếu đợt: " + s)
            self.tele("⚠ <b>Phiếu đợt</b>: " + PD._h(s))
        if ra.get("loi_ghi"):
            if self._ghi_loi_tu is None:
                self._ghi_loi_tu = now
            if self.lich.nen_noi("ghi_phieu", now):
                self.studio._pipe_log("⚠ " + ra["loi_ghi"])
            if now - self._ghi_loi_tu >= GHI_LOI_GIAY:
                self.bao_loi("ghi_phieu", f"{TEN_LOI['ghi_phieu']} hơn "
                             f"{GHI_LOI_GIAY // 60} phút: {ra['loi_ghi']}", now)
        else:
            self._ghi_loi_tu = None
            self.het_loi("ghi_phieu", now)
        for su in ra["su_kien"]:
            if su[0] == "mat_file":
                t = (f"MẤT FILE: kênh «{su[1]}» — phiếu tải ghi xong '{su[2]}' "
                     f"nhưng sau {PD.MAT_FILE_PHUT} phút không thấy file trong thư "
                     "mục và không có trong sổ")
                self.studio._pipe_log("⚠ " + t)
                self.tele(f"⚠ <b>MẤT FILE</b>: kênh «{PD._h(su[1])}» — phiếu tải ghi "
                          f"xong '{PD._h(su[2])}' nhưng sau {PD.MAT_FILE_PHUT} phút "
                          "không thấy file trong thư mục và không có trong sổ")
        self._bao_kck(ra.get("kck") or [], now)
        for dot, text in ra["bao_cao"]:
            if dot in self._da_dua_bao:
                continue
            if dot not in self._ghi_log_bc:
                self._ghi_log_bc.add(dot)
                self.studio._pipe_log("📦 " + text.replace("<b>", "").replace("</b>", ""))
            if self._dua_bao_cao(goc, dot, text):
                self._da_dua_bao.add(dot)

    def _bao_kck(self, ds: list, now: float) -> None:
        """#18: thư mục trong phiếu không có kênh cắt -> báo MỖI NGÀY 1 lần."""
        if not ds:
            return
        from datetime import datetime
        from app.ui.appsettings import app_settings
        hom = datetime.fromtimestamp(now).strftime("%Y-%m-%d")
        s = app_settings()
        if str(s.value(TC.KHOA + "kck_ngay", "") or "") == hom:
            return
        ten = ", ".join(sorted(set(str(x) for x in ds))[:6])
        t = (f"{len(set(ds))} thư mục trong phiếu tải KHÔNG có kênh cắt nào: {ten} "
             "— tạo kênh / sửa thư mục kênh (video ở đó sẽ không được cắt)")
        if self._kck_log != hom:            # log tối đa 1 lần/ngày (S2)
            self._kck_log = hom
            self.studio._pipe_log("⚠ " + t)
        if self._kck_dang == hom:            # đã xếp gửi, đang chờ bot -> không xếp trùng
            return

        def da_gui(s=s, hom=hom):
            # QSettings ghi ở luồng bot: chỉ 1 khoá, an toàn (đọc lại ở nhịp sau)
            s.setValue(TC.KHOA + "kck_ngay", hom)

        def xong(ok, hom=hom):
            # gửi xong (được: kck_ngay đã ghi -> hôm nay không gửi nữa; lỗi:
            # nhịp sau thử lại) -> gỡ cờ "đang xếp"
            self._kck_dang = ""
        # bật cờ TRƯỚC khi gửi: bên gửi có thể gọi khi_xong ngay (đồng bộ)
        self._kck_dang = hom
        if not self.tele("⚠ <b>Không có kênh cắt</b>: " + PD._h(t), khi_ok=da_gui,
                         khi_xong=xong):
            self._kck_dang = ""              # không có bot -> nhịp sau thử lại

    def _dua_bao_cao(self, goc, dot: str, text: str) -> bool:
        """#28: báo cáo nhóm đi chung tin "HẾT hàng chờ" của bot (không báo
        trùng). Bot CHƯA chạy -> KHÔNG đánh dấu "đã báo" (để có bot là gửi)."""
        def danh_dau():
            try:
                PD.danh_dau_da_bao(goc, dot)
            except Exception:  # noqa: BLE001
                pass
        try:
            from app.core import tele_bot as TB
            if TB._bot is not None:
                TB.them_bao_cao_nhom(text, danh_dau)
                return True
        except Exception:  # noqa: BLE001
            pass
        return False

    # ------------------------------------------------------- báo bot --
    def tele(self, text: str, khi_ok=None, khi_xong=None) -> bool:
        """Gửi bot ở LUỒNG BOT. khi_ok() chạy CHỈ khi gửi thành công; khi_xong(ok)
        chạy sau mọi lần thử. Không có bot -> False (không đánh dấu gì)."""
        try:
            from app.core import tele_bot as TB
            b = TB._bot
            if b is None:
                return False

            def gui():
                ok = b._gui_het(text)
                for fn, a in ((khi_ok, ()) if ok else (None, ()), (khi_xong, (ok,))):
                    if fn:
                        try:
                            fn(*a)
                        except Exception:  # noqa: BLE001
                            pass
            b._viec.submit(gui)
            return True
        except Exception:  # noqa: BLE001
            return False

    def bao_loi(self, loai: str, text: str, now: float) -> None:
        """Lỗi loại `loai` đang xảy ra: log + báo bot tối đa 1 lần/giờ (chỉ
        đánh dấu khi gửi được)."""
        e = self._loi.setdefault(loai, {"tu": now, "gui": None})
        if self.lich.nen_noi("log:" + loai, now):
            self.studio._pipe_log("⚠ Tự chạy: " + text)
        cuoi = self._gui_cuoi.get(loai)
        if cuoi is not None and now - cuoi < TC.NOI_LAI_GIAY:
            return                       # đã báo trong giờ này (kể cả đợt lỗi trước)
        if e.get("dang_gui") and now - e["dang_gui"] < 120:
            return

        def da(e=e, now=now, loai=loai):
            e["gui"] = now
            self._gui_cuoi[loai] = now
            e.pop("dang_gui", None)
        e["dang_gui"] = now
        if not self.tele("⚠ <b>Tự chạy dây chuyền</b>: " + PD._h(text), khi_ok=da):
            e.pop("dang_gui", None)

    def het_loi(self, loai: str, now: float) -> None:
        e = self._loi.pop(loai, None)
        if e and e.get("gui") is not None:
            ten = TEN_LOI.get(loai, loai).split(" — ")[0]
            self.studio._pipe_log(f"✅ Tự chạy: đã ổn lại — {ten}")
            self.tele(f"✅ <b>Tự chạy đã ổn lại</b>: {PD._h(ten)}")

    # --------------------------------------------------- trạng thái sống --
    def trang_thai(self, now: float | None = None, html: bool = False) -> str:
        now = self._dong_ho() if now is None else now
        cfg = self.cau_hinh()
        S = self.studio
        h = PD._h if html else (lambda x: str(x))
        if S._pipe_dang_quet_n():
            dang = "đang QUÉT thư mục kênh"
        elif S._bot_dang_nhan():
            dang = f"đang NHẬN {S._bot_dang_nhan()} video"
        else:
            dang = "rảnh (chờ nhịp)"
        nhom = "tất cả nhóm" if cfg.nhom == "__ALL__" else (cfg.nhom or "Chưa phân nhóm")
        d = [f"Tự chạy: {'BẬT' if cfg.bat else 'TẮT'} · {TC.mo_ta_khung(cfg.tu, cfg.den)}"
             f" · nhịp {cfg.phut} phút · nhóm «{h(nhom)}»"]
        if cfg.bo_ngay == TC.hom_nay(now):
            d.append("Hôm nay: ĐÃ BỎ QUA (bấm Chạy lại hôm nay để bỏ)")
        d.append(f"Đang: {dang}")
        if cfg.bat:
            d.append(f"Lượt tới: {TC.gio_hien(self.lich.hen)}"
                     + (" · đã bấm Chạy ngay" if self.lich.ep else ""))
        d.append(f"Đã chạy {self.lich.lan_chay} lượt · lần cuối {TC.gio_hien(self.lich.lan_cuoi)}")
        if self.lich.ly_do_cuoi:
            d.append(f"Lý do hoãn gần nhất ({TC.gio_hien(self.lich.ly_do_luc)}): "
                     + h(TC.LOI_NOI.get(self.lich.ly_do_cuoi, self.lich.ly_do_cuoi)))
        # số việc chờ MỚI khi vẽ, đệm 5 s (hộp vẽ mỗi giây trên luồng GD — N5)
        if now - getattr(self, "_dem_luc", -1e18) >= 5:
            self._dem_luc = now
            self.cho_phan_tich = self._dem_cho()
        d.append(f"Việc phân tích đang chờ: {self.cho_phan_tich} (ngưỡng nhận thêm "
                 f"{cfg.nguong_cho})" + (" · AI HẾT LƯỢT kéo dài" if self.het_luot_ai else ""))
        if self.o_dia is not None:
            d.append("Ổ đĩa: ổn" if self.o_dia[0] else f"Ổ đĩa: {h(self.o_dia[1])}")
        if self.dot_mo:
            d.append("Đợt đang mở: " + ", ".join(
                f"{h(x[0])} ({h(x[1])})" for x in self.dot_mo[:5]))
        if self._loi:
            d.append("Lỗi đang có: " + ", ".join(h(TEN_LOI.get(k, k)) for k in self._loi))
        return "\n".join(d)

    # -------------------------------------------- điều khiển (nút + bot) --
    def _luu(self, **kv) -> None:
        from app.ui.appsettings import app_settings
        s = app_settings()
        for k, v in kv.items():
            s.setValue(TC.KHOA + k, v)
        s.sync()

    def chay_ngay(self, now: float | None = None) -> str:
        """Nút "Chạy ngay": bấm nhiều lần = 1 lượt. Trả câu trả lời."""
        now = self._dong_ho() if now is None else now
        cfg = self.cau_hinh()
        if not cfg.bat:
            return "Tự chạy đang TẮT — bật trước, hoặc dùng Chạy dây chuyền (tay)."
        S = self.studio
        if S._pipe_dang_quet_n() or S._bot_dang_nhan():
            return "Lượt trước còn đang quét/nhận — chưa chạy thêm (không chạy trùng)."
        if not self.lich.chay_ngay():
            return "Đã xếp Chạy ngay rồi — đang chờ chạy."
        r = self.nhip(now)
        if r == "chay":
            return "Đã chạy 1 lượt ngay."
        if r == "hoan":
            return "Đã xếp — đang hoãn: " + TC.LOI_NOI.get(self.lich.ly_do_cuoi, "")
        self.lich.ep = False
        return "Không chạy được: " + TC.LOI_NOI.get(self.lich.ly_do_cuoi, r)

    def lenh(self, viec: str, arg=None) -> dict:
        """Lệnh từ bot (LUỒNG GIAO DIỆN qua goi_ui). Trả {"ok", "text"}."""
        now = self._dong_ho()
        try:
            if viec == "xem":
                return {"ok": True, "text": self.trang_thai(now, html=True)}
            if viec in ("bat", "tat"):
                self._luu(bat=(viec == "bat"))
                self.lich.dong_bo(self.cau_hinh(), now)
                return {"ok": True, "text": ("Đã BẬT Tự chạy — lượt đầu sau "
                                             f"{self.cau_hinh().phut} phút (không chạy ngay)."
                                             if viec == "bat" else "Đã TẮT Tự chạy.")}
            if viec == "ngay":
                return {"ok": True, "text": self.chay_ngay(now)}
            if viec == "dung":
                kq = self.studio._pipe_dung_luot()
                return {"ok": True, "text": f"Đã dừng lượt: bỏ {kq['bo']} video chưa nhận"
                        + (f" + {kq['quet']} lượt quét" if kq["quet"] else "")
                        + ". Việc đang cắt/xuất vẫn chạy tiếp, video gốc giữ nguyên."}
            if viec == "bo_qua":
                self._luu(bo_ngay=TC.hom_nay(now))
                return {"ok": True, "text": "Đã BỎ QUA hôm nay — mai tự chạy lại. "
                        "Gõ /tuchaylai để chạy lại ngay hôm nay."}
            if viec == "chay_lai":
                self._luu(bo_ngay="")
                return {"ok": True, "text": "Đã bỏ 'Bỏ qua hôm nay' — tự chạy lại theo nhịp."}
            if viec == "gio":
                tu, den = doc_khung(str(arg or ""))
                if tu is None:
                    return {"ok": False, "text": "Sai dạng. Gõ vd <code>/tuchaygio 06:00-22:00</code>"
                            " · 06:00-24:00 = tới hết ngày · 06:00-06:00 = cả ngày."}
                self._luu(tu=tu, den=den)
                return {"ok": True, "text": "Đã đặt khung giờ "
                        + TC.mo_ta_khung(TC.doc_gio(tu, tu), TC.doc_gio(den, den)) + "."}
            if viec == "nhip":
                try:
                    n = int(str(arg).strip())
                except (TypeError, ValueError):
                    n = 0
                if not 1 <= n <= 240:
                    return {"ok": False, "text": "Nhịp phải từ 1 đến 240 phút, vd "
                            "<code>/tuchaynhip 10</code>."}
                self._luu(phut=n)
                self.lich.dong_bo(self.cau_hinh(), now)
                return {"ok": True, "text": f"Đã đặt nhịp {n} phút — lượt tới "
                        f"{TC.gio_hien(self.lich.hen)}."}
            if viec == "nhom":
                g = "__ALL__" if arg in (None, "__ALL__") else str(arg)
                self._luu(nhom=TC.NHOM_CHUA if g == "" else g)
                return {"ok": True, "text": "Đã đặt nhóm Tự chạy: «"
                        + PD._h("tất cả" if g == "__ALL__" else (g or "Chưa phân nhóm")) + "»."}
            return {"ok": False, "text": "Lệnh Tự chạy không rõ."}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "text": f"Lệnh lỗi: {PD._h(str(e)[:150])}"}

    # ------------------------------------------------- trạng thái bận --
    def noi_dung_ban(self, now: float, dang_thoat: bool = False) -> dict:
        try:
            from app import services
            c = services.queue_counts() or {}
            dang_lam = int(c.get("analyzing", 0) or 0) + int(c.get("exporting", 0) or 0)
            cho = int(c.get("waiting", 0) or 0)
        except Exception:  # noqa: BLE001
            cho = dang_lam = 0
        from app.version import __version__
        S = self.studio
        tt = self.tinh_trang()
        ly = "tam_dung" if tt.tam_dung else ("o_day" if self.o_dia and not self.o_dia[0]
                                             else None)
        return PD.noi_dung_ban(cho, dang_lam, int(S._bot_dang_nhan() or 0),
                               S._pipe_dang_quet_n() > 0, os.getpid(), __version__,
                               ly_do=ly, now=now, dang_thoat=dang_thoat)

    def ghi_ban(self, now: float, dang_thoat: bool = False, dong_bo: bool = False) -> bool:
        """Dựng nội dung ở LUỒNG GIAO DIỆN (app treo -> không ai ghi -> file
        cũ đi, PCBot biết). Ghi bằng 1 luồng ngắn do chính nhịp này đẻ ra —
        không có vòng nền nào tự ghi hộ. `dong_bo` = lần cuối lúc thoát êm."""
        d = PD.thu_muc_exchange()
        if d is None:
            return False
        if not d.is_dir():
            return False                 # chưa cài PCBot -> im lặng (mục 12)
        nd = self.noi_dung_ban(now, dang_thoat)
        f = d / PD.TEN_FILE_BAN

        def ghi():
            try:
                PD.ghi_nguyen_tu(f, nd, thu_lai=2 if dong_bo else 5)
                self.so_ghi_ban += 1
            except OSError as e:
                if not self._ban_loi_da_ghi:
                    self._ban_loi_da_ghi = True
                    # chỉ đặt cờ ở luồng nền; nhật ký ghi ở nhịp sau (luồng GD)
                    self._ban_loi_cho = str(e)
        if dong_bo:
            ghi()
        else:
            threading.Thread(target=ghi, daemon=True, name="bq-ghi-ban").start()
        loi = getattr(self, "_ban_loi_cho", None)
        if loi:
            self._ban_loi_cho = None
            self.studio._pipe_log(f"ℹ Trạng thái bận: không ghi được ({loi}) — bỏ qua")
        return True

    def thoat(self) -> None:
        """closeEvent: ghi lần cuối `ban=false` (mục 12)."""
        try:
            self.ghi_ban(self._dong_ho(), dang_thoat=True, dong_bo=True)
        except Exception:  # noqa: BLE001
            pass


def doc_khung(s: str):
    """"06:00-22:00" -> ("06:00", "22:00"); "24:00" hợp lệ ở ô đến. Sai -> (None, None)."""
    import re
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})\s*", s or "")
    if not m:
        return None, None
    h1, m1, h2, m2 = (int(x) for x in m.groups())
    if not (0 <= h1 <= 23 and 0 <= m1 < 60 and 0 <= m2 < 60
            and (0 <= h2 <= 23 or (h2 == 24 and m2 == 0))):
        return None, None
    return f"{h1:02d}:{m1:02d}", f"{h2:02d}:{m2:02d}"


def kiem_thu_muc_phieu(d: str) -> str:
    """'' = dùng được; ngược lại lời báo. Ô trống = thư mục MẶC ĐỊNH, cũng
    kiểm (hộp cát test không đặt env thì bỏ qua). GỌI Ở LUỒNG NỀN."""
    from pathlib import Path
    p = Path(d) if (d or "").strip() else PD.thu_muc_phieu("")
    if p is None:
        return ""
    d = str(p)
    if not p.is_dir():
        return f"Thư mục không tồn tại: {d}"
    t = p / ".bq_thu_ghi.tmp"
    try:
        t.write_text("x", encoding="utf-8")
        t.unlink()
    except OSError as e:
        return f"Không ghi được vào thư mục: {e}"
    return ""


# --------------------------------------------------------- hộp cài đặt --
def mo_hop(studio, exec_: bool = True):
    """Hộp "Tự chạy dây chuyền" (menu ⋮ của hộp Dây chuyền). Nhãn CHỮ, không
    emoji. Bật ô KHÔNG chạy gì ngay: chỉ lưu khi bấm Lưu, nhịp đầu tiên rơi vào
    bây giờ + N phút; "Chạy ngay" / "Dừng lượt" đều HỎI XÁC NHẬN trước."""
    from PyQt6.QtCore import QTime
    from PyQt6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QFormLayout,
                                 QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                                 QPushButton, QTimeEdit, QVBoxLayout)
    from app.ui.appsettings import app_settings
    from app.ui.wheelguard import NoWheelComboBox, NoWheelSpinBox

    s = app_settings()
    cfg = TC.doc_cau_hinh(s)
    dlg = QDialog(studio)
    dlg.setWindowTitle("Tự chạy dây chuyền")
    lay = QVBoxLayout(dlg)
    gt = QLabel("Tự chạy gọi đúng nút Chạy dây chuyền theo nhịp trong khung giờ. "
                "Mặc định TẮT. Bật xong lượt đầu chạy sau đúng số phút của nhịp "
                "(không chạy ngay). Lượt tự chạy không nhảy màn hình. Các nút này "
                "cũng có qua bot Telegram: gõ /tuchay.")
    gt.setWordWrap(True)
    lay.addWidget(gt)
    f = QFormLayout()
    cb_bat = QCheckBox("Bật Tự chạy dây chuyền")
    cb_bat.setChecked(cfg.bat)
    f.addRow(cb_bat)

    def _te(phut):
        t = QTimeEdit()
        t.setDisplayFormat("HH:mm")
        t.setTime(QTime(min(23, phut // 60), phut % 60))
        return t
    te_tu, te_den = _te(cfg.tu), _te(cfg.den if cfg.den < 1440 else 0)
    cb_het = QCheckBox("đến hết ngày (24:00)")
    cb_het.setChecked(cfg.den >= 1440)
    te_den.setEnabled(not cb_het.isChecked())
    cb_het.toggled.connect(lambda v: te_den.setEnabled(not v))
    hb = QHBoxLayout()
    hb.addWidget(te_tu)
    hb.addWidget(QLabel("đến"))
    hb.addWidget(te_den)
    hb.addWidget(cb_het)
    f.addRow("Khung giờ:", hb)
    ghi_chu = QLabel("Từ = Đến là chạy CẢ NGÀY. Từ lớn hơn Đến là khung qua nửa đêm.")
    ghi_chu.setWordWrap(True)
    f.addRow("", ghi_chu)
    sp = NoWheelSpinBox()
    sp.setRange(1, 240)
    sp.setSuffix(" phút")
    sp.setValue(cfg.phut)
    f.addRow("Nhịp chạy:", sp)
    sp_ng = NoWheelSpinBox()
    sp_ng.setRange(1, 1000)
    sp_ng.setSuffix(" việc")
    sp_ng.setValue(cfg.nguong_cho)
    f.addRow("Chỉ nhận thêm khi việc phân tích chờ dưới:", sp_ng)
    cb_nhom = NoWheelComboBox()
    cb_nhom.addItem("Tất cả nhóm", "__ALL__")
    try:
        from app.database.db import db
        ds = [r["g"] for r in db.query(
            "SELECT DISTINCT COALESCE(grp,'') g FROM projects ORDER BY g")]
    except Exception:  # noqa: BLE001
        ds = []
    try:
        ds += [g for g in studio._extra_groups() if g not in ds]
    except Exception:  # noqa: BLE001
        pass
    for g in ds:
        cb_nhom.addItem(g or "Chưa phân nhóm", g)
    i = cb_nhom.findData(cfg.nhom) if cfg.nhom != "" else cb_nhom.findData("")
    if i < 0 and cfg.nhom != "__ALL__":
        cb_nhom.addItem(f"{cfg.nhom} (không còn kênh)", cfg.nhom)
        i = cb_nhom.count() - 1
    cb_nhom.setCurrentIndex(max(0, i))
    f.addRow("Nhóm:", cb_nhom)
    ed = QLineEdit(cfg.thu_muc)
    ed.setPlaceholderText(PD.THU_MUC_MAC_DINH)
    b_chon = QPushButton("Chọn thư mục")
    hb2 = QHBoxLayout()
    hb2.addWidget(ed, 1)
    hb2.addWidget(b_chon)
    f.addRow("Thư mục phiếu đợt:", hb2)

    def _chon():
        d = studio._busy_dialog(QFileDialog.getExistingDirectory, dlg,
                                "Thư mục phiếu đợt", ed.text() or PD.THU_MUC_MAC_DINH)
        if d:
            ed.setText(d)
    b_chon.clicked.connect(_chon)
    sp_v = NoWheelSpinBox()
    sp_v.setRange(1, 2000)
    sp_v.setSuffix(" GB")
    sp_v.setValue(int(cfg.o_video_gb))
    f.addRow("Dừng khi ổ chứa video còn dưới:", sp_v)
    sp_c = NoWheelSpinBox()
    sp_c.setRange(1, 2000)
    sp_c.setSuffix(" GB")
    sp_c.setValue(int(cfg.o_c_gb))
    f.addRow("Dừng khi ổ C còn dưới:", sp_c)
    lay.addLayout(f)

    tc = getattr(studio.window(), "_tu_chay", None)
    tt = QLabel()
    tt.setWordWrap(True)
    lay.addWidget(tt)
    hb_n = QHBoxLayout()
    b_ngay = QPushButton("Chạy ngay")
    b_dung = QPushButton("Dừng lượt đang chạy")
    b_bq = QPushButton("Bỏ qua hôm nay")
    for b in (b_ngay, b_dung, b_bq):
        hb_n.addWidget(b)
        b.setEnabled(tc is not None)
    lay.addLayout(hb_n)

    def _cap_nhat():
        try:
            if tc is None:
                tt.setText("Tự chạy chưa khởi động trong phiên này.")
                return
            tt.setText(tc.trang_thai())
            hn = TC.doc_cau_hinh(app_settings()).bo_ngay == TC.hom_nay(tc._dong_ho())
            b_bq.setText("Chạy lại hôm nay" if hn else "Bỏ qua hôm nay")
        except RuntimeError:
            pass
    _cap_nhat()
    t_song = QTimer(dlg)
    t_song.timeout.connect(_cap_nhat)
    t_song.start(1000)

    def _hoi(tieu_de, cau):
        return QMessageBox.question(dlg, tieu_de, cau) == QMessageBox.StandardButton.Yes

    def _ngay():
        if tc is None or not _hoi("Chạy ngay", "Chạy 1 lượt Tự chạy NGAY bây giờ?"):
            return
        tt.setText(tc.chay_ngay())

    def _dung():
        if tc is None or not _hoi("Dừng lượt", "Dừng lượt đang chạy? App NGỪNG NHẬN "
                                  "thêm video; việc đang cắt/xuất vẫn chạy tiếp, "
                                  "video gốc giữ nguyên."):
            return
        tt.setText(tc.lenh("dung")["text"])

    def _bq():
        if tc is None:
            return
        hn = TC.doc_cau_hinh(app_settings()).bo_ngay == TC.hom_nay(tc._dong_ho())
        tt.setText(tc.lenh("chay_lai" if hn else "bo_qua")["text"])
        _cap_nhat()
    b_ngay.clicked.connect(_ngay)
    b_dung.clicked.connect(_dung)
    b_bq.clicked.connect(_bq)

    hb3 = QHBoxLayout()
    hb3.addStretch(1)
    b_luu = QPushButton("Lưu")
    b_dong = QPushButton("Đóng")
    hb3.addWidget(b_luu)
    hb3.addWidget(b_dong)
    lay.addLayout(hb3)

    trang_luu = {"dang": False, "the": 0}

    def _luu():
        """Kiểm thư mục phiếu ở LUỒNG NỀN (ổ mạng có thể treo), có thời hạn
        5 s; xong mới ghi cài đặt. Trả "dang_kiem" (test đợi kết quả)."""
        if trang_luu["dang"]:
            return "dang_kiem"
        trang_luu["dang"] = True
        trang_luu["the"] += 1
        the = trang_luu["the"]
        b_luu.setEnabled(False)
        b_luu.setText("Đang kiểm thư mục")
        hop: dict = {}
        thu_muc = ed.text().strip()            # đọc ở LUỒNG GIAO DIỆN (N1)
        if not cb_bat.isChecked():
            hop["loi"] = ""                    # chỉ TẮT -> không kiểm (N2)

        def kiem():
            hop["loi"] = kiem_thu_muc_phieu(thu_muc)

        def het_han():
            if trang_luu["the"] != the or not trang_luu["dang"]:
                return
            if "loi" not in hop:
                hop["loi"] = "Kiểm thư mục quá 5 giây (ổ mạng chậm/chết?)"
            _ket_qua()

        def _ket_qua():
            try:
                _ket_qua_that()
            except RuntimeError:               # hộp đã đóng/huỷ giữa lúc kiểm
                trang_luu["dang"] = False

        def _ket_qua_that():
            if not trang_luu["dang"] or trang_luu["the"] != the:
                return
            trang_luu["dang"] = False
            try:
                b_luu.setEnabled(True)
                b_luu.setText("Lưu")
            except RuntimeError:
                return
            loi = hop.get("loi") or ""
            if loi:
                # N2: thiếu / không ghi được thư mục phiếu chỉ làm MẤT phần báo
                # cáo nhóm, video vẫn cắt theo quét -> cảnh báo rồi VẪN lưu.
                QMessageBox.warning(dlg, "Thư mục phiếu đợt", loi + "\nVẫn lưu: video "
                                    "vẫn được cắt theo quét thư mục, chỉ thiếu báo cáo "
                                    "nhóm cho tới khi thư mục có (tool tải tạo ra).")
            dlg._ket_luu = _ghi()

        def _cho():
            if "loi" in hop:
                _ket_qua()
            elif trang_luu["dang"] and trang_luu["the"] == the:
                QTimer.singleShot(50, _cho)
        dlg._ket_luu = None
        if "loi" not in hop:
            threading.Thread(target=kiem, daemon=True, name="bq-kiem-phieu").start()
        QTimer.singleShot(50, _cho)
        QTimer.singleShot(5000, het_han)
        return "dang_kiem"

    def _ghi():
        den = "24:00" if cb_het.isChecked() else te_den.time().toString("HH:mm")
        s.setValue(TC.KHOA + "bat", bool(cb_bat.isChecked()))
        s.setValue(TC.KHOA + "tu", te_tu.time().toString("HH:mm"))
        s.setValue(TC.KHOA + "den", den)
        s.setValue(TC.KHOA + "phut", int(sp.value()))
        s.setValue(TC.KHOA + "nguong_cho", int(sp_ng.value()))
        _g = cb_nhom.currentData()
        s.setValue(TC.KHOA + "nhom", TC.NHOM_CHUA if _g == "" else _g)
        s.setValue(TC.KHOA + "thu_muc", ed.text().strip())
        s.setValue(TC.KHOA + "o_video_gb", int(sp_v.value()))
        s.setValue(TC.KHOA + "o_c_gb", int(sp_c.value()))
        s.sync()
        try:
            studio._pipe_log(
                "Tự chạy: " + ("BẬT" if cb_bat.isChecked() else "TẮT")
                + f" · {TC.mo_ta_khung(TC.doc_gio(te_tu.time().toString('HH:mm'), '06:00'), TC.doc_gio(den, '22:00'))}"
                + f" · nhịp {sp.value()} phút · nhóm «{cb_nhom.currentText()}»")
        except Exception:  # noqa: BLE001
            pass
        if tc is not None:
            tc.lich.dong_bo(tc.cau_hinh(), tc._dong_ho())   # đổi nhịp -> hẹn lại ngay
        dlg.accept()
        return True
    b_luu.clicked.connect(_luu)
    b_dong.clicked.connect(dlg.reject)
    dlg.finished.connect(lambda *_: t_song.stop())
    dlg._luu = _luu                 # test gọi thẳng
    dlg._o = {"bat": cb_bat, "tu": te_tu, "den": te_den, "het_ngay": cb_het,
              "phut": sp, "nguong": sp_ng, "nhom": cb_nhom, "thu_muc": ed,
              "o_video": sp_v, "o_c": sp_c, "trang_thai": tt, "ngay": b_ngay,
              "dung": b_dung, "bo_qua": b_bq}
    studio._tu_chay_dlg = dlg
    if exec_:
        dlg.exec()
    return dlg
