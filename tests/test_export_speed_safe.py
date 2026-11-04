"""Kiểm các tăng tốc AN TOÀN của đường xuất (26/10/2026).

zoompan chỉ chạy trong cửa sổ (file ra TRÙNG từng byte) · nhớ `do_nhip` ·
NVENC lỗi tạm thời thì thử lại · dùng lại probe · giải mã GPU tuỳ chọn.
"""
import os, sys, shutil, subprocess, tempfile, unittest
from pathlib import Path
from unittest import mock
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
AREA = Path(tempfile.mkdtemp(prefix='export-speed-'))
os.environ.update(BQ_DATA_DIR=str(AREA), BQ_DB_PATH=str(AREA / 'test.db'),
                  BQ_QSETTINGS_INI=str(AREA / 'settings.ini'), BQ_BO_MANG='1')
import _test_guard  # noqa: F401,E402
from app.core import ffmpeg_utils as F  # noqa: E402
from app.core import hieu_ung as H  # noqa: E402

FF = shutil.which('ffmpeg')
HU = [{'bat': 0.0, 'het': 0.30, 'khoa': 'luot_ngang', 'dam': .12},
      {'bat': 1.0, 'het': 1.35, 'khoa': 'xien_hinh', 'dam': .12},
      {'bat': 1.9, 'het': 2.5, 'khoa': 'rung_lac', 'dam': .12}]


def _chuoi(cu: bool, fps=30):
    with mock.patch.dict(os.environ, {'BQ_ZOOMPAN_CA_CLIP': '1' if cu else '0'}):
        return H.chuoi_filter(HU, 270, 480, fps)


class ZoompanCuaSo(unittest.TestCase):
    def test_chuoi_moi_cat_manh_va_co_duong_lui(self):
        moi, cu = _chuoi(False), _chuoi(True)
        self.assertTrue(cu.startswith('zoompan='))
        self.assertEqual(moi.count('concat=n=3:v=1:a=0,settb=1/30'), 3)
        self.assertIn('[zw0a]', moi); self.assertIn('[zw2a]', moi)   # nhãn không trùng
        self.assertIn(",shear=", moi)        # phần sau zoompan vẫn giữ nguyên
        self.assertEqual(cu.count('zoompan='), moi.count('zoompan='))

    def test_cua_so_muon_khung_lon_khong_cat_manh(self):
        # 27/10/2026: cửa sổ giây 14,3 · 60 fps · 1080x1920 -> ffmpeg 17,7 GB RAM.
        muon = [{'bat': 14.3, 'het': 14.68, 'khoa': 'luot_ngang', 'dam': .12}]
        som = [{'bat': 0.12, 'het': 0.5, 'khoa': 'luot_ngang', 'dam': .12}]
        with mock.patch.dict(os.environ, {'BQ_ZOOMPAN_CA_CLIP': '0'}):
            s_muon = H.chuoi_filter(muon, 1080, 1920, 60)
            s_som = H.chuoi_filter(som, 1080, 1920, 60)
        self.assertTrue(s_muon.startswith('zoompan='))
        self.assertNotIn('split=3', s_muon)
        self.assertIn('split=3', s_som)                  # hook đầu clip vẫn nhanh
        self.assertGreater(H._ram_cua_so(14.3, 60, 1080, 1920), 10 * 1024 ** 3)
        self.assertLessEqual(H._ram_cua_so(0.12, 60, 1080, 1920), H.ZOOMPAN_RAM_TRAN)

    def test_tach_bo_loc_dau_ton_trong_nhay(self):
        a, b = H._tach_bo_loc_dau("zoompan=z='if(a,1,2)':d=1,shear=shx=1")
        self.assertEqual((a, b), ("zoompan=z='if(a,1,2)':d=1", "shear=shx=1"))

    @unittest.skipUnless(FF, 'không có ffmpeg')
    def test_file_ra_trung_tung_byte(self):
        td = Path(tempfile.mkdtemp(prefix='zp-'))
        for r, f in (('30', 30), ('30000/1001', 29.97)):
            src = td / 'a.mp4'
            subprocess.run([FF, '-v', 'error', '-y', '-f', 'lavfi', '-i',
                            f'testsrc2=s=270x480:r={r}:d=3', '-c:v', 'libx264',
                            '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', str(src)],
                           check=True)
            md5 = []
            for cu in (True, False):
                out = td / f'o{int(cu)}.mp4'
                g = (f'[0:v]{_chuoi(cu, f)},setpts=PTS/1.1,'
                     'fade=t=in:st=0:d=0.35[o]')
                subprocess.run([FF, '-v', 'error', '-y', '-i', str(src),
                                '-filter_complex', g, '-map', '[o]', '-c:v',
                                'libx264', '-preset', 'ultrafast', '-threads',
                                '1', str(out)], check=True)
                md5.append(out.read_bytes())
            self.assertEqual(md5[0], md5[1], f'lệch ở fps {r}')
        shutil.rmtree(td, ignore_errors=True)


