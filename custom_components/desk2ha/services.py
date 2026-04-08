"""Desk2HA service calls for fleet management and agent control."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN
from .coordinator import Desk2HACoordinator

logger = logging.getLogger(__name__)

SERVICE_FLEET_STATUS = "fleet_status"
SERVICE_REFRESH = "refresh"
SERVICE_RESTART_AGENT = "restart_agent"

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

    hass.services.async_register(
        DOMAIN, SERVICE_FLEET_STATUS, handle_fleet_status, schema=FLEET_STATUS_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_REFRESH, handle_refresh, schema=REFRESH_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_RESTART_AGENT, handle_restart_agent, schema=RESTART_SCHEMA
    )

    logger.info("Desk2HA services registered: fleet_status, refresh, restart_agent")


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload Desk2HA services when last entry is removed."""
    for service in (SERVICE_FLEET_STATUS, SERVICE_REFRESH, SERVICE_RESTART_AGENT):
        hass.services.async_remove(DOMAIN, service)
