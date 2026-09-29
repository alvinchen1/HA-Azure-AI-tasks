"""Validation helpers for image generation dimensions."""
from __future__ import annotations

import re

import voluptuous as vol

MAX_IMAGE_WIDTH = 3840
MAX_IMAGE_HEIGHT = 2160
_IMAGE_SIZE_PATTERN = re.compile(r"([0-9]+)x([0-9]+)")


def parse_image_size(value: str) -> tuple[int, int]:
    """Parse and validate a custom image size in WIDTHxHEIGHT format."""
    if not isinstance(value, str):
        raise ValueError("Image dimensions must be provided as WIDTHxHEIGHT text")
    match = _IMAGE_SIZE_PATTERN.fullmatch(value.strip())
    if match is None:
        raise ValueError("Enter image dimensions as WIDTHxHEIGHT, for example 800x480")

    width, height = (int(part) for part in match.groups())
    if width <= 0 or height <= 0:
        raise ValueError("Image width and height must be greater than zero")
    if width % 16 or height % 16:
        raise ValueError("Image width and height must both be divisible by 16")
    if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
        raise ValueError("Image dimensions cannot exceed 3840x2160")
    if width * 3 < height or height * 3 < width:
        raise ValueError("Image aspect ratio must be between 1:3 and 3:1")

    return width, height


def validate_image_size(value: str) -> str:
    """Voluptuous validator that returns normalized WIDTHxHEIGHT dimensions."""
    try:
        width, height = parse_image_size(value)
    except ValueError as err:
        raise vol.Invalid(str(err)) from err
    return f"{width}x{height}"