class NhoDoNhip(unittest.TestCase):
    def setUp(self):
        H._NHIP_NHO.clear()

    def test_trung_khoa_chi_do_mot_lan(self):
        with mock.patch.object(H, '_do_nhip_that', return_value=([.1], [.2], True)) as m:
            a = H.do_nhip('', dau_vao=['-i', 'x'], khoa_nho=('k',))
            b = H.do_nhip('', dau_vao=['-i', 'x'], khoa_nho=('k',))
            H.do_nhip('', dau_vao=['-i', 'x'])          # không khoá -> đo lại
        self.assertEqual(a, b); self.assertEqual(m.call_count, 2)
        b[0].append(9)                                   # sửa bản trả về
        self.assertEqual(H._NHIP_NHO[('k',)], ([.1], [.2]))

    def test_luot_hong_hoac_rong_khong_nho(self):
        with mock.patch.object(H, '_do_nhip_that', return_value=([.1], [.2], False)):
            H.do_nhip('', khoa_nho=('a',))
        with mock.patch.object(H, '_do_nhip_that', return_value=([], [], True)):
            H.do_nhip('', khoa_nho=('b',))
        self.assertEqual(H._NHIP_NHO, {})

    def test_gioi_han_so_muc(self):
        with mock.patch.object(H, '_do_nhip_that', return_value=([1], [1], True)):
            for i in range(H._NHIP_NHO_MAX + 5):
                H.do_nhip('', khoa_nho=(i,))
        self.assertEqual(len(H._NHIP_NHO), H._NHIP_NHO_MAX)
        self.assertNotIn((0,), H._NHIP_NHO)

    def test_khong_tieng_bo_luot_do_tieng(self):
        cmds = []
        with mock.patch.object(H, '_chay_ffmpeg', side_effect=lambda c, *a, **k: cmds.append(c) or 0):
            H.do_nhip('', ffmpeg='ffmpeg', dau_vao=['-i', 'x'], co_tieng=False)
        self.assertEqual(len(cmds), 1)
        self.assertNotIn('[0:a]', ' '.join(cmds[0]))

    def test_khoa_bo_qua_phan_dau_mkv(self):
        td = Path(tempfile.mkdtemp(prefix='vt-'))
        a, b = td / 'a.mkv', td / 'b.mkv'
        data = os.urandom(3 << 20)
        a.write_bytes(b'HEAD1' + data); b.write_bytes(b'HEAD2' + data)
        self.assertEqual(F._van_tay_file(a), F._van_tay_file(b))
        src = td / 's.mp4'; src.write_bytes(b'x')
        lst = td / 'l.txt'
        lst.write_text(f"ffconcat version 1.0\nfile '{a}'\n", encoding='utf-8')
        k1 = F._khoa_nho_nhip(src, [(0, 1), (2, 3)], str(lst))
        lst.write_text(f"ffconcat version 1.0\nfile '{b}'\n", encoding='utf-8')
        self.assertEqual(k1, F._khoa_nho_nhip(src, [(0, 1), (2, 3)], str(lst)))
        self.assertNotEqual(k1, F._khoa_nho_nhip(src, [(0, 1), (2, 4)], str(lst)))
        self.assertIsNone(F._khoa_nho_nhip(td / 'khong_co.mp4', [(0, 1)]))
        shutil.rmtree(td, ignore_errors=True)


def _gia_run(kich_ban):
    """kich_ban: list (mã, [dòng log]) theo thứ tự gọi; ghi lại encoder đã dùng."""
    goi = []

    def run(cmd, on_line=None, *a, **k):
        goi.append(cmd)
        code, lines = kich_ban[len(goi) - 1]
        for ln in lines:
            on_line and on_line(ln)
        return code
    return run, goi


TAM = ['[h264_nvenc @ 0x55] OpenEncodeSessionEx failed: out of memory (10): (no details)',
       '[h264_nvenc @ 0x55] No capable devices found']
