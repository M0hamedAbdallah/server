"""Input URL validation: only public YouTube / Instagram / Facebook hosts."""

from urllib.parse import urlparse

# Registrable domains whose subdomains are allowed.
ALLOWED_DOMAINS = {"youtube.com", "instagram.com", "facebook.com"}
# Explicitly allowed hosts (exact match), including subdomains without registrable-prefix.
ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "instagram.com",
    "www.instagram.com",
    "facebook.com",
    "www.facebook.com",
    "m.facebook.com",
    "fb.watch",
    "www.fb.watch",
}


class ValidationError(ValueError):
    """Raised when the caller-supplied URL is not acceptable."""


def validate_input_url(url):
    """Validate and normalize a caller-supplied URL.

    Returns the normalized URL string, or raises ValidationError.
    Rejects: non-https schemes, embedded credentials, missing/unsupported hosts,
    localhost and private IP addresses (implicitly, via the whitelist).
    """
    if not isinstance(url, str) or not url:
        raise ValidationError("الرابط مطلوب")
    if "@" in url:
        raise ValidationError("لا يُسمح ببيانات اعتماد مضمنة في الرابط")
    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise ValidationError("الرابط غير صالح") from exc

    scheme = (parsed.scheme or "").lower()
    if scheme != "https":
        raise ValidationError("يجب أن يبدأ الرابط بـ https://")

    host = (parsed.hostname or "").lower()
    if not host:
        raise ValidationError("لم يتم العثور على مضيف في الرابط")

    allowed = host in ALLOWED_HOSTS or any(
        host.endswith("." + domain) for domain in ALLOWED_DOMAINS
    )
    if not allowed:
        raise ValidationError(
            "هذا المضيف غير مدعوم. المنصات المدعومة: يوتيوب وإنستغرام وفيسبوك فقط"
        )

    netloc = host + (f":{parsed.port}" if parsed.port else "")
    return parsed._replace(scheme=scheme, netloc=netloc).geturl()
