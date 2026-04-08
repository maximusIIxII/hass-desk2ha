"""Number platform for Desk2HA.

Dynamically creates number entities for each display reported by the agent.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Desk2HACoordinator
from .entity import Desk2HAEntity

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class NumberDef:
    """Definition for a display number control."""

    suffix: str
    name_template: str
    command: str
    param_key: str
    min_value: float
    max_value: float
    step: float
    unit: str | None = None
    icon: str | None = None


DISPLAY_NUMBER_DEFS: list[NumberDef] = [
    NumberDef(
        "brightness_percent",
        "Display {idx} Brightness",
        "display.set_brightness",
        "value",
        0,
        100,
        1,
        "%",
        "mdi:brightness-6",
    ),
    NumberDef(
        "contrast_percent",
        "Display {idx} Contrast",
        "display.set_contrast",
        "value",
        0,
        100,
        1,
        "%",
        "mdi:contrast-box",
    ),
    NumberDef(
        "volume",
        "Display {idx} Volume",
        "display.set_volume",
        "value",
        0,
        100,
        1,
        "%",
        "mdi:volume-high",
    ),
]


def _extract_displays(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract display entries from metrics data."""
    return [d for d in data.get("displays", []) if isinstance(d, dict)]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Desk2HA number entities dynamically per display."""
    coordinator: Desk2HACoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[NumberEntity] = []

    displays = _extract_displays(coordinator.data or {})

    for i, display in enumerate(displays):
        target = display.get("id", f"display.{i}")
        idx = target.split(".")[-1] if "." in target else str(i)

        for defn in DISPLAY_NUMBER_DEFS:
            if defn.suffix not in display:
                continue
            name = defn.name_template.format(idx=idx)
            # Single display: drop index from name
            if len(displays) == 1:
                name = name.replace(f" {idx} ", " ")
            entities.append(
                Desk2HANumber(
                    coordinator=coordinator,
                    metric_key=f"{target}.{defn.suffix}",
                    name=name,
                    command=defn.command,
                    target=target,
                    param_key=defn.param_key,
                    min_value=defn.min_value,
                    max_value=defn.max_value,
                    step=defn.step,
                    unit=defn.unit,
                    icon=defn.icon,
                )
            )

    async_add_entities(entities)
    logger.info("Created %d number entities for %d display(s)", len(entities), len(displays))


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
