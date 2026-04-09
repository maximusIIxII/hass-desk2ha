"""Base entity for Desk2HA."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Desk2HACoordinator


class Desk2HAEntity(CoordinatorEntity[Desk2HACoordinator]):
    """Base class for Desk2HA entities (host device)."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Desk2HACoordinator,
        metric_key: str,
        name: str,
        device_key: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._metric_key = metric_key
        self._device_key = device_key or coordinator.device_key
        self._attr_name = name
        self._attr_unique_id = f"desk2ha_{self._device_key}_{metric_key}".replace(".", "_")

    @property
    def device_info(self) -> DeviceInfo:
        """Return host device info (main PC)."""
        info = self.coordinator.agent_info
        hw = info.get("hardware", {})
        identity = info.get("identity", {})
        config = info.get("config", {})
        http_config = config.get("http", {})

        config_url = None
        if http_config.get("enabled"):
            port = http_config.get("port", 9693)
            hostname = identity.get("hostname", "")
            if hostname:
                config_url = f"http://{hostname}:{port}"

        return DeviceInfo(
            identifiers={(DOMAIN, self._device_key)},
            name=(f"{hw.get('manufacturer', 'Unknown')} {hw.get('model', self._device_key)}"),
            manufacturer=hw.get("manufacturer"),
            model=hw.get("model"),
            serial_number=identity.get("serial_number"),
            sw_version=info.get("agent_version"),
            configuration_url=config_url,
        )

    _SENTINEL = object()
    _check_metric_available = True  # Subclasses can set False (buttons, commands)

    @property
    def available(self) -> bool:
        """Return False if the metric key is absent from the current data."""
        if not self._check_metric_available:
            return super().available
        if self.coordinator.data is None:
            return super().available
        # Check if the metric exists at all in the data (not just value)
        result = self._find_metric(self.coordinator.data, self._metric_key, self._SENTINEL)
        if result is self._SENTINEL:
            return False
        return super().available

    @property
    def metric_value(self) -> Any:
        """Get the current metric value from coordinator data."""
        if self.coordinator.data is None:
            return None
        return self._find_metric(self.coordinator.data, self._metric_key)

    @staticmethod
    def _find_metric(data: dict[str, Any], key: str, default: Any = None) -> Any:
        """Find a metric value in the nested response data."""
        # 1. Direct top-level key
        if key in data:
            val = data[key]
            if isinstance(val, dict) and "value" in val:
                return val["value"]
            return val

        parts = key.split(".")

        # 2. category.metric (supports dotted sub-keys like thermals.fan.gpu)
        if len(parts) >= 2:
            category = data.get(parts[0])
            if isinstance(category, dict) and "value" not in category:
                sub_key = ".".join(parts[1:])
                if sub_key not in category:
                    # Also try just parts[1] for simple 2-part keys
                    if len(parts) == 2:
                        return default
                    # Fall through to device array path for 3+ parts
                else:
                    sub = category[sub_key]
                    if isinstance(sub, dict) and "value" in sub:
                        return sub["value"]
                    return sub

        # 3. Device array
        if len(parts) >= 3:
            array_key_map = {
                "display": "displays",
                "peripheral": "peripherals",
                "audio": "audio",
            }
            array_key = array_key_map.get(parts[0], f"{parts[0]}s")
            devices = data.get(array_key, [])
            if isinstance(devices, list):
                target_id = f"{parts[0]}.{parts[1]}"
                metric_name = ".".join(parts[2:])
                for dev in devices:
                    if not isinstance(dev, dict):
                        continue
                    if dev.get("id") == target_id:
                        if metric_name not in dev:
                            return default
                        val = dev[metric_name]
                        if isinstance(val, dict) and "value" in val:
                            return val["value"]
                        return val

        return default


class Desk2HASubDeviceEntity(Desk2HAEntity):
    """Entity belonging to a sub-device (display, peripheral, etc.)."""

    def __init__(
        self,
        coordinator: Desk2HACoordinator,
        metric_key: str,
        name: str,
        sub_device_id: str = "",
        sub_device_name: str = "",
        sub_manufacturer: str | None = None,
        sub_model: str | None = None,
        **_kwargs: Any,
    ) -> None:
        super().__init__(coordinator, metric_key, name)
        self._sub_device_id = sub_device_id
        self._sub_device_name = sub_device_name
        self._sub_manufacturer = sub_manufacturer
        self._sub_model = sub_model

    @property
    def device_info(self) -> DeviceInfo:
        """Return sub-device info, or host device if no sub_device_id."""
        if not self._sub_device_id:
            return super().device_info
        return DeviceInfo(
            identifiers={(DOMAIN, self._sub_device_id)},
            name=self._sub_device_name,
            manufacturer=self._sub_manufacturer,
            model=self._sub_model,
            via_device=(DOMAIN, self.coordinator.device_key),
        )

    @property
    def available(self) -> bool:
        """Return False if the peripheral reports connected=false."""
        if not self._sub_device_id or self.coordinator.data is None:
            return super().available

        # Find the peripheral entry in coordinator data
        peripherals = self.coordinator.data.get("peripherals", [])
        for peripheral in peripherals:
            if not isinstance(peripheral, dict):
                continue
            dev_id = peripheral.get("id", "")
            expected_suffix = f"_{dev_id}"
            if self._sub_device_id.endswith(expected_suffix):
                connected_raw = peripheral.get("connected")
                if connected_raw is None:
                    break
                # Handle both dict-wrapped {"value": ...} and plain values
                if isinstance(connected_raw, dict) and "value" in connected_raw:
                    connected_val = connected_raw["value"]
                else:
                    connected_val = connected_raw
                if connected_val is False or str(connected_val).lower() == "false":
                    return False
                break

        return super().available
