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
from .entity import Desk2HASubDeviceEntity

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
    NumberDef(
        "sharpness",
        "Display {idx} Sharpness",
        "display.set_sharpness",
        "value",
        0,
        100,
        1,
        "%",
        "mdi:blur",
    ),
    NumberDef(
        "red_gain",
        "Display {idx} Red Gain",
        "display.set_red_gain",
        "value",
        0,
        100,
        1,
        "%",
        "mdi:palette",
    ),
    NumberDef(
        "green_gain",
        "Display {idx} Green Gain",
        "display.set_green_gain",
        "value",
        0,
        100,
        1,
        "%",
        "mdi:palette",
    ),
    NumberDef(
        "blue_gain",
        "Display {idx} Blue Gain",
        "display.set_blue_gain",
        "value",
        0,
        100,
        1,
        "%",
        "mdi:palette",
    ),
    NumberDef(
        "red_black_level",
        "Display {idx} Red Black Level",
        "display.set_red_black_level",
        "value",
        0,
        100,
        1,
        "%",
        "mdi:circle-half-full",
    ),
    NumberDef(
        "green_black_level",
        "Display {idx} Green Black Level",
        "display.set_green_black_level",
        "value",
        0,
        100,
        1,
        "%",
        "mdi:circle-half-full",
    ),
    NumberDef(
        "blue_black_level",
        "Display {idx} Blue Black Level",
        "display.set_blue_black_level",
        "value",
        0,
        100,
        1,
        "%",
        "mdi:circle-half-full",
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

        # Extract display metadata for sub-device
        model_raw = display.get("model", {})
        model_name = model_raw.get("value", "") if isinstance(model_raw, dict) else str(model_raw)
        mfg_raw = display.get("manufacturer", {})
        mfg_name = mfg_raw.get("value", "") if isinstance(mfg_raw, dict) else str(mfg_raw)
        sub_id = f"{coordinator.device_key}_display_{idx}"
        sub_name = model_name or f"Display {idx}"

        for defn in DISPLAY_NUMBER_DEFS:
            if defn.suffix not in display:
                continue
            entities.append(
                Desk2HANumber(
                    coordinator=coordinator,
                    metric_key=f"{target}.{defn.suffix}",
                    name=defn.name_template.format(idx=idx).replace(f"Display {idx} ", ""),
                    command=defn.command,
                    target=target,
                    param_key=defn.param_key,
                    min_value=defn.min_value,
                    max_value=defn.max_value,
                    step=defn.step,
                    unit=defn.unit,
                    icon=defn.icon,
                    sub_device_id=sub_id,
                    sub_device_name=sub_name,
                    sub_manufacturer=mfg_name or None,
                    sub_model=model_name or None,
                )
            )

    # Keyboard backlight (system-level)
    data = coordinator.data or {}
    system = data.get("system", {})
    kbd_bl = system.get("keyboard_backlight")
    if kbd_bl is not None:
        entities.append(
            Desk2HANumber(
                coordinator=coordinator,
                metric_key="system.keyboard_backlight",
                name="Keyboard Backlight",
                command="keyboard.set_backlight",
                target="",
                param_key="value",
                min_value=0,
                max_value=100,
                step=1,
                unit="%",
                icon="mdi:keyboard-settings",
            )
        )

    # HID++ peripheral DPI controls
    from .helpers import extract_peripherals, peripheral_metadata

    for peripheral in extract_peripherals(data):
        dev_id = peripheral.get("id", "")
        if not dev_id.startswith("peripheral.hidpp_"):
            continue

        meta = peripheral_metadata(peripheral, coordinator.device_key)
        if not meta:
            continue

        # DPI slider (mice)
        if "dpi" in peripheral:
            entities.append(
                Desk2HANumber(
                    coordinator=coordinator,
                    metric_key=f"{dev_id}.dpi",
                    name="DPI",
                    command="peripheral.set_dpi",
                    target=dev_id,
                    param_key="value",
                    min_value=200,
                    max_value=25600,
                    step=100,
                    unit="DPI",
                    icon="mdi:mouse",
                    sub_device_id=meta.get("sub_device_id", ""),
                    sub_device_name=meta.get("sub_device_name", ""),
                    sub_manufacturer=meta.get("sub_manufacturer"),
                    sub_model=meta.get("sub_model"),
                )
            )

        # Backlight slider (keyboards)
        if "backlight_level" in peripheral:
            entities.append(
                Desk2HANumber(
                    coordinator=coordinator,
                    metric_key=f"{dev_id}.backlight_level",
                    name="Backlight",
                    command="peripheral.set_backlight",
                    target=dev_id,
                    param_key="value",
                    min_value=0,
                    max_value=100,
                    step=1,
                    unit="%",
                    icon="mdi:keyboard-settings",
                    sub_device_id=meta.get("sub_device_id", ""),
                    sub_device_name=meta.get("sub_device_name", ""),
                    sub_manufacturer=meta.get("sub_manufacturer"),
                    sub_model=meta.get("sub_model"),
                )
            )

    # UVC webcam controls
    _WEBCAM_NUMBERS: dict[str, tuple[str, float, float, float, str | None, str]] = {
        # suffix: (command, min, max, step, unit, icon)
        "brightness": ("webcam.set_brightness", 0, 255, 1, None, "mdi:brightness-6"),
        "contrast": ("webcam.set_contrast", 0, 255, 1, None, "mdi:contrast-box"),
        "saturation": ("webcam.set_saturation", 0, 255, 1, None, "mdi:palette"),
        "sharpness": ("webcam.set_sharpness", 0, 255, 1, None, "mdi:blur"),
        "gain": ("webcam.set_gain", 0, 255, 1, None, "mdi:tune-variant"),
        "gamma": ("webcam.set_gamma", 0, 500, 1, None, "mdi:gamma"),
        "zoom": ("webcam.set_zoom", 100, 400, 1, None, "mdi:magnify-plus"),
        "focus": ("webcam.set_focus", 0, 255, 1, None, "mdi:camera-enhance"),
        "exposure": ("webcam.set_exposure", -13, 0, 1, None, "mdi:camera-iris"),
        "white_balance": (
            "webcam.set_white_balance",
            2000,
            10000,
            100,
            "K",
            "mdi:white-balance-sunny",
        ),
        "pan": ("webcam.set_pan", -180, 180, 1, "°", "mdi:pan-horizontal"),
        "tilt": ("webcam.set_tilt", -180, 180, 1, "°", "mdi:pan-vertical"),
        "backlight_compensation": (
            "webcam.set_backlight_compensation",
            0,
            10,
            1,
            None,
            "mdi:brightness-auto",
        ),
    }

    for peripheral in extract_peripherals(data):
        dev_id = peripheral.get("id", "")
        if not dev_id.startswith("peripheral.webcam_"):
            continue

        meta = peripheral_metadata(peripheral, coordinator.device_key)
        if not meta:
            continue

        for suffix, (cmd, mn, mx, step, unit, icon) in _WEBCAM_NUMBERS.items():
            if suffix not in peripheral:
                continue
            entities.append(
                Desk2HANumber(
                    coordinator=coordinator,
                    metric_key=f"{dev_id}.{suffix}",
                    name=suffix.replace("_", " ").title(),
                    command=cmd,
                    target=dev_id,
                    param_key="value",
                    min_value=mn,
                    max_value=mx,
                    step=step,
                    unit=unit,
                    icon=icon,
                    **meta,
                )
            )

    # HeadsetControl peripheral controls
    for peripheral in extract_peripherals(data):
        dev_id = peripheral.get("id", "")
        if not dev_id.startswith("peripheral.headset_"):
            continue

        meta = peripheral_metadata(peripheral, coordinator.device_key)
        if not meta:
            continue

        # Sidetone slider (0-128)
        if "sidetone" in peripheral:
            entities.append(
                Desk2HANumber(
                    coordinator=coordinator,
                    metric_key=f"{dev_id}.sidetone",
                    name="Sidetone",
                    command="headset.set_sidetone",
                    target=dev_id,
                    param_key="value",
                    min_value=0,
                    max_value=128,
                    step=1,
                    icon="mdi:headphones",
                    sub_device_id=meta.get("sub_device_id", ""),
                    sub_device_name=meta.get("sub_device_name", ""),
                    sub_manufacturer=meta.get("sub_manufacturer"),
                    sub_model=meta.get("sub_model"),
                )
            )

        # Chatmix slider (0-128, 64 = balanced)
        if "chatmix" in peripheral:
            entities.append(
                Desk2HANumber(
                    coordinator=coordinator,
                    metric_key=f"{dev_id}.chatmix",
                    name="Chat Mix",
                    command="headset.set_chatmix",
                    target=dev_id,
                    param_key="value",
                    min_value=0,
                    max_value=128,
                    step=1,
                    icon="mdi:headphones",
                    sub_device_id=meta.get("sub_device_id", ""),
                    sub_device_name=meta.get("sub_device_name", ""),
                    sub_manufacturer=meta.get("sub_manufacturer"),
                    sub_model=meta.get("sub_model"),
                )
            )

    async_add_entities(entities)
    logger.info("Created %d number entities", len(entities))


class Desk2HANumber(Desk2HASubDeviceEntity, NumberEntity):
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
        sub_device_id: str = "",
        sub_device_name: str = "",
        sub_manufacturer: str | None = None,
        sub_model: str | None = None,
    ) -> None:
        super().__init__(
            coordinator,
            metric_key,
            name,
            sub_device_id=sub_device_id,
            sub_device_name=sub_device_name,
            sub_manufacturer=sub_manufacturer,
            sub_model=sub_model,
        )
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
