"""Validation helpers for image generation dimensions."""
from __future__ import annotations

import re

MAX_IMAGE_DIMENSION = 3840
MIN_IMAGE_PIXELS = 655_360
MAX_IMAGE_PIXELS = 8_294_400
_IMAGE_SIZE_PATTERN = re.compile(r"([0-9]+)[x×]([0-9]+)")


def parse_image_size(value: str) -> tuple[int, int]:
    """Parse and validate custom dimensions in WIDTHxHEIGHT format."""
    if not isinstance(value, str):
        raise ValueError(
            "Enter image dimensions as WIDTHxHEIGHT or WIDTH×HEIGHT, "
            "for example 1024x1024"
        )
    match = _IMAGE_SIZE_PATTERN.fullmatch(value.strip())
    if match is None:
        raise ValueError(
            "Enter dimensions as WIDTHxHEIGHT or WIDTH×HEIGHT, for example "
            "1024x1024 or 1200×1600"
        )

    width, height = (int(part) for part in match.groups())
    if width <= 0 or height <= 0:
        raise ValueError(
            "Image width and height must be greater than zero; for GPT-image-2, "
            "each dimension must also be a multiple of 16"
        )
    if width % 16 or height % 16:
        raise ValueError(
            "GPT-image-2 requires both dimensions to be multiples of 16 "
            "(for example, 1200x1600)"
        )
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise ValueError(
            "GPT-image-2 dimensions cannot exceed 3840 pixels on either side; "
            "reduce the width or height"
        )
    if width * 3 < height or height * 3 < width:
        raise ValueError(
            "GPT-image-2 aspect ratio must be between 1:3 and 3:1; "
            "adjust the width or height"
        )
    pixels = width * height
    if not MIN_IMAGE_PIXELS <= pixels <= MAX_IMAGE_PIXELS:
        raise ValueError(
            "GPT-image-2 requires between 655,360 and 8,294,400 total pixels; "
            "increase or reduce the dimensions (for example, 800x832 or 1024x1024)"
        )

    return width, height
