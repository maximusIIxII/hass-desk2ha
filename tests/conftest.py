"""Shared test fixtures for hass-desk2ha.

Mocks Home Assistant imports so tests can run without HA installed.
Uses MagicMock modules with specific classes set to real types
to avoid metaclass conflicts when inheriting.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# --- Stub classes (must be real types, not MagicMock) ---


class _CoordinatorEntity:
    def __init__(self, coordinator=None):
        self.coordinator = coordinator

    def __class_getitem__(cls, item):
        return cls


class _DataUpdateCoordinator:
    def __class_getitem__(cls, item):
        return cls


class _UpdateFailed(Exception):
    pass


class _DeviceInfo(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


# --- Mock all HA modules ---

_HA_MODULES = [
    "homeassistant",
    "homeassistant.components",
    "homeassistant.components.binary_sensor",
    "homeassistant.components.button",
    "homeassistant.components.light",
    "homeassistant.components.media_player",
    "homeassistant.components.number",
    "homeassistant.components.select",
    "homeassistant.components.sensor",
    "homeassistant.components.switch",
    "homeassistant.components.update",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.helpers",
    "homeassistant.helpers.aiohttp_client",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.entity",
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.entity_registry",
    "homeassistant.helpers.update_coordinator",
]

for mod_name in _HA_MODULES:
    sys.modules[mod_name] = MagicMock()

# --- Patch specific attributes to real types ---

# update_coordinator
uc = sys.modules["homeassistant.helpers.update_coordinator"]
uc.CoordinatorEntity = _CoordinatorEntity
uc.DataUpdateCoordinator = _DataUpdateCoordinator
uc.UpdateFailed = _UpdateFailed

# device_registry
dr = sys.modules["homeassistant.helpers.device_registry"]
dr.DeviceInfo = _DeviceInfo

# const
const = sys.modules["homeassistant.const"]
const.EntityCategory = MagicMock()
const.EntityCategory.DIAGNOSTIC = "diagnostic"

# sensor
sensor = sys.modules["homeassistant.components.sensor"]
sensor.SensorDeviceClass = MagicMock()
sensor.SensorDeviceClass.TEMPERATURE = "temperature"
sensor.SensorDeviceClass.BATTERY = "battery"
sensor.SensorDeviceClass.POWER = "power"
sensor.SensorDeviceClass.DURATION = "duration"
sensor.SensorDeviceClass.DATA_SIZE = "data_size"
sensor.SensorDeviceClass.VOLTAGE = "voltage"
sensor.SensorDeviceClass.SIGNAL_STRENGTH = "signal_strength"
sensor.SensorEntity = type("SensorEntity", (), {})

# binary_sensor
bs = sys.modules["homeassistant.components.binary_sensor"]
bs.BinarySensorDeviceClass = MagicMock()
bs.BinarySensorEntity = type("BinarySensorEntity", (), {})

# button
btn = sys.modules["homeassistant.components.button"]
btn.ButtonEntity = type("ButtonEntity", (), {})
btn.ButtonDeviceClass = MagicMock()

# number
num = sys.modules["homeassistant.components.number"]
num.NumberEntity = type("NumberEntity", (), {})
num.NumberMode = MagicMock()

# select
sel = sys.modules["homeassistant.components.select"]
sel.SelectEntity = type("SelectEntity", (), {})

# switch
sw = sys.modules["homeassistant.components.switch"]
sw.SwitchEntity = type("SwitchEntity", (), {})

# light
lt = sys.modules["homeassistant.components.light"]
lt.LightEntity = type("LightEntity", (), {})
lt.ColorMode = MagicMock()

# media_player
mp = sys.modules["homeassistant.components.media_player"]
mp.MediaPlayerEntity = type("MediaPlayerEntity", (), {})
mp.MediaPlayerEntityFeature = MagicMock()

# update
up = sys.modules["homeassistant.components.update"]
up.UpdateEntity = type("UpdateEntity", (), {})
up.UpdateEntityFeature = MagicMock()
