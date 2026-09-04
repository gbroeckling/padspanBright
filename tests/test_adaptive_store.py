"""Unit tests for custom_components.padspan_bright.adaptive_store."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from custom_components.padspan_bright.adaptive_store import (
    _FP_VERSION,
    AdaptiveStore,
    _empty_data,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MockStore:
    """Minimal stand-in for homeassistant.helpers.storage.Store."""

    def __init__(self) -> None:
        self._data: dict | None = None

    async def async_load(self) -> dict | None:
        return self._data

    async def async_save(self, data: dict) -> None:
        self._data = data


def _make_store(store_data: dict | None = None) -> AdaptiveStore:
    ad = AdaptiveStore.__new__(AdaptiveStore)
    ad.hass = MagicMock()
    ms = _MockStore()
    ms._data = store_data
    ad.store = ms
    ad.data = _empty_data()
    return ad


# ---------------------------------------------------------------------------
# Tests: per-device normalized fingerprints (fp schema v2)
# ---------------------------------------------------------------------------


def test_normalization_tx_power_invariance() -> None:
    """Devices with different TX power at the same spot must score alike."""
    ad = _make_store()
    for _ in range(15):
        ad.observe("Kitchen", None, {"s1": -50.0, "s2": -70.0}, {}, {})  # strong
        ad.observe("Kitchen", None, {"s1": -60.0, "s2": -80.0}, {}, {})  # weak
        ad.observe("Office", None, {"s1": -75.0, "s2": -55.0}, {}, {})

    strong = ad.score_rooms({"s1": -50.0, "s2": -70.0}, {})
    weak = ad.score_rooms({"s1": -62.0, "s2": -82.0}, {})

    assert strong["Kitchen"] > 0.9
    assert strong.get("Office", 0.0) < 0.1
    assert weak["Kitchen"] > 0.9
    assert weak.get("Office", 0.0) < 0.1


def test_single_scanner_observation_rejected() -> None:
    """A single-scanner vector normalizes to zero — must not be recorded."""
    ad = _make_store()
    ad.observe("Kitchen", None, {"s1": -50.0}, {}, {})
    assert ad.data["stats"]["total_observations"] == 0
    assert ad.data["room_fingerprints"] == {}


def test_single_scanner_query_returns_nothing() -> None:
    ad = _make_store()
    for _ in range(15):
        ad.observe("Kitchen", None, {"s1": -50.0, "s2": -70.0}, {}, {})
    assert ad.score_rooms({"s1": -50.0}, {}) == {}


def test_v1_fingerprints_reset_on_load() -> None:
    """Raw-dBm (v1) fingerprints are incompatible and reset; the rest survives."""
    v1_data = {
        "room_fingerprints": {"Kitchen": {"s1": {"mean": -50.0, "var": 4.0, "n": 100}}},
        "transition_counts": {"Kitchen": {"Office": 12}},
        "floor_pairs": {"f1|f2": {"mean": -15.0, "var": 2.0, "n": 40}},
        "stats": {"total_observations": 100, "learning_since": None, "days_active": 0},
    }
    ad = _make_store(store_data=v1_data)
    asyncio.run(ad.async_load())

    assert ad.data["fp_version"] == _FP_VERSION
    assert ad.data["room_fingerprints"] == {}
    assert ad.data["transition_counts"] == {"Kitchen": {"Office": 12}}
    assert ad.data["floor_pairs"]["f1|f2"]["n"] == 40


def test_v2_fingerprints_survive_load() -> None:
    ad1 = _make_store()
    for _ in range(15):
        ad1.observe("Kitchen", None, {"s1": -50.0, "s2": -70.0}, {}, {})
    ad2 = _make_store(store_data=ad1.data)
    asyncio.run(ad2.async_load())
    assert ad2.data["room_fingerprints"] != {}
    assert ad2.data["fp_version"] == _FP_VERSION
