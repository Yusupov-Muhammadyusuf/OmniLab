"""Environment-backed configuration helpers."""

import os
from collections.abc import Mapping
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured


DJANGO_SECRET_KEY_ENVIRONMENT_VARIABLE = "OMNILAB_DJANGO_SECRET_KEY"
LOCAL_DEVELOPMENT_SECRET_KEY = (
    "omnilab-local-development-only-do-not-use-this-key-in-production"
)
DEFAULT_ALLOWED_HOSTS = (
    "omnilab-bk8q.onrender.com",
    "127.0.0.1",
    "localhost",
)
DEFAULT_PUBLIC_ORIGIN = "https://omnilab-bk8q.onrender.com"


def get_public_origin(
    environ: Mapping[str, str] | None = None,
) -> str:
    """Return the HTTPS origin used by every public discovery URL."""
    environment = os.environ if environ is None else environ
    configured_origin = environment.get(
        "OMNILAB_PUBLIC_ORIGIN",
        DEFAULT_PUBLIC_ORIGIN,
    ).strip().rstrip("/")
    parsed_origin = urlsplit(configured_origin)

    if (
        parsed_origin.scheme != "https"
        or not parsed_origin.netloc
        or parsed_origin.path
        or parsed_origin.query
        or parsed_origin.fragment
        or parsed_origin.username
        or parsed_origin.password
    ):
        raise ImproperlyConfigured(
            "OMNILAB_PUBLIC_ORIGIN must be an HTTPS origin without a path, "
            "query, fragment, or credentials."
        )

    return configured_origin


def is_search_indexing_disabled(
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Return whether this deployment must stay out of search indexes."""
    environment = os.environ if environ is None else environ
    return environment.get("OMNILAB_NOINDEX", "").strip().lower() == "true"


def is_production_environment(
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Return whether the current process is running in production."""
    environment = os.environ if environ is None else environ
    return (
        environment.get("RENDER", "").lower() == "true"
        or environment.get("OMNILAB_ENVIRONMENT", "").lower() == "production"
    )


def get_django_secret_key(
    environ: Mapping[str, str] | None = None,
) -> str:
    """Return the configured key, requiring it in production."""
    environment = os.environ if environ is None else environ
    configured_key = environment.get(
        DJANGO_SECRET_KEY_ENVIRONMENT_VARIABLE,
        "",
    ).strip()

    if configured_key:
        return configured_key
    if is_production_environment(environment):
        raise ImproperlyConfigured(
            f"{DJANGO_SECRET_KEY_ENVIRONMENT_VARIABLE} must be set in production."
        )

    return LOCAL_DEVELOPMENT_SECRET_KEY


def get_allowed_hosts(
    environ: Mapping[str, str] | None = None,
) -> list[str]:
    """Return configured host names while preserving the current defaults."""
    environment = os.environ if environ is None else environ
    configured_hosts = environment.get("OMNILAB_ALLOWED_HOSTS", "")
    hosts = [
        host.strip()
        for host in configured_hosts.split(",")
        if host.strip()
    ]
    return hosts or list(DEFAULT_ALLOWED_HOSTS)
