"""Tests for sensor utility functions (flatten, make_name, known sensors)."""

from __future__ import annotations

from custom_components.desk2ha.sensor import (
    KNOWN_SENSORS,
    _flatten_metrics,
    _make_name,
)


def test_flatten_simple_metric():
    data = {"cpu_package": {"value": 55.0, "timestamp": 1.0}}
    flat = _flatten_metrics(data)
    assert "cpu_package" in flat
    assert flat["cpu_package"]["value"] == 55.0


def test_flatten_nested_category():
    data = {"system": {"cpu_usage_percent": 42.0, "ram_used_gb": 8.5}}
    flat = _flatten_metrics(data)
    assert flat["system.cpu_usage_percent"] == 42.0
    assert flat["system.ram_used_gb"] == 8.5


def test_flatten_display_array():
    data = {
        "displays": [
            {
                "id": "display.0",
                "brightness_percent": {"value": 75},
                "model": {"value": "U2723QE"},
            }
        ]
    }
    flat = _flatten_metrics(data)
    assert "display.0.brightness_percent" in flat
    assert "display.0.model" in flat


def test_flatten_skips_metadata():
    data = {"schema_version": "2.0.0", "device_key": "ST-ABC", "cpu_package": {"value": 50}}
    flat = _flatten_metrics(data)
    assert "schema_version" not in flat
    assert "device_key" not in flat
    assert "cpu_package" in flat


def test_flatten_peripheral_array():
    data = {
        "peripherals": [
            {
                "id": "peripheral.usb_0",
                "model": {"value": "Speak2 75"},
                "manufacturer": {"value": "Jabra"},
            }
        ]
    }
    flat = _flatten_metrics(data)
    assert "peripheral.usb_0.model" in flat
    assert "peripheral.usb_0.manufacturer" in flat


def test_make_name_system():
    assert _make_name("system.cpu_usage_percent") == "Cpu Usage Percent"


def test_make_name_display():
    assert _make_name("display.0.brightness_percent") == "Display 0 Brightness Percent"


def test_make_name_peripheral():
    result = _make_name("peripheral.usb_0.model")
    assert "Peripheral" in result
    assert "Model" in result


def test_make_name_simple():
    assert _make_name("cpu_package") == "Cpu Package"


def test_known_sensors_has_core_metrics():
    assert "system.cpu_usage_percent" in KNOWN_SENSORS
    assert "battery.level_percent" in KNOWN_SENSORS
    assert "cpu_package" in KNOWN_SENSORS
    assert "agent.version" in KNOWN_SENSORS
    assert "network.wifi_ssid" in KNOWN_SENSORS


def test_known_sensors_diagnostic_flag():
    assert KNOWN_SENSORS["system.cpu_model"].diagnostic is True
    assert KNOWN_SENSORS["agent.version"].diagnostic is True
    assert KNOWN_SENSORS["system.cpu_usage_percent"].diagnostic is False
