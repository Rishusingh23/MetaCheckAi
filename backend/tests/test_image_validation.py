import io
import pytest
from PIL import Image

from app.services.ocr.quality import validate_image_file


def create_test_image_bytes(
    width: int = 200, height: int = 200, color=(200, 200, 200), fmt: str = "PNG"
) -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_validate_valid_png():
    data = create_test_image_bytes(fmt="PNG")
    res = validate_image_file(data)
    assert res.is_valid is True
    assert res.mime_type == "image/png"
    assert res.width == 200
    assert res.height == 200
    assert res.error_message is None


def test_validate_valid_jpeg():
    data = create_test_image_bytes(fmt="JPEG")
    res = validate_image_file(data)
    assert res.is_valid is True
    assert res.mime_type == "image/jpeg"
    assert res.width == 200
    assert res.height == 200


def test_validate_empty_bytes():
    res = validate_image_file(b"")
    assert res.is_valid is False
    assert "cannot be 0 bytes" in res.error_message


def test_validate_size_exceeded():
    data = create_test_image_bytes(fmt="PNG")
    res = validate_image_file(data, max_size_bytes=10)
    assert res.is_valid is False
    assert "exceeds limit" in res.error_message


def test_validate_unsupported_format():
    res = validate_image_file(b"This is just plain text content not an image.")
    assert res.is_valid is False
    assert "Unsupported or unrecognized image format" in res.error_message


def test_validate_corrupted_image_header():
    # Has PNG magic bytes but corrupted payload
    corrupted_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
    res = validate_image_file(corrupted_data)
    assert res.is_valid is False
    assert "Corrupted image payload" in res.error_message


def test_validate_too_small_dimensions():
    data = create_test_image_bytes(width=20, height=20, fmt="PNG")
    res = validate_image_file(data)
    assert res.is_valid is False
    assert "too small" in res.error_message
