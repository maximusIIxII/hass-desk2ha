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
from .entity import Desk2HASubDeviceEntity
from .helpers import display_metadata, extract_displays


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
    SwitchDef(
        "audio_mute",
        "Display {idx} Audio Mute",
        "display.set_audio_mute",
        "display.set_audio_mute",
        "mute",
        "mdi:volume-off",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Desk2HA switch entities dynamically per display."""
    coordinator: Desk2HACoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = []

    displays = extract_displays(coordinator.data or {})

    for i, display in enumerate(displays):
        target = display.get("id", f"display.{i}")
        idx = target.split(".")[-1] if "." in target else str(i)
        meta = display_metadata(display, idx, coordinator.device_key)

        for defn in DISPLAY_SWITCH_DEFS:
            if defn.suffix not in display:
                continue
            entities.append(
                Desk2HASwitch(
                    coordinator=coordinator,
                    metric_key=f"{target}.{defn.suffix}",
                    name=defn.name_template.format(idx=idx).replace(f"Display {idx} ", ""),
                    command_on=defn.command_on,
                    command_off=defn.command_off,
                    target=target,
                    param_key=defn.param_key,
                    icon=defn.icon,
                    **meta,
                )
            )

    # UVC webcam toggle switches
    from .helpers import extract_peripherals, peripheral_metadata

    _WEBCAM_SWITCHES: dict[str, tuple[str, str]] = {
        # suffix: (command, icon)
        "autofocus": ("webcam.set_autofocus", "mdi:camera-enhance"),
        "auto_wb": ("webcam.set_auto_wb", "mdi:white-balance-auto"),
        "auto_exposure": ("webcam.set_auto_exposure", "mdi:camera-iris"),
    }

    for peripheral in extract_peripherals(coordinator.data or {}):
        dev_id = peripheral.get("id", "")
        if not dev_id.startswith("peripheral.webcam_"):
            continue
        meta = peripheral_metadata(peripheral, coordinator.device_key)
        if not meta:
            continue
        for suffix, (cmd, icon) in _WEBCAM_SWITCHES.items():
            if suffix not in peripheral:
                continue
            entities.append(
                Desk2HASwitch(
                    coordinator=coordinator,
                    metric_key=f"{dev_id}.{suffix}",
                    name=suffix.replace("_", " ").title(),
                    command_on=cmd,
                    command_off=cmd,
                    target=dev_id,
                    param_key="value",
                    icon=icon,
                    **meta,
                )
            )

    # HeadsetControl LED switches

    for peripheral in extract_peripherals(coordinator.data or {}):
        dev_id = peripheral.get("id", "")
        if not dev_id.startswith("peripheral.headset_"):
            continue
        if "led" not in peripheral:
            continue

        meta = peripheral_metadata(peripheral, coordinator.device_key)
        if not meta:
            continue
        entities.append(
            Desk2HASwitch(
                coordinator=coordinator,
                metric_key=f"{dev_id}.led",
                name="LED",
                command_on="headset.set_led",
                command_off="headset.set_led",
                target=dev_id,
                param_key="enabled",
                icon="mdi:led-on",
                **meta,
            )
        )

    # BLE Scanning switch (system-level, not per-display)
    data = coordinator.data or {}
    system = data.get("system", {})
    ble_scanning = system.get("ble_scanning")
    if ble_scanning is not None:
        entities.append(
            Desk2HASwitch(
                coordinator=coordinator,
                metric_key="system.ble_scanning",
                name="BLE Scanning",
                command_on="ble.set_scanning",
                command_off="ble.set_scanning",
                target="",
                param_key="enabled",
                icon="mdi:bluetooth-settings",
            )
        )

    async_add_entities(entities)


class Desk2HASwitch(Desk2HASubDeviceEntity, SwitchEntity):
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
        **sub_kwargs: Any,
    ) -> None:
        super().__init__(coordinator, metric_key, name, **sub_kwargs)
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
            parameters={self._param_key: True},
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command(
            self._command_off,
            target=self._target,
            parameters={self._param_key: False},
        )
        await self.coordinator.async_request_refresh()
