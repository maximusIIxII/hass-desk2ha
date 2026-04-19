"""Update platform for Desk2HA.

Checks for new agent releases via the agent's /v1/update/check endpoint
and triggers installation via /v1/update/install.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Desk2HACoordinator
from .entity import Desk2HAEntity

logger = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Desk2HA update entity."""
    coordinator: Desk2HACoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([Desk2HAUpdateEntity(coordinator)])


class Desk2HAUpdateEntity(Desk2HAEntity, UpdateEntity):
    """Represents an agent update check."""

    _check_metric_available = False
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_supported_features = UpdateEntityFeature.INSTALL | UpdateEntityFeature.RELEASE_NOTES

    def __init__(self, coordinator: Desk2HACoordinator) -> None:
        super().__init__(coordinator, "agent_update", "Agent Update")
        self._update_info: dict[str, Any] = {}
        self._attr_entity_picture = f"/{DOMAIN}/brand/icon.png"

    @property
    def entity_picture(self) -> str | None:
        # HA core's UpdateEntity overrides entity_picture to always return
        # the brands.home-assistant.io URL, ignoring _attr_entity_picture.
        # Re-override here so our locally-served brand icon (registered as a
        # static path in __init__._register_card) wins.
        return self._attr_entity_picture

    @property
    def installed_version(self) -> str | None:
        return self._update_info.get(
            "installed_version",
            self.coordinator.agent_info.get("agent_version"),
        )

    @property
    def latest_version(self) -> str | None:
        return self._update_info.get("latest_version")

    @property
    def release_url(self) -> str | None:
        return self._update_info.get("release_url")

    def release_notes(self) -> str | None:
        return self._update_info.get("release_notes")

    async def async_update(self) -> None:
        """Check for updates via agent API."""
        try:
            self._update_info = await self.coordinator.async_check_update()
        except Exception:
            logger.debug("Update check failed", exc_info=True)

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        """Install an agent update."""
        await self.coordinator.async_install_update(version)
        # Re-check after install
        self._update_info = await self.coordinator.async_check_update()
