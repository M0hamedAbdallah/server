"""Minimal authenticated HTTP download endpoint for the Expo client."""

import os
import re
import shutil
from urllib.parse import parse_qs, urlparse

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from config import (
    DOWNLOAD_TIMEOUT_SECONDS,
    HOST,
    MAX_FILE_SIZE_BYTES,
    PLAYLIST_MAX_ENTRIES,
    PLAYLIST_TIMEOUT_SECONDS,
    PORT,
    TOKEN,
)
from downloader import DownloadError, download, extract_playlist
from validators import ValidationError, validate_input_url

app = Flask(__name__)

CHUNK_SIZE = 65536

# معرّف قائمة تشغيل يوتيوب: أحرف وأرقام وشرطة وسفلية، بطول 10 أحرف على الأقل.
PLAYLIST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,}$")


def _request_token():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):]
    return request.args.get("token", "")


def _cleanup_temp_dir(directory):
    """Best-effort removal of the download temp directory."""
    shutil.rmtree(directory, ignore_errors=True)


def _iter_file(path, directory):
    """Stream a file in chunks, removing its temp dir when done or aborted.

    The ``finally`` block runs when the generator is exhausted (full send) or
    closed (client disconnect), so cleanup is tied to response completion,
    not to a fixed timer that could delete mid-stream.
    """
    try:
        with open(path, "rb") as handle:
            while True:
                chunk = handle.read(CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk
    finally:
        _cleanup_temp_dir(directory)


@app.get("/")
def health():
    """Public health endpoint used by Render probes (HEAD / and GET /).

    No authentication, no yt-dlp, and no network calls. Flask answers HEAD
    automatically for this GET route with status 200 and an empty body.
    """
    return jsonify({"status": "ok"})


@app.get("/download")
def download_media():
    if _request_token() != TOKEN:
        return jsonify({"error": "غير مصرح به"}), 401

    url = request.args.get("url", "")
    try:
        valid_url = validate_input_url(url)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        result = download(
            valid_url,
            temp_dir=None,
            timeout=DOWNLOAD_TIMEOUT_SECONDS,
            max_file_size=MAX_FILE_SIZE_BYTES,
        )
    except DownloadError as exc:
        return jsonify({"error": str(exc)}), 502

    directory = os.path.dirname(result["path"])

    disposition = 'attachment; filename="{}"'.format(result["name"])
    response = app.response_class(
        _iter_file(result["path"], directory),
        mimetype=result["mime"] or "application/octet-stream",
        direct_passthrough=True,
    )
    response.headers["Content-Disposition"] = disposition
    response.headers["Content-Length"] = str(result["size"])
    return response


@app.get("/playlist")
def playlist_media():
    """إرجاع بيانات قائمة تشغيل يوتيوب العامة مرتبة (بدون تنزيل الفيديوهات).

    يجيب بـ {"playlist_id", "title", "count", "entries"} حيث كل Entry =
    {"id", "title", "url"}. سقف 50 عنصراً، ومهلة محددة، وبدون Shell
    أو بيانات اعتماد أو محتوى خاص/محمي.
    """
    if _request_token() != TOKEN:
        return jsonify({"error": "غير مصرح به"}), 401

    url = request.args.get("url", "")
    try:
        valid_url = validate_input_url(url)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    parsed = urlparse(valid_url)
    host = (parsed.hostname or "").lower()
    is_youtube = host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com")
    if not is_youtube:
        return jsonify(
            {"error": "هذه النقطة تدعم قوائم تشغيل يوتيوب العامة فقط"}
        ), 400

    playlist_id = (parse_qs(parsed.query).get("list") or [""])[0].strip()
    if not playlist_id or not PLAYLIST_ID_RE.fullmatch(playlist_id):
        return jsonify(
            {
                "error": "رابط قائمة تشغيل يوتيوب غير صالح أو مفقود معرف القائمة (list=). مثال: https://www.youtube.com/playlist?list=PL...."
            }
        ), 400

    try:
        result = extract_playlist(
            valid_url,
            timeout=PLAYLIST_TIMEOUT_SECONDS,
            max_entries=PLAYLIST_MAX_ENTRIES,
        )
    except DownloadError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify(result), 200


@app.errorhandler(HTTPException)
def handle_http_error(exc):  # noqa: ARG001 - normal HTTP statuses stay intact
    # الأخطاء العادية من التوجيه (مثل مسار غير معروف 404، طريقة غير مسموحة 405)
    # تُحتفظ برموز حالتها الصحيحة دون تسجيل أثر مكدّس.
    return jsonify({"error": exc.description}), exc.code


@app.errorhandler(Exception)
def handle_unexpected(exc):  # noqa: ARG001 - traceback stays in server logs only
    app.logger.exception("unhandled error in /download")
    return jsonify({"error": "حدث خطأ غير متوقع في الخادم"}), 500


if __name__ == "__main__":
    print(f"الخادم يعمل على http://{HOST}:{PORT}")
    print(f"رمز التنزيل: {TOKEN}")
    app.run(host=HOST, port=PORT)
