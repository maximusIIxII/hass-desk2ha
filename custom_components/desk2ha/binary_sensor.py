"""Binary sensor platform for Desk2HA."""

from __future__ import annotations

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

BINARY_SENSOR_DEFS: dict[str, tuple[str, str | None, str | None]] = {
    "power.source": ("On AC Power", BinarySensorDeviceClass.PLUG, "mdi:power-plug"),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: Desk2HACoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        Desk2HABinarySensor(coordinator, key, name, device_class, icon)
        for key, (name, device_class, icon) in BINARY_SENSOR_DEFS.items()
    ]
    async_add_entities(entities)


class Desk2HABinarySensor(Desk2HAEntity, BinarySensorEntity):

    def __init__(self, coordinator, metric_key, name, device_class=None, icon=None):
        super().__init__(coordinator, metric_key, f"{name}_binary")
        self._attr_unique_id = f"desk2ha_{coordinator.device_key}_{metric_key}_binary".replace(".", "_")
        self._attr_name = name
        if device_class:
            self._attr_device_class = device_class
        if icon:
            self._attr_icon = icon

    @property
    def is_on(self) -> bool | None:
        val = self.metric_value
        if val is None:
            return None
        if isinstance(val, str):
            return val.lower() == "ac"
        return bool(val)
