"""Config flow for Desk2HA integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_AGENT_HOST, CONF_AGENT_PORT, DEFAULT_PORT, DOMAIN


class Desk2HAConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Desk2HA."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # TODO: Validate connection to agent
            return self.async_create_entry(
                title=f"Desk2HA ({user_input[CONF_AGENT_HOST]})",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_AGENT_HOST): str,
                    vol.Optional(CONF_AGENT_PORT, default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )
