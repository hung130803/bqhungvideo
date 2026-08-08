/* ===================================================================
 * CHUYỂN CẢNH CHẠY TRÊN GPU — kernel OpenCL cho filter `xfade_opencl`
 * ===================================================================
 * Chuyển từ `gl-transitions` (https://github.com/gl-transitions/gl-transitions)
 * — GLSL, giấy phép **MIT**. Xem `NGUON_GIAY_PHEP.md` cùng thư mục.
 *
 * VÌ SAO CÓ FILE NÀY: máy anh Hùng đo được **CPU 96,7% mà GPU chỉ 11,3%**.
 * `xfade` thường tính trên CPU; `xfade_opencl` tính trên GPU -> thêm kiểu
 * chuyển cảnh mà KHÔNG lấy thêm CPU. Máy nào không có OpenCL thì app TỰ TẮT
 * nhóm này và dùng `xfade` CPU như cũ (KHÔNG nổ lỗi) — xem `hieu_ung_gpu.py`.
 *
 * === KHUÔN CHỮ KÝ ffmpeg BẮT BUỘC (sai 1 chữ là "Failed to build program") ===
 *   __kernel void <tên>(__write_only image2d_t dst,
 *                       __read_only  image2d_t src1,   // ảnh ĐI (from)
 *                       __read_only  image2d_t src2,   // ảnh ĐẾN (to)
 *                       float progress)
 * `progress` của ffmpeg chạy **1 -> 0** (1 = đầu chỗ nối). gl-transitions dùng
 * quy ước NGƯỢC (0 -> 1), nên mọi kernel dưới đây mở đầu bằng
 * `float pr = 1.0f - progress;` rồi mới dùng đúng công thức gốc.
 * ĐÃ ĐO chiều bằng ca `kiem_chieu` của `_do_gpu_chuyen_canh.py`, không đoán.
 *
 * `getFromColor(uv)` -> `g(src1, uv, dim)` · `getToColor(uv)` -> `g(src2, uv, dim)`
 * Trục y của ảnh OpenCL đi TỪ TRÊN XUỐNG (video), còn GLSL đi từ dưới lên ->
 * hướng "lên/xuống" đảo so với tên gốc. Tên tiếng Việt trong `hieu_ung_gpu.py`
 * ghi theo cái MẮT THẤY (đã xem khung render), không theo tên gốc.
 */

__constant sampler_t SP = CLK_NORMALIZED_COORDS_FALSE |
                          CLK_FILTER_NEAREST |
                          CLK_ADDRESS_CLAMP_TO_EDGE;

/* đọc 1 điểm theo toạ độ chuẩn hoá 0..1 (kẹp biên -> không ra ngoài ảnh) */
float4 g(__read_only image2d_t im, float2 uv, int2 dim)
{
    int2 q = (int2)(clamp((int)(uv.x * (float)dim.x), 0, dim.x - 1),
                    clamp((int)(uv.y * (float)dim.y), 0, dim.y - 1));
    return read_imagef(im, SP, q);
}

/* smoothstep KIỂU GLSL: gl-transitions gọi cả với e0 > e1 (vd
 * smoothstep(0.0,-size,x)); `smoothstep` của OpenCL nói rõ e0>=e1 là KHÔNG
 * XÁC ĐỊNH -> phải tự viết, không thì kernel chạy đúng trên máy này mà sai
 * trên GPU khác. */
float ss(float e0, float e1, float x)
{
    float t = clamp((x - e0) / (e1 - e0), 0.0f, 1.0f);
    return t * t * (3.0f - 2.0f * t);
}

/* `fract` của OpenCL nhận CON TRỎ (khác GLSL) -> tự viết cho khỏi lẫn */
float  fr1(float  x) { return x - floor(x); }
float2 fr2(float2 v) { return v - floor(v); }

float rnd(float2 co)
{
    float t = sin(co.x * 12.9898f + co.y * 78.233f) * 43758.5453f;
    return t - floor(t);
}

#define VAO  int2 dim = get_image_dim(dst);                       \
             int2 ip  = (int2)(get_global_id(0), get_global_id(1)); \
             if (ip.x >= dim.x || ip.y >= dim.y) return;          \
             float2 uv = (float2)(((float)ip.x + 0.5f) / (float)dim.x, \
                                  ((float)ip.y + 0.5f) / (float)dim.y); \
             float pr = 1.0f - progress;

/* ------------------------------------------------------------------ */
/* 01 crosswarp — 2 hình MÉO ĐẨY vào nhau (Eke Péter, MIT)            */
__kernel void gl_crosswarp(__write_only image2d_t dst,
                           __read_only image2d_t src1,
                           __read_only image2d_t src2, float progress)
{
    VAO
    float x = ss(0.0f, 1.0f, pr * 2.0f + uv.x - 1.0f);
    float4 a = g(src1, (uv - 0.5f) * (1.0f - x) + 0.5f, dim);
    float4 b = g(src2, (uv - 0.5f) * x + 0.5f, dim);
    write_imagef(dst, ip, mix(a, b, x));
}

/* 02 directional — GẠT MỀM sang trái (gre, MIT)
 *    LỖI ĐÃ SỬA (đo 08/08/2026): bản đầu viết hằng số ngưỡng là `-0.5f`, tức
 *    lấy `d = 0`. Công thức gốc là `d - 0.5` với `d = v.x*0.5 + v.y*0.5`; với
 *    hướng (-1,0) thì `v = (-1,0)` nên `d = -0.5` -> ngưỡng đúng là **-1.0f**.
 *    Lệch nửa màn hình làm chuyển cảnh XONG ngay giữa chừng: đo khung giữa
 *    "khác đoạn B" chỉ **2,4%** (đúng = ~19%). `gl_gat_len` dính y hệt (1,3%).  */
__kernel void gl_gat_trai(__write_only image2d_t dst,
                          __read_only image2d_t src1,
                          __read_only image2d_t src2, float progress)
{
    VAO
    float m = ss(-0.5f, 0.0f, -uv.x - (-1.0f + pr * 1.5f));
    write_imagef(dst, ip, mix(g(src1, uv, dim), g(src2, uv, dim), 1.0f - m));
}

/* 03 directional — GẠT MỀM lên trên (cùng lỗi `d`, xem 02)            */
__kernel void gl_gat_len(__write_only image2d_t dst,
                         __read_only image2d_t src1,
                         __read_only image2d_t src2, float progress)
{
    VAO
    float m = ss(-0.5f, 0.0f, -uv.y - (-1.0f + pr * 1.5f));
    write_imagef(dst, ip, mix(g(src1, uv, dim), g(src2, uv, dim), 1.0f - m));
}

/* 04 directionalwarp — gạt chéo CÓ MÉO (pschroen, MIT)                */
__kernel void gl_gat_cheo_meo(__write_only image2d_t dst,
                              __read_only image2d_t src1,
                              __read_only image2d_t src2, float progress)
{
    VAO
    float2 v = (float2)(-0.5f, 0.5f);
    float d = v.x * 0.5f + v.y * 0.5f;
    float m = 1.0f - ss(-0.5f, 0.0f,
                        v.x * uv.x + v.y * uv.y - (d - 0.5f + pr * 1.5f));
    float4 a = g(src1, (uv - 0.5f) * (1.0f - m) + 0.5f, dim);
    float4 b = g(src2, (uv - 0.5f) * m + 0.5f, dim);
    write_imagef(dst, ip, mix(a, b, m));
}

/* 05 wind — GIÓ THỔI dạng vệt ngang (gre, MIT)                        */
__kernel void gl_gio(__write_only image2d_t dst,
                     __read_only image2d_t src1,
                     __read_only image2d_t src2, float progress)
{
    VAO
    float size = 0.2f;
    float r = rnd((float2)(0.0f, uv.y));
    float m = ss(0.0f, -size, uv.x * (1.0f - size) + size * r
                              - (pr * (1.0f + size)));
    write_imagef(dst, ip, mix(g(src1, uv, dim), g(src2, uv, dim), m));
}

/* 06 ripple — GỢN SÓNG lan từ giữa (gre, MIT)                         */
__kernel void gl_gon_song(__write_only image2d_t dst,
                          __read_only image2d_t src1,
                          __read_only image2d_t src2, float progress)
{
    VAO
    float2 dir = uv - 0.5f;
    float di = length(dir);
    float2 off = dir * (sin(pr * di * 100.0f - pr * 50.0f) + 0.5f) / 30.0f;
    write_imagef(dst, ip, mix(g(src1, uv + off, dim), g(src2, uv, dim),
                              ss(0.2f, 1.0f, pr)));
}

/* 07 pixelize — VỠ Ô rồi hiện lại (gre, MIT)                          */
__kernel void gl_vo_o(__write_only image2d_t dst,
                      __read_only image2d_t src1,
                      __read_only image2d_t src2, float progress)
{
    VAO
    float d = min(pr, 1.0f - pr);
    float di = ceil(d * 50.0f) / 50.0f;
    float2 sq = 2.0f * di / (float2)(20.0f, 20.0f);
    float2 p = di > 0.0f ? (floor(uv / sq) + 0.5f) * sq : uv;
    write_imagef(dst, ip, mix(g(src1, p, dim), g(src2, p, dim), pr));
}

/* 08 squareswire — LƯỚI Ô VUÔNG quét chéo (gre, MIT)                  */
__kernel void gl_luoi_vuong(__write_only image2d_t dst,
                            __read_only image2d_t src1,
                            __read_only image2d_t src2, float progress)
{
    VAO
    float2 v = (float2)(1.0f, -0.5f);
    v /= (fabs(v.x) + fabs(v.y));
    float d = v.x * 0.5f + v.y * 0.5f;
    float off = 1.6f;
    float p2 = ss(-off, 0.0f,
                  v.x * uv.x + v.y * uv.y - (d - 0.5f + pr * (1.0f + off)));
    float2 sp = fr2(uv * (float2)(10.0f, 10.0f));
    float lo = p2 / 2.0f, hi = 1.0f - p2 / 2.0f;
    float a = (1.0f - step(pr, 0.0f)) * step(lo, sp.x) * step(lo, sp.y)
              * step(sp.x, hi) * step(sp.y, hi);
    write_imagef(dst, ip, mix(g(src1, uv, dim), g(src2, uv, dim), a));
}

/* 09 radial — QUẠT QUAY quét vòng (Xaychru, MIT)                      */
__kernel void gl_quat_quay(__write_only image2d_t dst,
                           __read_only image2d_t src1,
                           __read_only image2d_t src2, float progress)
{
    VAO
    float2 rp = uv * 2.0f - 1.0f;
    float m = ss(0.0f, 1.0f, atan2(rp.y, rp.x) - (pr - 0.5f) * 3.14159265f * 2.5f);
    write_imagef(dst, ip, mix(g(src2, uv, dim), g(src1, uv, dim), m));
}

/* 10 polkadotscurtain — RÈM ĐỐM TRÒN nở ra (bobylito, MIT)            */
__kernel void gl_dom_tron(__write_only image2d_t dst,
                          __read_only image2d_t src1,
                          __read_only image2d_t src2, float progress)
{
    VAO
    float dd = distance(fr2(uv * 20.0f), (float2)(0.5f, 0.5f));
    float k = pr / max(1e-4f, distance(uv, (float2)(0.0f, 0.0f)));
    write_imagef(dst, ip, dd < k ? g(src2, uv, dim) : g(src1, uv, dim));
}

/* 11 simplezoom — HÚT VÀO GIỮA rồi hiện cảnh sau (0gust1, MIT)        */
__kernel void gl_hut_giua(__write_only image2d_t dst,
                          __read_only image2d_t src1,
                          __read_only image2d_t src2, float progress)
{
    VAO
    float q = 0.8f;
    float am = ss(0.0f, q, pr);
    float2 z = 0.5f + ((uv - 0.5f) * (1.0f - am));
    write_imagef(dst, ip, mix(g(src1, z, dim), g(src2, uv, dim),
                              ss(q - 0.2f, 1.0f, pr)));
}

/* 12 crosshatch — GẠCH CHÉO lấp dần (pthrasher, MIT)                  */
__kernel void gl_gach_cheo(__write_only image2d_t dst,
                           __read_only image2d_t src1,
                           __read_only image2d_t src2, float progress)
{
    VAO
    float di = distance((float2)(0.5f, 0.5f), uv) / 3.0f;
    float r = pr - min(rnd((float2)(uv.y, 0.0f)), rnd((float2)(0.0f, uv.x)));
    float m = mix(0.0f, mix(step(di, r), 1.0f, ss(0.9f, 1.0f, pr)),
                  ss(0.0f, 0.1f, pr));
    write_imagef(dst, ip, mix(g(src1, uv, dim), g(src2, uv, dim), m));
}

/* 13 linearblur — NHOÈ MỜ rồi rõ lại (gre, MIT) — 72 lượt đọc/điểm,
 *    đúng loại việc GPU làm rẻ mà CPU làm đắt.                        */
