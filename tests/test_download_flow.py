"""Successful download flow test using mocks (no real platform network)."""

import os
import shutil
import sys
import tempfile
import unittest

os.environ["DOWNLOAD_TOKEN"] = "test-token-123"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch  # noqa: E402

import app as app_module  # noqa: E402


class TestDownloadFlow(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        self.tmpdir = tempfile.mkdtemp(prefix="vd-test-")
        self.file_path = os.path.join(self.tmpdir, "video.mp4")
        with open(self.file_path, "wb") as handle:
            handle.write(b"fake-video-bytes")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_successful_download_flow(self):
        with patch.object(
            app_module,
            "download",
            return_value={
                "path": self.file_path,
                "name": "video.mp4",
                "mime": "video/mp4",
                "size": 15,
            },
        ):
            response = self.client.get(
                "/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                "&token=test-token-123",
                headers={"Authorization": "Bearer test-token-123"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(), b"fake-video-bytes")
        self.assertEqual(response.headers.get("Content-Type"), "video/mp4")
        disposition = response.headers.get("Content-Disposition", "")
        self.assertIn("attachment", disposition)
        self.assertIn('filename="video.mp4"', disposition)
        response.close()
