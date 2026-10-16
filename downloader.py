"""yt-dlp based downloader with bounded cancellation, size/time limits, temp files and cleanup.

yt-dlp is invoked as a subprocess so a timeout can *actually terminate* the
downloader (kill + join) instead of merely abandoning a thread while yt-dlp
keeps running against a removed temp directory.
"""

import mimetypes
import os
import shutil
import subprocess
import sys
import tempfile
from subprocess import TimeoutExpired

try:
    import yt_dlp  # noqa: F401  (ensures yt-dlp is importable)
    YT_DLP_AVAILABLE = True
except Exception:  # pragma: no cover - yt-dlp may be absent in test envs
    YT_DLP_AVAILABLE = False


class DownloadError(Exception):
    """User-safe failure while fetching media (no implementation details)."""


def _build_yt_dlp_args(url, out_tmpl, timeout, max_file_size):
    """Build the yt-dlp CLI argument list without ever touching a shell."""
    args = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--quiet",
        "--no-warnings",
        "--no-playlist",
        "--output",
        out_tmpl,
        # Prefer an already-muxed MP4 (single file, no ffmpeg merge required);
        # fall back to the best available format so the client can use its
        # real extension instead of assuming .mp4.
        "--format",
        "best[ext=mp4]/best",
        "--socket-timeout",
        str(min(timeout or 300, 300)),
        url,
    ]
    if max_file_size is not None:
        args.insert(-1, "--max-filesize")
        args.insert(-1, str(max_file_size))
    return args


def download(url, *, temp_dir=None, timeout=None, max_file_size=None):
    """Download media to a temporary file.

    Returns {"path", "name", "mime", "size"}. The caller owns the temp file
    and must delete it after serving it to the client.

    On timeout the yt-dlp subprocess is killed and waited on, then the temp
    directory is removed; no downloader process keeps running against deleted
    files.
    """
    if not YT_DLP_AVAILABLE:
        raise DownloadError("yt-dlp غير مثبت على الخادم")

    temp_dir = temp_dir or tempfile.mkdtemp(prefix="vd-download-")
    os.makedirs(temp_dir, exist_ok=True)
    out_tmpl = os.path.join(temp_dir, "%(id)s.%(ext)s")

    args = _build_yt_dlp_args(url, out_tmpl, timeout, max_file_size)

    proc = None
    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
        try:
            proc.communicate(timeout=timeout)
        except TimeoutExpired:
            proc.kill()
            proc.wait()
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise DownloadError("انتهت مهلة التنزيل") from None
    finally:
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.wait()

    if proc.returncode not in (None, 0):
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise DownloadError("فشل التنزيل من المنصة")

    files = [
        name
        for name in os.listdir(temp_dir)
        if os.path.isfile(os.path.join(temp_dir, name))
    ]
    if len(files) != 1:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise DownloadError("لم يتم إنتاج ملف فيديو")

    file_path = os.path.join(temp_dir, files[0])
    size = os.path.getsize(file_path)
    if max_file_size is not None and size > max_file_size:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise DownloadError("حجم الملف يتجاوز الحد المسموح")

    mime, _ = mimetypes.guess_type(file_path)
    return {"path": file_path, "name": files[0], "mime": mime, "size": size}
