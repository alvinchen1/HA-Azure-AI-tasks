"""Tests for GPT-image-2 custom image dimensions."""
from unittest.mock import AsyncMock, MagicMock

import pytest
import voluptuous as vol

from custom_components.azure_ai_tasks.ai_task import AzureAITaskEntity
from custom_components.azure_ai_tasks.image_size import (
    parse_image_size,
    validate_image_size,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("800x480", (800, 480)),
        ("1200x1600", (1200, 1600)),
        ("3840x1280", (3840, 1280)),
        ("720x2160", (720, 2160)),
        (" 800x480 ", (800, 480)),
    ],
)
def test_parse_valid_image_sizes(value: str, expected: tuple[int, int]) -> None:
    """Supported custom sizes satisfy every model constraint."""
    assert parse_image_size(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "800by480",
        "",
        None,
        "0x480",
        "801x480",
        "800x481",
        "800x2400",
        "4000x1200",
        "800x2161",
        "320x1200",
        "1200x320",
    ],
)
def test_parse_rejects_invalid_image_sizes(value: str) -> None:
    """Malformed dimensions and constraint violations are rejected."""
    with pytest.raises(ValueError):
        parse_image_size(value)


def test_voluptuous_validator_normalizes_size() -> None:
    """Config entries store the validated size in canonical form."""
    assert validate_image_size(" 800x480 ") == "800x480"
    with pytest.raises(vol.Invalid):
        validate_image_size("801x480")


def test_custom_size_is_selected_only_for_gpt_image_2() -> None:
    """Other image models keep their established default size."""
    config_entry = MagicMock()
    config_entry.options = {}
    config_entry.data = {"image_size": "1200x1600"}
    entity = AzureAITaskEntity(
        "Azure AI Tasks",
        "https://my-resource.openai.azure.com",
        "secret",
        "",
        "gpt-image-2",
        MagicMock(),
        config_entry,
    )

    assert entity._image_size_for_model("gpt-image-2") == "1200x1600"
    assert entity._image_size_for_model("dall-e-3") == "1024x1024"


@pytest.mark.asyncio
async def test_gpt_image_2_request_uses_configured_size() -> None:
    """The custom dimensions reach Azure in the GPT-image-2 request payload."""
    config_entry = MagicMock()
    config_entry.entry_id = "test-entry"
    config_entry.options = {"image_size": "800x480"}
    config_entry.data = {}
    entity = AzureAITaskEntity(
        name="Azure AI Tasks",
        endpoint="https://my-resource.openai.azure.com",
        api_key="secret",
        chat_model="",
        image_model="gpt-image-2",
        hass=MagicMock(),
        config_entry=config_entry,
    )
    result = object()
    entity._process_image_generation_result = AsyncMock(return_value=result)
    response = MagicMock()
    response.status = 200
    response.json = AsyncMock(return_value={})
    response_context = MagicMock()
    response_context.__aenter__ = AsyncMock(return_value=response)
    response_context.__aexit__ = AsyncMock(return_value=None)
    session = MagicMock()
    session.post.return_value = response_context

    assert await entity._handle_standard_image_generation(
        session, "A landscape", "gpt-image-2", MagicMock()
    ) is result

    payload = session.post.call_args.kwargs["json"]
    assert payload["size"] == "800x480"
    assert payload["quality"] == "high"
