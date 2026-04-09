"""Tests for product image cache."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.desk2ha.images.cache import (
    MAX_IMAGE_BYTES,
    ImageCache,
)


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    d = tmp_path / "image_cache"
    d.mkdir()
    return d


@pytest.fixture
def cache(cache_dir: Path) -> ImageCache:
    return ImageCache(cache_dir)


class TestGet:
    def test_returns_none_when_empty(self, cache: ImageCache) -> None:
        assert cache.get("dev1") is None

    def test_returns_path_when_cached(self, cache: ImageCache, cache_dir: Path) -> None:
        img = cache_dir / "dev1.png"
        img.write_bytes(b"\x89PNG")
        assert cache.get("dev1") == img

    def test_prefers_jpg(self, cache: ImageCache, cache_dir: Path) -> None:
        (cache_dir / "dev1.jpg").write_bytes(b"\xff\xd8")
        (cache_dir / "dev1.png").write_bytes(b"\x89PNG")
        result = cache.get("dev1")
        assert result is not None
        assert result.suffix == ".jpg"


def _mock_session(resp: AsyncMock) -> AsyncMock:
    """Create a mock aiohttp session with proper async context manager."""
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session = AsyncMock()
    session.get = MagicMock(return_value=ctx)
    return session


class TestFetchAndStore:
    @pytest.mark.asyncio
    async def test_stores_valid_image(self, cache: ImageCache, cache_dir: Path) -> None:
        data = b"\x89PNG" + b"\x00" * 100
        resp = AsyncMock()
        resp.status = 200
        resp.content_type = "image/png"
        resp.content_length = len(data)
        resp.read = AsyncMock(return_value=data)

        result = await cache.fetch_and_store(
            "dev1", "https://example.com/img.png", _mock_session(resp)
        )
        assert result is not None
        assert result.exists()
        assert result.suffix == ".png"

    @pytest.mark.asyncio
    async def test_rejects_non_200(self, cache: ImageCache) -> None:
        resp = AsyncMock()
        resp.status = 404

        result = await cache.fetch_and_store(
            "dev1", "https://example.com/img.png", _mock_session(resp)
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_rejects_wrong_content_type(self, cache: ImageCache) -> None:
        resp = AsyncMock()
        resp.status = 200
        resp.content_type = "text/html"

        result = await cache.fetch_and_store(
            "dev1", "https://example.com/img.png", _mock_session(resp)
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_rejects_oversized(self, cache: ImageCache) -> None:
        resp = AsyncMock()
        resp.status = 200
        resp.content_type = "image/jpeg"
        resp.content_length = MAX_IMAGE_BYTES + 1

        result = await cache.fetch_and_store(
            "dev1", "https://example.com/img.jpg", _mock_session(resp)
        )
        assert result is None


class TestClear:
    def test_clear_specific(self, cache: ImageCache, cache_dir: Path) -> None:
        (cache_dir / "dev1.png").write_bytes(b"x")
        (cache_dir / "dev2.png").write_bytes(b"x")
        removed = cache.clear("dev1")
        assert removed == 1
        assert not (cache_dir / "dev1.png").exists()
        assert (cache_dir / "dev2.png").exists()

    def test_clear_all(self, cache: ImageCache, cache_dir: Path) -> None:
        (cache_dir / "dev1.png").write_bytes(b"x")
        (cache_dir / "dev2.jpg").write_bytes(b"x")
        removed = cache.clear()
        assert removed == 2
