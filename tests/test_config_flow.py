"""Tests for the Azure AI Tasks config flow."""

from homeassistant.data_entry_flow import SOURCE_USER
from voluptuous_serialize import convert

from custom_components.azure_ai_tasks.const import DOMAIN


async def test_user_flow_schema_is_serializable(
    hass, auto_enable_custom_integrations
) -> None:
    """The frontend can serialize the initial setup form schema."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == "form"
    convert(result["data_schema"])


async def test_invalid_image_size_returns_a_flow_error(
    hass, auto_enable_custom_integrations
) -> None:
    """Image size remains validated after switching to a serializable schema."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "name": "Azure AI Tasks",
            "endpoint": "https://my-resource.openai.azure.com",
            "api_key": "secret",
            "chat_model": "gpt-4o",
            "image_model": "",
            "image_size": "801x480",
        },
    )

    assert result["errors"] == {"base": "invalid_image_size"}
