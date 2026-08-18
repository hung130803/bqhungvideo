# LƯỢT 11 — VieNeu-TTS **v3.2.8**: 20 GIỌNG DỰNG SẴN CÓ THẬT KHÔNG?

*Ngày 19/08/2026. Anh Hùng gửi `github.com/pnnbao97/VieNeu-TTS` và nói nó vừa
cập nhật 1-2 tiếng trước:*

- *`v3.2.8`: thêm giọng tiếng Anh **Adam** (**20 preset voices**) — 1 giờ trước*
- *`v3.2.7`: sliding-window repetition penalty, **19 voices** — 2 giờ trước*

**Đây chính là bộ đã đo ở lượt 9 (`docs/GIONG_NHAN_BAN.md`), nhưng bản đó CHƯA
CÓ bộ giọng dựng sẵn** — lượt 9 chỉ đo được đường NHÂN BẢN (đưa mẫu 5 giây vào).
Bộ giọng dựng sẵn là thay đổi lớn, nên phải đo lại từ đầu.

**Không sửa một file nào trong `app/`. Không đẻ một luồng con nào. Không tăng
version, không tag, không push.**

> **Cách đọc:** nếu chỉ có 2 phút, đọc **PHẦN A** ở cuối. Các phần B–G là số đo
> để chứng minh.

---

# PHẦN G — Ý 6: GIẤY PHÉP *(viết trước vì nó là thứ chặn đường)*

## G1. Ba nguồn ĐỘC LẬP đều nói Apache-2.0 — phần MÃ và TRỌNG SỐ thì sạch

Tôi không đọc bài giới thiệu; tôi đọc từ máy chủ gốc:

| Đọc ở đâu | Cách đọc | Kết quả |
|---|---|---|
| **File `LICENSE` GỐC** trong kho GitHub | `raw.githubusercontent.com/.../main/LICENSE` | **Apache-2.0** — 11.357 byte, 169 dòng, đúng nguyên văn Apache 2.0 |
| **Thẻ GitHub tự nhận** | `api.github.com/repos/pnnbao97/VieNeu-TTS` | `spdx_id = Apache-2.0` |
| **Gói PyPI `vieneu`** | `pypi.org/pypi/vieneu/json` | classifier `License :: OSI Approved :: Apache Software License` |
| **TRỌNG SỐ** `pnnbao-ump/VieNeu-TTS-v3-Turbo` | API HuggingFace, thẻ `license:` | **`apache-2.0`**, `gated=False`, 355.117 lượt tải/tháng |
| **Bộ mã tiếng** `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX` | API HuggingFace | **`apache-2.0`**, không khoá |

**PyPI xác nhận bản mới nhất đúng là `3.2.8`** (71 bản, 5 bản cuối
`3.2.4 · 3.2.5 · 3.2.6 · 3.2.7 · 3.2.8`). Kho GitHub `pushed_at =
2026-08-18T15:44:06Z` — đúng "vừa cập nhật".

**Trọng số KHÔNG khác mã** ở lượt này — cả hai đều Apache-2.0. Đây là điều 10
lượt trước phải kiểm riêng vì đã bắt được 15 chỗ ghi sai; lần này nó khớp.

## G2. **NHƯNG BẢNG GIỌNG THÌ KHÔNG.** Đây là chỗ phải dừng lại đọc kỹ

Gói `vieneu` 3.2.8 chở **hai** bảng giọng, và chúng nói hai chuyện khác nhau:

| File trong gói | Số giọng | Trường `license` trong `meta` |
|---|---|---|
| `assets/voices.json` (bộ **v2**) | 6 | **`"CC BY-NC 4.0"`** |
| `assets/voices_v3_turbo.json` (bộ **v3 — 20 giọng đang hỏi**) | 20 | **KHÔNG CÓ TRƯỜNG NÀO** |

Nguyên văn `meta` của `voices.json`:

```json
{
  "spec": "vieneu.voice.presets",
  "engine": "VieNeu-TTS",
  "author": "Phạm Nguyễn Ngọc Bảo (pnnbao-ump)",
  "license": "CC BY-NC 4.0",
  "notice": "Model and voices are for non-commercial use only.
             Mention pnnbao-ump when using."
}
```

Nguyên văn `meta` của `voices_v3_turbo.json` — **toàn bộ, không cắt**:

