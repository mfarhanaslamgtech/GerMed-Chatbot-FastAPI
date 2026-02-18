"""
Image Upload Validators — Async-first for FastAPI.

🎓 MIGRATION NOTE:
Original Gervet had TWO image validators:
  - file_validators.py (Flask/werkzeug.FileStorage)
  - image_validator.py (FastAPI/UploadFile - partially done)

This file merges both into one clean, async-first module.
FastAPI's UploadFile is the ONLY file type we need to support.
"""
import io
import logging
from fastapi import UploadFile
from PIL import Image

from src.app.exceptions.custom_exceptions import InvalidImageException

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
MAX_FILE_SIZE_MB = 5


def validate_image_upload(file: UploadFile) -> None:
    """
    Quick sync validation — checks content type only.
    Use for fast pre-checks before reading file content.
    
    Raises:
        InvalidImageException: If file is missing or wrong type.
    """
    if not file:
        raise InvalidImageException("Image file is required.")

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise InvalidImageException(
            f"Invalid image type '{file.content_type}'. "
            f"Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )


async def validate_image_upload_async(file: UploadFile) -> bytes:
    """
    Full async validation — reads file, checks size, verifies it's a real image.
    Returns the raw bytes for downstream processing.
    
    🎓 KEY DIFFERENCE FROM FLASK:
    Flask's werkzeug.FileStorage.seek() is sync.
    FastAPI's UploadFile.read() / .seek() are async.
    
    Raises:
        InvalidImageException: If validation fails.
    """
    if not file:
        raise InvalidImageException("Image file is required.")

    # 1. Content type check
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise InvalidImageException(
            f"Invalid image type '{file.content_type}'. "
            f"Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )

    # 2. Read content (async)
    content = await file.read()

    # 3. Size check
    file_size_mb = len(content) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise InvalidImageException(
            f"Image too large ({file_size_mb:.1f}MB). Max: {MAX_FILE_SIZE_MB}MB."
        )

    # 4. Verify it's a real image (PIL)
    try:
        image = Image.open(io.BytesIO(content))
        image.verify()
    except Exception:
        raise InvalidImageException("Uploaded file is not a valid image.")

    # 5. Reset cursor for downstream reads
    await file.seek(0)

    return content


def validate_image_bytes(content: bytes) -> None:
    """
    Validate raw image bytes (used when image comes from Redis or another source).
    
    Raises:
        InvalidImageException: If validation fails.
    """
    if not content:
        raise InvalidImageException("Image content is required.")

    file_size_mb = len(content) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise InvalidImageException(
            f"Image too large ({file_size_mb:.1f}MB). Max: {MAX_FILE_SIZE_MB}MB."
        )

    try:
        image = Image.open(io.BytesIO(content))
        image.verify()
    except Exception:
        raise InvalidImageException("Content is not a valid image.")
