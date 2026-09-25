"""Repair flows for Azure AI Tasks.

A config entry migration that fails for a persistent reason raises a repair
issue instead of quietly parking the entry (see async_migrate_entry). This is
the flow behind that repair: once the user has fixed the underlying problem it
retries the migration, so they do not have to restart Home Assistant.

See https://developers.home-assistant.io/blog/2026/09/17/Use-config-entry-exc-in-migration
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)


async def _async_retry_migration(hass: HomeAssistant, entry_id: str) -> None:
    """Retry the migration of one config entry.

    `async_retry_migration` is the only way to do this: an entry parked in the
    migration_error state is non-recoverable, so `async_unload` - and therefore
    `async_reload` - raises OperationNotAllowed on it, and a restart is the only
    other thing that re-runs the migration.

    That call is newer than the minimum Home Assistant this integration
    supports, so on an older core we never raise a fixable issue in the first
    place (see `_can_retry_migration` in __init__.py) and this flow is not
    reachable. If it somehow is, fail loudly rather than reporting a fix that
    did not happen.
    """
    retry = getattr(hass.config_entries, "async_retry_migration", None)
    if retry is None:
        raise HomeAssistantError(
            "This version of Home Assistant cannot retry a config entry "
            "migration; restart Home Assistant instead."
        )

    await retry(entry_id)


class MigrationRepairFlow(RepairsFlow):
    """Ask the user to confirm, then retry the migration."""

    def __init__(self, entry_id: str) -> None:
        """Remember which entry this repair is about."""
        self.entry_id = entry_id

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Start the flow."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Retry the migration once the user confirms."""
        if user_input is not None:
            await _async_retry_migration(self.hass, self.entry_id)
            return self.async_create_entry(data={})

        return self.async_show_form(step_id="confirm", data_schema=vol.Schema({}))


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create the flow for a repair issue this integration raised."""
    if data and (entry_id := data.get("entry_id")):
        return MigrationRepairFlow(str(entry_id))

    return ConfirmRepairFlow()
