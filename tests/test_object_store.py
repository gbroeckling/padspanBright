"""Unit tests for custom_components.padspan_bright.object_store."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.padspan_bright.object_store import ObjectStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store() -> ObjectStore:
    """Create an ObjectStore backed by mocks."""
    hass = MagicMock()
    store = ObjectStore.__new__(ObjectStore)
    store.hass = hass
    store._store = AsyncMock()
    store._store.async_load = AsyncMock(return_value=None)
    store._store.async_save = AsyncMock()
    store._data = {}
    return store


# ---------------------------------------------------------------------------
# Tests: set / get / delete lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_and_get_label() -> None:
    """Setting a label stores it, and get returns it."""
    store = _make_store()
    await store.async_set("aa:bb:cc:dd:ee:ff", "Front Door Beacon")

    entry = store.get("AA:BB:CC:DD:EE:FF")
    assert entry is not None
    assert entry["label"] == "Front Door Beacon"
    assert "tagged_at" in entry


@pytest.mark.asyncio
async def test_mac_normalised_to_uppercase() -> None:
    """MAC addresses are stored and looked up in uppercase."""
    store = _make_store()
    await store.async_set("ab:cd:ef:01:23:45", "Tag1")

    # Look up with lowercase -- get() also uppercases
    assert store.get("ab:cd:ef:01:23:45") is not None
    # Internal storage uses uppercase key
    assert "AB:CD:EF:01:23:45" in store._data


@pytest.mark.asyncio
async def test_delete_label() -> None:
    """Deleting a label removes it from the store."""
    store = _make_store()
    await store.async_set("11:22:33:44:55:66", "OldTag")
    await store.async_delete("11:22:33:44:55:66")
    assert store.get("11:22:33:44:55:66") is None


@pytest.mark.asyncio
async def test_delete_nonexistent_is_noop() -> None:
    """Deleting a MAC that was never set does not raise."""
    store = _make_store()
    await store.async_delete("FF:FF:FF:FF:FF:FF")  # should not raise


@pytest.mark.asyncio
async def test_all_returns_copy() -> None:
    """all() returns all entries and does not expose the internal dict."""
    store = _make_store()
    await store.async_set("aa:aa:aa:aa:aa:aa", "A")
    await store.async_set("bb:bb:bb:bb:bb:bb", "B")

    result = store.all()
    assert len(result) == 2
    assert "AA:AA:AA:AA:AA:AA" in result
    assert "BB:BB:BB:BB:BB:BB" in result

    # Mutating the returned dict should not affect the store
    result.pop("AA:AA:AA:AA:AA:AA")
    assert store.get("AA:AA:AA:AA:AA:AA") is not None


@pytest.mark.asyncio
async def test_get_missing_returns_none() -> None:
    """get() for an unknown MAC returns None."""
    store = _make_store()
    assert store.get("00:00:00:00:00:00") is None


# ---------------------------------------------------------------------------
# Tests: label string edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_label() -> None:
    """An empty string label is accepted (the UI might allow clearing)."""
    store = _make_store()
    await store.async_set("CC:CC:CC:CC:CC:CC", "")
    entry = store.get("CC:CC:CC:CC:CC:CC")
    assert entry is not None
    assert entry["label"] == ""


@pytest.mark.asyncio
async def test_long_label_stored_as_is() -> None:
    """ObjectStore does not truncate labels itself (UI may do so)."""
    store = _make_store()
    long_label = "Z" * 5000
    await store.async_set("DD:DD:DD:DD:DD:DD", long_label)
    entry = store.get("DD:DD:DD:DD:DD:DD")
    assert entry is not None
    assert entry["label"] == long_label


@pytest.mark.asyncio
async def test_overwrite_label() -> None:
    """Setting a label twice overwrites the first."""
    store = _make_store()
    await store.async_set("EE:EE:EE:EE:EE:EE", "First")
    await store.async_set("EE:EE:EE:EE:EE:EE", "Second")
    entry = store.get("EE:EE:EE:EE:EE:EE")
    assert entry is not None
    assert entry["label"] == "Second"


# ---------------------------------------------------------------------------
# Tests: async_load
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_load_with_existing_data() -> None:
    """async_load populates _data from the underlying store."""
    store = _make_store()
    store._store.async_load = AsyncMock(
        return_value={"AA:BB:CC:DD:EE:FF": {"label": "Saved", "tagged_at": "2026-01-01T00:00:00"}}
    )
    await store.async_load()
    assert store.get("AA:BB:CC:DD:EE:FF") is not None
    assert store.get("AA:BB:CC:DD:EE:FF")["label"] == "Saved"


@pytest.mark.asyncio
async def test_async_load_with_none() -> None:
    """async_load starts with empty dict when store returns None."""
    store = _make_store()
    store._store.async_load = AsyncMock(return_value=None)
    await store.async_load()
    assert store.all() == {}
