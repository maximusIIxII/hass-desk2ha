"""Diagnostics support for Desk2HA."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import CONF_AGENT_TOKEN, DOMAIN
from .coordinator import Desk2HACoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: Desk2HACoordinator = hass.data[DOMAIN][entry.entry_id]

    # Redact sensitive data
    config = dict(entry.data)
    if CONF_AGENT_TOKEN in config:
        config[CONF_AGENT_TOKEN] = "**REDACTED**"

    # Count entities by domain
    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, entry.entry_id)
    entity_counts: dict[str, int] = {}
    for e in entities:
        domain = e.entity_id.split(".")[0]
        entity_counts[domain] = entity_counts.get(domain, 0) + 1

    # Try to get update info
    update_info: dict[str, Any] = {}
    try:
        update_info = await coordinator.async_check_update()
    except Exception:
        update_info = {"error": "could not reach update endpoint"}

    return {
        "config_entry": config,
        "agent_info": coordinator.agent_info,
        "latest_metrics": coordinator.data,
        "update_info": update_info,
        "entity_counts": entity_counts,
        "total_entities": len(entities),
    }
