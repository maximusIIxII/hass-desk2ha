"""Desk2HA — Multi-vendor desktop monitoring for Home Assistant."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, PLATFORMS
from .coordinator import Desk2HACoordinator

logger = logging.getLogger(__name__)

# unique_id patterns from v0.1.0-S1 that no longer match active entities.
_ORPHANED_UNIQUE_IDS = {
    "power_source_binary",
}

# Device names that indicate generic/orphaned sub-devices to remove.
_ORPHANED_DEVICE_NAMES = {
    "usb-eingabegerät",
    "usb-verbundgerät",
    "usb input device",
    "usb composite device",
    "logitech",  # bare "Logitech" with no model
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Desk2HA from a config entry."""
    coordinator = Desk2HACoordinator(hass, entry)

    # Fetch initial data
    await coordinator.fetch_info()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Register services (only once, on first entry)
    if len(hass.data[DOMAIN]) == 1:
        from .services import async_setup_services

        await async_setup_services(hass)

    # Clean up orphaned entities and devices from previous versions
    _cleanup_orphaned_entities(hass, entry)
    _cleanup_orphaned_devices(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Desk2HA config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: Desk2HACoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()

        # Unregister services when last entry is removed
        if not hass.data[DOMAIN]:
            from .services import async_unload_services

            await async_unload_services(hass)

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


def _cleanup_orphaned_devices(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove orphaned sub-devices (generic USB, duplicates, stale names)."""
    dev_registry = dr.async_get(hass)
    ent_registry = er.async_get(hass)
    devices = list(dr.async_entries_for_config_entry(dev_registry, entry.entry_id))
    removed_ids: set[str] = set()

    def _remove_device(device: Any) -> None:
        entities = er.async_entries_for_device(ent_registry, device.id)
        for entity in entities:
            ent_registry.async_remove(entity.entity_id)
        dev_registry.async_remove_device(device.id)
        removed_ids.add(device.id)

    for device in devices:
        if device.id in removed_ids:
            continue
        name = (device.name or "").lower().strip()

        # 1. Remove devices with generic/orphaned names
        if name in _ORPHANED_DEVICE_NAMES:
            _remove_device(device)
            continue

        # 2. Remove devices with manufacturer repeated in name
        #    e.g. name="Logitech Litra Glow" + manufacturer="Logitech"
        #    HA shows "Logitech Logitech Litra Glow"
        if device.manufacturer:
            mfg = device.manufacturer.lower()
            if name.startswith(mfg + " "):
                _remove_device(device)
                continue

    # 3. Deduplicate: same model shown as two devices (old vs new schema)
    #    Keep the device with more entities, remove the other
    remaining = [d for d in devices if d.id not in removed_ids]
    seen_models: dict[str, Any] = {}
    for device in remaining:
        # Use model as dedup key (more stable than name)
        model = (device.model or device.name or "").lower().strip()
        if not model:
            continue
        entity_count = len(er.async_entries_for_device(ent_registry, device.id))

        if model in seen_models:
            prev_device, prev_count = seen_models[model]
            # Keep the one with more entities
            if entity_count > prev_count:
                _remove_device(prev_device)
                seen_models[model] = (device, entity_count)
            else:
                _remove_device(device)
        else:
            seen_models[model] = (device, entity_count)

    if removed_ids:
        logger.info("Removed %d orphaned/duplicate devices", len(removed_ids))
