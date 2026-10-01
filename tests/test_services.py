"""Tests for the custom image-size AI Task action."""
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.components import ai_task

from custom_components.azure_ai_tasks import services
from custom_components.azure_ai_tasks.const import DOMAIN


@pytest.mark.parametrize("size", [None, "1024x640"])
def test_service_schema_size_is_optional(size: str | None) -> None:
    """The custom action accepts calls with and without a size."""
    data = {"task_name": "test", "instructions": "A landscape"}
    if size is not None:
        data["size"] = size

    validated = services.SERVICE_SCHEMA(data)

    assert validated.get("size") == size


def test_custom_service_registers_in_integration_domain() -> None:
    """The action belongs to the integration so its UI schema can be loaded."""
    hass = MagicMock()
    hass.data = {}

    services.async_register_services(hass, "entry-1")

    assert hass.services.async_register.call_args.args[:2] == (
        DOMAIN,
        services.SERVICE_GENERATE_IMAGE_WITH_SIZE,
    )


def test_custom_service_description_has_form_fields() -> None:
    """The UI-facing service description declares the available form fields."""
    import yaml

    description = yaml.safe_load(
        Path(services.__file__).with_name("services.yaml").read_text()
    )["generate_image_with_size"]

    assert set(description["fields"]) == {
        "task_name",
        "instructions",
        "entity_id",
        "attachments",
        "size",
    }
    assert description["fields"]["size"]["selector"] == {"text": None}


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [None, "1024x640"])
async def test_image_action_passes_optional_size_to_entity(
    monkeypatch: pytest.MonkeyPatch, size: str | None
) -> None:
    """The action forwards its optional size and returns the standard media result."""
    entity = MagicMock()
    entity.supported_features = {
        ai_task.AITaskEntityFeature.GENERATE_IMAGE,
    }
    image_result = MagicMock()
    image_result.as_dict.return_value = {
        "image_data": b"image",
        "revised_prompt": None,
    }
    image_result.mime_type = "image/png"
    entity.internal_async_generate_image = AsyncMock(return_value=image_result)

    component = MagicMock()
    component.get_entity.return_value = entity
    source = MagicMock()
    source.async_upload_media = AsyncMock(return_value="media-source-id")
    source.async_resolve_media = AsyncMock(
        return_value=SimpleNamespace(url="/media/image.png")
    )
    hass = MagicMock()
    hass.data = {
        services.DATA_COMPONENT: component,
        services.DATA_MEDIA_SOURCE: source,
    }
    call = MagicMock()
    call.hass = hass
    call.context = object()
    call.data = {
        "task_name": "test",
        "instructions": "A landscape",
        "entity_id": "ai_task.azure_ai_tasks",
    }
    if size is not None:
        call.data["size"] = size

    monkeypatch.setattr(
        services, "async_get_chat_session", lambda _hass: nullcontext(object())
    )
    monkeypatch.setattr(
        services, "_resolve_attachments", AsyncMock(return_value=[])
    )
    monkeypatch.setattr(
        services,
        "MediaSourceItem",
        SimpleNamespace(from_uri=MagicMock(return_value=object())),
    )
    monkeypatch.setattr(services, "async_sign_path", MagicMock(return_value="/signed"))

    response = await services.async_service_generate_image_with_size(call)

    task = entity.internal_async_generate_image.await_args.args[1]
    assert task.size == size
    assert response["revised_prompt"] == "A landscape"
    assert response["media_source_id"] == "media-source-id"
    assert response["url"] == "/signed"
