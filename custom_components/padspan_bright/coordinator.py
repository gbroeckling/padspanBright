# PadSpan Bright — BLE Room-Presence Tracking for Home Assistant
# Copyright (C) 2026 Garry Broeckling
# Licensed under the GNU General Public License v3.0
# See LICENSE file or https://www.gnu.org/licenses/gpl-3.0.html
from __future__ import annotations

"""
PadSpan Bright — Coordinator (dataclass)
=====================================
Lightweight in-memory state holder for the integration's config-entry data.
Lives in ``hass.data[DOMAIN]["coordinator"]``.

This is NOT a HomeAssistant DataUpdateCoordinator — the BLE polling is handled
by ``PresenceCoordinator`` instead.  This class exists solely to hold config
values (cloud toggle, room_tag_map, scan interval) and bookkeeping timestamps
so that the websocket layer and entity platforms can read them without coupling
to the config entry directly.
"""


import time
from dataclasses import dataclass, field
from typing import Any

from .const import DEFAULT_SCAN_INTERVAL


@dataclass
class PadSpanCoordinator:
    """Holds config-entry values and integration health timestamps."""

    # ── Config-entry values ───────────────────────────────────────────────
    scan_interval: int = DEFAULT_SCAN_INTERVAL
    enable_cloud: bool = False
    hub_url: str = ""
    api_key: str = ""

    # ── Runtime state ─────────────────────────────────────────────────────
    status: str = "local_only"           # "local_only" | "cloud_connected"
    cloud_reachable: bool = False
    devices: list[dict[str, Any]] = field(default_factory=list)
    room_tag_map: dict[str, list[str]] = field(default_factory=dict)
    test_presence: bool = False          # when True, sensors emit sample data

    # ── Health bookkeeping ────────────────────────────────────────────────
    last_success: str | None = None      # ISO timestamp of last successful refresh
    last_error: str | None = None        # most recent error message, cleared on success

    def ensure_defaults(self) -> None:
        """Guarantee room_tag_map is never None (simplifies downstream code)."""
        if not self.room_tag_map:
            self.room_tag_map = {}

    def mark_success(self) -> None:
        """Record a successful poll/refresh and clear any prior error."""
        self.last_success = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.last_error = None

    def mark_error(self, err: str) -> None:
        """Record the most recent failure reason (displayed in diagnostics)."""
        self.last_error = err

    def as_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict for the diagnostics WS endpoint."""
        return {
            "status": self.status,
            "cloud_enabled": self.enable_cloud,
            "cloud_reachable": self.cloud_reachable,
            "hub_url": self.hub_url,
            "scan_interval": self.scan_interval,
            "devices": self.devices,
            "room_tag_map": self.room_tag_map,
            "test_presence": self.test_presence,
            "last_success": self.last_success,
            "last_error": self.last_error,
        }
