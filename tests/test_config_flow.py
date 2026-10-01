"""Tests for the Azure AI Tasks config flow."""

from unittest.mock import MagicMock

from homeassistant.data_entry_flow import SOURCE_USER
from voluptuous_serialize import convert

from custom_components.azure_ai_tasks.const import DOMAIN
from custom_components.azure_ai_tasks.config_flow import OptionsFlowHandler


async def test_user_flow_schema_is_serializable(
    hass, auto_enable_custom_integrations
) -> None:
    """The frontend can serialize the initial setup form schema."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == "form"
    schema = convert(result["data_schema"])
    assert all(field.get("name") != "image_size" for field in schema)


def test_options_flow_has_no_image_size_option() -> None:
    """The options form no longer exposes a configurable image size."""
    config_entry = MagicMock(options={}, data={})
    schema = convert(OptionsFlowHandler(config_entry)._get_options_schema())

    assert all(field.get("name") != "image_size" for field in schema)
