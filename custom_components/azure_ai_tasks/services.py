"""Custom AI Task services for Azure AI Tasks."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import io
import mimetypes
from typing import Any

import voluptuous as vol

from homeassistant.components import ai_task
from homeassistant.components.ai_task.task import (
    DATA_COMPONENT,
    DATA_MEDIA_SOURCE,
    DATA_PREFERENCES,
    DOMAIN as AI_TASK_DOMAIN,
    IMAGE_DIR,
    IMAGE_EXPIRY_TIME,
    ImageData,
    _resolve_attachments,
)
from homeassistant.components.media_source import MediaSourceItem
from homeassistant.components.http.auth import async_sign_path
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, selector
from homeassistant.helpers.chat_session import async_get_chat_session
from homeassistant.util import RE_SANITIZE_FILENAME, dt as dt_util, slugify

SERVICE_GENERATE_IMAGE_WITH_SIZE = "generate_image_with_size"
DATA_SERVICE_ENTRY_IDS = f"{AI_TASK_DOMAIN}_image_size_service_entries"


@dataclass(slots=True)
class _SizedGenImageTask(ai_task.GenImageTask):
    """Image task carrying the optional size through the entity API."""

    size: str | None = None


SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("task_name"): cv.string,
        vol.Optional("entity_id"): cv.entity_id,
        vol.Required("instructions"): cv.string,
        vol.Optional("attachments"): selector.MediaSelector(
            {"accept": ["*/*"], "multiple": True}
        ),
        vol.Optional("size"): cv.string,
    }
)


async def async_service_generate_image_with_size(
    call: ServiceCall,
) -> dict[str, Any]:
    """Run image generation with an optional size passed to the AI Task entity."""
    hass = call.hass
    entity_id = call.data.get("entity_id")
    if entity_id is None:
        entity_id = hass.data[DATA_PREFERENCES].gen_image_entity_id
    if entity_id is None:
        raise HomeAssistantError("No entity_id provided and no preferred entity set")

    entity = hass.data[DATA_COMPONENT].get_entity(entity_id)
    if entity is None:
        raise HomeAssistantError(f"AI Task entity {entity_id} not found")
    if ai_task.AITaskEntityFeature.GENERATE_IMAGE not in entity.supported_features:
        raise HomeAssistantError(
            f"AI Task entity {entity_id} does not support generating images"
        )

    attachments = call.data.get("attachments")
    if (
        attachments
        and ai_task.AITaskEntityFeature.SUPPORT_ATTACHMENTS
        not in entity.supported_features
    ):
        raise HomeAssistantError(
            f"AI Task entity {entity_id} does not support attachments"
        )

    task_name = call.data["task_name"]
    instructions = call.data["instructions"]
    with async_get_chat_session(hass) as session:
        resolved_attachments = await _resolve_attachments(
            hass, session, attachments
        )
        task_result = await entity.internal_async_generate_image(
            session,
            _SizedGenImageTask(
                name=task_name,
                instructions=instructions,
                attachments=resolved_attachments or None,
                size=call.data.get("size"),
            ),
        )

    service_result = task_result.as_dict()
    image_data = service_result.pop("image_data")
    if service_result.get("revised_prompt") is None:
        service_result["revised_prompt"] = instructions

    source = hass.data[DATA_MEDIA_SOURCE]
    current_time = dt_util.now()
    extension = mimetypes.guess_extension(task_result.mime_type, False) or ".png"
    sanitized_task_name = RE_SANITIZE_FILENAME.sub("", slugify(task_name))
    image_file = ImageData(
        filename=f"{current_time.strftime('%Y-%m-%d_%H%M%S')}_{sanitized_task_name}{extension}",
        file=io.BytesIO(image_data),
        content_type=task_result.mime_type,
    )
    target_folder = MediaSourceItem.from_uri(
        hass, f"media-source://{AI_TASK_DOMAIN}/{IMAGE_DIR}", None
    )
    service_result["media_source_id"] = await source.async_upload_media(
        target_folder, image_file
    )

    item = MediaSourceItem.from_uri(hass, service_result["media_source_id"], None)
    service_result["url"] = async_sign_path(
        hass,
        (await source.async_resolve_media(item)).url,
        timedelta(seconds=IMAGE_EXPIRY_TIME),
    )
    return service_result


def async_register_services(hass: HomeAssistant, entry_id: str) -> None:
    """Register the custom AI Task service once for all config entries."""
    entry_ids = hass.data.get(DATA_SERVICE_ENTRY_IDS)
    if not entry_ids:
        if hass.services.has_service(AI_TASK_DOMAIN, SERVICE_GENERATE_IMAGE_WITH_SIZE):
            raise HomeAssistantError(
                f"Service {AI_TASK_DOMAIN}.{SERVICE_GENERATE_IMAGE_WITH_SIZE} "
                "is already registered"
            )
        hass.services.async_register(
            AI_TASK_DOMAIN,
            SERVICE_GENERATE_IMAGE_WITH_SIZE,
            async_service_generate_image_with_size,
            schema=SERVICE_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )
        entry_ids = hass.data[DATA_SERVICE_ENTRY_IDS] = set()
    entry_ids.add(entry_id)


def async_unregister_services(hass: HomeAssistant, entry_id: str) -> None:
    """Unregister the custom AI Task service."""
    entry_ids = hass.data.get(DATA_SERVICE_ENTRY_IDS)
    if not entry_ids or entry_id not in entry_ids:
        return
    entry_ids.remove(entry_id)
    if not entry_ids:
        if hass.services.has_service(AI_TASK_DOMAIN, SERVICE_GENERATE_IMAGE_WITH_SIZE):
            hass.services.async_remove(
                AI_TASK_DOMAIN, SERVICE_GENERATE_IMAGE_WITH_SIZE
            )
        hass.data.pop(DATA_SERVICE_ENTRY_IDS, None)
