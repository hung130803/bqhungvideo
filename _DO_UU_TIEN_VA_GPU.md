# 2 SỐ ĐO CÒN THIẾU cho VIỆC 0 (quá tải luồng) — 07/08/2026

> Viết riêng file này vì `ffmpeg_utils.py` đang được **một phiên khác sửa cùng
> lúc** (ghi lúc 20:58, đúng lúc tôi đang đo). KHÔNG sửa file đó ở đây để khỏi
> đè mất việc của nhau. Bản vá tương ứng nằm ở `_va_uu_tien_hwdec.patch`
> (`git apply _va_uu_tien_hwdec.patch`) — **nhưng nó dựa trên bản `main`, phải
> gộp tay vào bản đang làm dở.**

Việc chặn luồng (`decode_threads` / `-filter_threads` / `-threads` nhánh nvenc)
phiên kia đã làm và đo kỹ hơn tôi — **không đụng vào**. Dưới đây là 2 chỗ phiên
kia CHƯA đụng, mỗi chỗ đều đã đo trên video thật của anh Hùng.

---

## 1. ĐỘ ƯU TIÊN TIẾN TRÌNH — chỗ rẻ nhất, lãi lớn nhất

`_run()` spawn ffmpeg với `_IDLE_PRIORITY = 0x40` (IDLE_PRIORITY_CLASS — mức
**thấp nhất** Windows có), ý tốt là "nhường máy cho anh Hùng dùng". **Đo ra thì
nó phản tác dụng.**

CÙNG 1 lệnh dựng khung 60s (1080p → 1080x1920, nền mờ + đốt .ass, NVENC),
**đan xen 4 vòng** lấy trung vị (`_do_uu_tien2.py`):

| mức ưu tiên | CPU-giây | giây tường |
|---|---|---|
| idle *(app đang dùng)* | 50,8 | 11,2 |
| dưới trung bình | 50,4 | 11,1 |
| **trung bình** | **34,4** | **7,0** |

**−32% CPU-giây và −37% thời gian, chỉ đổi 1 hằng số.** Lặp 4/4 vòng đều thế.

**Vì sao ngược đời:** 1 lệnh xuất đẻ ~54 luồng. Ở ưu tiên thấp hơn MỌI thứ
khác, luồng đang **giữ khoá** bị Windows cắt ngang, 53 luồng còn lại quay vòng
chờ → đốt CPU không ra sản phẩm. Máy anh Hùng lúc nào cũng có prodown (yt-dlp)
+ Defender chạy ở ưu tiên thường nên ffmpeg bị bỏ đói **liên tục**.

Chú ý: `dưới trung bình` KHÔNG ăn thua (50,4 ≈ 50,8) — vách ngăn nằm đúng ở
mức *trung bình*. Nửa vời không có tác dụng.

> **Kết luận cho VIỆC 0:** cách "nhường máy" ĐÚNG là **dùng ít nhân hơn**
> (chặn luồng + semaphore số tiến trình — đúng hướng phiên kia đang làm), chứ
> không phải hạ ưu tiên. Hai cái này cộng lại mới đủ.

Bản vá: bảng `_PRIORITY_CLASS` + `_uu_tien_co()` đọc `BQ_FFMPEG_PRIORITY`
(mặc định `normal`, đặt `idle` để đối chứng lại hành vi cũ).

---

## 2. GIẢI MÃ BẰNG GPU (NVDEC) — chỉ ở PHA DỰNG KHUNG

`-hwaccel cuda` đặt **trước `-i`**. NVDEC là khối silicon riêng, không tranh
với NVENC.

| | CPU-giây | luồng |
|---|---|---|
| pha dựng khung, giải mã CPU | 49,8 | 54 |
| pha dựng khung, **giải mã GPU** | **41,4** | **32** |

**−17% CPU và −22 luồng.**

**NHƯNG Ở PHA TÁCH ĐOẠN THÌ NGƯỢC LẠI — đừng bật:** mỗi context CUDA đẻ ~20
luồng, mà pha đó chỉ giải mã 30 giây nên không bù lại được (1 đoạn 30s):

| pha tách đoạn | CPU-giây | luồng | giây |
|---|---|---|---|
| `-threads 4` | 5,4 | 49 | 1,7 |
| thêm `-hwaccel cuda` | 6,8 | **76** | 2,8 |

→ lỗ cả 3 mặt. Vì vậy `_dat_input_opts(..., hwdec=False)` cho `_build_seg`.

