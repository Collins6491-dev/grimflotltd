"""Strict settings for Render-compatible production deployments.

Production media is intentionally restricted to S3-compatible object storage:
the temporary application filesystem must never become the media source of
truth. Deployment configuration supplies the required credentials.
"""

from __future__ import annotations

import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False

# Django's development server serves static files directly. WhiteNoise belongs
# only in the production stack, where collected static assets are immutable.
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405

if SECRET_KEY.startswith("unsafe-development-"):  # noqa: F405
    raise ImproperlyConfigured("SECRET_KEY must be set to a secure value in production.")

if not os.getenv("DATABASE_URL"):
    raise ImproperlyConfigured("DATABASE_URL must be configured for production.")

DATABASES = {
    "default": dj_database_url.config(
        conn_max_age=int(os.getenv("DATABASE_CONN_MAX_AGE", "60")),
        conn_health_checks=True,
    )
}

MEDIA_STORAGE_PROVIDER = os.getenv("MEDIA_STORAGE_PROVIDER", "").lower()
if MEDIA_STORAGE_PROVIDER != "s3":
    raise ImproperlyConfigured(
        "MEDIA_STORAGE_PROVIDER=s3 is required in production; local media storage is not persistent."
    )

required_storage_values = ("MEDIA_STORAGE_BUCKET", "MEDIA_STORAGE_ACCESS_KEY", "MEDIA_STORAGE_SECRET_KEY")
missing_storage_values = [name for name in required_storage_values if not os.getenv(name)]
if missing_storage_values:
    raise ImproperlyConfigured(
        f"Missing required object-storage configuration: {', '.join(missing_storage_values)}"
    )

AWS_STORAGE_BUCKET_NAME = os.environ["MEDIA_STORAGE_BUCKET"]
AWS_ACCESS_KEY_ID = os.environ["MEDIA_STORAGE_ACCESS_KEY"]
AWS_SECRET_ACCESS_KEY = os.environ["MEDIA_STORAGE_SECRET_KEY"]
AWS_S3_ENDPOINT_URL = os.getenv("MEDIA_STORAGE_ENDPOINT") or None
AWS_S3_REGION_NAME = os.getenv("MEDIA_STORAGE_REGION") or None
AWS_S3_CUSTOM_DOMAIN = os.getenv("MEDIA_STORAGE_CUSTOM_DOMAIN") or None
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = False
AWS_S3_FILE_OVERWRITE = False

STORAGES = {
    "default": {"BACKEND": "storages.backends.s3.S3Storage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
REFERRER_POLICY = "strict-origin-when-cross-origin"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/1"),
    }
}
