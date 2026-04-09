"""Config flow for Desk2HA integration."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback

from .const import (
    CONF_AGENT_TOKEN,
    CONF_AGENT_URL,
    CONF_DEVICE_KEY,
    CONF_FETCH_IMAGES,
    CONF_POLL_INTERVAL,
    CONF_TRANSPORT,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)


class Desk2HAConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Desk2HA."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_url: str = ""
        self._install_result: Any = None
        self._scan_results: dict[str, Any] = {}
        self._selected_host: str = ""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle setup method selection."""
        if user_input is not None:
            method = user_input["method"]
            if method == "manual_url":
                return await self.async_step_manual()
            if method == "install_agent":
                return await self.async_step_install_scan()
            if method == "distribute_agent":
                return await self.async_step_distribute()
            return await self.async_step_manual()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("method", default="distribute_agent"): vol.In(
                        {
                            "distribute_agent": "Distribute agent (install link)",
                            "manual_url": "Enter agent URL manually",
                            "install_agent": "Install agent on remote machine (SSH/WinRM)",
                        }
                    ),
                }
            ),
        )

    async def async_step_distribute(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Generate an install link for agent distribution."""
        from .install_server import InstallServer

        server: InstallServer | None = self.hass.data.get(f"{DOMAIN}_install_server")
        if server is None:
            return self.async_abort(reason="install_server_unavailable")

        # Determine HA external/internal URL
        ha_url = self._get_ha_url()
        token, _agent_token = server.create_token(ha_url)
        install_url = f"{ha_url}/{DOMAIN}/install/{token}"

        return self.async_show_form(
            step_id="distribute",
            data_schema=vol.Schema({}),
            description_placeholders={
                "install_url": install_url,
            },
        )

    def _get_ha_url(self) -> str:
        """Get the best HA URL for agent communication."""
        try:
            from homeassistant.helpers.network import get_url

            return get_url(self.hass, prefer_external=False)
        except Exception:
            return f"http://{self.hass.config.api.host}:{self.hass.config.api.port}"

    async def async_step_phone_home(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Auto-setup after agent phone-home."""
        if user_input is None:
            return self.async_abort(reason="cannot_connect")

        url = user_input.get("agent_url", "")
        token = user_input.get("agent_token", "")
        device_key = user_input.get("device_key", "unknown")
        hardware = user_input.get("hardware", {})

        try:
            info = await self._fetch_agent_info(url, token)
            device_key = info.get("device_key", device_key)
            hw = info.get("hardware", hardware)

            await self.async_set_unique_id(device_key)
            self._abort_if_unique_id_configured()

            title = f"{hw.get('manufacturer', 'Desk2HA')} {hw.get('model', device_key)}"
            return self.async_create_entry(
                title=title,
                data={
                    CONF_AGENT_URL: url,
                    CONF_AGENT_TOKEN: token,
                    CONF_DEVICE_KEY: device_key,
                    CONF_TRANSPORT: "http",
                },
            )
        except Exception:
            # Agent might not be fully ready yet — create entry with phone-home data
            mfg = hardware.get("manufacturer", "Desk2HA")
            model = hardware.get("model", device_key)
            title = f"{mfg} {model}"
            await self.async_set_unique_id(device_key)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=title,
                data={
                    CONF_AGENT_URL: url,
                    CONF_AGENT_TOKEN: token,
                    CONF_DEVICE_KEY: device_key,
                    CONF_TRANSPORT: "http",
                },
            )

    async def async_step_install_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Scan the network for hosts and let user pick one or enter manually."""
        if user_input is not None:
            selected = user_input.get("host", "")
            if selected == "_manual_":
                return await self.async_step_install_choose_os()
            # Pre-fill host from scan results
            host_info = self._scan_results.get(selected, {})
            self._selected_host = selected
            os_hint = host_info.get("os_hint", "linux")
            if os_hint == "windows":
                return await self.async_step_install_winrm()
            return await self.async_step_install_ssh()

        # Run network scan
        from .discovery import scan_network

        hosts = await scan_network()
        # Filter out hosts that already have an agent
        installable = [h for h in hosts if not h.agent]

        choices: dict[str, str] = {}
        for h in installable:
            self._scan_results[h.ip] = {
                "hostname": h.hostname,
                "os_hint": h.os_hint,
                "ssh": h.ssh,
                "winrm": h.winrm,
            }
            choices[h.ip] = h.label

        # Always offer manual entry
        choices["_manual_"] = "Enter host manually..."

        return self.async_show_form(
            step_id="install_scan",
            data_schema=vol.Schema(
                {
                    vol.Required("host"): vol.In(choices),
                }
            ),
            description_placeholders={
                "count": str(len(installable)),
            },
        )

    async def async_step_install_choose_os(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose target OS for remote installation."""
        if user_input is not None:
            os_type = user_input["os_type"]
            if os_type == "windows":
                return await self.async_step_install_winrm()
            return await self.async_step_install_ssh()

        return self.async_show_form(
            step_id="install_choose_os",
            data_schema=vol.Schema(
                {
                    vol.Required("os_type", default="linux"): vol.In(
                        {
                            "linux": "Linux",
                            "macos": "macOS",
                            "windows": "Windows",
                        }
                    ),
                }
            ),
        )

    async def async_step_install_ssh(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Install agent via SSH on Linux/macOS."""
        errors: dict[str, str] = {}

        if user_input is not None:
            from .lifecycle.remote_install import install_via_ssh

            result = await install_via_ssh(
                host=user_input["host"],
                port=user_input.get("ssh_port", 22),
                username=user_input["username"],
                password=user_input.get("password"),
                agent_port=user_input.get("agent_port", DEFAULT_PORT),
            )

            if result.success:
                self._install_result = result
                return await self.async_step_install_complete()
            errors["base"] = "install_failed"

        default_host = self._selected_host or ""
        return self.async_show_form(
            step_id="install_ssh",
            data_schema=vol.Schema(
                {
                    vol.Required("host", default=default_host): str,
                    vol.Optional("ssh_port", default=22): int,
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                    vol.Optional("agent_port", default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )

    async def async_step_install_winrm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Install agent via WinRM on Windows."""
        errors: dict[str, str] = {}

        if user_input is not None:
            from .lifecycle.remote_install import install_via_winrm

            result = await install_via_winrm(
                host=user_input["host"],
                username=user_input["username"],
                password=user_input["password"],
                agent_port=user_input.get("agent_port", DEFAULT_PORT),
            )

            if result.success:
                self._install_result = result
                return await self.async_step_install_complete()
            errors["base"] = "install_failed"

        default_host = self._selected_host or ""
        return self.async_show_form(
            step_id="install_winrm",
            data_schema=vol.Schema(
                {
                    vol.Required("host", default=default_host): str,
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                    vol.Optional("agent_port", default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )

    async def async_step_install_complete(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Complete installation — verify and create entry."""
        result = self._install_result
        if result is None:
            return self.async_abort(reason="install_failed")

        url = result.agent_url
        token = result.token

        try:
            info = await self._fetch_agent_info(url, token)
            device_key = info.get("device_key", "unknown")
            await self.async_set_unique_id(device_key)
            self._abort_if_unique_id_configured()

            hw = info.get("hardware", {})
            title = f"{hw.get('manufacturer', 'Desk2HA')} {hw.get('model', device_key)}"

            return self.async_create_entry(
                title=title,
                data={
                    CONF_AGENT_URL: url,
                    CONF_AGENT_TOKEN: token,
                    CONF_DEVICE_KEY: device_key,
                    CONF_TRANSPORT: "http",
                },
            )
        except Exception:
            return self.async_abort(reason="cannot_connect")

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual agent URL entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            url = user_input[CONF_AGENT_URL].rstrip("/")
            token = user_input.get(CONF_AGENT_TOKEN, "")

            try:
                info = await self._fetch_agent_info(url, token)
                device_key = info.get("device_key", "unknown")

                await self.async_set_unique_id(device_key)
                self._abort_if_unique_id_configured()

                hw = info.get("hardware", {})
                title = f"{hw.get('manufacturer', 'Desk2HA')} {hw.get('model', device_key)}"

                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_AGENT_URL: url,
                        CONF_AGENT_TOKEN: token,
                        CONF_DEVICE_KEY: device_key,
                        CONF_TRANSPORT: "http",
                    },
                )
            except aiohttp.ClientResponseError as exc:
                if exc.status == 401:
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_AGENT_URL, default="http://192.168.1.x:9693"): str,
                    vol.Optional(CONF_AGENT_TOKEN): str,
                }
            ),
            errors=errors,
        )

    async def async_step_zeroconf(self, discovery_info: Any) -> ConfigFlowResult:
        """Handle Zeroconf discovery."""
        host = discovery_info.host
        port = discovery_info.port or DEFAULT_PORT
        url = f"http://{host}:{port}"

        try:
            health = await self._fetch_health(url)
        except Exception:
            return self.async_abort(reason="cannot_connect")

        device_key = health.get("device_key")
        if device_key:
            await self.async_set_unique_id(device_key)
            self._abort_if_unique_id_configured()

        self.context["title_placeholders"] = {
            "name": health.get("hostname", host),
        }
        self._discovered_url = url
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm Zeroconf discovery."""
        if user_input is not None:
            token = user_input.get(CONF_AGENT_TOKEN, "")
            url = self._discovered_url

            try:
                info = await self._fetch_agent_info(url, token)
                device_key = info.get("device_key", "unknown")
                hw = info.get("hardware", {})
                title = f"{hw.get('manufacturer', 'Desk2HA')} {hw.get('model', device_key)}"

                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_AGENT_URL: url,
                        CONF_AGENT_TOKEN: token,
                        CONF_DEVICE_KEY: device_key,
                        CONF_TRANSPORT: "http",
                    },
                )
            except Exception:
                return self.async_abort(reason="cannot_connect")

        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_AGENT_TOKEN): str,
                }
            ),
        )

    async def _fetch_health(self, url: str) -> dict[str, Any]:
        async with (
            aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session,
            session.get(f"{url}/v1/health") as resp,
        ):
            resp.raise_for_status()
            return await resp.json()

    async def _fetch_agent_info(self, url: str, token: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        async with (
            aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session,
            session.get(f"{url}/v1/info", headers=headers) as resp,
        ):
            resp.raise_for_status()
            return await resp.json()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: Any) -> Desk2HAOptionsFlow:
        return Desk2HAOptionsFlow(config_entry)


class Desk2HAOptionsFlow(OptionsFlow):
    """Handle Desk2HA options."""

    def __init__(self, config_entry: Any) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_POLL_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_POLL_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(int, vol.Range(min=10, max=600)),
                    vol.Optional(
                        CONF_FETCH_IMAGES,
                        default=self._config_entry.options.get(CONF_FETCH_IMAGES, False),
                    ): bool,
                }
            ),
        )
