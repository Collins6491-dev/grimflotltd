"""Validation shared by content models that accept uploaded media or links."""

from __future__ import annotations

import os
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.text import slugify
from PIL import Image, UnidentifiedImageError


MAX_IMAGE_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_DIMENSION = 10_000
IMAGE_FORMAT_EXTENSIONS = {
    "JPEG": {".jpg", ".jpeg"},
    "PNG": {".png"},
    "WEBP": {".webp"},
    "GIF": {".gif"},
    "ICO": {".ico"},
}


def safe_upload_filename(filename: str) -> str:
    """Return a storage-safe image name while retaining its file extension.

    Django's ``slugify`` intentionally removes a period, so applying it to an
    entire filename turns ``control-panel.webp`` into ``control-panelwebp``.
    Storage backends and clients use the extension to determine the media type;
    keep it while discarding directories and normalising the visible name.
    """
    basename = str(filename).replace("\\", "/").rsplit("/", 1)[-1]
    stem, extension = os.path.splitext(basename)
    return f"{slugify(stem) or 'image'}{extension.lower()}"


def validate_content_image(upload) -> None:
    """Reject oversized, invalid, or impractically large image uploads.

    Pillow verifies the actual image stream rather than trusting only the
    filename supplied by a browser.  The file pointer is restored afterwards
    so Django's storage backend can save the same uploaded file normally.
    """
    if not upload:
        return
    if upload.size > MAX_IMAGE_UPLOAD_BYTES:
        raise ValidationError("Images must be 10 MB or smaller.")

    try:
        position = upload.tell()
        image = Image.open(upload)
        image_format = image.format
        image.verify()
        upload.seek(position)
        image = Image.open(upload)
        width, height = image.size
    except (OSError, UnidentifiedImageError, ValueError) as error:
        raise ValidationError("Upload a valid image file.") from error
    finally:
        try:
            upload.seek(0)
        except (AttributeError, OSError):
            pass

    if max(width, height) > MAX_IMAGE_DIMENSION:
        raise ValidationError(
            f"Images must not exceed {MAX_IMAGE_DIMENSION:,} pixels on either side."
        )

    extension = os.path.splitext(str(getattr(upload, "name", "")))[1].lower()
    allowed_extensions = IMAGE_FORMAT_EXTENSIONS.get(image_format or "", set())
    if extension not in allowed_extensions:
        raise ValidationError(
            "The image filename extension must match its verified image format."
        )


def validate_cta_target(value: str) -> None:
    """Allow local anchors/paths or a complete HTTPS destination, never script URLs."""
    if not value or value.startswith(("#", "/")):
        return

    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValidationError("Use an on-site path or a complete HTTPS URL.")
    URLValidator(schemes=["https"])(value)
