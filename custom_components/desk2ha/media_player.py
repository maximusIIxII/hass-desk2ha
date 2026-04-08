"""Media player platform for Desk2HA.

Exposes display speakers as media players for volume control and mute.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import Desk2HACoordinator
from .entity import Desk2HAEntity

logger = logging.getLogger(__name__)


def _extract_displays(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [d for d in data.get("displays", []) if isinstance(d, dict)]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Desk2HA media player entities for displays with volume."""
    coordinator: Desk2HACoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[MediaPlayerEntity] = []

    displays = _extract_displays(coordinator.data or {})

    for i, display in enumerate(displays):
        if "volume" not in display:
            continue

        target = display.get("id", f"display.{i}")
        idx = target.split(".")[-1] if "." in target else str(i)

        model = display.get("model", {})
        model_name = model.get("value", "") if isinstance(model, dict) else str(model)

        name = f"Display {model_name} Speaker" if model_name else f"Display {idx} Speaker"
        if len(displays) == 1 and model_name:
            name = f"{model_name} Speaker"

        entities.append(Desk2HADisplaySpeaker(coordinator, target, name))

    async_add_entities(entities)


class Desk2HADisplaySpeaker(Desk2HAEntity, MediaPlayerEntity):
    """Display speaker as a media player for volume control."""

    _attr_device_class = MediaPlayerDeviceClass.SPEAKER
    _attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_SET | MediaPlayerEntityFeature.VOLUME_STEP
    )

    def __init__(
        self,
        coordinator: Desk2HACoordinator,
        target: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, f"{target}.speaker", name)
        self._target = target
        self._volume_key = f"{target}.volume"
        self._power_key = f"{target}.power_state"

    @property
    def state(self) -> MediaPlayerState:
        power = self._find_metric(self.coordinator.data or {}, self._power_key)
        if power is not None and str(power).lower() != "on":
            return MediaPlayerState.OFF
        return MediaPlayerState.IDLE

    @property
    def volume_level(self) -> float | None:
        val = self._find_metric(self.coordinator.data or {}, self._volume_key)
        if val is not None:
            return float(val) / 100.0  # HA uses 0.0-1.0
        return None

    async def async_set_volume_level(self, volume: float) -> None:
        pct = int(volume * 100)
        await self.coordinator.async_send_command(
            "display.set_volume",
            target=self._target,
            parameters={"value": pct},
        )
        await self.coordinator.async_request_refresh()

    async def async_volume_up(self) -> None:
        current = self.volume_level or 0.5
        await self.async_set_volume_level(min(1.0, current + 0.05))

    async def async_volume_down(self) -> None:
        current = self.volume_level or 0.5
        await self.async_set_volume_level(max(0.0, current - 0.05))
