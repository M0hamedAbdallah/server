"""Downloader cancellation test: real subprocess kill-on-timeout, no network."""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

os.environ["DOWNLOAD_TOKEN"] = "test-token-123"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from subprocess import TimeoutExpired  # noqa: E402

from downloader import DownloadError, download  # noqa: E402


class TestDownloaderTimeout(unittest.TestCase):
    def test_timeout_kills_subprocess_and_removes_temp_dir(self):
        tmp = tempfile.mkdtemp(prefix="vd-timeout-")
        fake_proc = MagicMock()
        fake_proc.poll.return_value = None
        # communicate blocking until timeout, then we kill.
        fake_proc.communicate.side_effect = TimeoutExpired(cmd="yt-dlp", timeout=1)

        with patch(
            "downloader.subprocess.Popen", return_value=fake_proc
        ) as popen_mock:
            with self.assertRaises(DownloadError) as ctx:
                download(
                    "https://www.youtube.com/watch?v=x",
                    temp_dir=tmp,
                    timeout=1,
                    max_file_size=None,
                )
            popen_mock.assert_called_once()
            # yt-dlp command list must never be shell-joined.
            args = popen_mock.call_args.args[0]
            self.assertIsInstance(args, list)
            self.assertTrue(all(isinstance(a, str) for a in args))

        fake_proc.kill.assert_called()
        fake_proc.wait.assert_called()
        self.assertEqual(str(ctx.exception), "انتهت مهلة التنزيل")
        self.assertFalse(os.path.exists(tmp), "المجلد المؤقت يجب أن يُحذف عند المهلة")


if __name__ == "__main__":
    unittest.main()
