"""Tests for Desk2HA shared helpers."""

from __future__ import annotations

from custom_components.desk2ha.helpers import (
    _get_value,
    _is_generic_usb,
    display_metadata,
    extract_displays,
    extract_peripherals,
    peripheral_metadata,
)


def test_extract_displays_empty():
    assert extract_displays({}) == []
    assert extract_displays({"displays": []}) == []


def test_extract_displays():
    data = {"displays": [{"model": "U2723QE"}, {"model": "P2422H"}]}
    result = extract_displays(data)
    assert len(result) == 2
    assert result[0]["model"] == "U2723QE"


def test_extract_displays_skips_non_dicts():
    data = {"displays": [{"model": "U2723QE"}, "invalid", None]}
    result = extract_displays(data)
    assert len(result) == 1


def test_extract_peripherals():
    data = {"peripherals": [{"id": "usb_0", "model": "Speak2 75"}]}
    result = extract_peripherals(data)
    assert len(result) == 1
    assert result[0]["model"] == "Speak2 75"


def test_get_value_dict():
    assert _get_value({"value": 42}) == "42"
    assert _get_value({"value": "hello"}) == "hello"


def test_get_value_plain():
    assert _get_value("test") == "test"
    assert _get_value(None) == ""
    assert _get_value("  spaced  ") == "spaced"


def test_display_metadata():
    display = {"model": {"value": "U2723QE"}, "manufacturer": {"value": "Dell"}}
    meta = display_metadata(display, "0", "ST-ABC123")
    assert meta["sub_device_id"] == "ST-ABC123_display_0"
    assert meta["sub_device_name"] == "U2723QE"
    assert meta["sub_manufacturer"] == "Dell"
    assert meta["sub_model"] == "U2723QE"


def test_display_metadata_no_model():
    meta = display_metadata({}, "1", "ST-ABC123")
    assert meta["sub_device_name"] == "Display 1"
    assert meta["sub_manufacturer"] is None


def test_peripheral_metadata():
    peripheral = {
        "id": "usb_0",
        "model": {"value": "Speak2 75"},
        "manufacturer": {"value": "Jabra"},
    }
    meta = peripheral_metadata(peripheral, "ST-ABC123")
    assert meta["sub_device_id"] == "ST-ABC123_usb_0"
    assert meta["sub_device_name"] == "Speak2 75"
    assert meta["sub_manufacturer"] == "Jabra"


def test_peripheral_metadata_generic_usb():
    peripheral = {"id": "usb_5", "model": {"value": "USB-Eingabegerät"}}
    meta = peripheral_metadata(peripheral, "ST-ABC123")
    assert meta == {}


def test_is_generic_usb():
    assert _is_generic_usb("USB-Eingabegerät") is True
    assert _is_generic_usb("USB Composite Device") is True
    assert _is_generic_usb("usb hub") is True
    assert _is_generic_usb("Jabra Speak2 75") is False
    assert _is_generic_usb("Dell Webcam WB7022") is False
