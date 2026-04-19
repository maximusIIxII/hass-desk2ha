"""Tests for entity availability logic.

Ensures:
1. Action-only entities (buttons, update) have _check_metric_available = False
2. _find_metric resolves all key patterns correctly
3. available property returns correct values for present/absent metrics
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.desk2ha.button import (
    Desk2HACommandButton,
    Desk2HADisplayCommandButton,
    Desk2HARefreshButton,
    Desk2HARestartButton,
)
from custom_components.desk2ha.entity import Desk2HAEntity, Desk2HASubDeviceEntity
from custom_components.desk2ha.update import Desk2HAUpdateEntity

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_coordinator(data: dict | None = None, agent_info: dict | None = None):
    """Create a minimal mock coordinator."""
    coord = MagicMock()
    coord.data = data
    coord.device_key = "test_host"
    coord.agent_info = agent_info or {"agent_version": "0.8.5"}
    return coord


# ---------------------------------------------------------------------------
# 1. Action entities MUST NOT check metric availability
# ---------------------------------------------------------------------------

_ACTION_ENTITY_CLASSES = [
    Desk2HARefreshButton,
    Desk2HARestartButton,
    Desk2HACommandButton,
    Desk2HADisplayCommandButton,
    Desk2HAUpdateEntity,
]


@pytest.mark.parametrize("cls", _ACTION_ENTITY_CLASSES, ids=lambda c: c.__name__)
def test_action_entities_skip_metric_check(cls):
    """Action-only entities must have _check_metric_available = False."""
    assert cls._check_metric_available is False, (
        f"{cls.__name__} is an action entity but _check_metric_available is not False. "
        "This will cause the entity to show as 'unavailable' in HA."
    )


# ---------------------------------------------------------------------------
# 2. Metric-based entities MUST check metric availability
# ---------------------------------------------------------------------------

_METRIC_ENTITY_CLASSES = [
    Desk2HAEntity,
    Desk2HASubDeviceEntity,
]


@pytest.mark.parametrize("cls", _METRIC_ENTITY_CLASSES, ids=lambda c: c.__name__)
def test_metric_entities_check_availability(cls):
    """Metric entities must have _check_metric_available = True (default)."""
    assert cls._check_metric_available is True, f"{cls.__name__} should check metric availability."


# ---------------------------------------------------------------------------
# 3. _find_metric resolves all key patterns
# ---------------------------------------------------------------------------

SAMPLE_DATA = {
    "cpu_usage": {"value": 42},
    "hostname": "DESKTOP-TEST",
    "thermals": {
        "cpu": {"value": 65},
        "gpu": {"value": 72},
        "fan.cpu": {"value": 2100},
        "fan.gpu": {"value": 1800},
    },
    "system": {
        "lid_open": {"value": True},
        "network.wlan.ssid": {"value": "MyWiFi"},
        "network.wlan.signal_dbm": {"value": -55},
    },
    "displays": [
        {"id": "display.0", "brightness": {"value": 80}, "name": "Dell U2723QE"},
    ],
    "peripherals": [
        {"id": "peripheral.bt_mouse", "battery": {"value": 75}, "connected": True},
    ],
}


class TestFindMetric:
    """Test _find_metric key resolution for all supported patterns."""

    def test_direct_top_level_dict(self):
        assert Desk2HAEntity._find_metric(SAMPLE_DATA, "cpu_usage") == 42

    def test_direct_top_level_plain(self):
        assert Desk2HAEntity._find_metric(SAMPLE_DATA, "hostname") == "DESKTOP-TEST"

    def test_category_metric_2part(self):
        assert Desk2HAEntity._find_metric(SAMPLE_DATA, "thermals.cpu") == 65

    def test_category_metric_dotted_subkey_3part(self):
        """3-part key: thermals.fan.gpu must resolve to thermals['fan.gpu']."""
        assert Desk2HAEntity._find_metric(SAMPLE_DATA, "thermals.fan.gpu") == 1800

    def test_category_metric_dotted_subkey_fan_cpu(self):
        assert Desk2HAEntity._find_metric(SAMPLE_DATA, "thermals.fan.cpu") == 2100

    def test_system_network_wlan_ssid(self):
        """4-part key: system.network.wlan.ssid."""
        assert Desk2HAEntity._find_metric(SAMPLE_DATA, "system.network.wlan.ssid") == "MyWiFi"

    def test_system_network_wlan_signal(self):
        assert Desk2HAEntity._find_metric(SAMPLE_DATA, "system.network.wlan.signal_dbm") == -55

    def test_device_array_display(self):
        assert Desk2HAEntity._find_metric(SAMPLE_DATA, "display.0.brightness") == 80

    def test_device_array_peripheral(self):
        assert Desk2HAEntity._find_metric(SAMPLE_DATA, "peripheral.bt_mouse.battery") == 75

    def test_missing_key_returns_default(self):
        assert Desk2HAEntity._find_metric(SAMPLE_DATA, "nonexistent.key") is None

    def test_missing_key_returns_custom_default(self):
        sentinel = object()
        assert Desk2HAEntity._find_metric(SAMPLE_DATA, "nonexistent.key", sentinel) is sentinel

    def test_missing_subkey_in_category(self):
        sentinel = object()
        result = Desk2HAEntity._find_metric(SAMPLE_DATA, "thermals.nonexistent", sentinel)
        assert result is sentinel

    def test_missing_dotted_subkey_in_category(self):
        sentinel = object()
        result = Desk2HAEntity._find_metric(SAMPLE_DATA, "thermals.fan.nonexistent", sentinel)
        assert result is sentinel


# ---------------------------------------------------------------------------
# 4. available property integration tests
# ---------------------------------------------------------------------------


class TestEntityAvailability:
    """Test the available property on entity instances."""

    def test_metric_entity_available_when_metric_present(self):
        coord = _make_coordinator(data=SAMPLE_DATA)
        entity = Desk2HAEntity(coord, "cpu_usage", "CPU Usage")
        assert entity.available is True

    def test_metric_entity_unavailable_when_metric_absent(self):
        coord = _make_coordinator(data=SAMPLE_DATA)
        entity = Desk2HAEntity(coord, "nonexistent_metric", "Missing")
        assert entity.available is False

    def test_metric_entity_available_when_no_data(self):
        coord = _make_coordinator(data=None)
        # When data is None, falls through to super().available
        entity = Desk2HAEntity(coord, "cpu_usage", "CPU Usage")
        # super().available is True from mock, just verify no crash
        _ = entity.available

    def test_action_entity_always_available(self):
        """Buttons must stay available even when their key has no metric data."""
        coord = _make_coordinator(data=SAMPLE_DATA)
        button = Desk2HARefreshButton(coord)
        # Should not raise and should not return False
        result = button.available
        # Result comes from super().available (MagicMock), but must NOT be False
        assert result is not False

    def test_dotted_subkey_entity_available(self):
        coord = _make_coordinator(data=SAMPLE_DATA)
        entity = Desk2HAEntity(coord, "thermals.fan.gpu", "GPU Fan")
        assert entity.available is True

    def test_dotted_subkey_entity_unavailable_when_absent(self):
        coord = _make_coordinator(data=SAMPLE_DATA)
        entity = Desk2HAEntity(coord, "thermals.fan.missing", "Missing Fan")
        assert entity.available is False


# ---------------------------------------------------------------------------
# Update entity icon override
# ---------------------------------------------------------------------------


class TestUpdateEntityIcon:
    """HA core's UpdateEntity.entity_picture forces the brands.home-assistant.io
    URL by default. We serve our own brand icon as a static path and need
    entity_picture to resolve to it — pin the override so a future HA-core
    refactor can't silently regress us back to the brands URL.
    """

    def test_entity_picture_uses_local_brand_path(self):
        coord = _make_coordinator(data=SAMPLE_DATA)
        entity = Desk2HAUpdateEntity(coord)
        assert entity.entity_picture == "/desk2ha/brand/icon.png"

    def test_entity_picture_does_not_use_brands_homeassistant_io(self):
        coord = _make_coordinator(data=SAMPLE_DATA)
        entity = Desk2HAUpdateEntity(coord)
        assert "brands.home-assistant.io" not in (entity.entity_picture or "")