HONG_HAN = ['[h264_nvenc @ 0x55] Cannot load nvcuda.dll']


class NvencThuLai(unittest.TestCase):
    def setUp(self):
        self._cu = (F._ENCODER_CACHE, F._NVENC_NOTE, F._NVENC_CHO_THU_LAI)
        F._ENCODER_CACHE = 'h264_nvenc'; F._NVENC_CHO_THU_LAI = 0.0

    def tearDown(self):
        F._ENCODER_CACHE, F._NVENC_NOTE, F._NVENC_CHO_THU_LAI = self._cu

    def _chay(self, kich_ban):
        run, goi = _gia_run(kich_ban)
        with mock.patch.object(F, '_run', run), \
                mock.patch.object(F, '_save_nvenc_cache') as luu:
            try:
                F._run_with_fallback(lambda enc: ['ffmpeg', '-c:v', enc], 'h264_nvenc',
                                     1.0, None, 'thử')
                loi = None
            except RuntimeError as e:
                loi = e
        return [c[-1] for c in goi], luu, loi

    def test_tam_thoi_thu_lai_nvenc_thanh_cong(self):
        enc, luu, loi = self._chay([(1, TAM), (0, [])])
        self.assertIsNone(loi)
        self.assertEqual(enc, ['h264_nvenc', 'h264_nvenc'])
        self.assertEqual(F._ENCODER_CACHE, 'h264_nvenc'); luu.assert_not_called()

    def test_tam_thoi_hai_lan_lui_cpu_nhung_giu_phien(self):
        enc, luu, loi = self._chay([(1, TAM), (1, TAM), (0, [])])
        self.assertIsNone(loi)
        self.assertEqual(enc, ['h264_nvenc', 'h264_nvenc', 'libx264'])
        self.assertEqual(F._ENCODER_CACHE, 'h264_nvenc'); luu.assert_not_called()

    def test_thieu_driver_van_lui_ngay_nhu_cu(self):
        enc, luu, loi = self._chay([(1, HONG_HAN), (0, [])])
        self.assertIsNone(loi)
        self.assertEqual(enc, ['h264_nvenc', 'libx264'])
        self.assertEqual(F._ENCODER_CACHE, 'libx264'); luu.assert_called_once()

    def test_nhan_dien(self):
        self.assertTrue(F._looks_nvenc_transient('\n'.join(TAM)))
        self.assertFalse(F._looks_nvenc_transient('\n'.join(HONG_HAN)))
        # "out of memory" của bộ lọc (không dính NVENC) -> KHÔNG phải lỗi NVENC
        self.assertFalse(F._looks_nvenc_transient('[Parsed_scale_0 @ 0x1] out of memory'))


class GiaiMaGpuVaProbe(unittest.TestCase):
    def setUp(self):
        F._HWACCEL_HONG = False

    def tearDown(self):
        F._HWACCEL_HONG = False

    def test_mac_dinh_tat(self):
        with mock.patch.object(F.settings, 'HWACCEL_DECODE', False, create=True):
            self.assertEqual(F._hwaccel_vao(), [])

    def test_bat_hong_thi_chay_lai_khong_hwaccel(self):
        run, goi = _gia_run([(1, ['[h264 @ 0x1] hwaccel init failed']), (0, [])])
        with mock.patch.object(F.settings, 'HWACCEL_DECODE', True, create=True), \
                mock.patch.object(F, '_run', run):
            F._run_with_fallback(lambda enc: ['ffmpeg', *F._hwaccel_vao(), '-i', 'x', enc],
                                 'libx264', 1.0, None, 'thử')
        self.assertIn('-hwaccel', goi[0]); self.assertNotIn('-hwaccel', goi[1])
        self.assertTrue(F._HWACCEL_HONG)

    def test_tach_doan_dung_lai_probe(self):
        info = F.MediaInfo.__new__(F.MediaInfo)
        for k, v in dict(fps=30.0, duration=20.0, has_audio=False, width=64,
                         height=64).items():
            setattr(info, k, v)
        with mock.patch.object(F, 'probe', side_effect=AssertionError('probe lần 2')), \
                mock.patch.object(F, '_run_with_fallback'):
            lst, temps = F._extract_segments_to_temp('x.mp4', [(0, 1), (2, 3)],
                                                     'libx264', info=info)
        F._cleanup_paths(temps)
        self.assertTrue(lst.endswith('_list.txt'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
