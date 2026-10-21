"""Small, shared security helpers for public mutation endpoints."""

from __future__ import annotations

from functools import wraps
from hashlib import sha256

from django.core.cache import cache
from django.shortcuts import render


def _client_key(request, scope: str) -> str:
    """Make a non-reversible cache key without storing a visitor's IP raw."""
    source = request.META.get("REMOTE_ADDR", "unknown")
    digest = sha256(f"{scope}:{source}".encode()).hexdigest()
    return f"rate-limit:{scope}:{digest}"


def rate_limit(scope: str, *, limit: int = 8, window: int = 300):
    """Use the configured shared cache to limit costly anonymous submissions.

    Redis is used by production settings, so this remains effective when the
    application has several workers.  A deliberately modest limit leaves room
    for normal mistakes while protecting forms from automated abuse.
    """

    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method != "POST":
                return view(request, *args, **kwargs)
            key = _client_key(request, scope)
            if cache.add(key, 1, timeout=window):
                return view(request, *args, **kwargs)
            try:
                attempts = cache.incr(key)
            except ValueError:
                attempts = limit + 1
            if attempts > limit:
                return render(request, "errors/429.html", status=429)
            return view(request, *args, **kwargs)

        return wrapped

    return decorator
