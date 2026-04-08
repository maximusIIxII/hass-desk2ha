"""Shared helpers for entity setup."""

from __future__ import annotations

from typing import Any


def extract_displays(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract display entries from metrics data."""
    return [d for d in data.get("displays", []) if isinstance(d, dict)]


def extract_peripherals(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract peripheral entries from metrics data."""
    return [d for d in data.get("peripherals", []) if isinstance(d, dict)]


def _strip_manufacturer_prefix(name: str, manufacturer: str) -> str:
    """Remove manufacturer name from the beginning of a device name.

    Prevents HA from showing 'Dell Dell KM7321W Keyboard' when manufacturer
    is already set on the device. HA prepends manufacturer automatically.
    """
    if not name or not manufacturer:
        return name
    # Check if name starts with manufacturer (case-insensitive)
    mfg_lower = manufacturer.lower().strip()
    name_lower = name.lower().strip()
    if name_lower.startswith(mfg_lower):
        stripped = name[len(manufacturer) :].strip()
        return stripped if stripped else name
    return name


def _get_value(raw: Any) -> str:
    """Extract string value from a metric (dict with 'value' or plain)."""
    if isinstance(raw, dict) and "value" in raw:
        return str(raw["value"]).strip()
    return str(raw).strip() if raw else ""


def display_metadata(display: dict[str, Any], idx: str, device_key: str) -> dict[str, str | None]:
    """Extract display metadata for sub-device creation."""
    model = _get_value(display.get("model", ""))
    mfg = _get_value(display.get("manufacturer", ""))

    # Use model as name (don't repeat manufacturer)
    name = _strip_manufacturer_prefix(model, mfg) or f"Display {idx}"

    return {
        "sub_device_id": f"{device_key}_display_{idx}",
        "sub_device_name": name,
        "sub_manufacturer": mfg or None,
        "sub_model": model or None,
    }


def peripheral_metadata(peripheral: dict[str, Any], device_key: str) -> dict[str, str | None]:
    """Extract peripheral metadata for sub-device creation."""
    dev_id = peripheral.get("id", "unknown")
    model = _get_value(peripheral.get("model", ""))
    mfg = _get_value(peripheral.get("manufacturer", ""))

    # Skip generic/unknown USB devices (no sub-device)
    if _is_generic_usb(model):
        return {}

    # Use model as name, strip manufacturer prefix to avoid "Dell Dell KM7321W"
    name = _strip_manufacturer_prefix(model, mfg) or dev_id

    return {
        "sub_device_id": f"{device_key}_{dev_id}",
        "sub_device_name": name,
        "sub_manufacturer": mfg or None,
        "sub_model": model or None,
    }


_GENERIC_USB_PATTERNS = [
    "usb-eingabe",
    "usb-verbund",
    "usb input",
    "usb composite",
    "usb hub",
    "usb-eingabeger",
    "usb-verbundger",
    "eingabeger",
    "verbundger",
    "generic usb",
    "billboard",
    "root hub",
]


def _is_generic_usb(model: str) -> bool:
    """Check if a USB device name is generic/unhelpful."""
    lower = model.lower()
    return any(g in lower for g in _GENERIC_USB_PATTERNS)
