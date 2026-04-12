"""DataUpdateCoordinator for Desk2HA."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_AGENT_TOKEN,
    CONF_AGENT_URL,
    CONF_POLL_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

logger = logging.getLogger(__name__)


class Desk2HACoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch data from a Desk2HA agent."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._url = entry.data[CONF_AGENT_URL]
        self._token = entry.data.get(CONF_AGENT_TOKEN)
        interval = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_SCAN_INTERVAL)
        self._session: aiohttp.ClientSession | None = None
        self.agent_info: dict[str, Any] = {}

        super().__init__(
            hass,
            logger,
            name=f"Desk2HA ({self._url})",
            update_interval=timedelta(seconds=interval),
        )

    @property
    def device_key(self) -> str:
        return self.agent_info.get("device_key", "unknown")

    @property
    def agent_url(self) -> str:
        return self._url

    @property
    def agent_token(self) -> str | None:
        return self._token

    @property
    def headers(self) -> dict[str, str]:
        h: dict[str, str] = {}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self._session

    async def async_shutdown(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch_info(self) -> dict[str, Any]:
        """Fetch /v1/info from agent."""
        session = await self._ensure_session()
        try:
            async with session.get(f"{self._url}/v1/info", headers=self.headers) as resp:
                resp.raise_for_status()
                self.agent_info = await resp.json()
                return self.agent_info
        except Exception as exc:
            raise UpdateFailed(f"Cannot fetch agent info: {exc}") from exc

    async def async_send_command(
        self,
        command: str,
        target: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a command to the agent via POST /v1/commands."""
        session = await self._ensure_session()
        payload: dict[str, Any] = {"command": command}
        if target:
            payload["target"] = target
        if parameters:
            payload["parameters"] = parameters

        try:
            async with session.post(
                f"{self._url}/v1/commands",
                headers=self.headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as exc:
            raise UpdateFailed(f"Command failed: {exc}") from exc

    async def async_check_update(self) -> dict[str, Any]:
        """Check for agent updates via GET /v1/update/check."""
        session = await self._ensure_session()
        try:
            async with session.get(f"{self._url}/v1/update/check", headers=self.headers) as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as exc:
            raise UpdateFailed(f"Update check failed: {exc}") from exc

    async def async_install_update(self, version: str | None = None) -> dict[str, Any]:
        """Install agent update via POST /v1/update/install."""
        session = await self._ensure_session()
        payload: dict[str, Any] = {}
        if version:
            payload["version"] = version
        try:
            async with session.post(
                f"{self._url}/v1/update/install",
                headers=self.headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as exc:
            raise UpdateFailed(f"Update install failed: {exc}") from exc

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch /v1/metrics from agent and refresh agent_info periodically."""
        session = await self._ensure_session()
        try:
            async with session.get(f"{self._url}/v1/metrics", headers=self.headers) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except aiohttp.ClientError as exc:
            raise UpdateFailed(f"Cannot fetch metrics: {exc}") from exc

        # Refresh agent_info if the agent reports a different version
        reported_version = data.get("agent_version")
        if reported_version and reported_version != self.agent_info.get("agent_version"):
            try:
                await self.fetch_info()
                logger.info("Agent version updated to %s", reported_version)
            except Exception:
                pass  # Non-critical, will retry next cycle

        # Sync device registry with latest peripheral metadata
        self._sync_device_registry(data)

        return data

    def _sync_device_registry(self, data: dict[str, Any]) -> None:
        """Update device registry entries when agent reports better metadata.

        Fixes stale device names (e.g. raw IDs like 'peripheral.webcam_0')
        and fills in missing manufacturers from agent data.
        """
        dev_registry = dr.async_get(self.hass)
        device_key = self.device_key

        # Helper to extract string values from metric wrappers
        def _val(raw: Any) -> str:
            if isinstance(raw, dict) and "value" in raw:
                return str(raw["value"]).strip()
            return str(raw).strip() if raw else ""

        # Sync peripheral sub-devices (webcams, BT devices, USB peripherals)
        for peripheral in data.get("peripherals", []):
            if not isinstance(peripheral, dict):
                continue
            dev_id = peripheral.get("id", "")
            if not dev_id:
                continue

            model = _val(peripheral.get("model", ""))
            mfg = _val(peripheral.get("manufacturer", ""))
            if not model:
                continue

            sub_device_id = f"{device_key}_{dev_id}"
            device_entry = dev_registry.async_get_device(identifiers={(DOMAIN, sub_device_id)})
            if device_entry is None:
                continue

            # Strip manufacturer prefix to prevent "Dell Dell Webcam WB7022"
            display_name = model
            if mfg and model.lower().startswith(mfg.lower()):
                display_name = model[len(mfg) :].strip() or model

            # Check if device registry needs updating
            needs_update = False
            updates: dict[str, Any] = {}

            # Fix missing or placeholder names
            current_name = device_entry.name or ""
            if (
                current_name.startswith("peripheral.")
                or current_name.startswith("webcam_")
                or not current_name
            ):
                updates["name"] = display_name
                needs_update = True

            # Fill in missing manufacturer
            if not device_entry.manufacturer:
                if mfg:
                    updates["manufacturer"] = mfg
                    needs_update = True
                elif "webcam" in dev_id.lower() or "ir" in model.lower():
                    # Built-in webcams: inherit manufacturer from host device
                    hw = self.agent_info.get("hardware", {})
                    host_mfg = hw.get("manufacturer", "")
                    if host_mfg:
                        updates["manufacturer"] = host_mfg
                        needs_update = True

            # Fill in missing model
            if not device_entry.model and model:
                updates["model"] = model
                needs_update = True

            if needs_update:
                dev_registry.async_update_device(device_entry.id, **updates)
                logger.info(
                    "Updated device registry for %s: %s",
                    sub_device_id,
                    updates,
                )
