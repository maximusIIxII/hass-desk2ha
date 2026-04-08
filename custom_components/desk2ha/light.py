"""Light platform for Desk2HA.

Exposes external displays as dimmable lights, with brightness mapped
to the DDC/CI brightness value (0-100%). This allows natural HA
interactions: light.turn_on/off, brightness slider, automations.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Desk2HACoordinator
from .entity import Desk2HASubDeviceEntity
from .helpers import display_metadata, extract_displays

logger = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Desk2HA light entities for each display with brightness."""
    coordinator: Desk2HACoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[LightEntity] = []

    displays = extract_displays(coordinator.data or {})

    for i, display in enumerate(displays):
        if "brightness_percent" not in display:
            continue

        target = display.get("id", f"display.{i}")
        idx = target.split(".")[-1] if "." in target else str(i)
        meta = display_metadata(display, idx, coordinator.device_key)

        entities.append(Desk2HADisplayLight(coordinator, target, meta["sub_device_name"], **meta))

    async_add_entities(entities)


class Desk2HADisplayLight(Desk2HASubDeviceEntity, LightEntity):
    """A display represented as a dimmable light."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(
        self,
        coordinator: Desk2HACoordinator,
        target: str,
        name: str,
        **sub_kwargs: Any,
    ) -> None:
        super().__init__(coordinator, f"{target}.light", name, **sub_kwargs)
        self._target = target
        self._brightness_key = f"{target}.brightness_percent"
        self._power_key = f"{target}.power_state"

    @property
    def brightness(self) -> int | None:
        """Return brightness as 0-255 (HA scale)."""
        val = self._find_metric(self.coordinator.data or {}, self._brightness_key)
        if val is not None:
            # Convert 0-100% to 0-255
            return min(255, max(0, int(float(val) * 255 / 100)))
        return None

    @property
    def is_on(self) -> bool | None:
        power = self._find_metric(self.coordinator.data or {}, self._power_key)
        if power is not None:
            return str(power).lower() == "on"
        # If no power state, infer from brightness
        b = self.brightness
        return b is not None and b > 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        if ATTR_BRIGHTNESS in kwargs:
            # Convert 0-255 back to 0-100%
            pct = int(kwargs[ATTR_BRIGHTNESS] * 100 / 255)
            await self.coordinator.async_send_command(
                "display.set_brightness",
                target=self._target,
                parameters={"value": pct},
            )
        else:
            await self.coordinator.async_send_command(
                "display.set_power_state",
                target=self._target,
                parameters={"state": "on"},
            )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command(
            "display.set_power_state",
            target=self._target,
            parameters={"state": "standby"},
        )
        await self.coordinator.async_request_refresh()
