"""Shared helpers for entity setup."""

from __future__ import annotations

from typing import Any


def extract_displays(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract display entries from metrics data."""
    return [d for d in data.get("displays", []) if isinstance(d, dict)]


def extract_peripherals(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract peripheral entries from metrics data."""
    return [d for d in data.get("peripherals", []) if isinstance(d, dict)]


def display_metadata(display: dict[str, Any], idx: str, device_key: str) -> dict[str, str | None]:
    """Extract display metadata for sub-device creation."""
    model_raw = display.get("model", {})
    model = model_raw.get("value", "") if isinstance(model_raw, dict) else str(model_raw)
    mfg_raw = display.get("manufacturer", {})
    mfg = mfg_raw.get("value", "") if isinstance(mfg_raw, dict) else str(mfg_raw)

    return {
        "sub_device_id": f"{device_key}_display_{idx}",
        "sub_device_name": f"{mfg} {model}".strip() or f"Display {idx}",
        "sub_manufacturer": mfg or None,
        "sub_model": model or None,
    }


def peripheral_metadata(peripheral: dict[str, Any], device_key: str) -> dict[str, str | None]:
    """Extract peripheral metadata for sub-device creation."""
    dev_id = peripheral.get("id", "unknown")
    model_raw = peripheral.get("model", {})
    model = model_raw.get("value", "") if isinstance(model_raw, dict) else str(model_raw)
    mfg_raw = peripheral.get("manufacturer", {})
    mfg = mfg_raw.get("value", "") if isinstance(mfg_raw, dict) else str(mfg_raw)

    return {
        "sub_device_id": f"{device_key}_{dev_id}",
        "sub_device_name": f"{mfg} {model}".strip() or dev_id,
        "sub_manufacturer": mfg or None,
        "sub_model": model or None,
    }
