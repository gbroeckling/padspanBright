# PadSpan Bright — BLE Room-Presence Tracking for Home Assistant
# Copyright (C) 2026 Garry Broeckling
# Licensed under the GNU General Public License v3.0
# See LICENSE file or https://www.gnu.org/licenses/gpl-3.0.html
"""PadSpan Bright — Diagnostics endpoint for HA's "Download diagnostics" button."""
from __future__ import annotations

from typing import Any
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, VERSION


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coord = hass.data.get(DOMAIN, {}).get("coordinator")
    return {
        "version": VERSION,
        "entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "coordinator": coord.as_dict() if coord else None,
        "note": "Share this diagnostics blob + traceback if any flows fail.",
    }
