"""Desk2HA service calls for fleet management and agent control."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN
from .coordinator import Desk2HACoordinator

logger = logging.getLogger(__name__)

SERVICE_FLEET_STATUS = "fleet_status"
SERVICE_REFRESH = "refresh"
SERVICE_RESTART_AGENT = "restart_agent"
SERVICE_FETCH_IMAGES = "fetch_product_images"
SERVICE_WAKE_ON_LAN = "wake_on_lan"
SERVICE_HEALTH_CHECK = "device_health_check"

FLEET_STATUS_SCHEMA = vol.Schema({})
REFRESH_SCHEMA = vol.Schema(
    {
        vol.Optional("device_key"): str,
    }
)
RESTART_SCHEMA = vol.Schema(
    {
        vol.Required("device_key"): str,
    }
)
WOL_SCHEMA = vol.Schema(
    {
        vol.Required("device_key"): str,
        vol.Required("mac"): str,
    }
)


def _get_coordinators(hass: HomeAssistant) -> dict[str, Desk2HACoordinator]:
    """Get all active Desk2HA coordinators keyed by device_key."""
    coordinators: dict[str, Desk2HACoordinator] = {}
    domain_data = hass.data.get(DOMAIN, {})
    for _entry_id, coordinator in domain_data.items():
        if isinstance(coordinator, Desk2HACoordinator):
            coordinators[coordinator.device_key] = coordinator
    return coordinators


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register Desk2HA services."""

    async def handle_fleet_status(call: ServiceCall) -> dict[str, Any]:
        """Return status of all configured desks."""
        coordinators = _get_coordinators(hass)
        fleet: list[dict[str, Any]] = []

        for device_key, coordinator in coordinators.items():
            desk: dict[str, Any] = {
                "device_key": device_key,
                "online": coordinator.last_update_success,
                "last_update": coordinator.last_update.isoformat()
                if coordinator.last_update
                else None,
            }

            info = coordinator.agent_info
            if info:
                hw = info.get("hardware", {})
                desk["manufacturer"] = hw.get("manufacturer", "")
                desk["model"] = hw.get("model", "")
                desk["agent_version"] = info.get("agent_version", "")
                desk["collectors"] = [c.get("name", "") for c in info.get("collectors", [])]

            fleet.append(desk)

        result = {
            "total_desks": len(fleet),
            "online": sum(1 for d in fleet if d.get("online")),
            "offline": sum(1 for d in fleet if not d.get("online")),
            "desks": fleet,
        }

        hass.bus.async_fire(f"{DOMAIN}_fleet_status", result)
        return result

    async def handle_refresh(call: ServiceCall) -> None:
        """Force-refresh one or all desks."""
        device_key = call.data.get("device_key")
        coordinators = _get_coordinators(hass)

        if device_key:
            coordinator = coordinators.get(device_key)
            if coordinator:
                await coordinator.async_request_refresh()
                logger.info("Refreshed desk %s", device_key)
        else:
            for coordinator in coordinators.values():
                await coordinator.async_request_refresh()
            logger.info("Refreshed all %d desks", len(coordinators))

    async def handle_restart_agent(call: ServiceCall) -> None:
        """Send restart command to a specific agent."""
        import aiohttp

        device_key = call.data["device_key"]
        coordinators = _get_coordinators(hass)
        coordinator = coordinators.get(device_key)

        if coordinator is None:
            logger.warning("Desk %s not found", device_key)
            return

        url = coordinator.agent_url
        token = coordinator.agent_token

        try:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            async with (
                aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session,
                session.post(
                    f"{url}/v1/commands",
                    json={"command": "agent.restart"},
                    headers=headers,
                ) as resp,
            ):
                result = await resp.json()
                logger.info("Restart agent %s: %s", device_key, result)
        except Exception:
            logger.exception("Failed to restart agent %s", device_key)

    async def handle_fetch_images(call: ServiceCall) -> None:
        """Fetch product images for all configured desks."""
        import aiohttp

        from .images.cache import ImageCache
        from .images.resolver import resolve_image_url

        cache_dir = (
            Path(hass.config.config_dir) / "custom_components" / DOMAIN / "images" / "cache"
        )
        cache = ImageCache(cache_dir)
        coordinators = _get_coordinators(hass)
        fetched = 0

        async with aiohttp.ClientSession() as session:
            for device_key, coordinator in coordinators.items():
                # Skip if already cached
                if cache.get(device_key):
                    logger.debug("Image already cached for %s", device_key)
                    continue

                # Build device info from agent_info
                info = coordinator.agent_info
                if not info:
                    continue

                hw = info.get("hardware", {})
                identity = info.get("identity", {})
                device_info = {
                    "manufacturer": hw.get("manufacturer", ""),
                    "model": hw.get("model", ""),
                    "service_tag": (
                        identity.get("serial_number", "") or identity.get("service_tag", "")
                    ),
                }

                url = await resolve_image_url(device_info, session)
                if url:
                    result = await cache.fetch_and_store(device_key, url, session)
                    if result:
                        fetched += 1

        logger.info("Fetched %d product images for %d desks", fetched, len(coordinators))

    hass.services.async_register(
        DOMAIN, SERVICE_FLEET_STATUS, handle_fleet_status, schema=FLEET_STATUS_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_REFRESH, handle_refresh, schema=REFRESH_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_RESTART_AGENT, handle_restart_agent, schema=RESTART_SCHEMA
    )

    async def handle_wake_on_lan(call: ServiceCall) -> None:
        """Send Wake-on-LAN magic packet via a specific agent."""
        import aiohttp

        device_key = call.data["device_key"]
        mac = call.data["mac"]
        coordinators = _get_coordinators(hass)
        coordinator = coordinators.get(device_key)

        if coordinator is None:
            logger.warning("Desk %s not found for WoL", device_key)
            return

        url = coordinator.agent_url
        token = coordinator.agent_token

        try:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            async with (
                aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session,
                session.post(
                    f"{url}/v1/commands",
                    json={
                        "command": "remote.wake_on_lan",
                        "parameters": {"mac": mac},
                    },
                    headers=headers,
                ) as resp,
            ):
                result = await resp.json()
                logger.info("WoL via %s to %s: %s", device_key, mac, result)
        except Exception:
            logger.exception("WoL failed via %s", device_key)

    async def handle_health_check(call: ServiceCall) -> None:
        """Scan all devices for issues and optionally auto-fix them.

        Checks performed:
        1. Bad/generic device names (raw IDs, error strings)
        2. Missing manufacturer on sub-devices
        3. Orphan devices with 0 entities
        4. Duplicate manufacturer in device name
        5. Entity availability (unavailable/unknown states)
        6. Stale/disconnected devices (ALL entities unavailable)
        7. Disabled/orphaned entities (delete instead of accumulating)
        """
        from homeassistant.helpers import device_registry as dr
        from homeassistant.helpers import entity_registry as er

        auto_fix = call.data.get("auto_fix", True)
        dev_registry = dr.async_get(hass)
        ent_registry = er.async_get(hass)

        issues: list[dict[str, Any]] = []
        fixed: list[dict[str, Any]] = []

        # Patterns indicating problematic device names
        _BAD_NAME_PATTERNS = [
            "peripheral.",
            "webcam_",
            "unbekanntes usb",
            "unknown usb",
            "fehler beim anfordern",
            "device descriptor request",
        ]

        def _remove_device(device: Any, reason: str) -> None:
            """Remove a device and all its entities."""
            entities = er.async_entries_for_device(ent_registry, device.id)
            for entity in entities:
                ent_registry.async_remove(entity.entity_id)
            dev_registry.async_remove_device(device.id)
            fixed.append(
                {
                    "device_id": device.id,
                    "device_name": device.name or "",
                    "issue": reason,
                    "action": f"removed ({len(entities)} entities)",
                }
            )

        # Collect currently reported peripheral IDs from all coordinators
        active_peripheral_ids: set[str] = set()
        for _entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
            if not isinstance(coordinator, Desk2HACoordinator):
                continue
            data = coordinator.data or {}
            for peripheral in data.get("peripherals", []):
                if isinstance(peripheral, dict) and peripheral.get("id"):
                    active_peripheral_ids.add(f"{coordinator.device_key}_{peripheral['id']}")

        for _entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
            if not isinstance(coordinator, Desk2HACoordinator):
                continue

            config_entry = coordinator.config_entry
            if not config_entry:
                continue

            devices = dr.async_entries_for_config_entry(dev_registry, config_entry.entry_id)

            for device in devices:
                name = (device.name or "").strip()
                name_lower = name.lower()
                mfg = device.manufacturer or ""
                entities = er.async_entries_for_device(ent_registry, device.id)
                entity_count = len(entities)

                # ── Check 1: Bad/generic device name ──
                if any(p in name_lower for p in _BAD_NAME_PATTERNS):
                    issue = {
                        "device_id": device.id,
                        "device_name": name,
                        "issue": "generic_or_error_name",
                        "detail": f"Name '{name}' is a raw ID or error string",
                    }
                    issues.append(issue)
                    if auto_fix and entity_count == 0:
                        _remove_device(device, "generic_or_error_name")

                # ── Check 2: Missing manufacturer ──
                if not mfg and device.via_device_id:
                    issues.append(
                        {
                            "device_id": device.id,
                            "device_name": name,
                            "issue": "missing_manufacturer",
                            "detail": "No manufacturer set on sub-device",
                        }
                    )

                # ── Check 3: Orphan device with 0 entities ──
                if entity_count == 0 and device.via_device_id:
                    issue = {
                        "device_id": device.id,
                        "device_name": name,
                        "issue": "orphan_no_entities",
                        "detail": "Sub-device has 0 entities",
                    }
                    issues.append(issue)
                    if auto_fix:
                        _remove_device(device, "orphan_no_entities")
                        continue

                # ── Check 4: Duplicate manufacturer in name (sub-devices only) ──
                # Skip host devices — HA displays "{manufacturer} {name}" automatically
                if mfg and name_lower.startswith(mfg.lower() + " ") and device.via_device_id:
                    issue = {
                        "device_id": device.id,
                        "device_name": name,
                        "issue": "duplicate_manufacturer_in_name",
                        "detail": f"Name starts with manufacturer '{mfg}'",
                    }
                    issues.append(issue)
                    if auto_fix:
                        clean_name = name[len(mfg) :].strip()
                        if clean_name:
                            dev_registry.async_update_device(device.id, name=clean_name)
                            fixed.append(
                                {
                                    **issue,
                                    "action": f"renamed to '{clean_name}'",
                                }
                            )

                # ── Check 5: Stale device (ALL entities unavailable + not reported) ──
                if entity_count > 0 and device.via_device_id:
                    unavailable_entities = []
                    for entity in entities:
                        state = hass.states.get(entity.entity_id)
                        if state and state.state in ("unavailable", "unknown"):
                            unavailable_entities.append(entity.entity_id)

                    if len(unavailable_entities) == entity_count:
                        # ALL entities are unavailable — check if agent still reports it
                        dev_identifiers = device.identifiers or set()
                        is_active = False
                        for domain, identifier in dev_identifiers:
                            if domain == DOMAIN and identifier in active_peripheral_ids:
                                is_active = True
                                break

                        if not is_active:
                            issue = {
                                "device_id": device.id,
                                "device_name": name,
                                "issue": "stale_disconnected",
                                "detail": (
                                    f"All {entity_count} entities unavailable "
                                    f"and device not reported by agent"
                                ),
                            }
                            issues.append(issue)
                            if auto_fix:
                                _remove_device(device, "stale_disconnected")

                # Note: Partial unavailability (device on but some entities unavailable)
                # is expected behavior — e.g. Litra off (no brightness), monitor without
                # DCM helper (no thermals). We don't report these as issues.

        # ── Check 7: Disabled/orphaned entities — delete instead of accumulating ──
        disabled_removed = 0
        for _entry_id2, coordinator2 in hass.data.get(DOMAIN, {}).items():
            if not isinstance(coordinator2, Desk2HACoordinator):
                continue
            config_entry2 = coordinator2.config_entry
            if not config_entry2:
                continue
            all_entities = er.async_entries_for_config_entry(ent_registry, config_entry2.entry_id)
            for entity in all_entities:
                should_remove = False

                # 7a: Disabled entities — no longer needed, delete them
                if entity.disabled_by is not None:
                    should_remove = True

                # 7b: Entity whose state is unavailable and not in agent data
                if not should_remove:
                    state = hass.states.get(entity.entity_id)
                    if state and state.state == "unavailable":
                        # Check if this entity's metric is in current data
                        data = coordinator2.data or {}
                        uid = entity.unique_id or ""
                        # Peripheral entities contain the peripheral ID
                        is_orphan_peripheral = False
                        for suffix in (
                            "hp_officejet",
                            "peripheral_usb_0_",
                            "peripheral_usb_1_",
                            "peripheral_usb_2_",
                            "peripheral_usb_3_",
                            "peripheral_usb_4_",
                            "peripheral_usb_5_",
                            "peripheral_receiver_",
                        ):
                            if suffix in uid.lower():
                                is_orphan_peripheral = True
                                break
                        if is_orphan_peripheral:
                            should_remove = True

                if should_remove and auto_fix:
                    ent_registry.async_remove(entity.entity_id)
                    disabled_removed += 1

        if disabled_removed:
            issues.append(
                {
                    "device_id": "",
                    "device_name": "",
                    "issue": "disabled_or_orphan_entities_cleaned",
                    "detail": f"Removed {disabled_removed} disabled/orphaned entities",
                }
            )
            fixed.append(
                {
                    "device_id": "",
                    "device_name": "",
                    "issue": "disabled_or_orphan_entities_cleaned",
                    "action": f"deleted {disabled_removed} entities",
                }
            )
            logger.info("Cleaned up %d disabled/orphaned entities", disabled_removed)

        report = {
            "total_issues": len(issues),
            "total_fixed": len(fixed),
            "issues": issues,
            "fixed": fixed,
        }

        hass.bus.async_fire(f"{DOMAIN}_health_report", report)
        logger.info(
            "Device health check: %d issues found, %d auto-fixed",
            len(issues),
            len(fixed),
        )

        # Create persistent notification with results summary
        lines: list[str] = []
        if fixed:
            lines.append(f"**Auto-fixed {len(fixed)} issue(s):**")
            for f_item in fixed:
                lines.append(
                    f"- {f_item.get('device_name', '?')}: "
                    f"{f_item.get('action', f_item.get('issue', ''))}"
                )
        remaining = [
            i
            for i in issues
            if not any(
                f_item.get("device_id") == i.get("device_id")
                and f_item.get("issue") == i.get("issue")
                for f_item in fixed
            )
        ]
        if remaining:
            lines.append(f"\n**{len(remaining)} issue(s) require attention:**")
            for item in remaining:
                detail = item.get("detail", item.get("issue", ""))
                lines.append(f"- **{item.get('device_name', '?')}**: {detail}")
        if not issues:
            lines.append("All devices and entities are healthy.")

        try:
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "message": "\n".join(lines),
                    "title": f"Desk2HA Health Check ({len(issues)} issues)",
                    "notification_id": f"{DOMAIN}_health_check",
                },
            )
        except Exception:
            logger.debug("Could not create persistent notification", exc_info=True)

    hass.services.async_register(
        DOMAIN, SERVICE_FETCH_IMAGES, handle_fetch_images, schema=vol.Schema({})
    )
    hass.services.async_register(
        DOMAIN, SERVICE_WAKE_ON_LAN, handle_wake_on_lan, schema=WOL_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_HEALTH_CHECK,
        handle_health_check,
        schema=vol.Schema({vol.Optional("auto_fix", default=True): bool}),
    )

    logger.info(
        "Desk2HA services registered: fleet_status, refresh, restart_agent, "
        "fetch_images, wol, device_health_check"
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload Desk2HA services when last entry is removed."""
    for service in (
        SERVICE_FLEET_STATUS,
        SERVICE_REFRESH,
        SERVICE_RESTART_AGENT,
        SERVICE_FETCH_IMAGES,
        SERVICE_WAKE_ON_LAN,
        SERVICE_HEALTH_CHECK,
    ):
        hass.services.async_remove(DOMAIN, service)
