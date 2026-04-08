"""Desk2HA — Multi-vendor desktop monitoring for Home Assistant."""

from __future__ import annotations

import logging

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
    """Remove orphaned sub-devices (generic USB, duplicates, bare manufacturer names)."""
    dev_registry = dr.async_get(hass)
    ent_registry = er.async_get(hass)
    devices = dr.async_entries_for_config_entry(dev_registry, entry.entry_id)
    removed = 0

    for device in devices:
        name = (device.name or "").lower().strip()

        # Remove devices with generic/orphaned names
        if name in _ORPHANED_DEVICE_NAMES:
            # First remove all entities belonging to this device
            entities = er.async_entries_for_device(ent_registry, device.id)
            for entity in entities:
                ent_registry.async_remove(entity.entity_id)
            dev_registry.async_remove_device(device.id)
            removed += 1
            continue

        # Remove devices that look like duplicates with manufacturer in name
        # e.g. "Dell KM7321W Keyboard" when there's also "KM7321W Keyboard"
        # These are from older entity schemas before _strip_manufacturer_prefix
        if device.manufacturer and name.startswith(device.manufacturer.lower()):
            stripped = name[len(device.manufacturer) :].strip()
            # Check if a device with the stripped name exists
            for other in devices:
                other_name = (other.name or "").lower().strip()
                if other.id != device.id and other_name == stripped:
                    # This is the duplicate with manufacturer prefix — remove it
                    entities = er.async_entries_for_device(ent_registry, device.id)
                    for entity in entities:
                        ent_registry.async_remove(entity.entity_id)
                    dev_registry.async_remove_device(device.id)
                    removed += 1
                    break

    if removed:
        logger.info("Removed %d orphaned/duplicate devices", removed)
