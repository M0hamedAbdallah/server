"""Authentication tests for the /download endpoint (no network)."""

import os
import sys
import unittest

os.environ["DOWNLOAD_TOKEN"] = "test-token-123"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch  # noqa: E402

import app as app_module  # noqa: E402
from downloader import DownloadError  # noqa: E402
from app import app  # noqa: E402


class TestAuth(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_missing_token_rejected(self):
        response = self.client.get(
            "/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {"error": "غير مصرح به"})

    def test_wrong_token_rejected(self):
        response = self.client.get(
            "/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&token=wrong"
        )
        self.assertEqual(response.status_code, 401)

    def _download_error(self):
        return patch.object(app_module, "download", side_effect=DownloadError)

    def test_query_param_token_accepted(self):
        with self._download_error():
            response = self.client.get(
                "/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                "&token=test-token-123"
            )
        self.assertEqual(response.status_code, 502)

    def test_bearer_header_accepted(self):
        with self._download_error():
            response = self.client.get(
                "/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                headers={"Authorization": "Bearer test-token-123"},
            )
        self.assertEqual(response.status_code, 502)

    def test_valid_token_reaches_url_validation(self):
        # invalid scheme passes auth but fails validation with 400
        response = self.client.get(
            "/download?url=http://www.youtube.com/watch?v=dQw4w9WgXcQ"
            "&token=test-token-123"
        )
        self.assertEqual(response.status_code, 400)
