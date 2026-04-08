"""Button platform for Desk2HA."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
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

    async_add_entities(
        [
            Desk2HARefreshButton(coordinator),
            Desk2HARestartButton(coordinator),
            Desk2HACommandButton(
                coordinator, "system_lock", "Lock Screen", "system.lock", "mdi:lock"
            ),
            Desk2HACommandButton(
                coordinator, "system_sleep", "Sleep", "system.sleep", "mdi:power-sleep"
            ),
            Desk2HACommandButton(
                coordinator,
                "system_shutdown",
                "Shutdown",
                "system.shutdown",
                "mdi:power",
            ),
        ]
    )


class Desk2HARefreshButton(Desk2HAEntity, ButtonEntity):
    """Button to force a data refresh."""

    _attr_icon = "mdi:refresh"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: Desk2HACoordinator) -> None:
        super().__init__(coordinator, "refresh", "Refresh Data")

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()


class Desk2HARestartButton(Desk2HAEntity, ButtonEntity):
    """Button to restart the agent."""

    _attr_icon = "mdi:restart"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: Desk2HACoordinator) -> None:
        super().__init__(coordinator, "agent_restart", "Restart Agent")

    async def async_press(self) -> None:
        await self.coordinator.async_send_command("agent.restart")


class Desk2HACommandButton(Desk2HAEntity, ButtonEntity):
    """Generic button that sends a command to the agent."""

    def __init__(
        self,
        coordinator: Desk2HACoordinator,
        key: str,
        name: str,
        command: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, key, name)
        self._command = command
        self._attr_icon = icon

    async def async_press(self) -> None:
        await self.coordinator.async_send_command(self._command)