__kernel void gl_nhoe_mo(__write_only image2d_t dst,
                         __read_only image2d_t src1,
                         __read_only image2d_t src2, float progress)
{
    VAO
    float4 c1 = (float4)(0.0f), c2 = (float4)(0.0f);
    float disp = 0.1f * (0.5f - distance(0.5f, pr));
    for (int xi = 0; xi < 6; xi++) {
        float x = (float)xi / 6.0f - 0.5f;
        for (int yi = 0; yi < 6; yi++) {
            float y = (float)yi / 6.0f - 0.5f;
            float2 v = (float2)(x, y) * disp;
            c1 += g(src1, uv + v, dim);
            c2 += g(src2, uv + v, dim);
        }
    }
    write_imagef(dst, ip, mix(c1 / 36.0f, c2 / 36.0f, pr));
}

/* 14 swirl — XOÁY TRÒN (Sergey Kosarevsky, MIT)                       */
__kernel void gl_xoay_tron(__write_only image2d_t dst,
                           __read_only image2d_t src1,
                           __read_only image2d_t src2, float progress)
{
    VAO
    float2 c = uv - 0.5f;
    float di = length(c);
    if (di < 1.0f) {
        float pc = (1.0f - di);
        float A = (pr <= 0.5f) ? mix(0.0f, 1.0f, pr / 0.5f)
                               : mix(1.0f, 0.0f, (pr - 0.5f) / 0.5f);
        float th = pc * pc * A * 8.0f * 3.14159265f;
        float s = sin(th), co = cos(th);
        c = (float2)(c.x * co - c.y * s, c.x * s + c.y * co);
    }
    c += 0.5f;
    write_imagef(dst, ip, mix(g(src1, c, dim), g(src2, c, dim), pr));
}

/* 15 morph — BIẾN HÌNH theo độ sáng 2 khung (paniq, MIT)              */
__kernel void gl_bien_hinh(__write_only image2d_t dst,
                           __read_only image2d_t src1,
                           __read_only image2d_t src2, float progress)
{
    VAO
    float4 ca = g(src1, uv, dim), cb = g(src2, uv, dim);
    float2 oa = ((ca.xy + ca.z) * 0.5f) * 2.0f - 1.0f;
    float2 ob = ((cb.xy + cb.z) * 0.5f) * 2.0f - 1.0f;
    float2 oc = mix(oa, ob, 0.5f) * 0.1f;
    write_imagef(dst, ip, mix(g(src1, uv + oc * pr, dim),
                              g(src2, uv - oc * (1.0f - pr), dim), pr));
}

/* 16 windowslice — LƯỢC SỌC DỌC (gre, MIT)                            */
__kernel void gl_soc_doc(__write_only image2d_t dst,
                         __read_only image2d_t src1,
                         __read_only image2d_t src2, float progress)
{
    VAO
    float p2 = ss(-0.5f, 0.0f, uv.x - pr * 1.5f);
    float s = step(p2, fr1(10.0f * uv.x));
    write_imagef(dst, ip, mix(g(src1, uv, dim), g(src2, uv, dim), s));
}

/* 17 randomsquares — Ô VUÔNG NGẪU NHIÊN lật dần (gre, MIT)            */
__kernel void gl_o_ngau(__write_only image2d_t dst,
                        __read_only image2d_t src1,
                        __read_only image2d_t src2, float progress)
{
    VAO
    float r = rnd(floor((float2)(10.0f, 10.0f) * uv));
    float m = ss(0.0f, -0.5f, r - (pr * 1.5f));
    write_imagef(dst, ip, mix(g(src1, uv, dim), g(src2, uv, dim), m));
}

/* 18 waterdrop — GIỌT NƯỚC rơi giữa khung (Paweł Płóciennik, MIT)     */
__kernel void gl_giot_nuoc(__write_only image2d_t dst,
                           __read_only image2d_t src1,
                           __read_only image2d_t src2, float progress)
{
    VAO
    float2 dir = uv - 0.5f;
    float di = length(dir);
    float4 o;
    if (di > pr)
        o = mix(g(src1, uv, dim), g(src2, uv, dim), pr);
    else {
        float2 off = dir * sin(di * 30.0f - pr * 30.0f);
        o = mix(g(src1, uv + off, dim), g(src2, uv, dim), pr);
    }
    write_imagef(dst, ip, o);
}

/* 19 angular — KIM ĐỒNG HỒ quét (Fernando Kuteken, MIT)               */
__kernel void gl_kim_dong_ho(__write_only image2d_t dst,
                             __read_only image2d_t src1,
                             __read_only image2d_t src2, float progress)
{
    VAO
    float PI = 3.14159265f;
    float an = atan2(uv.y - 0.5f, uv.x - 0.5f) + PI / 2.0f;
    float na = (an + PI) / (2.0f * PI);
    na = na - floor(na);
    write_imagef(dst, ip, mix(g(src1, uv, dim), g(src2, uv, dim),
                              step(na, pr)));
}

