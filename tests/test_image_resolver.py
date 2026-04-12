"""Tests for product image URL resolver."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.desk2ha.images.resolver import (
    _dell_cdn_fallback,
    _resolve_logitech,
    resolve_image_url,
)


class TestResolveImageUrl:
    @pytest.mark.asyncio
    async def test_dell_dispatches(self) -> None:
        session = AsyncMock()
        info = {"manufacturer": "Dell Inc.", "model": "Latitude 5550", "service_tag": "ABC123"}
        # Mock _resolve_dell to avoid HTTP
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "custom_components.desk2ha.images.resolver._resolve_dell",
                AsyncMock(return_value="https://i.dell.com/test.png"),
            )
            result = await resolve_image_url(info, session)
        assert result == "https://i.dell.com/test.png"

    @pytest.mark.asyncio
    async def test_unknown_manufacturer_returns_none(self) -> None:
        session = AsyncMock()
        info = {"manufacturer": "Acme Corp", "model": "X100", "service_tag": ""}
        result = await resolve_image_url(info, session)
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_info_returns_none(self) -> None:
        session = AsyncMock()
        result = await resolve_image_url({}, session)
        assert result is None


class TestDellCdnFallback:
    def test_generates_url(self) -> None:
        url = _dell_cdn_fallback("Latitude 5550")
        assert url is not None
        assert "latitude-5550" in url
        assert url.startswith("https://i.dell.com/")

    def test_empty_model(self) -> None:
        assert _dell_cdn_fallback("") is None


class TestResolveLogitech:
    def test_known_product(self) -> None:
        url = _resolve_logitech("Litra Glow")
        assert url is not None
        assert "litra-glow" in url

    def test_mx_master(self) -> None:
        url = _resolve_logitech("MX Master 3S Wireless Mouse")
        assert url is not None
        assert "mx-master-3s" in url

    def test_unknown_product(self) -> None:
        assert _resolve_logitech("Unknown Device") is None

    def test_case_insensitive(self) -> None:
        url = _resolve_logitech("LITRA BEAM")
        assert url is not None
