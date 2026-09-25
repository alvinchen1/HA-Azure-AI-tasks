"""The Azure AI Tasks integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, __version__ as ha_version
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)

from .const import (
    CONF_API_KEY,
    CONF_ENDPOINT,
    CONFIG_ENTRY_VERSION,
    DOMAIN,
    ISSUE_MIGRATION_DOWNGRADE,
    ISSUE_MIGRATION_INCOMPLETE,
    ISSUE_MIGRATION_INCOMPLETE_RESTART,
)

PLATFORMS: list[Platform] = [Platform.AI_TASK]

_LOGGER = logging.getLogger(__name__)

# Minimum Home Assistant version required
MIN_HA_VERSION = "2025.10.0"


def _check_ha_version() -> None:
    """Refuse to set up on a Home Assistant older than we support.

    Running on an older core is not something retrying fixes, so this raises
    ConfigEntryError rather than ConfigEntryNotReady. If the version string
    cannot be parsed at all we log and carry on - an unparseable version is not
    evidence that the core is too old.
    """
    from packaging import version

    try:
        current_version = version.parse(ha_version.split(".dev")[0])  # Remove .dev suffix if present
        min_version = version.parse(MIN_HA_VERSION)
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.warning(
            "Unable to verify Home Assistant version compatibility: %s. "
            "Integration may not work correctly if running on older versions.",
            err
        )
        return

    if current_version < min_version:
        raise ConfigEntryError(
            f"Home Assistant {MIN_HA_VERSION} or newer is required. "
            f"Current version: {ha_version}"
        )


def _issue_id(issue: str, config_entry: ConfigEntry) -> str:
    """Issue ID for one entry, so two entries raise two separate repairs."""
    return f"{issue}_{config_entry.entry_id}"


def _clear_migration_issues(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Drop any repair issue a previous migration attempt raised for this entry."""
    for issue in (
        ISSUE_MIGRATION_DOWNGRADE,
        ISSUE_MIGRATION_INCOMPLETE,
        ISSUE_MIGRATION_INCOMPLETE_RESTART,
    ):
        async_delete_issue(hass, DOMAIN, _issue_id(issue, config_entry))


def _can_retry_migration(hass: HomeAssistant) -> bool:
    """Whether this Home Assistant can retry a migration without a restart.

    config_entries.async_retry_migration is newer than the minimum Home
    Assistant this integration supports. Without it there is no way to offer a
    Fix button honestly: an entry in the migration_error state is
    non-recoverable, so async_unload - and therefore async_reload - refuses it,
    and only a restart re-runs the migration.
    """
    return hasattr(hass.config_entries, "async_retry_migration")


def _migrate_v1_to_v2(config_entry: ConfigEntry) -> tuple[dict, dict]:
    """Return the version 2 data and options for a version 1 entry.

    Version 2 drops the deprecated gpt-35-turbo chat model, which Azure has
    retired - an entry still naming it would fail on every request.
    """
    new_data = dict(config_entry.data)
    new_options = dict(config_entry.options)

    for store, label in ((new_data, "data"), (new_options, "options")):
        if store.get("chat_model") == "gpt-35-turbo":
            store["chat_model"] = ""
            _LOGGER.info("Removed deprecated gpt-35-turbo from %s.chat_model", label)

    return new_data, new_options


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate an old config entry to the current version.

    Home Assistant treats a raised ConfigEntryError (or a False return) as
    non-recoverable and parks the entry in the `migration_error` state, so the
    two outcomes are kept distinct here:

    * transient problems raise ConfigEntryNotReady, and Home Assistant retries
      the migration by itself;
    * persistent problems raise a repair issue the user can act on and then
      ConfigEntryError. Fixing the repair retries the migration (see
      repairs.py) rather than making the user restart Home Assistant.

    See https://developers.home-assistant.io/blog/2026/09/17/Use-config-entry-exc-in-migration
    """
    _LOGGER.debug(
        "Migrating Azure AI Tasks config entry %s from version %s to version %s",
        config_entry.entry_id,
        config_entry.version,
        CONFIG_ENTRY_VERSION,
    )

    if config_entry.version > CONFIG_ENTRY_VERSION:
        # The entry was written by a newer release - most likely the user
        # downgraded the integration. Migrating backwards is not something we
        # can do, and retrying will never help, so tell them plainly.
        async_create_issue(
            hass,
            DOMAIN,
            _issue_id(ISSUE_MIGRATION_DOWNGRADE, config_entry),
            is_fixable=False,
            is_persistent=False,
            severity=IssueSeverity.ERROR,
            translation_key=ISSUE_MIGRATION_DOWNGRADE,
            translation_placeholders={
                "title": config_entry.title,
                "entry_version": str(config_entry.version),
                "supported_version": str(CONFIG_ENTRY_VERSION),
            },
        )
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key=ISSUE_MIGRATION_DOWNGRADE,
            translation_placeholders={
                "title": config_entry.title,
                "entry_version": str(config_entry.version),
                "supported_version": str(CONFIG_ENTRY_VERSION),
            },
        )

    if config_entry.version == 1:
        try:
            new_data, new_options = _migrate_v1_to_v2(config_entry)
            hass.config_entries.async_update_entry(
                config_entry,
                data=new_data,
                options=new_options,
                version=CONFIG_ENTRY_VERSION,
            )
        except (OSError, TimeoutError) as err:
            # Writing the entry back touches storage. A disk or timeout error
            # is transient - ask to be retried rather than parking the entry in
            # a state the user has to dig it out of.
            _LOGGER.warning(
                "Azure AI Tasks migration of %s will be retried: %s",
                config_entry.entry_id,
                err,
            )
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="migrate_transient",
            ) from err

        _LOGGER.info(
            "Migrated Azure AI Tasks config entry %s to version %s",
            config_entry.entry_id,
            CONFIG_ENTRY_VERSION,
        )

    # The migrated entry has to be usable. An entry with no endpoint or no API
    # key cannot be set up, and no amount of retrying fixes that - the user has
    # to reconfigure it, so raise a repair that walks them through it.
    if not config_entry.data.get(CONF_ENDPOINT) or not config_entry.data.get(
        CONF_API_KEY
    ):
        _LOGGER.error(
            "Azure AI Tasks config entry %s has no endpoint or API key after migration",
            config_entry.entry_id,
        )
        # Offer a Fix button only where retrying the migration actually works;
        # otherwise raise the variant that tells the user to restart.
        fixable = _can_retry_migration(hass)
        issue = (
            ISSUE_MIGRATION_INCOMPLETE
            if fixable
            else ISSUE_MIGRATION_INCOMPLETE_RESTART
        )
        async_create_issue(
            hass,
            DOMAIN,
            _issue_id(issue, config_entry),
            is_fixable=fixable,
            is_persistent=False,
            severity=IssueSeverity.ERROR,
            translation_key=issue,
            translation_placeholders={"title": config_entry.title},
            data={"entry_id": config_entry.entry_id} if fixable else None,
        )
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key=ISSUE_MIGRATION_INCOMPLETE,
            translation_placeholders={"title": config_entry.title},
        )

    _clear_migration_issues(hass, config_entry)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Azure AI Tasks from a config entry."""
    # Check Home Assistant version compatibility
    _check_ha_version()
    
    # Set up the integration
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # Forward entry setup to AI task platform
    await hass.config_entries.async_forward_entry_setups(entry, ["ai_task"])
    
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    _LOGGER.info("Azure AI Tasks options updated for entry %s", entry.entry_id)
    _LOGGER.info("New options: %s", entry.options)
    # Reload the integration when options change
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok