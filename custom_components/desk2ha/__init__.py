"""Desk2HA — Multi-vendor desktop monitoring for Home Assistant."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, PLATFORMS
from .coordinator import Desk2HACoordinator

logger = logging.getLogger(__name__)

CARD_JS = Path(__file__).parent / "card" / "desk2ha-card.js"
CARD_URL_PATH = f"/{DOMAIN}/desk2ha-card.js"

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
    "usb-massenspeichergerät",
    "usb-massenspeichergerat",
    "usb mass storage device",
    "kompatibles usb-speichergerät",
    "universal receiver",  # suppressed on agent side since v0.8.0
}

# Manufacturer names that are actually Windows driver class names, not real manufacturers.
_DRIVER_CLASS_MANUFACTURERS = {
    "winusb-gerät",
    "winusb-gerat",
    "winusb device",
    "kompatibles usb-speichergerät",
    "kompatibles usb-speichergerat",
    "compatible usb storage device",
    "(standardsystemgeräte)",
    "(standard system devices)",
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Desk2HA from a config entry."""
    coordinator = Desk2HACoordinator(hass, entry)

    # Fetch initial data — raise ConfigEntryNotReady so HA retries instead of
    # marking the entry as permanently broken when the agent is unreachable.
    try:
        await coordinator.fetch_info()
    except Exception as exc:
        raise ConfigEntryNotReady(f"Cannot reach agent: {exc}") from exc
    await coordinator.async_config_entry_first_refresh()

    # Migrate: set unique_id if missing (entries created before v0.7.1)
    if not entry.unique_id and coordinator.device_key != "unknown":
        hass.config_entries.async_update_entry(entry, unique_id=coordinator.device_key)
        logger.info("Migrated unique_id to %s", coordinator.device_key)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Register services, card, and install server (only once, on first entry)
    if len(hass.data[DOMAIN]) == 1:
        from .services import async_setup_services

        await async_setup_services(hass)
        await _register_card(hass)
        _register_install_server(hass)

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


def _register_install_server(hass: HomeAssistant) -> None:
    """Set up the install page server for agent distribution."""
    from .install_server import InstallServer

    if f"{DOMAIN}_install_server" not in hass.data:
        server = InstallServer(hass)
        server.register_routes(hass.http.app)
        hass.data[f"{DOMAIN}_install_server"] = server
        logger.info("Install server ready")


async def _register_card(hass: HomeAssistant) -> None:
    """Serve the Lovelace card JS file via HA's HTTP server."""
    if CARD_JS.is_file():
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL_PATH, str(CARD_JS), cache_headers=False)]
        )
        logger.info("Registered Lovelace card at %s", CARD_URL_PATH)


def _cleanup_orphaned_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove entity registry entries that belong to removed/renamed definitions."""
    import re

    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, entry.entry_id)
    removed = 0

    # Pattern for old index-based USB peripheral IDs (e.g. peripheral_usb_0_model)
    # These were replaced by VID:PID-based IDs in v0.8.1 (peripheral_usb_413c_c015_model)
    _OLD_USB_INDEX_PATTERN = re.compile(r"peripheral_usb_\d+_")
    # Pattern for old receiver IDs (suppressed in v0.8.0)
    _OLD_RECEIVER_PATTERN = re.compile(r"peripheral_receiver_\d+_")

    for entity in entities:
        if not entity.unique_id:
            continue
        # Check if unique_id suffix matches a known orphan pattern
        for orphan_suffix in _ORPHANED_UNIQUE_IDS:
            if entity.unique_id.endswith(orphan_suffix):
                registry.async_remove(entity.entity_id)
                removed += 1
                break
        else:
            # Remove old index-based USB and receiver entities
            uid = entity.unique_id
            if _OLD_USB_INDEX_PATTERN.search(uid) or _OLD_RECEIVER_PATTERN.search(uid):
                registry.async_remove(entity.entity_id)
                removed += 1

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
        try:
            dev_registry.async_remove_device(device.id)
        except Exception:
            logger.warning("Cleanup: could not remove device %s", device.id, exc_info=True)
        removed_ids.add(device.id)

    for device in devices:
        if device.id in removed_ids:
            continue
        name = (device.name or "").lower().strip()

        # 1. Remove devices with generic/orphaned names
        if name in _ORPHANED_DEVICE_NAMES:
            _remove_device(device)
            continue

        # 1b. Remove devices whose manufacturer is a Windows driver class name
        mfg_lower = (device.manufacturer or "").lower().strip()
        if mfg_lower in _DRIVER_CLASS_MANUFACTURERS:
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

    # 3. Deduplicate: same device shown twice (old vs new schema)
    #    Match by name (what HA displays), keep the one with more entities
    remaining = [d for d in devices if d.id not in removed_ids]
    seen_names: dict[str, Any] = {}
    for device in remaining:
        # Normalize: strip manufacturer prefix from name for matching
        name = (device.name or "").lower().strip()
        if device.manufacturer:
            mfg = device.manufacturer.lower()
            if name.startswith(mfg + " "):
                name = name[len(mfg) :].strip()
        if not name:
            continue
        entity_count = len(er.async_entries_for_device(ent_registry, device.id))

        if name in seen_names:
            prev_device, prev_count = seen_names[name]
            # Keep the one with more entities
            if entity_count > prev_count:
                _remove_device(prev_device)
                seen_names[name] = (device, entity_count)
            else:
                _remove_device(device)
        else:
            seen_names[name] = (device, entity_count)

    if removed_ids:
        logger.info("Removed %d orphaned/duplicate devices", len(removed_ids))
