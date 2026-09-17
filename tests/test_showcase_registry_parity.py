# PadSpan Bright — BLE Room-Presence Tracking for Home Assistant
# Copyright (C) 2026 Garry Broeckling
# Licensed under the GNU General Public License v3.0
"""The Showcase theme and Automorph style registries live in exactly two
places each: the frontend registry that draws them (iso_lights.js:
SHOWCASE_THEMES / AUTOMORPH_STYLE_LABELS) and the backend whitelist that
validates a saved setting or preset (ws_settings.py: _SHOWCASE_THEMES /
_AUTOMORPH_STYLES). Nothing held them equal.

That is the exact drift ws_settings.py's own comment warns about: a key
added to one side and not the other is either a theme the renderer knows
but the backend silently rewrites to "classic" on every save (invisible —
no error anywhere), or a backend-accepted key the renderer has no palette
for. Found while removing three themes on 2026-09-16 — the removal had to
be made in two files by hand with nothing to catch a miss.

The frontend lists are read straight out of the source with a regex rather
than executed under node: the registries are plain object literals at
module top level, and a parity check must not depend on node being
installed (test_lights_renderer.py's node tests are skipped without it —
this one must never be).
"""

from __future__ import annotations

import re
from pathlib import Path

from custom_components.padspan_bright.ws_settings import _AUTOMORPH_STYLES, _SHOWCASE_THEMES

_ISO = (Path(__file__).resolve().parents[1] / "custom_components" / "padspan_bright"
        / "www" / "padspan-bright" / "views" / "iso_lights.js")


def _block(name: str) -> str:
    src = _ISO.read_text(encoding="utf-8")
    start = src.index(f"export const {name} = {{")
    # The registry ends at the first "};" that closes the top-level literal.
    end = src.index("};", start)
    return src[start:end]


def _frontend_theme_keys() -> list[str]:
    body = re.sub(r"//[^\n]*", "", _block("SHOWCASE_THEMES"))
    # A theme is a top-level "  key: {" line (two-space indent, then a brace).
    return re.findall(r"^  ([a-z_]+): \{", body, re.MULTILINE)


def _frontend_style_keys() -> list[str]:
    body = re.sub(r"//[^\n]*", "", _block("AUTOMORPH_STYLE_LABELS"))
    return re.findall(r"\b([a-z]+): \"", body)


def test_frontend_showcase_themes_equal_backend_whitelist():
    fe = _frontend_theme_keys()
    assert fe, "no themes parsed out of iso_lights.js — the registry moved or changed shape"
    assert sorted(fe) == sorted(_SHOWCASE_THEMES), (
        "SHOWCASE_THEMES (iso_lights.js) and _SHOWCASE_THEMES (ws_settings.py) differ:\n"
        f"  only in frontend: {sorted(set(fe) - set(_SHOWCASE_THEMES))}\n"
        f"  only in backend:  {sorted(set(_SHOWCASE_THEMES) - set(fe))}"
    )


def test_frontend_theme_keys_are_unique():
    fe = _frontend_theme_keys()
    assert len(fe) == len(set(fe)), f"duplicate theme key(s) in iso_lights.js: {fe}"


def test_frontend_automorph_styles_equal_backend_whitelist():
    fe = _frontend_style_keys()
    assert fe, "no styles parsed out of iso_lights.js — the registry moved or changed shape"
    assert sorted(fe) == sorted(_AUTOMORPH_STYLES), (
        "AUTOMORPH_STYLE_LABELS (iso_lights.js) and _AUTOMORPH_STYLES (ws_settings.py) differ:\n"
        f"  only in frontend: {sorted(set(fe) - set(_AUTOMORPH_STYLES))}\n"
        f"  only in backend:  {sorted(set(_AUTOMORPH_STYLES) - set(fe))}"
    )


def test_the_three_removed_themes_stay_removed_on_both_sides():
    # The 2026-09-16 audit removed these as near-duplicates. If one comes
    # back it must come back deliberately, on both sides, not as a stale
    # key resurrected from a merge.
    for gone in ("editorial_minimalist", "elevated_blueprint", "nightscape"):
        assert gone not in _SHOWCASE_THEMES, gone
        assert gone not in _frontend_theme_keys(), gone
