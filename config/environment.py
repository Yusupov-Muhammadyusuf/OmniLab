"""Environment-backed configuration helpers."""

import os
from collections.abc import Mapping

from django.core.exceptions import ImproperlyConfigured


DJANGO_SECRET_KEY_ENVIRONMENT_VARIABLE = "OMNILAB_DJANGO_SECRET_KEY"
LOCAL_DEVELOPMENT_SECRET_KEY = (
    "omnilab-local-development-only-do-not-use-this-key-in-production"
)


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
