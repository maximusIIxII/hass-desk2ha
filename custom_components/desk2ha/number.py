"""Number platform for Desk2HA."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
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
    coordinator: Desk2HACoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[NumberEntity] = []

    # Display brightness (per display from agent data)
    entities.append(
        Desk2HANumber(
            coordinator=coordinator,
            metric_key="display.0.brightness_percent",
            name="Display Brightness",
            command="display.set_brightness",
            target="display.0",
            param_key="value",
            min_value=0,
            max_value=100,
            step=1,
            unit="%",
            icon="mdi:brightness-6",
        )
    )

    # Display contrast
    entities.append(
        Desk2HANumber(
            coordinator=coordinator,
            metric_key="display.0.contrast_percent",
            name="Display Contrast",
            command="display.set_contrast",
            target="display.0",
            param_key="value",
            min_value=0,
            max_value=100,
            step=1,
            unit="%",
            icon="mdi:contrast-box",
        )
    )

    # Display volume
    entities.append(
        Desk2HANumber(
            coordinator=coordinator,
            metric_key="display.0.volume",
            name="Display Volume",
            command="display.set_volume",
            target="display.0",
            param_key="value",
            min_value=0,
            max_value=100,
            step=1,
            unit="%",
            icon="mdi:volume-high",
        )
    )

    async_add_entities(entities)


class Desk2HANumber(Desk2HAEntity, NumberEntity):
    """A Desk2HA number entity for controlling values."""

    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: Desk2HACoordinator,
        metric_key: str,
        name: str,
        command: str,
        target: str,
        param_key: str,
        min_value: float,
        max_value: float,
        step: float,
        unit: str | None = None,
        icon: str | None = None,
    ) -> None:
        super().__init__(coordinator, metric_key, name)
        self._command = command
        self._target = target
        self._param_key = param_key
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        if unit:
            self._attr_native_unit_of_measurement = unit
        if icon:
            self._attr_icon = icon

    @property
    def native_value(self) -> float | None:
        val = self.metric_value
        if val is not None:
            return float(val)
        return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_send_command(
            self._command,
            target=self._target,
            parameters={self._param_key: int(value)},
        )
        await self.coordinator.async_request_refresh()
