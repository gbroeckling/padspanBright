# PadSpan Bright — BLE Room-Presence Tracking for Home Assistant
# Copyright (C) 2026 Garry Broeckling
# Licensed under the GNU General Public License v3.0
"""_pollTick's settings repoll (panel.js), RUN rather than read.

Week-review finding, 2026-09-19: state.settings.flood_latches — the sole
source for the emergency banner, the map's flood ripple, and the
Mapping->Lights tab — used to refresh only on boot, manual Refresh, or a
tab-focus/visibility wake-up, never from the 5s live poll. A kiosk display
simply being watched, never losing focus, could miss a newly-tripped flood
alarm on the always-visible emergency banner indefinitely. Fixed by giving
_pollTick the same 30s-inside-the-5s-tick settings throttle lights_panel.js's
own _poll() already uses for the identical staleness problem on that surface.

tests/js/poll_settings_throttle.mjs lifts the real _pollTick method's source
out of panel.js and runs it against a fake `this`, so a future edit that
drops the repoll (or re-adds the un-throttled version, which would hammer
settings_get every 5s) breaks this the way it would break the live page.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_PANEL = _ROOT / "custom_components" / "padspan_bright" / "www" / "padspan-bright" / "panel.js"
_SCRIPT = Path(__file__).parent / "js" / "poll_settings_throttle.mjs"
_NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(_NODE is None, reason="node is not installed")


@pytest.fixture(scope="module")
def run() -> subprocess.CompletedProcess:
    return subprocess.run(
        [_NODE, str(_SCRIPT), str(_PANEL)],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )


def test_poll_tick_repolls_settings_on_a_throttle_not_never_and_not_every_tick(run) -> None:
    if run.returncode != 0:
        pytest.fail(f"_pollTick's settings throttle regressed:\n{run.stdout}\n{run.stderr[-2000:]}")


def test_the_harness_actually_ran_its_cases(run) -> None:
    """A harness that silently stops finding the method would pass forever."""
    m = re.search(r"(\d+) passed, (\d+) failed", run.stdout)
    assert m, f"harness produced no summary:\n{run.stdout}\n{run.stderr[-2000:]}"
    assert int(m.group(1)) >= 4, f"only {m.group(1)} case(s) ran:\n{run.stdout}"
