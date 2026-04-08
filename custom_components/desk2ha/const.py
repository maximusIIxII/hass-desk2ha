"""Constants for the Desk2HA integration."""

from __future__ import annotations

DOMAIN = "desk2ha"

CONF_AGENT_HOST = "agent_host"
CONF_AGENT_PORT = "agent_port"
CONF_AGENT_TOKEN = "agent_token"
CONF_AGENT_URL = "url"
CONF_TRANSPORT = "transport"
CONF_POLL_INTERVAL = "poll_interval"
CONF_DEVICE_KEY = "device_key"

DEFAULT_PORT = 9693
DEFAULT_SCAN_INTERVAL = 30

SCHEMA_VERSION = "2.0.0"

# Entity platforms to set up
PLATFORMS = ["sensor", "binary_sensor", "number", "select", "button"]
