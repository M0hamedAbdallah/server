"""Error-case tests: invalid URL, unsupported host, downloader failure (no network)."""

import os
import sys
import unittest

os.environ["DOWNLOAD_TOKEN"] = "test-token-123"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch  # noqa: E402

import app as app_module  # noqa: E402
from downloader import DownloadError  # noqa: E402


class TestDownloadError(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def test_invalid_scheme_rejected(self):
        response = self.client.get(
            "/download?url=http://www.youtube.com/watch?v=x&token=test-token-123"
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("Traceback", response.get_data(as_text=True))

    def test_embedded_credentials_rejected(self):
        response = self.client.get(
            "/download?url=https://user:pass@www.youtube.com/watch?v=x"
            "&token=test-token-123"
        )
        self.assertEqual(response.status_code, 400)

    def test_unsupported_host_rejected(self):
        response = self.client.get(
            "/download?url=https://www.example.com/video&token=test-token-123"
        )
        self.assertEqual(response.status_code, 400)

    def test_downloader_error_returns_safe_json(self):
        with patch.object(
            app_module, "download", side_effect=DownloadError("الفيديو غير متاح")
        ):
            response = self.client.get(
                "/download?url=https://www.youtube.com/watch?v=x"
                "&token=test-token-123"
            )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json(), {"error": "الفيديو غير متاح"})
        self.assertNotIn("Traceback", response.get_data(as_text=True))
