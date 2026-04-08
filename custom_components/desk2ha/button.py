"""Button platform for Desk2HA."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Desk2HACoordinator
from .entity import Desk2HAEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Desk2HACoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        Desk2HARefreshButton(coordinator),
        Desk2HARestartButton(coordinator),
    ])


class Desk2HARefreshButton(Desk2HAEntity, ButtonEntity):
    """Button to force a data refresh."""

    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: Desk2HACoordinator) -> None:
        super().__init__(coordinator, "refresh", "Refresh Data")

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()


class Desk2HARestartButton(Desk2HAEntity, ButtonEntity):
    """Button to restart the agent."""

    _attr_icon = "mdi:restart"

    def __init__(self, coordinator: Desk2HACoordinator) -> None:
        super().__init__(coordinator, "agent_restart", "Restart Agent")

    async def async_press(self) -> None:
        await self.coordinator.async_send_command("agent.restart")
