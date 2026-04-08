"""Desk2HA — Multi-vendor desktop monitoring for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, PLATFORMS
from .coordinator import Desk2HACoordinator

logger = logging.getLogger(__name__)

# unique_id patterns from v0.1.0-S1 that no longer match active entities.
# These were replaced by dynamic entity creation in S2.
_ORPHANED_UNIQUE_IDS = {
    # Old binary_sensor based on power.source (now uses battery.state)
    "power_source_binary",
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Desk2HA from a config entry."""
    coordinator = Desk2HACoordinator(hass, entry)

    # Fetch initial data
    await coordinator.fetch_info()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Clean up orphaned entities from previous versions
    _cleanup_orphaned_entities(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Desk2HA config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: Desk2HACoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
    return unload_ok


def _cleanup_orphaned_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove entity registry entries that belong to removed/renamed definitions."""
    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, entry.entry_id)
    removed = 0

    for entity in entities:
        if not entity.unique_id:
            continue
        # Check if unique_id suffix matches a known orphan pattern
        for orphan_suffix in _ORPHANED_UNIQUE_IDS:
            if entity.unique_id.endswith(orphan_suffix):
                registry.async_remove(entity.entity_id)
                removed += 1
                break

    if removed:
        logger.info("Removed %d orphaned entity registry entries", removed)
