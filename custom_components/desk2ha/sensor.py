"""Sensor platform for Desk2HA.

Dynamically creates sensor entities based on metrics the agent actually reports.
Known metrics get rich metadata (device_class, unit, icon); unknown metrics get
auto-generated entities with sensible defaults.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Desk2HACoordinator
from .entity import Desk2HASubDeviceEntity
from .helpers import display_metadata, extract_displays, extract_peripherals, peripheral_metadata

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SensorDef:
    """Definition for a known sensor metric."""

    name: str
    device_class: str | None = None
    unit: str | None = None
    state_class: str | None = None
    icon: str | None = None
    diagnostic: bool = False


# Known metric keys with rich metadata.
# Only metrics present in the agent response will create entities.
KNOWN_SENSORS: dict[str, SensorDef] = {
    # System
    "system.cpu_usage_percent": SensorDef(
        "CPU Usage", unit="%", state_class="measurement", icon="mdi:cpu-64-bit"
    ),
    "system.cpu_frequency_mhz": SensorDef(
        "CPU Frequency", unit="MHz", state_class="measurement", icon="mdi:speedometer"
    ),
    "system.ram_usage_percent": SensorDef(
        "RAM Usage", unit="%", state_class="measurement", icon="mdi:memory"
    ),
    "system.ram_used_gb": SensorDef(
        "RAM Used", SensorDeviceClass.DATA_SIZE, "GB", "measurement", "mdi:memory"
    ),
    "system.ram_total_gb": SensorDef(
        "RAM Total", SensorDeviceClass.DATA_SIZE, "GB", "measurement", "mdi:memory"
    ),
    "system.swap_usage_percent": SensorDef(
        "Swap Usage", unit="%", state_class="measurement", icon="mdi:memory"
    ),
    "system.disk_usage_percent": SensorDef(
        "Disk Usage", unit="%", state_class="measurement", icon="mdi:harddisk"
    ),
    "system.disk_free_gb": SensorDef(
        "Disk Free", SensorDeviceClass.DATA_SIZE, "GB", "measurement", "mdi:harddisk"
    ),
    "system.uptime_hours": SensorDef(
        "System Uptime", SensorDeviceClass.DURATION, "h", "measurement", "mdi:clock-outline"
    ),
    "system.process_count": SensorDef(
        "Process Count", state_class="measurement", icon="mdi:format-list-numbered"
    ),
    "system.net_sent_mb": SensorDef(
        "Network Sent", SensorDeviceClass.DATA_SIZE, "MB", "total_increasing", "mdi:upload-network"
    ),
    "system.net_recv_mb": SensorDef(
        "Network Received",
        SensorDeviceClass.DATA_SIZE,
        "MB",
        "total_increasing",
        "mdi:download-network",
    ),
    # System static info (diagnostic — shown under Diagnostics in HA)
    "system.cpu_model": SensorDef("CPU Model", icon="mdi:cpu-64-bit", diagnostic=True),
    "system.cpu_cores": SensorDef("CPU Cores", icon="mdi:cpu-64-bit", diagnostic=True),
    "system.cpu_threads": SensorDef("CPU Threads", icon="mdi:cpu-64-bit", diagnostic=True),
    "system.gpu_model": SensorDef("GPU Model", icon="mdi:expansion-card", diagnostic=True),
    "system.gpu_vram_gb": SensorDef(
        "GPU VRAM", SensorDeviceClass.DATA_SIZE, "GB", icon="mdi:expansion-card", diagnostic=True
    ),
    "system.gpu_driver": SensorDef("GPU Driver", icon="mdi:expansion-card", diagnostic=True),
    "system.screen_resolution": SensorDef(
        "Screen Resolution", icon="mdi:monitor", diagnostic=True
    ),
    "system.os_name": SensorDef("OS Name", icon="mdi:microsoft-windows", diagnostic=True),
    "system.os_version": SensorDef("OS Version", icon="mdi:microsoft-windows", diagnostic=True),
    "system.os_build": SensorDef("OS Build", icon="mdi:microsoft-windows", diagnostic=True),
    "system.bios_version": SensorDef("BIOS Version", icon="mdi:chip", diagnostic=True),
    "system.disk_model": SensorDef("Disk Model", icon="mdi:harddisk", diagnostic=True),
    # Thermals (standard + Dell DCM)
    "cpu_package": SensorDef(
        "CPU Temperature", SensorDeviceClass.TEMPERATURE, "°C", "measurement", "mdi:thermometer"
    ),
    "cpu_core_max": SensorDef(
        "CPU Core Max Temperature",
        SensorDeviceClass.TEMPERATURE,
        "°C",
        "measurement",
        "mdi:thermometer",
    ),
    "gpu": SensorDef(
        "GPU Temperature", SensorDeviceClass.TEMPERATURE, "°C", "measurement", "mdi:thermometer"
    ),
    "ambient": SensorDef(
        "Ambient Temperature",
        SensorDeviceClass.TEMPERATURE,
        "°C",
        "measurement",
        "mdi:thermometer",
    ),
    "skin": SensorDef(
        "Skin Temperature", SensorDeviceClass.TEMPERATURE, "°C", "measurement", "mdi:thermometer"
    ),
    "ssd": SensorDef(
        "SSD Temperature", SensorDeviceClass.TEMPERATURE, "°C", "measurement", "mdi:thermometer"
    ),
    "memory": SensorDef(
        "Memory Temperature", SensorDeviceClass.TEMPERATURE, "°C", "measurement", "mdi:thermometer"
    ),
    "pch": SensorDef(
        "PCH Temperature", SensorDeviceClass.TEMPERATURE, "°C", "measurement", "mdi:thermometer"
    ),
    "charger": SensorDef(
        "Charger Temperature",
        SensorDeviceClass.TEMPERATURE,
        "°C",
        "measurement",
        "mdi:thermometer",
    ),
    "battery_temp": SensorDef(
        "Battery Temperature",
        SensorDeviceClass.TEMPERATURE,
        "°C",
        "measurement",
        "mdi:thermometer",
    ),
    # Fans (Dell DCM)
    "fan.cpu": SensorDef("CPU Fan Speed", icon="mdi:fan", unit="/min", state_class="measurement"),
    "fan.gpu": SensorDef("GPU Fan Speed", icon="mdi:fan", unit="/min", state_class="measurement"),
    # Power (Dell DCM)
    "power.ac_adapter_watts": SensorDef(
        "AC Adapter Wattage", SensorDeviceClass.POWER, "W", "measurement", "mdi:power-plug"
    ),
    # Battery
    "battery.level_percent": SensorDef(
        "Battery Level", SensorDeviceClass.BATTERY, "%", "measurement"
    ),
    "battery.state": SensorDef("Battery State", icon="mdi:battery-charging"),
    "battery.time_remaining_seconds": SensorDef(
        "Battery Time Remaining",
        SensorDeviceClass.DURATION,
        "s",
        "measurement",
        "mdi:battery-clock",
    ),
    "battery.cycle_count": SensorDef("Battery Cycles", state_class="measurement"),
    "battery.health_percent": SensorDef("Battery Health", unit="%", state_class="measurement"),
    # Power
    "power.consumption_watts": SensorDef(
        "Power Consumption", SensorDeviceClass.POWER, "W", "measurement"
    ),
    "power.source": SensorDef("Power Source", icon="mdi:power-plug"),
    "power.usb_pd_connected": SensorDef("USB PD Connected", icon="mdi:usb-port"),
    "power.charging": SensorDef("Charging", icon="mdi:battery-charging"),
    "power.design_voltage": SensorDef(
        "Design Voltage", SensorDeviceClass.VOLTAGE, "V", "measurement", "mdi:flash"
    ),
    # Network
    "network.wifi_signal_percent": SensorDef(
        "WiFi Signal", unit="%", state_class="measurement", icon="mdi:wifi"
    ),
    "network.wifi_rssi_dbm": SensorDef(
        "WiFi RSSI",
        SensorDeviceClass.SIGNAL_STRENGTH,
        "dBm",
        "measurement",
        "mdi:wifi",
    ),
    "network.wifi_ssid": SensorDef("WiFi SSID", icon="mdi:wifi"),
    # Agent
    "agent.version": SensorDef("Agent Version", icon="mdi:information", diagnostic=True),
    "agent.uptime": SensorDef(
        "Agent Uptime", SensorDeviceClass.DURATION, "s", "measurement", "mdi:clock-outline"
    ),
}

# Suffix-based enrichment for auto-discovered peripheral/device metrics.
# Applied when the full key is not in KNOWN_SENSORS but the suffix matches.
_SUFFIX_ENRICHMENT: dict[str, dict[str, Any]] = {
    "battery_level": {
        "device_class": SensorDeviceClass.BATTERY,
        "unit": "%",
        "state_class": "measurement",
        "icon": "mdi:battery",
    },
    "firmware": {"icon": "mdi:chip", "diagnostic": True},
    "model": {"icon": "mdi:information", "diagnostic": True},
    "manufacturer": {"icon": "mdi:domain", "diagnostic": True},
    "charging": {"icon": "mdi:battery-charging"},
    "sidetone": {"icon": "mdi:headphones", "unit": "level"},
    "chatmix": {"icon": "mdi:headphones", "unit": "level"},
    "led": {"icon": "mdi:led-on"},
    "volume_percent": {"icon": "mdi:volume-high", "unit": "%", "state_class": "measurement"},
    "muted": {"icon": "mdi:volume-off"},
    # Webcam
    "brightness": {"icon": "mdi:brightness-6", "state_class": "measurement"},
    "contrast": {"icon": "mdi:contrast-box", "state_class": "measurement"},
    "saturation": {"icon": "mdi:palette", "state_class": "measurement"},
    "sharpness": {"icon": "mdi:blur", "state_class": "measurement"},
    "exposure": {"icon": "mdi:camera-iris", "state_class": "measurement"},
    "zoom": {"icon": "mdi:magnify-plus", "state_class": "measurement"},
    "white_balance": {
        "icon": "mdi:white-balance-sunny",
        "unit": "K",
        "state_class": "measurement",
    },
    "autofocus": {"icon": "mdi:camera-enhance"},
    "auto_wb": {"icon": "mdi:white-balance-auto"},
    "resolution": {"icon": "mdi:monitor", "diagnostic": True},
}

# Metric keys to skip as sensors (handled by other platforms)
_SKIP_KEYS = {
    "schema_version",
    "agent_version",
    "device_key",
    "snapshot_timestamp",
}

# Display metrics handled by number/select/switch platforms (skip as sensors)
_DISPLAY_CONTROL_KEYS = {
    "brightness_percent",
    "contrast_percent",
    "volume",
    "input_source",
    "power_state",
    "kvm_active_pc",
    "pbp_mode",
    "auto_brightness",
    "auto_color_temp",
}


def _flatten_metrics(data: dict[str, Any]) -> dict[str, Any]:
    """Flatten the nested /v1/metrics response into dot-separated keys."""
    flat: dict[str, Any] = {}

    for top_key, top_val in data.items():
        if top_key in _SKIP_KEYS:
            continue

        if isinstance(top_val, dict) and "value" in top_val:
            # Direct metric with value wrapper (e.g. thermals)
            flat[top_key] = top_val
        elif isinstance(top_val, dict):
            # Nested category (system, battery, power, agent)
            for sub_key, sub_val in top_val.items():
                flat[f"{top_key}.{sub_key}"] = sub_val
        elif isinstance(top_val, list):
            # Array of devices (displays, peripherals, audio)
            for i, item in enumerate(top_val):
                if not isinstance(item, dict):
                    continue
                dev_id = item.get("id", f"{top_key}.{i}")
                for mk, mv in item.items():
                    if mk == "id":
                        continue
                    flat[f"{dev_id}.{mk}"] = mv

    return flat


def _make_name(metric_key: str) -> str:
    """Generate a human-readable name from a metric key."""
    # Remove common prefixes
    parts = metric_key.split(".")
    if len(parts) >= 2 and parts[0] in ("system", "agent", "power"):
        name_part = ".".join(parts[1:])
    elif len(parts) >= 3 and parts[0] in ("display", "peripheral", "audio"):
        # display.0.model -> Display 0 Model
        suffix = " ".join(p.replace("_", " ").title() for p in parts[2:])
        return f"{parts[0].title()} {parts[1]} {suffix}"
    else:
        name_part = metric_key

    return name_part.replace("_", " ").replace(".", " ").title()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Desk2HA sensors dynamically from agent metrics."""
    coordinator: Desk2HACoordinator = hass.data[DOMAIN][entry.entry_id]

    if coordinator.data is None:
        return

    data = coordinator.data
    flat = _flatten_metrics(data)
    entities: list[Desk2HASensor] = []

    # Build sub-device lookup for display/peripheral sensors
    sub_device_map: dict[str, dict[str, str | None]] = {}
    for i, display in enumerate(extract_displays(data)):
        target = display.get("id", f"display.{i}")
        idx = target.split(".")[-1] if "." in target else str(i)
        meta = display_metadata(display, idx, coordinator.device_key)
        sub_device_map[target] = meta
    for peripheral in extract_peripherals(data):
        dev_id = peripheral.get("id", "")
        if dev_id:
            meta = peripheral_metadata(peripheral, coordinator.device_key)
            sub_device_map[dev_id] = meta

    for metric_key in flat:
        key_suffix = metric_key.rsplit(".", 1)[-1] if "." in metric_key else metric_key
        if metric_key.startswith("display.") and key_suffix in _DISPLAY_CONTROL_KEYS:
            continue

        # Determine sub-device (display.0.xxx → display.0, peripheral.usb_3.xxx → peripheral.usb_3)
        parts = metric_key.split(".")
        sub_key = f"{parts[0]}.{parts[1]}" if len(parts) >= 3 else ""
        sub_meta = sub_device_map.get(sub_key, {})

        defn = KNOWN_SENSORS.get(metric_key)
        if defn:
            entities.append(
                Desk2HASensor(
                    coordinator=coordinator,
                    metric_key=metric_key,
                    name=defn.name,
                    device_class=defn.device_class,
                    unit=defn.unit,
                    state_class=defn.state_class,
                    icon=defn.icon,
                    diagnostic=defn.diagnostic,
                    **sub_meta,
                )
            )
        else:
            enrich = _SUFFIX_ENRICHMENT.get(key_suffix, {})
            # Simplify name for sub-device sensors (drop prefix)
            name = _make_name(metric_key)
            if sub_meta:
                name = key_suffix.replace("_", " ").title()
            entities.append(
                Desk2HASensor(
                    coordinator=coordinator,
                    metric_key=metric_key,
                    name=name,
                    device_class=enrich.get("device_class"),
                    unit=enrich.get("unit"),
                    state_class=enrich.get("state_class"),
                    icon=enrich.get("icon"),
                    diagnostic=enrich.get("diagnostic", False),
                    **sub_meta,
                )
            )

    async_add_entities(entities)
    logger.info("Created %d sensor entities from %d metrics", len(entities), len(flat))


class Desk2HASensor(Desk2HASubDeviceEntity, SensorEntity):
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
        diagnostic: bool = False,
        **sub_kwargs: Any,
    ) -> None:
        super().__init__(coordinator, metric_key, name, **sub_kwargs)
        if device_class:
            self._attr_device_class = device_class
        if unit:
            self._attr_native_unit_of_measurement = unit
        if state_class:
            self._attr_state_class = state_class
        if icon:
            self._attr_icon = icon
        if diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Any:
        return self.metric_value
