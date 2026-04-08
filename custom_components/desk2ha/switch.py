"""Switch platform for Desk2HA.

Dynamically creates switch entities for boolean display features
(auto-brightness, auto-color-temp, smart HDR, power nap).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Desk2HACoordinator
from .entity import Desk2HAEntity


@dataclass(frozen=True, slots=True)
class SwitchDef:
    """Definition for a display switch control."""

    suffix: str
    name_template: str
    command_on: str
    command_off: str
    param_key: str
    icon: str | None = None


DISPLAY_SWITCH_DEFS: list[SwitchDef] = [
    SwitchDef(
        "auto_brightness",
        "Display {idx} Auto Brightness",
        "display.set_auto_brightness",
        "display.set_auto_brightness",
        "value",
        "mdi:brightness-auto",
    ),
    SwitchDef(
        "auto_color_temp",
        "Display {idx} Auto Color Temp",
        "display.set_auto_color_temp",
        "display.set_auto_color_temp",
        "value",
        "mdi:palette",
    ),
]


def _extract_displays(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [d for d in data.get("displays", []) if isinstance(d, dict)]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Desk2HA switch entities dynamically per display."""
    coordinator: Desk2HACoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = []

    displays = _extract_displays(coordinator.data or {})

    for i, display in enumerate(displays):
        target = display.get("id", f"display.{i}")
        idx = target.split(".")[-1] if "." in target else str(i)

        for defn in DISPLAY_SWITCH_DEFS:
            if defn.suffix not in display:
                continue
            name = defn.name_template.format(idx=idx)
            if len(displays) == 1:
                name = name.replace(f" {idx} ", " ")
            entities.append(
                Desk2HASwitch(
                    coordinator=coordinator,
                    metric_key=f"{target}.{defn.suffix}",
                    name=name,
                    command_on=defn.command_on,
                    command_off=defn.command_off,
                    target=target,
                    param_key=defn.param_key,
                    icon=defn.icon,
                )
            )

    async_add_entities(entities)


class Desk2HASwitch(Desk2HAEntity, SwitchEntity):
    """A Desk2HA switch entity for boolean display features."""

    def __init__(
        self,
        coordinator: Desk2HACoordinator,
        metric_key: str,
        name: str,
        command_on: str,
        command_off: str,
        target: str,
        param_key: str,
        icon: str | None = None,
    ) -> None:
        super().__init__(coordinator, metric_key, name)
        self._command_on = command_on
        self._command_off = command_off
        self._target = target
        self._param_key = param_key
        if icon:
            self._attr_icon = icon

    @property
    def is_on(self) -> bool | None:
        val = self.metric_value
        if val is None:
            return None
        return bool(val)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command(
            self._command_on,
            target=self._target,
            parameters={self._param_key: 1},
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command(
            self._command_off,
            target=self._target,
            parameters={self._param_key: 0},
        )
        await self.coordinator.async_request_refresh()