```json
{ "note": "v3 turbo curated preset voices (named)", "count": 20 }
```

**Hai điều phải nói thẳng:**

1. **`CC BY-NC 4.0` là CẤM THƯƠNG MẠI.** Anh Hùng **bán/dùng app kiếm tiền**,
   nên với bộ 6 giọng v2 thì đây là **cửa đóng**, không phải chuyện nhỏ. Và câu
   `notice` còn nói rộng hơn cả bộ giọng: *"**Model** and voices are for
   non-commercial use only"* — tức nó **mâu thuẫn thẳng với file `LICENSE`
   Apache-2.0** của cùng kho.
2. **Bộ 20 giọng v3 KHÔNG khai giấy phép gì cả.** Theo đúng tiền lệ đã chốt
   trong repo này (giọng Piper `25hours_single` giấy phép *"Unknown"* →
   **im lặng KHÔNG phải là cho phép**), chỗ trống này **không được đọc thành
   Apache-2.0**. Nó chỉ là chỗ trống.

> **CHỐT Ý 6 (phần giấy phép):** **mã Apache-2.0 · trọng số Apache-2.0 — sạch.
> Nhưng BẢNG GIỌNG DỰNG SẴN thì bộ cũ ghi rõ CẤM THƯƠNG MẠI và bộ mới (20
> giọng) KHÔNG khai gì.** Đây là rủi ro pháp lý THẬT với người bán app, và nó
> nằm đúng ở thứ đang được hỏi. Phải hỏi thẳng tác giả trước khi dùng để kiếm
> tiền.

## G3. 20 giọng ấy tên gì — đọc từ chính file, không đọc thẻ model

`voices_v3_turbo.json`, `default_voice = "Phạm Tuyên"`. Mỗi mục chở **`speaker_emb`
192 chiều** + **`codes`** (39–76 khối mã tiếng) — tức mỗi "giọng dựng sẵn" thực
chất là **một mẫu nhân bản đã đóng gói sẵn**, đúng cơ chế lượt 9 đã đo.

| # | Tên | Giới | Vùng | Phong cách |
|---|---|---|---|---|
| 1 | Minh Đức | nam | Bắc | tin tức |
| 2 | **Phạm Tuyên** *(mặc định)* | nam | Bắc | tự nhiên |
| 3 | Thái Sơn | nam | Nam | kể chuyện |
| 4 | Xuân Vĩnh | nam | Nam | tự nhiên |
| 5 | Thanh Bình | nam | Bắc | kể chuyện |
| 6 | Trúc Ly | nữ | Bắc | tự nhiên |
| 7 | Ngọc Linh | nữ | Bắc | kể chuyện |
| 8 | Đoan Trang | nữ | Bắc | tự nhiên |
| 9 | Mai Anh | nữ | Bắc | tin tức |
| 10 | Thục Đoan | nữ | Nam | kể chuyện |
| 11 | Minh Triết | nam | Nam | tin tức |
| 12 | Thùy Dung | nữ | Nam | tin tức |
| 13 | Quang Sơn | nam | **Trung** | tự nhiên |
| 14 | Ngọc Trân | nữ | **Trung** | tự nhiên |
| 15 | Mỹ Duyên | nữ | Nam | đọc truyện |
| 16 | Quỳnh Anh | nữ | Bắc | đọc truyện |
| 17 | Đức Trí | nam | Nam | đọc truyện |
| 18 | Kim Thanh | nữ | Nam | đọc truyện |
| 19 | **Ngọc Huyền** | nữ | Bắc | tự nhiên |
| 20 | **Adam** | nam | **Tiếng Anh** | tự nhiên |

Theo thẻ tự khai: **19 giọng Việt + 1 giọng Anh**; 11 nữ / 9 nam; Bắc 9 · Nam 8
· Trung 2 · Anh 1.

**Hai cái tên phải để ý ngay:**
- **`Ngọc Huyền`** trùng tên với **`HN-Ngọc Huyền`** — một trong 3 giọng Vbee
  anh Hùng muốn mua (`docs/GIONG_CHOT.md`). Trùng tên **chưa chứng minh được
  gì** (Ngọc Huyền là tên phổ biến), nhưng nó là thứ phải đo chứ không được bỏ
  qua.
- **`Adam`** — xem phần G4.

*(Còn tiếp — các phần B, C, D, E, F và G4 ghi tiếp bên dưới khi đo xong.)*
