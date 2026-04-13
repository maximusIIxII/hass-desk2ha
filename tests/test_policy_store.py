"""Tests for the fleet policy store."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_store():
    """Create a mock HA Store and patch it into the storage module."""
    store_instance = MagicMock()
    store_instance.async_load = AsyncMock(return_value=None)
    store_instance.async_save = AsyncMock()

    store_cls = MagicMock(return_value=store_instance)
    storage_mod = MagicMock()
    storage_mod.Store = store_cls
    sys.modules["homeassistant.helpers.storage"] = storage_mod

    # Force re-import so the module picks up our mock
    if "custom_components.desk2ha.policy_store" in sys.modules:
        del sys.modules["custom_components.desk2ha.policy_store"]

    yield store_instance

    # Cleanup
    if "custom_components.desk2ha.policy_store" in sys.modules:
        del sys.modules["custom_components.desk2ha.policy_store"]


@pytest.fixture
def hass():
    return MagicMock()


@pytest.mark.asyncio
async def test_load_empty(mock_store, hass):
    from custom_components.desk2ha.policy_store import PolicyStore

    store = PolicyStore(hass)
    await store.async_load()
    assert store.get_all() == {}


@pytest.mark.asyncio
async def test_load_existing(mock_store, hass):
    mock_store.async_load.return_value = {
        "policies": {
            "corp-display": {
                "policy_id": "corp-display",
                "kind": "DisplayPolicy",
                "name": "Corporate Standard",
                "rules": {"brightness_percent": {"min": 30, "max": 80}},
            }
        }
    }

    from custom_components.desk2ha.policy_store import PolicyStore

    store = PolicyStore(hass)
    await store.async_load()
    assert "corp-display" in store.get_all()
    assert store.get("corp-display")["kind"] == "DisplayPolicy"


@pytest.mark.asyncio
async def test_add_and_save(mock_store, hass):
    from custom_components.desk2ha.policy_store import PolicyStore

    store = PolicyStore(hass)
    await store.async_load()
    await store.async_add(
        {
            "policy_id": "test-policy",
            "kind": "AgentPolicy",
            "name": "Test",
            "rules": {},
        }
    )

    assert store.get("test-policy") is not None
    mock_store.async_save.assert_called_once()
    saved_data = mock_store.async_save.call_args[0][0]
    assert "test-policy" in saved_data["policies"]


@pytest.mark.asyncio
async def test_remove(mock_store, hass):
    from custom_components.desk2ha.policy_store import PolicyStore

    store = PolicyStore(hass)
    await store.async_load()
    await store.async_add(
        {
            "policy_id": "to-remove",
            "kind": "AgentPolicy",
            "name": "Remove Me",
            "rules": {},
        }
    )
    mock_store.async_save.reset_mock()

    removed = await store.async_remove("to-remove")
    assert removed is True
    assert store.get("to-remove") is None
    mock_store.async_save.assert_called_once()


@pytest.mark.asyncio
async def test_remove_nonexistent(mock_store, hass):
    from custom_components.desk2ha.policy_store import PolicyStore

    store = PolicyStore(hass)
    await store.async_load()
    removed = await store.async_remove("does-not-exist")
    assert removed is False
