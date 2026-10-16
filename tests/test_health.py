"""Health endpoint tests: public GET / and HEAD /, no auth, no network."""

import os
import sys
import unittest

os.environ["DOWNLOAD_TOKEN"] = "test-token-123"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402


class TestHealth(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_root_returns_200(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_head_root_returns_200_with_empty_body(self):
        response = self.client.head("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(b""), b"")

    def test_unknown_route_returns_404(self):
        response = self.client.get("/no-such-route")
        self.assertEqual(response.status_code, 404)

    def test_disallowed_method_returns_405(self):
        response = self.client.post("/download")
        self.assertEqual(response.status_code, 405)

    def test_download_without_token_still_returns_401(self):
        response = self.client.get(
            "/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {"error": "غير مصرح به"})
