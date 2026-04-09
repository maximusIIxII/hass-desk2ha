"""Local image cache for product images (Tier 3)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiohttp

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 1_048_576  # 1 MB per image
MAX_CACHE_BYTES = 104_857_600  # 100 MB total
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class ImageCache:
    """Download and cache product images locally."""

    def __init__(self, cache_dir: Path) -> None:
        self._dir = cache_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def get(self, device_key: str) -> Path | None:
        """Return cached image path if it exists."""
        for ext in (".jpg", ".png", ".webp"):
            path = self._dir / f"{device_key}{ext}"
            if path.is_file():
                return path
        return None

    async def fetch_and_store(
        self,
        device_key: str,
        url: str,
        session: aiohttp.ClientSession,
    ) -> Path | None:
        """Download image from URL and store locally. Returns path or None."""
        try:
            import aiohttp as _aiohttp

            async with session.get(url, timeout=_aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    logger.warning("Image fetch failed for %s: HTTP %d", device_key, resp.status)
                    return None

                content_type = resp.content_type or ""
                if content_type not in ALLOWED_CONTENT_TYPES:
                    logger.warning("Unexpected content type for %s: %s", device_key, content_type)
                    return None

                content_length = resp.content_length or 0
                if content_length > MAX_IMAGE_BYTES:
                    logger.warning("Image too large for %s: %d bytes", device_key, content_length)
                    return None

                data = await resp.read()
                if len(data) > MAX_IMAGE_BYTES:
                    return None

                # Determine extension from content type
                ext = {
                    "image/jpeg": ".jpg",
                    "image/png": ".png",
                    "image/webp": ".webp",
                }.get(content_type, ".jpg")

                # Check total cache size
                self._enforce_cache_limit()

                path = self._dir / f"{device_key}{ext}"
                path.write_bytes(data)
                logger.info("Cached product image for %s (%d bytes)", device_key, len(data))
                return path

        except Exception:
            logger.debug("Failed to fetch image for %s from %s", device_key, url, exc_info=True)
            return None

    def clear(self, device_key: str | None = None) -> int:
        """Clear cached images. If device_key given, clear only that device."""
        removed = 0
        if device_key:
            for ext in (".jpg", ".png", ".webp"):
                path = self._dir / f"{device_key}{ext}"
                if path.is_file():
                    path.unlink()
                    removed += 1
        else:
            for path in self._dir.iterdir():
                if path.suffix in (".jpg", ".png", ".webp"):
                    path.unlink()
                    removed += 1
        return removed

    def _enforce_cache_limit(self) -> None:
        """Remove oldest files if total cache exceeds limit."""
        files = sorted(self._dir.glob("*.*"), key=lambda p: p.stat().st_mtime)
        total = sum(f.stat().st_size for f in files)
        while total > MAX_CACHE_BYTES and files:
            oldest = files.pop(0)
            total -= oldest.stat().st_size
            oldest.unlink()
            logger.info("Cache limit: removed %s", oldest.name)
