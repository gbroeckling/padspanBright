# PadSpan Bright — BLE Room-Presence Tracking for Home Assistant
# Copyright (C) 2026 Garry Broeckling
# Licensed under the GNU General Public License v3.0
"""The Atlas builder's resize/rotate handles (maps.js's _wireTransformHandles)
— one of five drag handlers on this tab, and until 2026-09-16 the only one
that committed unconditionally on pointerup with no way to tell a real
release from an interrupted one. A pointercancel (the OS yanking the touch
away mid-resize — a notification, switching apps, a stray second finger) now
discards the in-progress transform instead of silently writing whatever the
last pointermove happened to compute, matching every sibling drag handler
(_wireDoorCircle, the plain marker drag, the drop-pin drag, the room-name
long-press) which already guard on it.

_wireTransformHandles builds real SVG handle elements and wires real pointer
listeners; toVB (the viewBox-coordinate converter) needs a live SVGPoint /
getScreenCTM the node shim does not implement, but it is only ever called
from inside the pointermove handler — never from pointerdown or pointerup/
pointercancel — so a cancel test never has to touch it.

Runs the real module under node; skipped, not failed, without node.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_VIEWS = _ROOT / "custom_components" / "padspan_bright" / "www" / "padspan-bright" / "views"
_NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(_NODE is None, reason="node is not installed")

_MODEL = {
    "floors": [{"id": "main", "name": "Main", "level": 0}],
    "room_geometry_m": {
        "Kitchen": {"type": "poly", "floor_id": "main", "points_m": [[0, 0], [10, 0], [10, 8], [0, 8]]},
    },
    "light_positions_m": {
        "light.a": {"x_m": 5.0, "y_m": 4.0, "floor_id": "main"},
    },
}


def _run(script: str) -> dict:
    src = (
        "import { pathToFileURL } from 'node:url';\n"
        f"const {{ install }} = await import(pathToFileURL({json.dumps(str(_ROOT / 'tests' / 'js' / 'dom_shim.mjs'))}).href);\n"
        "install(globalThis);\n"
        f"const M = await import(pathToFileURL({json.dumps(str(_VIEWS / 'maps.js'))}).href);\n"
        f"const IL = await import(pathToFileURL({json.dumps(str(_VIEWS / 'iso_lights.js'))}).href);\n"
        f"const MODEL = {json.dumps(_MODEL)};\n"
        "const frame = IL.fabricFrame(MODEL, MODEL.floors, 150, 0);\n"
        "const renderCalls = [];\n"
        "const ctx = { state: { model: MODEL },\n"
        "  actions: { renderRooms: () => renderCalls.push(1) } };\n"
        "const o = { mapState: {}, lightsByEid: {} };\n"
        "const NS = 'http://www.w3.org/2000/svg';\n"
        "const svg = document.createElementNS(NS, 'svg');\n"
        "const g = document.createElementNS(NS, 'g');\n"
        "const [hx, hy] = frame.iso(5.0, 4.0, frame.levelOf('main'));\n"
        "g.setAttribute('data-cx', String(hx));\n"
        "g.setAttribute('data-cy', String(hy));\n"
        "g.setAttribute('data-z', String(frame.levelOf('main')));\n"
        "M._wireTransformHandles(ctx, svg, g, 'light.a', frame, o, () => ({x: 0, y: 0}));\n"
        "const handles = svg.querySelectorAll('rect');\n"
        "const wHandle = handles[1];\n"  # 0 is the dashed bounding box, 1 is the first real handle
        "const out = { renderCalls };\n" + script + "\nconsole.log(JSON.stringify(out));\n"
    )
    res = subprocess.run([_NODE, "--input-type=module", "-e", src], capture_output=True,
                         text=True, encoding="utf-8", timeout=60, cwd=str(_VIEWS))
    assert res.returncode == 0, f"node failed:\n{res.stderr}"
    return json.loads(res.stdout.strip().splitlines()[-1])


def test_a_pointercancel_discards_the_in_progress_resize():
    out = _run("""
wHandle.dispatchEvent({ type: 'pointerdown', pointerId: 1, preventDefault(){}, stopPropagation(){} });
out.draggingDuringDrag = o.mapState._editDragging;
wHandle.dispatchEvent({ type: 'pointercancel', pointerId: 1 });
out.draggingAfterCancel = o.mapState._editDragging;
out.draftAfterCancel = o.mapState._lightsDraftM || null;
""")
    assert out["draggingDuringDrag"] is True, out
    assert out["draggingAfterCancel"] is False, out
    assert out["draftAfterCancel"] is None, (
        "a pointercancel must never commit a draft transform — the bug this fix closed", out)
    assert out["renderCalls"] == [1], "a cancel must still re-render to clear the stale live preview"


def test_a_real_pointerup_still_commits_the_resize():
    """The guard is conditioned on event.type, not on skipping the commit
    path altogether — a genuine release must behave exactly as before."""
    out = _run("""
wHandle.dispatchEvent({ type: 'pointerdown', pointerId: 1, preventDefault(){}, stopPropagation(){} });
wHandle.dispatchEvent({ type: 'pointerup', pointerId: 1 });
out.draggingAfterUp = o.mapState._editDragging;
out.draft = o.mapState._lightsDraftM;
""")
    assert out["draggingAfterUp"] is False, out
    assert out["draft"] and "light.a" in out["draft"], (
        "a genuine pointerup must still commit the transform, same as before this fix", out)
    assert out["renderCalls"] == [1]
