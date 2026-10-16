"""Minimal authenticated HTTP download endpoint for the Expo client."""

import os
import shutil

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from config import (
    DOWNLOAD_TIMEOUT_SECONDS,
    HOST,
    MAX_FILE_SIZE_BYTES,
    PORT,
    TOKEN,
)
from downloader import DownloadError, download
from validators import ValidationError, validate_input_url

app = Flask(__name__)

CHUNK_SIZE = 65536


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