**An toàn máy nhân viên:** chỉ thêm cờ khi lượt này encode bằng `h264_nvenc`
(bằng chứng CUDA sống trên máy đó). Không NVIDIA → encoder là `libx264` →
**không thêm cờ nào, hành vi y như cũ**. Có `BQ_NO_HWDEC=1` để tắt.

---

## 3. KẾT QUẢ GỘP (đo đầu-cuối, chưa có phần chặn luồng của phiên kia)

`_do_luong_xuat.py`, 1 lượt xuất thật, 2 đoạn 60s, video thật, máy rảnh 4,7%:

| | bản `main` | + 2 vá trên | đổi |
|---|---|---|---|
| luồng ffmpeg đỉnh | 61 | 49 | −20% |
| **CPU-giây** | **64,5** | **27,8** | **−57%** |
| giây tường | 15,5 | 9,8 | −37% |
| NVENC dùng | 58,9% | 91,4% | GPU gánh thay CPU |
| tụt về libx264 | 0 lệnh | 0 lệnh | ✓ không rớt CPU |

10 làn song song trên bản `main` (mốc để phiên kia so): **374 luồng đỉnh ·
914,5 CPU-giây · 147,4s · độ trễ luồng chính p95 28,2ms**.

---

## 4. HAI THỨ ĐÃ THỬ VÀ **BÁC BỎ** — đừng mất công lại

### a) Bỏ pha tách file tạm bằng `inpoint/outpoint` của concat demuxer
Rẻ hơn thật (9,8 vs 12,5 CPU-giây, **0 MB rác đĩa** thay vì 66 MB) **nhưng CẮT
SAI CHỖ**: `inpoint` bám keyframe chứ không đúng khung.

- độ dài ra **41,63s** thay vì 40,0s
- khung đầu mỗi đoạn lệch **12,4 và 72,7** (thang 0-255) so với video gốc;
  bản 2 pha lệch 0,26 và 0,31

Phụ đề `.ass` và mốc tiếng động dựng theo mốc đoạn → lệch hết. **Giữ 2 pha.**
Bộ đo: `_do_mot_pha.py` (chạy lại được, có sẵn ca hook-first ngược thời gian).

### b) Giới hạn phiên NVENC vì sợ card GeForce chặn
**Không phải vấn đề trên máy anh Hùng**: RTX 3060 driver 610.62 mở **≥12 phiên
encode song song** không lỗi (`_do_nvenc_phien.py`).
Vẫn nên giữ semaphore vì lý do CPU/luồng, không phải vì GPU.
⚠ Máy nhân viên driver cũ (< 2023) có thể còn giới hạn 3-5 phiên → lúc đó
`_run_with_fallback` sẽ tụt libx264 **và có thể ghi cache tắt GPU 7 ngày**
(`_looks_nvenc_env_failure`). Nếu bật nhiều làn cho máy nhân viên thì phải
chạy `_do_nvenc_phien.py` trên máy đó trước.

---

## 5. BỘ ĐO ĐỂ LẠI (chạy lại được, không đụng dữ liệu thật)

| file | dùng để |
|---|---|
| `_do_luong_xuat.py` | đo 1 lượt xuất THẬT: luồng/CPU-giây theo pha, NVENC%, độ trễ luồng chính, có `--lanes N` |
| `_do_pha_xuat.py` | mổ xẻ: bóc từng lớp filter để biết CPU tiêu vào đâu |
| `_do_uu_tien2.py` | chốt câu hỏi ưu tiên (đan xen, chống nhiễu) |
| `_do_quet_luong.py` | quét số luồng filter 1/2/4/8/16 |
| `_do_mot_pha.py` | thử bỏ pha tách (đã bác bỏ, giữ để khỏi thử lại) |
| `_do_nvenc_phien.py` | đếm giới hạn phiên NVENC của máy |

**Bài học về CÁCH ĐO** (đã sập 2 lần trong buổi này):
1. **Phải đan xen.** Đo liền mạch từng biến thể cho ra `idle 53,1 vs thường
   34,2` rồi lượt sau ra `−1%`. Máy có prodown chạy nền, trôi tải theo giờ.
   Đan xen A,B,C – A,B,C rồi lấy trung vị mới tin được.
2. **CPU-giây phải lấy qua handle `GetProcessTimes`**, không lấy mẫu psutil:
   nhịp cuối cách lúc tiến trình chết tới 100ms × 24 nhân = hụt tới 2,4
   CPU-giây mỗi tiến trình.
