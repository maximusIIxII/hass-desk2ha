"""Select platform for Desk2HA."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
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

    entities = [
        Desk2HASelect(
            coordinator=coordinator,
            metric_key="display.0.input_source",
            name="Display Input Source",
            command="display.set_input_source",
            target="display.0",
            param_key="input_source",
            options=["DP1", "DP2", "HDMI1", "HDMI2", "USBC1", "USBC2"],
            icon="mdi:video-input-hdmi",
        ),
        Desk2HASelect(
            coordinator=coordinator,
            metric_key="display.0.power_state",
            name="Display Power",
            command="display.set_power_state",
            target="display.0",
            param_key="power_state",
            options=["on", "standby", "off"],
            icon="mdi:power",
        ),
    ]

    async_add_entities(entities)


class Desk2HASelect(Desk2HAEntity, SelectEntity):
    """A Desk2HA select entity."""

    def __init__(
        self,
        coordinator: Desk2HACoordinator,
        metric_key: str,
        name: str,
        command: str,
        target: str,
        param_key: str,
        options: list[str],
        icon: str | None = None,
    ) -> None:
        super().__init__(coordinator, metric_key, name)
        self._command = command
        self._target = target
        self._param_key = param_key
        self._attr_options = options
        if icon:
            self._attr_icon = icon

    @property
    def current_option(self) -> str | None:
        val = self.metric_value
        return str(val) if val is not None else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_send_command(
            self._command,
            target=self._target,
            parameters={self._param_key: option},
        )
        await self.coordinator.async_request_refresh()
