"""Settings intended only for local development and automated tests."""

from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = "development-only-secret-key-not-for-production"
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "grimflot-development",
    }
}
