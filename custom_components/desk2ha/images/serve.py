"""HTTP endpoint for serving device product images.

Serves cached Tier 3 product images and falls back to the agent's
Tier 1/2 SVG icons. Mounted at /desk2ha/images/{device_key}.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from aiohttp import web
from homeassistant.core import HomeAssistant

from ..const import DOMAIN

logger = logging.getLogger(__name__)

IMAGE_URL_BASE = f"/{DOMAIN}/images"


def register_image_routes(hass: HomeAssistant) -> None:
    """Register the image serving route on HA's HTTP server."""
    hass.http.app.router.add_get(
        f"{IMAGE_URL_BASE}/{{device_key}}",
        _handle_image_request,
    )
    logger.info("Image endpoint registered at %s/{{device_key}}", IMAGE_URL_BASE)


async def _handle_image_request(request: web.Request) -> web.Response:
    """Serve a product image for a device_key.

    Priority:
    1. Cached Tier 3 image (JPEG/PNG/WebP from vendor fetch)
    2. Agent Tier 1/2 SVG icon via proxy
    """
    device_key = request.match_info["device_key"]
    hass: HomeAssistant = request.app["hass"]

    # 1. Check local Tier 3 cache
    cache_dir = Path(hass.config.config_dir) / "custom_components" / DOMAIN / "images" / "cache"
    from .cache import ImageCache

    cache = ImageCache(cache_dir)
    cached = cache.get(device_key)
    if cached and cached.is_file():
        content_type = {
            ".jpg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }.get(cached.suffix, "image/jpeg")
        return web.Response(
            body=cached.read_bytes(),
            content_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )

    # 2. Proxy to agent's /v1/image/{device_key} for SVG icons
    # For BT devices, check HA device registry for device name to help agent pick correct icon
    actual_key = device_key
    if "bt_" in device_key:
        # Try to find the device name in HA device registry to build a better key
        from homeassistant.helpers import device_registry as dr

        dev_registry = dr.async_get(hass)
        for _dk, coordinator in _get_coordinators(hass).items():
            sub_id = f"{coordinator.device_key}_{device_key}"
            dev_entry = dev_registry.async_get_device(identifiers={(DOMAIN, sub_id)})
            if dev_entry and dev_entry.name:
                name_lower = dev_entry.name.lower()
                # Append device type hint to the key for the agent
                if "mouse" in name_lower or "ms9" in name_lower:
                    actual_key = "peripheral.mouse"
                elif "keyboard" in name_lower or "kb" in name_lower:
                    actual_key = "peripheral.keyboard"
                elif "headset" in name_lower:
                    actual_key = "peripheral.headset"
                elif "earbud" in name_lower:
                    actual_key = "peripheral.earbud"
                elif "speak" in name_lower:
                    actual_key = "peripheral.speak"
                break

    coordinators = _get_coordinators(hass)
    for _dk, coordinator in coordinators.items():
        try:
            import aiohttp

            url = f"{coordinator.agent_url}/v1/image/{actual_key}"
            headers: dict[str, str] = {}
            if coordinator.agent_token:
                headers["Authorization"] = f"Bearer {coordinator.agent_token}"
            async with (
                aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session,
                session.get(url, headers=headers) as resp,
            ):
                if resp.status == 200:
                    body = await resp.read()
                    ct = resp.content_type or "image/svg+xml"
                    return web.Response(
                        body=body,
                        content_type=ct,
                        headers={"Cache-Control": "public, max-age=3600"},
                    )
        except Exception:
            logger.debug("Agent image proxy failed for %s", device_key, exc_info=True)

    return web.Response(status=404, text="Image not found")


def _get_coordinators(hass: HomeAssistant) -> dict[str, Any]:
    """Get all active coordinators."""
    from ..coordinator import Desk2HACoordinator

    result: dict[str, Any] = {}
    for _entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
        if isinstance(coordinator, Desk2HACoordinator):
            result[coordinator.device_key] = coordinator
    return result
