"""Sensor platform for Desk2HA."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Desk2HACoordinator
from .entity import Desk2HAEntity

logger = logging.getLogger(__name__)

# Sensor definitions: metric_key -> (name, device_class, unit, state_class, icon)
SENSOR_DEFS: dict[str, tuple[str, str | None, str | None, str | None, str | None]] = {
    # System metrics
    "system.cpu_usage_percent": ("CPU Usage", None, "%", "measurement", "mdi:cpu-64-bit"),
    "system.cpu_frequency_mhz": ("CPU Frequency", None, "MHz", "measurement", "mdi:speedometer"),
    "system.ram_usage_percent": ("RAM Usage", None, "%", "measurement", "mdi:memory"),
    "system.ram_used_gb": ("RAM Used", SensorDeviceClass.DATA_SIZE, "GB", "measurement", "mdi:memory"),
    "system.disk_usage_percent": ("Disk Usage", None, "%", "measurement", "mdi:harddisk"),
    "system.disk_free_gb": ("Disk Free", SensorDeviceClass.DATA_SIZE, "GB", "measurement", "mdi:harddisk"),
    "system.uptime_hours": ("System Uptime", SensorDeviceClass.DURATION, "h", "measurement", "mdi:clock-outline"),
    "system.process_count": ("Process Count", None, None, "measurement", "mdi:format-list-numbered"),
    # Thermal
    "cpu_package": ("CPU Temperature", SensorDeviceClass.TEMPERATURE, "°C", "measurement", "mdi:thermometer"),
    # Battery
    "battery.level_percent": ("Battery Level", SensorDeviceClass.BATTERY, "%", "measurement", None),
    "battery.state": ("Battery State", None, None, None, "mdi:battery-charging"),
    "battery.cycle_count": ("Battery Cycles", None, None, "measurement", None),
    "battery.health_percent": ("Battery Health", None, "%", "measurement", None),
    # Power
    "power.consumption_watts": ("Power Consumption", SensorDeviceClass.POWER, "W", "measurement", None),
    "power.source": ("Power Source", None, None, None, "mdi:power-plug"),
    # Agent
    "agent.version": ("Agent Version", None, None, None, "mdi:information"),
    "agent.uptime": ("Agent Uptime", SensorDeviceClass.DURATION, "s", "measurement", "mdi:clock-outline"),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Desk2HA sensors based on agent data."""
    coordinator: Desk2HACoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[Desk2HASensor] = []

    # Create sensors for known metric keys that exist in the data
    for metric_key, (name, device_class, unit, state_class, icon) in SENSOR_DEFS.items():
        entities.append(
            Desk2HASensor(
                coordinator=coordinator,
                metric_key=metric_key,
                name=name,
                device_class=device_class,
                unit=unit,
                state_class=state_class,
                icon=icon,
            )
        )

    async_add_entities(entities)


class Desk2HASensor(Desk2HAEntity, SensorEntity):
    """A Desk2HA sensor entity."""

    def __init__(
        self,
        coordinator: Desk2HACoordinator,
        metric_key: str,
        name: str,
        device_class: str | None = None,
        unit: str | None = None,
        state_class: str | None = None,
        icon: str | None = None,
    ) -> None:
        super().__init__(coordinator, metric_key, name)
        if device_class:
            self._attr_device_class = device_class
        if unit:
            self._attr_native_unit_of_measurement = unit
        if state_class:
            self._attr_state_class = state_class
        if icon:
            self._attr_icon = icon

    @property
    def native_value(self) -> Any:
        return self.metric_value
