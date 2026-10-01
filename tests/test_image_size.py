"""Tests for GPT-image-2 request image dimensions."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.azure_ai_tasks import ai_task as ai_task_module
from custom_components.azure_ai_tasks.ai_task import AzureAITaskEntity
from custom_components.azure_ai_tasks.image_size import (
    parse_image_size,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1024x640", (1024, 640)),
        ("1200x1600", (1200, 1600)),
        ("1200×1600", (1200, 1600)),
        ("640x1024", (640, 1024)),
        ("3840x1280", (3840, 1280)),
        ("1280x3840", (1280, 3840)),
        (" 1024x640 ", (1024, 640)),
        ("800x832", (800, 832)),
    ],
)
def test_parse_valid_image_sizes(value: str, expected: tuple[int, int]) -> None:
    """Supported request sizes satisfy every GPT-image-2 constraint."""
    assert parse_image_size(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "800by480",
        "",
        None,
        "800x480",
        "1024x608",
        "0x480",
        "801x480",
        "800x481",
        "3840x2176",
        "4000x1280",
        "384x1152",
        "1152x384",
        "4096x2048",
        "3840x3840",
        "320x1200",
        "1200x320",
    ],
)
def test_parse_rejects_invalid_image_sizes(value: str) -> None:
    """Malformed dimensions and constraint violations are rejected."""
    with pytest.raises(ValueError):
        parse_image_size(value)


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("1200*1600", "WIDTHxHEIGHT or WIDTH×HEIGHT"),
        ("800x480", "655,360 and 8,294,400 total pixels"),
        ("1024x600", "multiples of 16"),
        ("4000x1280", "cannot exceed 3840 pixels"),
        ("368x1152", "aspect ratio must be between 1:3 and 3:1"),
    ],
)
def test_parse_errors_explain_how_to_correct_size(value: str, message: str) -> None:
    """Invalid sizes tell users which GPT-image-2 requirement to fix."""
    with pytest.raises(ValueError, match=message):
        parse_image_size(value)


def test_size_option_is_used_only_for_gpt_image_2() -> None:
    """GPT-image-2 accepts a request size; legacy config values are ignored."""
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

    assert entity._image_size_for_model("gpt-image-2") == "1024x1024"
    assert entity._image_size_for_model("gpt-image-2", "1024x640") == "1024x640"
    assert entity._image_size_for_model("gpt-image-2", "1200×1600") == "1200x1600"
    assert entity._image_size_for_model("gpt-image-2", " 1024x640 ") == "1024x640"
    assert entity._image_size_for_model("dall-e-3", "1024x640") == "1024x1024"
    with pytest.raises(
        HomeAssistantError,
        match="Invalid image size option:.*655,360 and 8,294,400 total pixels",
    ):
        entity._image_size_for_model("gpt-image-2", "800x480")


@pytest.mark.asyncio
async def test_async_image_generation_forwards_task_size(monkeypatch) -> None:
    """Forward an explicit task size when the Home Assistant task provides one."""
    config_entry = MagicMock()
    config_entry.options = {}
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
    session = MagicMock()
    chat_log = MagicMock()
    task = MagicMock(size="1024x640")
    result = object()
    entity._extract_message_and_attachments = MagicMock(
        return_value=("A landscape", [])
    )
    entity._handle_standard_image_generation = AsyncMock(return_value=result)
    monkeypatch.setattr(
        ai_task_module, "async_get_clientsession", lambda _hass: session
    )

    assert await entity._async_generate_image(task, chat_log) is result
    entity._handle_standard_image_generation.assert_awaited_once_with(
        session, "A landscape", "gpt-image-2", chat_log, "1024x640"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("endpoint", "is_v1"),
    [
        ("https://my-resource.openai.azure.com", False),
        ("https://my-resource.services.ai.azure.com", True),
    ],
)
@pytest.mark.parametrize(
    (
        "image_model",
        "requested_size",
        "expected_size",
        "expected_quality",
        "expected_api_version",
    ),
    [
        ("gpt-image-2", "1024x640", "1024x640", "high", "2025-04-01-preview"),
        ("gpt-image-2", None, "1024x1024", "high", "2025-04-01-preview"),
        ("dall-e-3", "1024x640", "1024x1024", "standard", "2024-10-21"),
    ],
)
async def test_standard_image_generation_preserves_model_size_contract(
    endpoint: str,
    is_v1: bool,
    image_model: str,
    requested_size: str | None,
    expected_size: str,
    expected_quality: str,
    expected_api_version: str,
) -> None:
    """Custom sizes reach GPT-image-2 only, on both Azure endpoint surfaces."""
    config_entry = MagicMock()
    config_entry.entry_id = "test-entry"
    config_entry.options = {}
    config_entry.data = {}
    entity = AzureAITaskEntity(
        name="Azure AI Tasks",
        endpoint=endpoint,
        api_key="secret",
        chat_model="",
        image_model=image_model,
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
        session,
        "A landscape",
        image_model,
        MagicMock(),
        requested_size,
    ) is result

    expected_url = (
        f"{endpoint}/openai/v1/images/generations"
        if is_v1
        else f"{endpoint}/openai/deployments/{image_model}/images/generations"
    )
    expected_params = None if is_v1 else {"api-version": expected_api_version}
    assert session.post.call_args.args[0] == expected_url
    assert session.post.call_args.kwargs["params"] == expected_params
    payload = session.post.call_args.kwargs["json"]
    assert payload["size"] == expected_size
    assert payload["quality"] == expected_quality
    assert payload["model"] == image_model
