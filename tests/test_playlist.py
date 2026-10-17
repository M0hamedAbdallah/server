"""Playlist endpoint tests: the yt-dlp extractor is mocked, no platform network."""

import json
import os
import sys
import unittest
from subprocess import TimeoutExpired
from unittest.mock import patch

os.environ["DOWNLOAD_TOKEN"] = "test-token-123"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402
from downloader import DownloadError, extract_playlist  # noqa: E402
import downloader as downloader_module  # noqa: E402


FAKE_PLAYLIST_RESULT = {
    "playlist_id": "PLfakePlaylistId",
    "title": "قائمة تجريبية",
    "count": 2,
    "entries": [
        {"id": "video1", "title": "الفيديو الأول", "url": "https://www.youtube.com/watch?v=video1"},
        {"id": "video2", "title": "الفيديو الثاني", "url": "https://www.youtube.com/watch?v=video2"},
    ],
}

SIXTY_ENTRIES = [{"id": f"vid{i}", "title": f"العنوان {i}"} for i in range(60)]


class TestPlaylistEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def _auth_headers(self):
        return {"Authorization": "Bearer test-token-123"}

    def test_playlist_returns_ordered_entries(self):
        with patch.object(app_module, "extract_playlist", return_value=FAKE_PLAYLIST_RESULT):
            response = self.client.get(
                "/playlist?url=https://www.youtube.com/playlist?list=PLfakePlaylistId&token=test-token-123",
                headers=self._auth_headers(),
            )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["playlist_id"], "PLfakePlaylistId")
        self.assertEqual(data["count"], 2)
        self.assertEqual([entry["id"] for entry in data["entries"]], ["video1", "video2"])
        self.assertEqual([entry["title"] for entry in data["entries"]], ["الفيديو الأول", "الفيديو الثاني"])
        for entry in data["entries"]:
            self.assertTrue(entry["url"].startswith("https://www.youtube.com/watch?v="))
        self.assertNotIn("Traceback", response.get_data(as_text=True))

    def test_playlist_missing_list_param_rejected(self):
        response = self.client.get(
            "/playlist?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&token=test-token-123",
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 400)

    def test_playlist_invalid_id_rejected(self):
        response = self.client.get(
            "/playlist?url=https://www.youtube.com/playlist?list=short&token=test-token-123",
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 400)

    def test_playlist_non_youtube_host_rejected(self):
        response = self.client.get(
            "/playlist?url=https://www.instagram.com/p/Cx7Fm5pL7bD/?list=PLfakePlaylistId&token=test-token-123",
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 400)

    def test_playlist_missing_token_rejected(self):
        response = self.client.get(
            "/playlist?url=https://www.youtube.com/playlist?list=PLfakePlaylistId"
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {"error": "غير مصرح به"})

    def test_playlist_extractor_error_returns_502(self):
        with patch.object(
            app_module, "extract_playlist", side_effect=DownloadError("قائمة التشغيل غير متاحة")
        ):
            response = self.client.get(
                "/playlist?url=https://www.youtube.com/playlist?list=PLfakePlaylistId&token=test-token-123",
                headers=self._auth_headers(),
            )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json(), {"error": "قائمة التشغيل غير متاحة"})


class TestExtractorCap(unittest.TestCase):
    def _make_proc(self, stdout_lines, returncode=0):
        proc = unittest.mock.MagicMock()
        proc.communicate.return_value = (
            "\n".join(stdout_lines).encode("utf-8"),
            b"",
        )
        proc.returncode = returncode
        proc.poll.return_value = returncode
        return proc

    def _captured_popen_args(self):
        """Capture the args passed to subprocess.Popen by extract_playlist."""
        captured = {}

        def fake_popen(args, **kwargs):
            captured["args"] = args
            return self._make_proc([])

        return captured, fake_popen

    def test_extract_playlist_caps_entries_at_max(self):
        lines = [
            json.dumps(
                {
                    "id": f"vid{i}",
                    "title": f"العنوان {i}",
                    "playlist_id": "PLx",
                    "playlist_title": "قائمة",
                }
            )
            for i in range(60)
        ]
        proc = self._make_proc(lines)
        with patch.object(downloader_module.subprocess, "Popen", return_value=proc):
            result = extract_playlist(
                "https://www.youtube.com/playlist?list=PLx",
                timeout=30,
                max_entries=50,
            )
        self.assertEqual(len(result["entries"]), 50)
        self.assertEqual(result["entries"][0]["id"], "vid0")
        self.assertEqual(result["entries"][49]["id"], "vid49")
        self.assertEqual(result["playlist_id"], "PLx")
        self.assertEqual(result["title"], "قائمة")
        proc.kill.assert_not_called()

    def test_extract_playlist_cli_args_include_playlist_items(self):
        captured, fake_popen = self._captured_popen_args()
        with patch.object(
            downloader_module.subprocess, "Popen", side_effect=fake_popen
        ):
            try:
                extract_playlist(
                    "https://www.youtube.com/playlist?list=PLx",
                    timeout=30,
                    max_entries=50,
                )
            except DownloadError:
                pass  # expected: proc returns empty stdout → non-playlist rejected
        args = captured.get("args", [])
        self.assertIn("--playlist-items", args)
        idx = args.index("--playlist-items")
        self.assertEqual(args[idx + 1], "1:50")
        self.assertIn("--flat-playlist", args)
        self.assertIn("--dump-json", args)

    def test_extract_playlist_non_playlist_rejected(self):
        proc = self._make_proc([], returncode=0)
        with patch.object(downloader_module.subprocess, "Popen", return_value=proc):
            with self.assertRaises(DownloadError):
                extract_playlist(
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    timeout=30,
                    max_entries=50,
                )

    def test_extract_playlist_timeout_kills_process(self):
        proc = self._make_proc([])
        proc.communicate.side_effect = TimeoutExpired(cmd="yt-dlp", timeout=30)
        with patch.object(downloader_module.subprocess, "Popen", return_value=proc):
            with self.assertRaises(DownloadError):
                extract_playlist(
                    "https://www.youtube.com/playlist?list=PLx",
                    timeout=1,
                    max_entries=50,
                )
        proc.kill.assert_called_once()
        proc.wait.assert_called()

    def test_extract_playlist_nonzero_returncode_rejected(self):
        proc = self._make_proc([], returncode=1)
        with patch.object(downloader_module.subprocess, "Popen", return_value=proc):
            with self.assertRaises(DownloadError):
                extract_playlist(
                    "https://www.youtube.com/playlist?list=PLx",
                    timeout=30,
                    max_entries=50,
                )


if __name__ == "__main__":
    unittest.main()
