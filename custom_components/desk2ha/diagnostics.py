"""Diagnostics support for Desk2HA."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_AGENT_TOKEN, DOMAIN
from .coordinator import Desk2HACoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: Desk2HACoordinator = hass.data[DOMAIN][entry.entry_id]

    # Redact sensitive data
    data = dict(entry.data)
    if CONF_AGENT_TOKEN in data:
        data[CONF_AGENT_TOKEN] = "**REDACTED**"

    return {
        "config_entry": data,
        "agent_info": coordinator.agent_info,
        "latest_metrics": coordinator.data,
    }
