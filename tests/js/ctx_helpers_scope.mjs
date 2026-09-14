// PadSpan Bright — BLE Room-Presence Tracking for Home Assistant
// Copyright (C) 2026 Garry Broeckling
// Licensed under the GNU General Public License v3.0
//
// Every top-level function that calls an el()/esc()/pill()/helpBtn()/
// radioShortId()/roomColor()/scannerStatus() must destructure it from
// ctx.helpers ITSELF — render(ctx)'s own `const { el, ... } = ctx.helpers`
// is a closure-local to render(), and does not reach a sibling top-level
// function. Every view module already follows this convention correctly in
// dozens of places; this exists because it is easy to add ONE more function
// and forget the one line, and when that happens `node --check` still
// passes and render_smoke.mjs's shim still stays quiet (see the doc comment
// in test_frontend_renders.py for exactly why render_smoke cannot see it:
// its innerHTML setter never parses the SVG STRING buildIsoSVG returns into
// real nodes, so isoDiv.querySelector("svg") finds nothing and every
// onHexesBuilt wiring function — _wireLightsBuild, _wireHoverHud,
// _wireLightsPicker, _wireDoorCircle, _wireTransformHandles — returns
// before it ever runs). Two real, live-shipped instances of exactly this
// bug (2026-09-12/13): _wireHoverHud threw the moment the Lights builder
// tab tried to render at all (a totally blank tab); _wireLightsPicker (the
// right-click marker disambiguation menu, shipped in v0.38.37) threw only
// when a user actually right-clicked a stacked marker, so it went unnoticed
// for a full release. Both were `const { el } = ctx.helpers;` short by one
// line. This is a static, scope-aware check — not a full parser — so it
// cannot see everything a real interpreter would, but it costs nothing to
// run and would have caught both bugs before they shipped.

import fs from "node:fs";
import path from "node:path";

const VOCAB = ["el", "esc", "pill", "helpBtn", "radioShortId", "roomColor", "scannerStatus"];

function findTopLevelFunctions(src) {
  const fns = [];
  const re = /^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)\s*\{/gm;
  let m;
  while ((m = re.exec(src))) {
    const name = m[1], params = m[2];
    const bodyStart = m.index + m[0].length;
    let depth = 1, i = bodyStart;
    while (depth > 0 && i < src.length) {
      const c = src[i];
      if (c === "{") depth++;
      else if (c === "}") depth--;
      else if (c === '"' || c === "'" || c === "`") {
        const quote = c; i++;
        while (i < src.length && src[i] !== quote) { if (src[i] === "\\") i++; i++; }
      } else if (c === "/" && src[i + 1] === "/") {
        while (i < src.length && src[i] !== "\n") i++;
      } else if (c === "/" && src[i + 1] === "*") {
        i += 2;
        while (i < src.length && !(src[i] === "*" && src[i + 1] === "/")) i++;
        i++;
      }
      i++;
    }
    fns.push({ name, params, body: src.slice(bodyStart, i - 1), line: src.slice(0, m.index).split("\n").length });
  }
  return fns;
}

function localBindings(fnBody, fnParams) {
  const bound = new Set(fnParams.split(",").map(p => p.trim().split("=")[0].trim()).filter(Boolean));
  let m;
  const destructureRe = /(?:const|let)\s*\{([^}]*)\}\s*=/g;
  while ((m = destructureRe.exec(fnBody))) {
    for (let part of m[1].split(",")) {
      part = part.trim();
      if (!part) continue;
      const asName = (part.includes(":") ? part.split(":")[1] : part).split("=")[0].trim();
      bound.add(asName);
    }
  }
  const plainConstRe = /(?:const|let|var)\s+(\w+)\s*=/g;
  while ((m = plainConstRe.exec(fnBody))) bound.add(m[1]);
  const nestedFnRe = /function\s+(\w+)\s*\(/g;
  while ((m = nestedFnRe.exec(fnBody))) bound.add(m[1]);
  return bound;
}

export function findUnboundCtxHelperCalls(src) {
  if (!/ctx\.helpers/.test(src)) return [];
  const findings = [];
  for (const fn of findTopLevelFunctions(src)) {
    const bound = localBindings(fn.body, fn.params);
    for (const ident of VOCAB) {
      const useRe = new RegExp(`(?<![.\\w])${ident}\\s*\\(`, "g");
      const uses = [...fn.body.matchAll(useRe)];
      if (!uses.length || bound.has(ident)) continue;
      const lineInFn = fn.body.slice(0, uses[0].index).split("\n").length;
      findings.push({ fn: fn.name, ident, line: fn.line + lineInFn - 1 });
    }
  }
  return findings;
}

const VIEWS_DIR = process.argv[2];
if (!VIEWS_DIR) { console.error("usage: ctx_helpers_scope.mjs <views-dir>"); process.exit(2); }

const results = {};
for (const file of fs.readdirSync(VIEWS_DIR).filter(f => f.endsWith(".js"))) {
  const src = fs.readFileSync(path.join(VIEWS_DIR, file), "utf-8");
  const findings = findUnboundCtxHelperCalls(src);
  if (findings.length) results[file] = findings;
}
console.log(JSON.stringify(results));
