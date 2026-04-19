"""Tests for sensor utility functions (flatten, make_name, known sensors)."""

from __future__ import annotations

from custom_components.desk2ha.sensor import (
    _DISPLAY_CONTROL_KEYS,
    _WEBCAM_CONTROL_KEYS,
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


def test_charge_mode_is_enum_with_ac_idle_option():
    """power.charge_mode surfaces adaptive-pause state ("ac_idle").

    Without this option HA would flag the value as unknown and hide the
    sensor — which would silently regress the fix.
    """
    from homeassistant.components.sensor import SensorDeviceClass

    defn = KNOWN_SENSORS["power.charge_mode"]
    assert defn.device_class is SensorDeviceClass.ENUM
    assert defn.options is not None
    assert "ac_idle" in defn.options
    assert "charging" in defn.options
    assert "discharging" in defn.options
    assert "full" in defn.options


# ---------------------------------------------------------------------------
# Sensor-exclusion sets: display controls & webcam controls
# ---------------------------------------------------------------------------


def test_display_control_keys_excludes_known_controls():
    """Display metrics handled by number/select/switch must be in the exclusion set."""
    expected = {
        "brightness_percent",
        "contrast_percent",
        "volume",
        "input_source",
        "color_preset",
        "sharpness",
        "audio_mute",
    }
    assert expected.issubset(_DISPLAY_CONTROL_KEYS)


def test_webcam_control_keys_matches_number_and_switch():
    """Every webcam number/switch suffix must appear in _WEBCAM_CONTROL_KEYS."""
    number_suffixes = {
        "brightness",
        "contrast",
        "saturation",
        "sharpness",
        "gain",
        "gamma",
        "zoom",
        "focus",
        "exposure",
        "white_balance",
        "pan",
        "tilt",
        "backlight_compensation",
    }
    switch_suffixes = {"autofocus", "auto_wb", "auto_exposure"}
    assert number_suffixes.issubset(_WEBCAM_CONTROL_KEYS)
    assert switch_suffixes.issubset(_WEBCAM_CONTROL_KEYS)


def test_webcam_control_keys_would_filter_sensor(monkeypatch):
    """Webcam control metrics must be skipped during sensor entity creation.

    Simulates the filter logic from async_setup_entry to ensure
    peripheral.webcam_* metrics with control suffixes are excluded.
    """
    webcam_metrics = {f"peripheral.webcam_0.{suffix}": 42 for suffix in _WEBCAM_CONTROL_KEYS}
    # Add a non-control webcam metric that SHOULD pass through
    webcam_metrics["peripheral.webcam_0.resolution"] = "1920x1080"

    skipped = []
    passed = []
    for metric_key in webcam_metrics:
        key_suffix = metric_key.rsplit(".", 1)[-1]
        if metric_key.startswith("peripheral.webcam_") and key_suffix in _WEBCAM_CONTROL_KEYS:
            skipped.append(metric_key)
        else:
            passed.append(metric_key)

    assert len(skipped) == len(_WEBCAM_CONTROL_KEYS)
    assert "peripheral.webcam_0.resolution" in passed
    assert all("peripheral.webcam_0." in k for k in skipped)
