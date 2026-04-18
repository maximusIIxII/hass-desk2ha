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
    ATTR_COLOR_TEMP_KELVIN,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Desk2HACoordinator
from .entity import Desk2HASubDeviceEntity
from .helpers import display_metadata, extract_displays, extract_peripherals, peripheral_metadata

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

        entities.append(Desk2HADisplayLight(coordinator, target, "Backlight", **meta))

    # Litra desk lamps as lights with brightness + color temp
    for peripheral in extract_peripherals(coordinator.data or {}):
        dev_id = peripheral.get("id", "")
        if not dev_id.startswith("peripheral.litra_"):
            continue

        meta = peripheral_metadata(peripheral, coordinator.device_key)
        if not meta:
            continue
        entities.append(
            Desk2HALitraLight(coordinator, dev_id, meta["sub_device_name"] or "Litra", **meta)
        )

    async_add_entities(entities)


class Desk2HADisplayLight(Desk2HASubDeviceEntity, LightEntity):
    """A display represented as a dimmable light."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    # Availability is gated at setup time via `"brightness_percent" not in display`;
    # the metric_key "display.X.light" is a composite identifier the agent doesn't emit.
    _check_metric_available = False

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


class Desk2HALitraLight(Desk2HASubDeviceEntity, LightEntity):
    """Logitech Litra as a dimmable light with color temperature.

    State is read from agent metrics (HID polling), never assumed or restored.
    The ``assumed_state`` flag tells HA not to optimistically update the UI
    or send turn_on/turn_off commands to synchronise a restored state.
    """

    _attr_color_mode = ColorMode.COLOR_TEMP
    _attr_supported_color_modes = {ColorMode.COLOR_TEMP}
    _attr_min_color_temp_kelvin = 2700
    _attr_max_color_temp_kelvin = 6500
    _attr_min_mireds = 153  # 6500K
    _attr_max_mireds = 370  # 2700K
    _attr_assumed_state = True

    def __init__(
        self,
        coordinator: Desk2HACoordinator,
        peripheral_id: str,
        name: str,
        **sub_kwargs: Any,
    ) -> None:
        super().__init__(coordinator, f"{peripheral_id}.light", name, **sub_kwargs)
        self._peripheral_id = peripheral_id

    @property
    def brightness(self) -> int | None:
        val = self._find_metric(
            self.coordinator.data or {},
            f"{self._peripheral_id}.brightness_percent",
        )
        if val is not None:
            return min(255, max(0, int(float(val) * 255 / 100)))
        return None

    @property
    def color_temp_kelvin(self) -> int | None:
        val = self._find_metric(
            self.coordinator.data or {},
            f"{self._peripheral_id}.color_temp",
        )
        return int(float(val)) if val is not None else None

    @property
    def is_on(self) -> bool | None:
        val = self._find_metric(
            self.coordinator.data or {},
            f"{self._peripheral_id}.power",
        )
        if val is not None:
            return bool(val)
        return self.brightness is not None and self.brightness > 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        # Power on first
        await self.coordinator.async_send_command(
            "litra.set_power",
            target=self._peripheral_id,
            parameters={"on": True},
        )
        if ATTR_BRIGHTNESS in kwargs:
            # Convert HA 0-255 to Litra 20-250 lumen
            lumen = int(kwargs[ATTR_BRIGHTNESS] * 250 / 255)
            lumen = max(20, min(250, lumen))
            await self.coordinator.async_send_command(
                "litra.set_brightness",
                target=self._peripheral_id,
                parameters={"lumen": lumen},
            )
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            kelvin = int(kwargs[ATTR_COLOR_TEMP_KELVIN])
            kelvin = max(2700, min(6500, kelvin))
            await self.coordinator.async_send_command(
                "litra.set_color_temp",
                target=self._peripheral_id,
                parameters={"kelvin": kelvin},
            )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command(
            "litra.set_power",
            target=self._peripheral_id,
            parameters={"on": False},
        )
        await self.coordinator.async_request_refresh()
