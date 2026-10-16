"""Tests for host/URL validation (no network)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validators import ValidationError, validate_input_url  # noqa: E402

VALID_URLS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXcQ",
    "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.instagram.com/reel/Cx7Fm5pL7bD/",
    "https://instagram.com/p/Cx7Fm5pL7bD/",
    "https://www.facebook.com/reel/123456789/",
    "https://facebook.com/watch/?v=123456789",
    "https://m.facebook.com/story.php?story_fbid=123",
    "https://fb.watch/123456789/",
    "https://www.fb.watch/123456789/",
]

INVALID_URLS = [
    None,
    "",
    "   ",
    "not a url",
    "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "ftp://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://user:pass@www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com:443@evil.com/",
    "https://localhost/video",
    "https://127.0.0.1/video",
    "https://[::1]/video",
    "https://www.example.com/video",
    "https://youtube.com.evil.com/video",
    "https://www.youtube.com.evil.com/video",
    "https://evil.instagram.com.evil.com/",
]


class TestValidators(unittest.TestCase):
    def test_valid_urls_accepted(self):
        for url in VALID_URLS:
            with self.subTest(url=url):
                result = validate_input_url(url)
                self.assertIsInstance(result, str)
                self.assertTrue(result.startswith("https://"))

    def test_invalid_urls_rejected(self):
        for url in INVALID_URLS:
            with self.subTest(url=url):
                with self.assertRaises(ValidationError):
                    validate_input_url(url)

    def test_case_insensitive_host(self):
        result = validate_input_url("HTTPS://WWW.YOUTUBE.COM/watch?v=dQw4w9WgXcQ")
        self.assertTrue(result.startswith("https://www.youtube.com"))
