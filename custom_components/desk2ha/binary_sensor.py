"""Binary sensor platform for Desk2HA.

Dynamically creates binary sensors from agent metrics.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Desk2HACoordinator
from .entity import Desk2HAEntity


@dataclass(frozen=True, slots=True)
class BinarySensorDef:
    """Definition for a known binary sensor."""

    name: str
    metric_key: str
    device_class: str | None = None
    icon: str | None = None
    is_on_fn: Callable[[Any], bool | None] = lambda v: bool(v)


def _battery_is_on_ac(val: Any) -> bool | None:
    """Return True when battery state indicates AC power."""
    if val is None:
        return None
    if isinstance(val, str):
        return val.lower() in ("ac", "full", "charging")
    return bool(val)


BINARY_SENSOR_DEFS: list[BinarySensorDef] = [
    BinarySensorDef(
        name="On AC Power",
        metric_key="battery.state",
        device_class=BinarySensorDeviceClass.PLUG,
        icon="mdi:power-plug",
        is_on_fn=_battery_is_on_ac,
    ),
]

# Map metric_key -> required data key to check existence
_EXISTENCE_CHECKS: dict[str, str] = {
    "battery.state": "battery",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Desk2HA binary sensors from agent data."""
    coordinator: Desk2HACoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[Desk2HABinarySensor] = []

    data = coordinator.data or {}

    for defn in BINARY_SENSOR_DEFS:
        # Only create if the required data section exists
        check_key = _EXISTENCE_CHECKS.get(defn.metric_key)
        if check_key and check_key not in data:
            continue
        entities.append(Desk2HABinarySensor(coordinator, defn))

    async_add_entities(entities)


class Desk2HABinarySensor(Desk2HAEntity, BinarySensorEntity):
    """A Desk2HA binary sensor entity."""

    def __init__(
        self,
        coordinator: Desk2HACoordinator,
        defn: BinarySensorDef,
    ) -> None:
        super().__init__(coordinator, defn.metric_key, defn.name)
        self._is_on_fn = defn.is_on_fn
        if defn.device_class:
            self._attr_device_class = defn.device_class
        if defn.icon:
            self._attr_icon = defn.icon

    @property
    def is_on(self) -> bool | None:
        return self._is_on_fn(self.metric_value)
