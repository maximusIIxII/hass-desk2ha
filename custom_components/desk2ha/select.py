"""Select platform for Desk2HA.

Dynamically creates select entities for each display reported by the agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Desk2HACoordinator
from .entity import Desk2HAEntity


@dataclass(frozen=True, slots=True)
class SelectDef:
    """Definition for a display select control."""

    suffix: str
    name_template: str
    command: str
    param_key: str
    options: list[str]
    icon: str | None = None


DISPLAY_SELECT_DEFS: list[SelectDef] = [
    SelectDef(
        "input_source", "Display {idx} Input Source",
        "display.set_input_source", "source",
        ["DP1", "DP2", "HDMI1", "HDMI2", "USBC1", "USBC2", "THUNDERBOLT", "THUNDERBOLT2"],
        "mdi:video-input-hdmi",
    ),
    SelectDef(
        "power_state", "Display {idx} Power",
        "display.set_power_state", "state",
        ["on", "standby", "off"],
        "mdi:power",
    ),
    SelectDef(
        "kvm_active_pc", "Display {idx} KVM",
        "display.set_kvm", "pc",
        ["PC1", "PC2", "PC3"],
        "mdi:monitor-multiple",
    ),
    SelectDef(
        "pbp_mode", "Display {idx} PBP Mode",
        "display.set_pbp_mode", "mode",
        ["off", "pbp"],
        "mdi:monitor-multiple",
    ),
]


def _extract_displays(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [d for d in data.get("displays", []) if isinstance(d, dict)]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Desk2HA select entities dynamically per display."""
    coordinator: Desk2HACoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = []

    displays = _extract_displays(coordinator.data or {})

    for i, display in enumerate(displays):
        target = display.get("id", f"display.{i}")
        idx = target.split(".")[-1] if "." in target else str(i)

        for defn in DISPLAY_SELECT_DEFS:
            if defn.suffix not in display:
                continue
            name = defn.name_template.format(idx=idx)
            if len(displays) == 1:
                name = name.replace(f" {idx} ", " ")
            entities.append(
                Desk2HASelect(
                    coordinator=coordinator,
                    metric_key=f"{target}.{defn.suffix}",
                    name=name,
                    command=defn.command,
                    target=target,
                    param_key=defn.param_key,
                    options=defn.options,
                    icon=defn.icon,
                )
            )

    async_add_entities(entities)


class Desk2HASelect(Desk2HAEntity, SelectEntity):
    """A Desk2HA select entity."""

    def __init__(
        self,
        coordinator: Desk2HACoordinator,
        metric_key: str,
        name: str,
        command: str,
        target: str,
        param_key: str,
        options: list[str],
        icon: str | None = None,
    ) -> None:
        super().__init__(coordinator, metric_key, name)
        self._command = command
        self._target = target
        self._param_key = param_key
        self._attr_options = options
        if icon:
            self._attr_icon = icon

    @property
    def current_option(self) -> str | None:
        val = self.metric_value
        if val is None:
            return None
        val_str = str(val)
        # If current value not in options, add it dynamically
        if val_str not in self._attr_options:
            self._attr_options = [*self._attr_options, val_str]
        return val_str

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_send_command(
            self._command,
            target=self._target,
            parameters={self._param_key: option},
        )
        await self.coordinator.async_request_refresh()
