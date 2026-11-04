"""Giải mã GPU tự dò (ffmpeg_utils._hwaccel_vao) + ảnh bìa `_Bia` đã BỎ.

27/10/2026 anh Hùng: "bỏ cái bìa đó đi tôi không cần nữa" -> `app/core/bia.py`
bị gỡ; ca dưới canh để lượt xuất không tự mọc lại thư mục `_Bia`."""
import ast
import unittest
from pathlib import Path
from unittest import mock

from app.core import ffmpeg_utils as F

ROOT = Path(__file__).resolve().parents[1]


class BiaDaBo(unittest.TestCase):
    def test_khong_con_ma_luu_bia(self):
        self.assertFalse((ROOT / "app" / "core" / "bia.py").exists())
        src = (ROOT / "app" / "modules" / "m1_highlight.py").read_text(encoding="utf-8")
        ten = {n.module for n in ast.walk(ast.parse(src))
               if isinstance(n, ast.ImportFrom) and n.module}
        self.assertNotIn("app.core.bia", ten)


class NvdecTests(unittest.TestCase):
    def setUp(self):
        F._HWACCEL_HONG = False

    def tearDown(self):
        F._HWACCEL_HONG = False

    def test_auto_chi_bat_khi_nvenc_va_thu_that_dat(self):
        with mock.patch.object(F.settings, "HWACCEL_DECODE", "auto", create=True):
            with mock.patch.object(F, "detect_encoder", return_value="h264_nvenc"), \
                 mock.patch.object(F, "_nvdec_works", return_value=True):
                self.assertEqual(F._hwaccel_vao(), ["-hwaccel", "cuda"])
            with mock.patch.object(F, "detect_encoder", return_value="h264_nvenc"), \
                 mock.patch.object(F, "_nvdec_works", return_value=False):
                self.assertEqual(F._hwaccel_vao(), [])
            with mock.patch.object(F, "detect_encoder", return_value="libx264"), \
                 mock.patch.object(F, "_nvdec_works", return_value=True) as w:
                self.assertEqual(F._hwaccel_vao(), [])
                w.assert_not_called()           # máy không NVENC: khỏi thử

    def test_tat_han_va_da_hong(self):
        with mock.patch.object(F.settings, "HWACCEL_DECODE", False, create=True):
            self.assertEqual(F._hwaccel_vao(), [])
        F._HWACCEL_HONG = True
        with mock.patch.object(F.settings, "HWACCEL_DECODE", True, create=True):
            self.assertEqual(F._hwaccel_vao(), [])


if __name__ == "__main__":
    unittest.main()
