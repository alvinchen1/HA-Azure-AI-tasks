"""Validation helpers for image generation dimensions."""
from __future__ import annotations

import re

MAX_IMAGE_DIMENSION = 3840
MIN_IMAGE_PIXELS = 655_360
MAX_IMAGE_PIXELS = 8_294_400
_IMAGE_SIZE_PATTERN = re.compile(r"([0-9]+)x([0-9]+)")


def parse_image_size(value: str) -> tuple[int, int]:
    """Parse and validate a custom image size in WIDTHxHEIGHT format."""
    if not isinstance(value, str):
        raise ValueError("Image dimensions must be provided as WIDTHxHEIGHT text")
    match = _IMAGE_SIZE_PATTERN.fullmatch(value.strip())
    if match is None:
        raise ValueError("Enter image dimensions as WIDTHxHEIGHT, for example 1024x640")

    width, height = (int(part) for part in match.groups())
    if width <= 0 or height <= 0:
        raise ValueError("Image width and height must be greater than zero")
    if width % 16 or height % 16:
        raise ValueError("Image width and height must both be divisible by 16")
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise ValueError("Neither image dimension can exceed 3840 pixels")
    if width * 3 < height or height * 3 < width:
        raise ValueError("Image aspect ratio must be between 1:3 and 3:1")
    pixels = width * height
    if not MIN_IMAGE_PIXELS <= pixels <= MAX_IMAGE_PIXELS:
        raise ValueError(
            "Image dimensions must contain between 655360 and 8294400 pixels"
        )

    return width, height
