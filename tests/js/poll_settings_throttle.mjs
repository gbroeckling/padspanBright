// PadSpan Bright — BLE Room-Presence Tracking for Home Assistant
// Copyright (C) 2026 Garry Broeckling
// Licensed under the GNU General Public License v3.0
//
// _pollTick's settings repoll, RUN rather than read.
//
// Week-review finding, 2026-09-19: the emergency banner / flood ripple /
// Mapping->Lights tab all read state.settings.flood_latches, which used to
// refresh only on boot, manual Refresh, or a tab-focus/visibility wake-up —
// never from the 5s live poll. A kiosk display simply being watched, never
// losing focus, could miss a newly-tripped flood alarm indefinitely. Fixed
// by giving _pollTick the same 30s-inside-the-5s-tick settings throttle
// lights_panel.js's own _poll() already uses.
//
// Same extraction technique as whats_new_card.mjs: lift the real method's
// source out of panel.js by text and run it, so a rename or a dropped
// `await` breaks this the way it would break the live page — not a hand
// reimplementation that could quietly drift from what actually ships.
//
// Run:  node tests/js/poll_settings_throttle.mjs <panel.js path>

import { readFileSync } from "node:fs";

const PANEL = process.argv[2];
if (!PANEL) { console.error("usage: poll_settings_throttle.mjs <panel.js>"); process.exit(2); }

const src = readFileSync(PANEL, "utf8");
const ok = [], fail = [];

/** Source of a class method `name(...)`, optionally `async`. */
function extractMethod(name) {
  const re = new RegExp(`^\\s{2}(?:async\\s+)?${name}\\s*\\(`, "m");
  const m = re.exec(src);
  if (!m) throw new Error(`could not find method ${name}() in panel.js — renamed? update this test`);
  let p = src.indexOf("(", m.index), depth = 0, bodyStart = -1;
  for (let j = p; j < src.length; j++) {
    const c = src[j];
    if (c === "(") depth++;
    else if (c === ")") { depth--; if (!depth) { bodyStart = src.indexOf("{", j); break; } }
  }
  if (bodyStart < 0) throw new Error(`could not find the body of ${name}()`);
  depth = 0;
  for (let j = bodyStart; j < src.length; j++) {
    const c = src[j];
    if (c === "{") depth++;
    else if (c === "}") { depth--; if (!depth) return src.slice(m.index, j + 1); }
  }
  throw new Error(`unbalanced braces reading ${name}()`);
}

const pollTickSrc = extractMethod("_pollTick");

function build() {
  // eslint-disable-next-line no-new-func
  return new Function(`
    const obj = { ${pollTickSrc} };
    return obj._pollTick;
  `)();
}

const _pollTick = build();

function ctx() {
  const calls = { getMapsList: 0, getModel: 0, getLiveSnapshot: 0, getStatus: 0, fetchSettings: 0, updateBadges: 0 };
  return {
    calls,
    _hass: {},
    state: {
      dataMode: "live", view: "overview",
      maps: { list: [{}] }, model: { floors: [{}] },
      timing: {},
    },
    _pollInFlight: false,
    _getMapsList: async () => { calls.getMapsList++; },
    _getModel: async () => { calls.getModel++; },
    _getLiveSnapshot: async () => { calls.getLiveSnapshot++; },
    _getStatus: async () => { calls.getStatus++; },
    _fetchSettings: async () => { calls.fetchSettings++; },
    _updateBadges: () => { calls.updateBadges++; },
    _scheduleRender: () => {},
  };
}

async function run(label, check) {
  try {
    await check();
    ok.push(label);
  } catch (e) {
    fail.push(`${label}: ${e && e.stack ? e.stack : e}`);
  }
}

await run("first tick always repolls settings (throttle timestamp unset)", async () => {
  const c = ctx();
  await _pollTick.call(c);
  if (c.calls.fetchSettings !== 1) throw new Error(`expected 1 fetchSettings call, got ${c.calls.fetchSettings}`);
  if (c.calls.getLiveSnapshot !== 1 || c.calls.getStatus !== 1) throw new Error("live snapshot/status must run every tick too");
});

await run("a second tick right after the first does NOT repoll settings", async () => {
  const c = ctx();
  await _pollTick.call(c);
  await _pollTick.call(c);
  if (c.calls.fetchSettings !== 1) throw new Error(`throttle should have held it at 1, got ${c.calls.fetchSettings}`);
  if (c.calls.getLiveSnapshot !== 2) throw new Error("the fast poll itself must never be throttled, only settings");
});

await run("once 30s have passed, the next tick repolls settings again", async () => {
  const c = ctx();
  await _pollTick.call(c);
  c._settingsPollTs = Date.now() - 30001;
  await _pollTick.call(c);
  if (c.calls.fetchSettings !== 2) throw new Error(`expected a second fetchSettings call after 30s, got ${c.calls.fetchSettings}`);
});

await run("sample mode still bails out before touching anything (unchanged guard)", async () => {
  const c = ctx();
  c.state.dataMode = "sample";
  await _pollTick.call(c);
  if (c.calls.fetchSettings !== 0 || c.calls.getLiveSnapshot !== 0) throw new Error("sample mode must not poll at all");
});

for (const o of ok) console.log(`  ok   ${o}`);
for (const f of fail) console.log(`  FAIL ${f}`);
console.log(`${ok.length} passed, ${fail.length} failed`);
process.exit(fail.length ? 1 : 0);
