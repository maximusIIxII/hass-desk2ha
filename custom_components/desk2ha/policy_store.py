"""Persistent policy store for fleet management policies.

Stores policies as JSON in .storage/desk2ha_policies so they survive
HA restarts and can be re-distributed to agents on reconnect.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

logger = logging.getLogger(__name__)

STORAGE_KEY = f"{DOMAIN}_policies"
STORAGE_VERSION = 1


class PolicyStore:
    """Manages fleet policies with persistent storage."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._policies: dict[str, dict[str, Any]] = {}

    @property
    def policies(self) -> dict[str, dict[str, Any]]:
        return dict(self._policies)

    async def async_load(self) -> None:
        """Load policies from persistent storage."""
        data = await self._store.async_load()
        self._policies = data.get("policies", {}) if data else {}
        logger.info("Loaded %d fleet policies from storage", len(self._policies))

    async def async_save(self) -> None:
        """Save policies to persistent storage."""
        await self._store.async_save({"policies": self._policies})

    async def async_add(self, policy: dict[str, Any]) -> None:
        """Add or update a policy and persist."""
        policy_id = policy["policy_id"]
        self._policies[policy_id] = policy
        await self.async_save()
        logger.info("Policy stored: %s", policy_id)

    async def async_remove(self, policy_id: str) -> bool:
        """Remove a policy by ID. Returns True if it existed."""
        if policy_id in self._policies:
            del self._policies[policy_id]
            await self.async_save()
            logger.info("Policy removed from store: %s", policy_id)
            return True
        return False

    def get(self, policy_id: str) -> dict[str, Any] | None:
        """Get a single policy by ID."""
        return self._policies.get(policy_id)

    def get_all(self) -> dict[str, dict[str, Any]]:
        """Get all stored policies."""
        return dict(self._policies)
