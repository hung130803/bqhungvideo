# -*- coding: utf-8 -*-
"""THỬ PHÁ CỔNG 92 — gỡ từng chốt rồi bắt cổng phải ĐỎ.

Cổng nào cũng có thể chỉ là một con dấu. Cách duy nhất biết được là **gỡ hẳn
một chốt** rồi xem cổng có kêu không.

BỐN LUẬT CỦA FILE NÀY (mỗi luật là một lần repo đã trả giá):

 1. **GỠ HẲN chốt, đừng đổi giá trị bên trong nó.** Đổi giá trị có thể làm
    hàm CHẶT HƠN, rồi bảng đọc thành "cổng không bắt được" trong khi thật ra
    cổng xanh ĐÚNG (bài học cổng 80 LỌT 7).
 2. **"Không tìm thấy chỗ phá" là LỖI CỦA PHÉP THỬ, KHÔNG phải LỌT.** File
    repo là **CRLF**, chuỗi tìm nhiều dòng viết `\\n` sẽ KHÔNG khớp — đã có
    lần 4/6 phép phá im lặng không phá được gì mà bảng vẫn **đếm vào cột
    LỌT**, tức báo cáo NGƯỢC sự thật (bài học cổng 54). Nên ở đây mọi neo tìm
    đều là **MỘT DÒNG**, và không khớp thì vào cột riêng.
 3. **Chạy ĐỐI CHỨNG trước.** Cổng đỏ sẵn thì mọi phép phá đều "BẮT" oan.
 4. **NEO PHẢI DUY NHẤT, VÀ BẢN ĐÃ PHÁ PHẢI CÒN BIÊN DỊCH ĐƯỢC.** Đây là bẫy
    lượt chạy đầu của chính file này đã sập: neo
    `except Exception as e:  # noqa: BLE001` có **12 chỗ** trong
    `giong_vieneu.py`, `replace(..., 1)` sửa nhằm chỗ ĐẦU TIÊN (một hàm khác)
    -> file **SyntaxError** -> cổng chết lúc `import` -> mã thoát 1 -> bảng
    ghi **BẮT**. Tức phép thử "bắt được" một chốt mà nó **chưa hề chạm tới**.
    Nay: neo trùng nhiều chỗ thì phải có `neo_sau` tách bạch, còn **không tách
    được là KHÔNG PHÁ ĐƯỢC**; và sau khi vá thì `compile()` lại — không biên
    dịch được cũng là **KHÔNG PHÁ ĐƯỢC**, không phải BẮT.

Chạy:  .venv\\Scripts\\python -u _pha_doc_lan.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
PY = str(REPO / ".venv" / "Scripts" / "python.exe")
CONG = REPO / "_test_doc_lan.py"

DL = REPO / "app" / "core" / "doc_lan.py"
GV = REPO / "app" / "core" / "giong_vieneu.py"
CB = REPO / "app" / "core" / "giong_chatter.py"
#: Bộ chấm của chính phép HIỆU CHUẨN. Nó không phải mã app, nhưng ngưỡng của
#: `doc_lan` sinh ra TỪ nó — bộ chấm hỏng thì bảng hiệu chuẩn tự ĐẠT OAN và
#: ngưỡng đặt ra từ một bảng số rỗng. Vì vậy nó cũng phải chịu được phép phá.
DVE = REPO / "_do_vieneu_en.py"
DAE = REPO / "_do_adam_en.py"

#: (nhãn, file, dòng CŨ, dòng MỚI, neo_sau). Neo MỘT DÒNG — xem luật 2 và 4.
#: `neo_sau` = một dòng DUY NHẤT nằm trong 3 dòng ngay sau chỗ cần vá, dùng để
#: tách bạch khi dòng `cu` trùng ở nhiều chỗ. Rỗng = đòi `cu` phải duy nhất.
PHEP: list[tuple[str, Path, str, str, str]] = [
    ("1. gỡ chốt CHỈ NHẬN KHI ĐỠ HƠN (nhận bừa mọi bản đọc lại)",
     GV,
     "                if l2 > 0 and l2 <= cu - DOC_LAI_BIEN:",
     "                if l2 > 0:", ""),
    ("2. gỡ TRẦN THEO LOẠT (đọc lại cả loạt, không giới hạn)",
     GV,
     "            nghi = nghi[:tran]",
     "            pass", ""),
    ("3. gỡ chốt MỐC GỐC (khớp lại mốc trên chính nhóm nghi ngờ)",
     GV,
     "                l2 = doc_lan.lan_vuot(chu[i], g2, moc[0], moc[1])",
     "                l2 = doc_lan.soi_loat([chu[i]], [g2])[0][0]", ""),
    ("4. gỡ chốt TẮT-VẪN-DÒ (tắt là câm luôn, mất cột đối chứng)",
     GV,
     "        if not bao[\"bat_co\"]:",
     "        if True:", ""),
    ("5. gỡ lưới KHÔNG-BAO-GIỜ-NÉM của lượt dò",
     GV,
     "    except Exception as e:  # noqa: BLE001",
     "    except ZeroDivisionError as e:",
     '        _ghi_log(f"Dò câu lan man hỏng ({type(e).__name__}: {e}) -> BỎ QUA, "'),
    ("6. gỡ SÀN của `lan_vuot` (chia thẳng cho ước lượng)",
     DL,
     "        return round(float(giay) / max(san_giay, uoc), 2)",
     "        return round(float(giay) / uoc, 2) if uoc > 0 else 0.0", ""),
    ("7. gỡ chốt ĐỦ MẪU của `moc_nhip`",
     DL,
     "        if len(pts) < TOI_THIEU_MUC:",
     "        if len(pts) < 2:", ""),
    ("8. gỡ chốt NHỊP-ÂM-LÀ-VÔ-NGHĨA (trong `moc_nhip`)",
     DL,
     "        if b <= 0:",
     "        if False:",
     "            return (0.0, 0.0)"),
    ("9. đổi Theil-Sen thành TRUNG BÌNH (điểm ngoại lai kéo được mốc)",
     DL,
     "        b = float(_st.median(doc))",
     "        b = float(sum(doc) / len(doc))", ""),
    ("10. `giong_chatter` chép lại công thức (đẻ bản sao thứ hai)",
     CB,
     "        lan = doc_lan.lan_vuot(text, giay, 0.0, 1.0 / LAN_MAN_CHU_MOI_GIAY)",
     "        lan = round(giay / max(0.35, n / LAN_MAN_CHU_MOI_GIAY), 2)", ""),
    # ─────────────────────────────────── nhóm ĐA NGÔN NGỮ (26/08, lượt 2)
    # LƯU Ý LUẬT 1: với một HẰNG SỐ ĐÃ HIỆU CHUẨN thì chính GIÁ TRỊ là cái
    # chốt, nên "gỡ chốt" ở đây = đặt nó XUỐNG DƯỚI mức hiệu chuẩn. Đây là
    # chiều LÀM LỎNG (trần bắt đầu kêu oan), không phải chiều làm chặt — nên
    # nó không dính bẫy "phá xong hàm lại chặt hơn" của cổng 80.
    ("11. hạ NGƯỠNG xuống dưới mức đã hiệu chuẩn (trần bắt đầu kêu oan)",
     DL, "NGUONG_LAN = 1.5", "NGUONG_LAN = 1.2", ""),
    ("12. bộ đếm từ của phép hiệu chuẩn quay về LATIN-ONLY (vứt chữ CJK)",
     DVE,
     "    return _tach_tu(_RAC_RE.sub(\" \", (s or \"\").lower()))",
     "    return re.sub(r\"[^0-9a-zà-ỹA-ZÀ-Ỹ\\\\s]\", \" \", (s or \"\").lower()).split()",
     ""),
    ("13. `dem_op` tự đẻ bộ chuẩn hoá thứ hai (bản sao lệch nhau)",
     DAE,
     "    a, b = DV.chuan_tu(goc), DV.chuan_tu(nghe)",
     "    a, b = (goc or \"\").lower().split(), (nghe or \"\").lower().split()",
     ""),
    ("14. chép ngược ghi cứng hai ngôn ngữ (ép whisper chép Trung bằng Việt)",
     DVE, "    ep = nn", "    ep = \"en\" if nn == \"en\" else \"vi\"", ""),
    ("15. gỡ ALL-OR-NOTHING (cho video lẫn hai giọng giữa chừng)",
     GV, "BO_LOAT_TU_SO_CAU = 3", "BO_LOAT_TU_SO_CAU = 99999", ""),
    ("15b. coi câu chỉ-dấu-câu là HỎNG (một dấu `-` giết cả giọng nhân bản)",
     GV,
     "        return not (_CHU_CO_AM.search(s) or _CHU_G2P_BO.search(s))",
     "        return False", ""),
    # ────────────────────── nhóm HỆ CHỮ NGOÀI TẦM PHIÊN ÂM (27/08, lượt 3)
    # Đây là chốt CHẶN, không phải chốt chấm điểm — phá nó thì hậu quả không
    # phải "bảng số xấu đi" mà là **video ra 17-21 giây lảm nhảm mỗi câu với
    # mã thoát 0** (ca tiếng Hàn, đo được ở `_kq_lan_nn.txt`).
    ("16. gỡ HẲN chốt chặn khỏi `_doc` (không hỏi bộ dò nữa)",
     GV,
     "    chan, ty = khong_doc_duoc([texts[i] for i in can])",
     "    chan, ty = (False, 0.0)", ""),
    # LUẬT 1 lần nữa: với hằng ĐÃ HIỆU CHUẨN thì GIÁ TRỊ là cái chốt. Ở đây
    # có HAI chiều hỏng và chúng NGƯỢC nhau, nên phải phá cả hai — phá một
    # chiều thì mục canh chiều kia vẫn xanh và bảng đọc thành "cổng có răng".
    # Đo nền: vi/en = 0,000 · zh 0,808 · ja 0,859 · ko 0,853 -> khoảng trống
    # 0,000-0,808 rất rộng, trần 0,5 nằm giữa.
    ("17. nới trần chữ-bị-xoá lên 0,9 (BỎ SÓT: tiếng Trung lọt qua chốt)",
     GV, "TY_LE_CHU_BO_TOI_DA = 0.5", "TY_LE_CHU_BO_TOI_DA = 0.9", ""),
    ("18. hạ trần chữ-bị-xoá về 0,0 (CHẶN OAN: câu Việt chen chữ Hán bị cấm)",
     GV, "TY_LE_CHU_BO_TOI_DA = 0.5", "TY_LE_CHU_BO_TOI_DA = 0.0", ""),
    # Đúng bẫy cổng 54 (`recap._CJK_CHARS` nuốt/để lọt hangul vì dán ký tự
    # thật vào dải regex), lần này ở chiều ĐỂ LỌT: mất hangul thì tiếng Hàn —
    # ca DUY NHẤT không tự lùi edge — đi thẳng vào máy đọc.
    ("19. bỏ HANGUL khỏi bộ dò hệ chữ (ca Hàn lọt: 17-21 giây lảm nhảm)",
     GV,
     "    \"가-힣ᄀ-ᇿ]\"          # hangul (âm tiết + jamo)",
     "    \"]\"", ""),
    # Núm ngưỡng-theo-tiếng mà không ĐỌC bảng thì nó là đồ trang trí: lượt
    # hiệu chuẩn sau thêm một dòng vào bảng và tưởng đã đổi được ngưỡng.
    ("20. `nguong_cho` bỏ qua bảng theo tiếng (núm thành đồ trang trí)",
     DL,
     "        return float(NGUONG_THEO_NN.get(khoa, NGUONG_LAN))",
     "        return float(NGUONG_LAN)", ""),
]


def _va(than: str, cu: str, moi: str, neo_sau: str) -> tuple[str, str]:
    """Vá ĐÚNG MỘT chỗ. Trả `(thân mới, lý do chịu)` — lý do rỗng = vá được."""
    dong = than.split("\n")
    ung = [i for i, d in enumerate(dong) if d.rstrip("\r") == cu]
    if neo_sau:
        ung = [i for i in ung
               if any(d.rstrip("\r") == neo_sau
                      for d in dong[i + 1:i + 4])]
    if not ung:
        return than, "không tìm thấy neo"
    if len(ung) > 1:
        return than, f"neo TRÙNG {len(ung)} chỗ (thiếu `neo_sau` tách bạch)"
    xuong = "\r" if dong[ung[0]].endswith("\r") else ""
    dong[ung[0]] = moi + xuong
    return "\n".join(dong), ""


def chay() -> tuple[int, int, int, str]:
    r = subprocess.run([PY, "-u", str(CONG)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(REPO))
    dat = hong = -1
    for d in (r.stdout or "").splitlines():
        if d.startswith("KETQUA:"):
            try:
                dat = int(d.split("ĐẠT")[1].split("·")[0].strip())
                hong = int(d.split("HỎNG")[1].strip())
            except Exception:                                   # noqa: BLE001
                pass
    muc = [d.strip()[2:] for d in (r.stdout or "").splitlines()
           if d.strip().startswith("- ")]
    return r.returncode, dat, hong, " | ".join(muc[:4])


def main() -> int:
    print("=" * 78)
    print("THỬ PHÁ CỔNG 92 — DÒ CÂU LAN MAN RỒI ĐỌC LẠI")
    print("=" * 78)
    rc, dat, hong, _m = chay()
    print(f"ĐỐI CHỨNG (chưa phá): mã {rc} · ĐẠT {dat} · HỎNG {hong}")
    if rc != 0:
        print("DỪNG: cổng ĐÃ ĐỎ TRƯỚC KHI PHÁ -> mọi phép thử dưới đây vô "
              "nghĩa (mọi phép đều 'BẮT' oan).")
        return 2

    bat = lot = khong = 0
    for nhan, f, cu, moi, neo in PHEP:
        goc = f.read_bytes()
        than = goc.decode("utf-8")
        moi_than, chiu = _va(than, cu, moi, neo)
        if chiu:
            print(f"\n[{nhan}]\n  KHÔNG PHÁ ĐƯỢC — {chiu} (LỖI CỦA PHÉP THỬ, "
                  f"KHÔNG phải LỌT)")
            khong += 1
            continue
        try:
            compile(moi_than, str(f), "exec")
        except SyntaxError as e:
            # Luật 4: bản đã phá mà không biên dịch được thì cổng sẽ đỏ vì
            # `import` chết, KHÔNG phải vì chốt bị gỡ -> đó là BẮT OAN.
            print(f"\n[{nhan}]\n  KHÔNG PHÁ ĐƯỢC — bản đã phá KHÔNG BIÊN DỊCH "
                  f"ĐƯỢC ({e.lineno}: {e.msg}); cổng sẽ đỏ vì `import` chết "
                  f"chứ không vì chốt -> BẮT OAN, không tính")
            khong += 1
            continue
        try:
            f.write_bytes(moi_than.encode("utf-8"))
            rc2, dat2, hong2, muc = chay()
        finally:
            f.write_bytes(goc)
        if rc2 != 0:
            bat += 1
            print(f"\n[{nhan}]\n  BẮT — mã {rc2} · ĐẠT {dat2} · HỎNG {hong2}"
                  f"\n     {muc}")
        else:
            lot += 1
            print(f"\n[{nhan}]\n  **LỌT** — cổng vẫn XANH ({dat2} ĐẠT). Chốt "
                  f"này KHÔNG có mục nào canh.")

    print("\n" + "=" * 78)
    print(f"BẮT {bat} · LỌT {lot} · KHÔNG PHÁ ĐƯỢC {khong}")
    rc3, dat3, hong3, _ = chay()
    print(f"KIỂM LẠI sau khi trả nguyên: mã {rc3} · ĐẠT {dat3} · HỎNG {hong3}")
    return 0 if (lot == 0 and khong == 0 and rc3 == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
