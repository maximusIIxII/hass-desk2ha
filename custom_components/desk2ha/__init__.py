"""Desk2HA — Multi-vendor desktop monitoring for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

DOMAIN = "desk2ha"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Desk2HA from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    # TODO: Initialize coordinator, set up platforms
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Desk2HA config entry."""
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
