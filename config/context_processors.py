"""Template context derived from deployment-owned settings."""

from urllib.parse import urlsplit

from django.conf import settings


def _hostname(value: str) -> str | None:
    """Return a normalized hostname, failing closed for invalid values."""
    try:
        return urlsplit(value).hostname
    except (TypeError, ValueError):
        return None


def product_analytics(request) -> dict[str, bool]:
    """Enable analytics only on the configured, indexable public host."""
    public_origin = getattr(settings, "OMNILAB_PUBLIC_ORIGIN", "")
    request_hostname = _hostname(f"//{request.get_host()}")
    public_hostname = _hostname(public_origin)

    return {
        "product_analytics_enabled": bool(
            not settings.OMNILAB_NOINDEX
            and public_hostname
            and request_hostname == public_hostname
        )
    }
