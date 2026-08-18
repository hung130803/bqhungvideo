# LƯỢT 10 — THỬ TAY NỐT 18 BỘ CỦA LƯỢT 9

*Ngày 18/08/2026. Lượt thứ 10. Lượt 9 (`GIONG_QUET_CUOI.md`) tìm được 18 bộ
mới nhưng **17/18 chưa thử tay** vì máy chủ dùng thử ZeroGPU của Hugging Face
chặn sau 2 câu. Lượt này **không đi tìm bộ mới** — chỉ đo nốt.*

**KHÔNG sửa một file nào trong `app/`. Không tăng version, không tag, không
push. Không đẻ một luồng con nào.**

---

## 0. ĐƯỜNG SPACE ĐÃ ĐÓNG HẲN — ĐO LẠI ĐỂ CHẮC

Việc đầu tiên là thử lại đúng cái cửa lượt 9 bị chặn. Máy chủ trả nguyên văn:

> `❌ Lỗi khi suy luận: 'You have exceeded your ZeroGPU runs limit.
> Authenticate with a Hugging Face token for more quota'`

Space **vẫn sống** (hỏi được bảng tham số, thấy đủ 6 mục trong ô chọn giọng),
chỉ là **hết hạn mức tính toán**. Muốn chạy tiếp phải đăng nhập bằng tài khoản
Hugging Face của anh Hùng — **tôi không đi tìm/dùng chìa khoá của anh**.

→ Nên toàn bộ lượt này **chạy TẠI MÁY** (tải trọng số về, RTX 3060), đúng như
đề bài dặn.

**Một điều lượt 9 ghi thiếu, đọc bảng tham số của Space mới thấy:** ô chọn
giọng của Kani-TTS-Vie có **6 mục** chứ không phải 3 —
`Khoa – Nam miền Bắc` · `Hùng – Nam miền Nam` · `Trinh – Nữ miền Nam` ·
**`David – English (British)`** · **`Katie – English (Irish)`** ·
`Không chỉ định`. Tức nó có **giọng tiếng Anh riêng**, đúng thứ anh Hùng hỏi
("cho cả tiếng Anh với tiếng Việt"). Thẻ model còn kể thêm một danh sách giọng
"cross-lingual" (Puck, Kore, Andrew, Seulgi, Maria, Mei…) — **phải đo xem có
thật không**, không đọc quảng cáo rồi chép vào bảng.

---

## 1. ARM ĐỐI CHỨNG edge-tts — CHẠY LẠI TRÊN CHÍNH BỘ CÂU LƯỢT NÀY

**Không chép số cũ.** Lượt 9 đã chứng minh thước đổi theo bộ câu (6,8% cũ đo
trên bản chép tự động có lỗi sẵn; bộ câu sạch cho edge-tts 0,0%). Bộ câu lượt
này: **8 câu tiếng Việt + 8 câu tiếng Anh** — 4 câu đầu mỗi thứ tiếng lấy
nguyên từ `_bo_cau_thu_doc.py` (loại `cau_thuong`, đã dùng ở việc "đọc sai chữ
nước ngoài"), 4 câu sau viết thêm cho đủ dài, kiểu câu kể chuyện.

### 1a. Sai từ / bịa chữ — mốc PHẢI VƯỢT

| edge-tts (ĐANG CHẠY) | sai từ | bịa chữ | số câu |
|---|---|---|---|
| **tiếng Việt** (HoaiMy + NamMinh) | **5,2%** | **0,0%** | 8/8 |
| **tiếng Anh** (Aria + Andrew) | **0,0%** | **0,0%** | 8/8 |

Hai lỗi đọc thật của tiếng Việt, ghi ra để biết thước còn răng:
*"cô gái **mỉm** cười"* → máy nghe ra *"**miễn** cười"* (8,3%) ·
*"Tiếng **chuông** vang lên giữa đêm **khuya làm cả xóm** thức giấc"* →
*"Tiếng **chung** vang lên giữa đêm **khuy lầm cả sóng** thức giấc"* (33,3%).

> ⚠ **ĐỪNG so 5,2% này với "0,0%" của lượt 9.** Lượt 9 chỉ dùng 4 câu ngắn;
> lượt này thêm 4 câu dài hơn nên thước khó hơn. Cách đọc đúng là so **trong
> cùng bảng** — mọi bộ ở dưới đều chạy trên ĐÚNG 8 câu này.

### 1b. Nhấn nhá — dựng lại mốc "trải 3,31" trên chính câu lượt này

| | số giọng | f0_std thấp nhất – cao nhất | **TRẢI** |
|---|---|---|---|
| **edge-tts en-US** | **17** | 2,20 – 5,35 | **3,15** |
| edge-tts vi | 2 | 3,38 – 3,74 | 0,36 |

Mốc lượt 5 ghi **3,31** (2,38–5,69) trên một câu tiếng Anh KHÁC. Đo lại hôm
nay ra **3,15** — **hai phép đo độc lập gặp nhau trong 0,16 nửa cung**, tức
thước đứng vững và mốc dùng được. Từ đây lấy **3,15** làm mốc so (cùng câu,
cùng lượt), và ghi kèm 3,31 để nối với lượt cũ.

Giọng trải rộng nhất: `en-US-Andrew` **5,35** · hẹp nhất `en-US-Ana` **2,20`.

---

*(còn tiếp — các bộ đo tiếp theo ghi bên dưới, mỗi bộ xong là commit)*
