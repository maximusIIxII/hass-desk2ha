"""Product image URL resolution per vendor (Tier 3).

Each vendor resolver returns a direct image URL or None.
The caller is responsible for downloading and caching.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import aiohttp

logger = logging.getLogger(__name__)


async def resolve_image_url(
    device_info: dict[str, Any],
    session: aiohttp.ClientSession,
) -> str | None:
    """Resolve a product image URL based on device manufacturer and identifiers."""
    manufacturer = (device_info.get("manufacturer") or "").lower()
    model = device_info.get("model") or ""
    service_tag = device_info.get("service_tag") or ""

    if "dell" in manufacturer and service_tag:
        return await _resolve_dell(service_tag, model, session)
    if "lenovo" in manufacturer and model:
        return await _resolve_lenovo(model, session)
    if ("hp" in manufacturer or "hewlett" in manufacturer) and model:
        return await _resolve_hp(model, session)
    if "logitech" in manufacturer and model:
        return _resolve_logitech(model)

    return None


async def _resolve_dell(
    service_tag: str,
    model: str,
    session: aiohttp.ClientSession,
) -> str | None:
    """Resolve Dell product image via support page API.

    Dell's support site returns JSON with product details including image URL
    when queried with a service tag.
    """
    try:
        url = f"https://www.dell.com/support/home/en-us/product-support/servicetag/{service_tag}/overview"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html",
        }
        async with session.get(url, headers=headers, timeout=_timeout()) as resp:
            if resp.status != 200:
                return None
            text = await resp.text()

        # Dell support pages embed product image URL in meta tags or JSON-LD
        # Pattern: og:image meta tag
        match = re.search(r'property="og:image"\s+content="([^"]+)"', text)
        if match:
            img_url = match.group(1)
            if img_url.startswith("http") and ("dell.com" in img_url or "i.dell.com" in img_url):
                return img_url

        # Alternative: Dell product image CDN pattern
        # i.dell.com/is/image/DellContent/content/dam/...
        match = re.search(r'(https://i\.dell\.com/is/image/[^"\'>\s]+)', text)
        if match:
            return match.group(1)

    except Exception:
        logger.debug("Dell image resolve failed for %s", service_tag, exc_info=True)

    # Fallback: try known Dell CDN pattern based on model name
    return _dell_cdn_fallback(model)


def _dell_cdn_fallback(model: str) -> str | None:
    """Try known Dell image CDN URL patterns based on model name."""
    if not model:
        return None

    # Normalize: "Precision 5770" -> "precision-5770"
    slug = re.sub(r"[^a-z0-9]+", "-", model.lower()).strip("-")

    # Dell's CDN uses these patterns for product images
    candidates = [
        f"https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/notebooks/precision-notebooks/{slug}/media-gallery/{slug}-front.psd?fmt=png&wid=400",
        f"https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/notebooks/latitude-notebooks/{slug}/media-gallery/{slug}-front.psd?fmt=png&wid=400",
    ]
    # Return first candidate — caller will validate via HTTP
    return candidates[0] if candidates else None


async def _resolve_lenovo(
    model: str,
    session: aiohttp.ClientSession,
) -> str | None:
    """Resolve Lenovo product image via PSREF."""
    try:
        # PSREF API returns product info including image
        slug = model.replace(" ", "+")
        url = f"https://psref.lenovo.com/api/search?query={slug}"
        headers = {"Accept": "application/json"}

        async with session.get(url, headers=headers, timeout=_timeout()) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()

        # Extract image URL from search results
        results = data if isinstance(data, list) else data.get("results", [])
        for item in results[:3]:
            img = item.get("imageUrl") or item.get("image") or ""
            if img.startswith("http"):
                return img

    except Exception:
        logger.debug("Lenovo image resolve failed for %s", model, exc_info=True)

    return None


async def _resolve_hp(
    model: str,
    session: aiohttp.ClientSession,
) -> str | None:
    """Resolve HP product image via product page."""
    try:
        slug = model.lower().replace(" ", "-")
        url = f"https://support.hp.com/us-en/product/details/{slug}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        async with session.get(url, headers=headers, timeout=_timeout()) as resp:
            if resp.status != 200:
                return None
            text = await resp.text()

        match = re.search(r'property="og:image"\s+content="([^"]+)"', text)
        if match:
            return match.group(1)

    except Exception:
        logger.debug("HP image resolve failed for %s", model, exc_info=True)

    return None


# Known Logitech product image URLs (no API, curated list)
_LOGITECH_IMAGES: dict[str, str] = {
    "litra glow": "https://resource.logitech.com/w_800,c_limit,q_auto,f_auto,dpr_1.0/d_transparent.gif/content/dam/logitech/en/products/lighting/litra-glow/gallery/litra-glow-gallery-1.png",
    "litra beam": "https://resource.logitech.com/w_800,c_limit,q_auto,f_auto,dpr_1.0/d_transparent.gif/content/dam/logitech/en/products/lighting/litra-beam/gallery/litra-beam-gallery-1.png",
    "mx master 3s": "https://resource.logitech.com/w_800,c_limit,q_auto,f_auto,dpr_1.0/d_transparent.gif/content/dam/logitech/en/products/mice/mx-master-3s/gallery/mx-master-3s-mouse-top-view-graphite.png",
    "mx keys s": "https://resource.logitech.com/w_800,c_limit,q_auto,f_auto,dpr_1.0/d_transparent.gif/content/dam/logitech/en/products/keyboards/mx-keys-s/gallery/mx-keys-s-top-view-graphite.png",
    "bolt receiver": "https://resource.logitech.com/w_800,c_limit,q_auto,f_auto,dpr_1.0/d_transparent.gif/content/dam/logitech/en/products/mice/logi-bolt-usb-receiver/gallery/logi-bolt-gallery-1.png",
}


def _resolve_logitech(model: str) -> str | None:
    """Resolve Logitech product image from known URLs."""
    model_lower = model.lower().strip()
    for key, url in _LOGITECH_IMAGES.items():
        if key in model_lower:
            return url
    return None


def _timeout() -> aiohttp.ClientTimeout:
    import aiohttp

    return aiohttp.ClientTimeout(total=15)