/* 20 circleopen — VÒNG TRÒN mở ra giữa khung (gre, MIT)               */
__kernel void gl_vong_mo(__write_only image2d_t dst,
                         __read_only image2d_t src1,
                         __read_only image2d_t src2, float progress)
{
    VAO
    float m = ss(-0.3f, 0.0f,
                 1.41421356f * distance((float2)(0.5f, 0.5f), uv)
                 - pr * 1.3f);
    write_imagef(dst, ip, mix(g(src1, uv, dim), g(src2, uv, dim), 1.0f - m));
}

/* 21 pinwheel — CHONG CHÓNG quay (Mr Speaker, MIT)                    */
__kernel void gl_chong_chong(__write_only image2d_t dst,
                             __read_only image2d_t src1,
                             __read_only image2d_t src2, float progress)
{
    VAO
    float cp = atan2(uv.y - 0.5f, uv.x - 0.5f) + pr * 2.0f;
    float mp = cp - floor(cp / (3.1415f / 4.0f)) * (3.1415f / 4.0f);
    float sg = sign(pr - mp);
    write_imagef(dst, ip, mix(g(src2, uv, dim), g(src1, uv, dim),
                              step(sg, 0.5f)));
}

/* 22 dreamy — TRÔI MỀM như mơ (mikolalysenko, MIT)                    */
__kernel void gl_troi_mem(__write_only image2d_t dst,
                          __read_only image2d_t src1,
                          __read_only image2d_t src2, float progress)
{
    VAO
    float s1 = 0.03f * pr * cos(10.0f * (pr + uv.x));
    float q = 1.0f - pr;
    float s2 = 0.03f * q * cos(10.0f * (q + uv.x));
    write_imagef(dst, ip, mix(g(src1, uv + (float2)(0.0f, s1), dim),
                              g(src2, uv + (float2)(0.0f, s2), dim), pr));
}

/* 23 multiply_blend — CHỒNG TỐI (nhân 2 khung) (Fernando Kuteken, MIT) */
__kernel void gl_chong_toi(__write_only image2d_t dst,
                           __read_only image2d_t src1,
                           __read_only image2d_t src2, float progress)
{
    VAO
    float4 a = g(src1, uv, dim), b = g(src2, uv, dim);
    float4 bl = a * b;
    write_imagef(dst, ip, pr < 0.5f ? mix(a, bl, 2.0f * pr)
                                    : mix(bl, b, 2.0f * pr - 1.0f));
}

/* 24 glitchmemories — GIẬT KHỐI kiểu băng lỗi (Gunnar Roth, MIT).
 *    Bản gốc tính `floor(p/16)` với p là 0..1 nên LUÔN ra 0 (khối biến mất);
 *    ở đây dùng TOẠ ĐỘ PIXEL để ra đúng khối 16 px như tên gọi.          */
__kernel void gl_giat_khoi(__write_only image2d_t dst,
                           __read_only image2d_t src1,
                           __read_only image2d_t src2, float progress)
{
    VAO
    float2 blk = floor((float2)((float)ip.x, (float)ip.y) / 16.0f);
    float2 un = blk / 64.0f
                + floor((float2)(pr, pr) * (float2)(1200.0f, 3500.0f)) / 64.0f;
    float2 d = pr > 0.0f ? (fr2(un) - 0.5f) * 0.3f * (1.0f - pr)
                         : (float2)(0.0f, 0.0f);
    float2 r = uv + d * 0.2f, gg = uv + d * 0.3f, b = uv + d * 0.5f;
    write_imagef(dst, ip, (float4)(
        mix(g(src1, r, dim), g(src2, r, dim), pr).x,
        mix(g(src1, gg, dim), g(src2, gg, dim), pr).y,
        mix(g(src1, b, dim), g(src2, b, dim), pr).z, 1.0f));
}

/* CA KIỂM CHIỀU — KHÔNG phải hiệu ứng: nửa trên = ảnh ĐI, nửa dưới = ảnh ĐẾN
 * khi progress=1. Dùng để CHỨNG MINH chiều `progress` chứ không đoán.        */
__kernel void kiem_chieu(__write_only image2d_t dst,
                         __read_only image2d_t src1,
                         __read_only image2d_t src2, float progress)
{
    VAO
    write_imagef(dst, ip, progress > 0.5f ? g(src1, uv, dim)
                                          : g(src2, uv, dim));
}
