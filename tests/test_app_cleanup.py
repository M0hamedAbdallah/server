"""Endpoint cleanup test: temp dir removed when the response is closed, no network."""

import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ["DOWNLOAD_TOKEN"] = "test-token-123"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402


class TestCleanupOnClose(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        self.tmpdir = tempfile.mkdtemp(prefix="vd-cleanup-")
        self.file_path = os.path.join(self.tmpdir, "video.mp4")
        with open(self.file_path, "wb") as handle:
            handle.write(b"video-bytes")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_cleanup_on_response_close(self):
        with patch.object(
            app_module,
            "download",
            return_value={
                "path": self.file_path,
                "name": "video.mp4",
                "mime": "video/mp4",
                "size": 12,
            },
        ):
            response = self.client.get(
                "/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                "&token=test-token-123",
                headers={"Authorization": "Bearer test-token-123"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(), b"video-bytes")

        # الإرسال اكتمل (أو أغلق العميل)، لذا يجب إزالة المجلد المؤقت فوراً.
        response.close()
        self.assertFalse(os.path.exists(self.tmpdir), "يجب حذف الملف المؤقت بعد إغلاق الاستجابة")
