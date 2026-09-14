"""The Mapping -> Lights hover HUD and Alt+click stack cycle, pinned at the
source level.

Garry (2026-09-12): "add a mouse over in the upper left so I can clearly see
the device a click would have me work on. Also make it so the device
underneath can also be selected somehow, and showing in the mouseover text."
The wiring is UI glue in maps.js (verified live, like the rest of
_wireLightsBuild); these tests pin the two things that would silently break
it — the shadow-DOM-correct hit test, and the Alt+click cycle reading from
that same hit test rather than from a bounding-box guess.
"""

from __future__ import annotations

from pathlib import Path

_WWW = Path(__file__).resolve().parents[1] / "custom_components" / "padspan_bright" / "www" / "padspan-bright"
_MAPS = (_WWW / "views" / "maps.js").read_text(encoding="utf-8")
_CSS = (_WWW / "styles.css").read_text(encoding="utf-8")


def _block(src: str, start: str, end: str) -> str:
    i = src.index(start)
    return src[i:src.index(end, i)]


def test_the_hud_hit_tests_through_the_panels_own_shadow_root():
    """document.elementsFromPoint stops at the shadow host and never sees the
    SVG — the panel lives in shadow DOM, so the stage's own root must do the
    hit test, topmost first, or "Click" names nothing at all."""
    hud = _block(_MAPS, "function _wireHoverHud(", "function _wireLightsPicker(")
    assert "isoDiv.getRootNode()" in hud
    assert ".elementsFromPoint(x, y)" in hud
    assert 'closest("g.lhex[data-eid]")' in hud, "the stack is markers only"
    assert 'closest("g.lroom[data-room]")' in hud, "a bare room click is named too"
    # Reading the HUD (pointer over it) must not clear it.
    assert "hud.contains(ev.target)" in hud


def test_the_builder_wires_the_hud_and_alt_click_cycles_the_same_stack():
    build = _block(_MAPS, "function _wireLightsBuild(", "function _wireHoverHud(")
    assert "const stackAt = _wireHoverHud(ctx, isoDiv, svg, o);" in build
    # The plain-click branch of the marker handler: Alt picks from the stack
    # the HUD shows, next-down from the current selection, wrapping.
    click = _block(build, "let selEid = eid;", "ctx.actions.renderRooms();")
    assert "(e.altKey || ev.altKey) && stackAt" in click
    assert "stackAt(e.clientX, e.clientY)" in click
    assert "stack[i < 0 ? 1 : (i + 1) % stack.length]" in click
    assert "o.mapState._selLight = { eid: selEid, mapId: null };" in click


def test_the_hud_rides_the_stages_scroll_without_pushing_the_drawing():
    assert ".lv-hoverhud-anchor{position:sticky;top:0;left:0;height:0;" in _CSS
    assert ".lv-hoverhud{position:absolute;top:0;left:0;" in _CSS
