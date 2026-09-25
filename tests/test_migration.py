"""Tests for config entry migration.

A migration that returns False - or raises a generic exception - now parks the
entry in the non-recoverable `migration_error` state. These tests pin down which
failures are treated as transient (retried by Home Assistant) and which raise a
repair issue the user can act on.
"""
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.azure_ai_tasks import async_migrate_entry
from custom_components.azure_ai_tasks.const import (
    CONF_API_KEY,
    CONF_ENDPOINT,
    CONFIG_ENTRY_VERSION,
    DOMAIN,
    ISSUE_MIGRATION_DOWNGRADE,
    ISSUE_MIGRATION_INCOMPLETE,
)
from custom_components.azure_ai_tasks.repairs import (
    MigrationRepairFlow,
    async_create_fix_flow,
)

GOOD_CONFIG = {
    CONF_ENDPOINT: "https://my-resource.openai.azure.com",
    CONF_API_KEY: "secret",
    "chat_model": "gpt-4o",
    "image_model": "",
}


def _entry(hass: HomeAssistant, version: int, data: dict, options: dict | None = None):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Azure AI Tasks",
        data=data,
        options=options or {},
        version=version,
    )
    entry.add_to_hass(hass)
    return entry


def _issue_ids(hass: HomeAssistant) -> set[str]:
    from homeassistant.helpers import issue_registry as ir

    return {
        issue.issue_id
        for issue in ir.async_get(hass).issues.values()
        if issue.domain == DOMAIN
    }


async def test_v1_entry_migrates_and_strips_deprecated_model(
    hass: HomeAssistant,
) -> None:
    """The v1 -> v2 migration still does what it always did."""
    entry = _entry(
        hass,
        1,
        {**GOOD_CONFIG, "chat_model": "gpt-35-turbo"},
        {"chat_model": "gpt-35-turbo"},
    )

    assert await async_migrate_entry(hass, entry) is True

    assert entry.version == CONFIG_ENTRY_VERSION
    assert entry.data["chat_model"] == ""
    assert entry.options["chat_model"] == ""
    assert not _issue_ids(hass)


async def test_current_version_entry_is_left_alone(hass: HomeAssistant) -> None:
    """An entry already at the current version migrates cleanly."""
    entry = _entry(hass, CONFIG_ENTRY_VERSION, GOOD_CONFIG)

    assert await async_migrate_entry(hass, entry) is True
    assert entry.data == GOOD_CONFIG


async def test_downgrade_raises_config_entry_error_and_an_issue(
    hass: HomeAssistant,
) -> None:
    """A future entry version is non-recoverable, and says so."""
    entry = _entry(hass, CONFIG_ENTRY_VERSION + 1, GOOD_CONFIG)

    with pytest.raises(ConfigEntryError):
        await async_migrate_entry(hass, entry)

    assert f"{ISSUE_MIGRATION_DOWNGRADE}_{entry.entry_id}" in _issue_ids(hass)


@pytest.mark.parametrize(
    "data",
    [
        {**GOOD_CONFIG, CONF_ENDPOINT: ""},
        {**GOOD_CONFIG, CONF_API_KEY: ""},
        {"chat_model": "gpt-4o"},
    ],
)
async def test_unusable_entry_raises_a_fixable_issue(
    hass: HomeAssistant, data: dict
) -> None:
    """No endpoint or no API key is persistent - raise a repair, not a retry."""
    entry = _entry(hass, 1, data)

    with pytest.raises(ConfigEntryError):
        await async_migrate_entry(hass, entry)

    assert f"{ISSUE_MIGRATION_INCOMPLETE}_{entry.entry_id}" in _issue_ids(hass)


async def test_storage_failure_is_transient(hass: HomeAssistant) -> None:
    """A storage error asks to be retried instead of parking the entry."""
    entry = _entry(hass, 1, GOOD_CONFIG)

    with patch.object(
        hass.config_entries, "async_update_entry", side_effect=OSError("disk full")
    ):
        with pytest.raises(ConfigEntryNotReady):
            await async_migrate_entry(hass, entry)

    # Transient: no repair issue, because there is nothing for the user to do.
    assert not _issue_ids(hass)


async def test_successful_migration_clears_a_previous_issue(
    hass: HomeAssistant,
) -> None:
    """Once the user fixes the config, the repair goes away."""
    entry = _entry(hass, 1, {**GOOD_CONFIG, CONF_API_KEY: ""})

    with pytest.raises(ConfigEntryError):
        await async_migrate_entry(hass, entry)
    assert _issue_ids(hass)

    hass.config_entries.async_update_entry(entry, data=GOOD_CONFIG)
    assert await async_migrate_entry(hass, entry) is True
    assert not _issue_ids(hass)


async def test_fix_flow_retries_the_migration(hass: HomeAssistant) -> None:
    """The repair flow retries the migration for the entry it was raised for."""
    flow = await async_create_fix_flow(
        hass, f"{ISSUE_MIGRATION_INCOMPLETE}_abc", {"entry_id": "abc"}
    )
    assert isinstance(flow, MigrationRepairFlow)
    assert flow.entry_id == "abc"

    flow.hass = hass
    result = await flow.async_step_init()
    assert result["step_id"] == "confirm"

    retry = AsyncMock()
    with patch.object(
        hass.config_entries, "async_retry_migration", retry, create=True
    ):
        await flow.async_step_confirm({})
    retry.assert_awaited_once_with("abc")


async def test_fix_flow_falls_back_to_reload_on_older_cores(
    hass: HomeAssistant,
) -> None:
    """async_retry_migration is newer than our minimum HA; degrade gracefully."""
    flow = MigrationRepairFlow("abc")
    flow.hass = hass

    reload_entry = AsyncMock()
    with patch.object(hass.config_entries, "async_reload", reload_entry):
        # Force the fallback even on a core that does have the newer call.
        with patch.object(
            hass.config_entries, "async_retry_migration", None, create=True
        ):
            await flow.async_step_confirm({})

    reload_entry.assert_awaited_once_with("abc")


async def test_fix_flow_without_entry_id_is_a_confirm(hass: HomeAssistant) -> None:
    """A repair with no entry attached still yields a usable flow."""
    flow = await async_create_fix_flow(hass, ISSUE_MIGRATION_DOWNGRADE, None)
    assert not isinstance(flow, MigrationRepairFlow)
