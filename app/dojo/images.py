"""Product images, stored as files on disk (not in SQLite).

Uploaded images are saved at ``<DB_PATH's directory>/images/<product_id>.jpg``
on the same volume as the database, so `POST /api/reset` can wipe them back
to "no custom image" alongside the rest of the data. The bundled default
image ships inside the application image itself (not the data volume), so
it survives a reset.
"""
from __future__ import annotations

from pathlib import Path

from .db import DB_PATH
from .errors import ApiError, field_error

IMAGES_DIR = Path(DB_PATH).parent / "images"
DEFAULT_IMAGE_PATH = Path(__file__).parent / "assets" / "default-product.jpg"

MAX_BYTES = 2 * 1024 * 1024  # 2 MB
_JPEG_SOI = b"\xff\xd8\xff"
_JPEG_EOI = b"\xff\xd9"


def _ensure_dir() -> None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def image_file(product_id: int) -> Path:
    return IMAGES_DIR / f"{product_id}.jpg"


def has_custom_image(product_id: int) -> bool:
    return image_file(product_id).is_file()


def resolve_image_path(product_id: int) -> Path:
    p = image_file(product_id)
    return p if p.is_file() else DEFAULT_IMAGE_PATH


def validate_and_save(product_id: int, data: bytes) -> None:
    """Accepts only JPEG content (checked by content, not by filename) of at
    most 2 MB, and saves it as ``<product_id>.jpg`` — REQ-CAT-010."""
    if not data:
        raise ApiError("VALIDATION_ERROR", details=[field_error("image", "required")])
    if len(data) > MAX_BYTES:
        raise ApiError("VALIDATION_ERROR", details=[field_error("image", "image_size")])
    if not data.startswith(_JPEG_SOI) or not data.rstrip(b"\r\n\x00").endswith(_JPEG_EOI):
        raise ApiError("VALIDATION_ERROR", details=[field_error("image", "image_format")])
    _ensure_dir()
    image_file(product_id).write_bytes(data)


def clear_all() -> None:
    """Delete every uploaded image (used by POST /api/reset)."""
    if IMAGES_DIR.is_dir():
        for f in IMAGES_DIR.glob("*.jpg"):
            f.unlink()
