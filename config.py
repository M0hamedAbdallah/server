"""Configuration for the self-hosted video downloader backend."""

import os
import secrets

HOST = os.environ.get("DOWNLOAD_HOST", "127.0.0.1")
PORT = int(os.environ.get("DOWNLOAD_PORT", "8000"))
# bearer token required by the Expo client; generated randomly if not configured
TOKEN = os.environ.get("DOWNLOAD_TOKEN") or secrets.token_urlsafe(24)
MAX_FILE_SIZE_BYTES = int(os.environ.get("MAX_FILE_SIZE_BYTES", str(500 * 1024 * 1024)))
DOWNLOAD_TIMEOUT_SECONDS = int(os.environ.get("DOWNLOAD_TIMEOUT_SECONDS", "600"))
TEMP_DIR = os.environ.get("TEMP_DIR") or None
# عدد عناصر القائمة الأقصى الذي يُعاد من نقطة نهاية /playlist (منع الاستنزاف)
PLAYLIST_MAX_ENTRIES = int(os.environ.get("PLAYLIST_MAX_ENTRIES", "50"))
# مهلة جلب بيانات القائمة فقط (وليس تنزيل الفيديوهات) بالثواني
PLAYLIST_TIMEOUT_SECONDS = int(os.environ.get("PLAYLIST_TIMEOUT_SECONDS", "120"))
