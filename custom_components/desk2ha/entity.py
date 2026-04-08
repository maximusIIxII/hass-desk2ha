"""Base entity for Desk2HA."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Desk2HACoordinator


class Desk2HAEntity(CoordinatorEntity[Desk2HACoordinator]):
    """Base class for Desk2HA entities."""

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
        info = self.coordinator.agent_info
        hw = info.get("hardware", {})
        identity = info.get("identity", {})
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_key)},
            name=f"{hw.get('manufacturer', 'Unknown')} {hw.get('model', self._device_key)}",
            manufacturer=hw.get("manufacturer"),
            model=hw.get("model"),
            serial_number=identity.get("serial_number"),
            sw_version=info.get("agent_version"),
        )

    @property
    def metric_value(self) -> Any:
        """Get the current metric value from coordinator data."""
        if self.coordinator.data is None:
            return None
        # Navigate nested data structure
        return self._find_metric(self.coordinator.data, self._metric_key)

    def _find_metric(self, data: dict[str, Any], key: str) -> Any:
        """Find a metric value in the nested response data."""
        # Try direct key access (for flat metrics like thermals)
        if key in data:
            val = data[key]
            if isinstance(val, dict) and "value" in val:
                return val["value"]
            return val

        # Try category.key (e.g., "battery.level_percent")
        parts = key.split(".", 1)
        if len(parts) == 2:
            category = data.get(parts[0])
            if isinstance(category, dict):
                sub = category.get(parts[1])
                if isinstance(sub, dict) and "value" in sub:
                    return sub["value"]
                return sub

        return None
