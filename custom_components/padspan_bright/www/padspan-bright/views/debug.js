// PadSpan Bright — BLE Room-Presence Tracking for Home Assistant
// Copyright (C) 2026 Garry Broeckling
// Licensed under the GNU General Public License v3.0
// See LICENSE file or https://www.gnu.org/licenses/gpl-3.0.html
/**
 * Debug view — raw panel state inspector.
 * Serializes the entire ctx.state object to formatted JSON, including Sets.
 * Useful for diagnosing UI-side issues like dead buttons or missing views
 * without needing browser dev tools.
 */

export function render(ctx){
  const { el } = ctx.helpers;
  const root = el("section",{id:"debug"});
  root.className = ctx.state.view==="debug" ? "" : "hidden";

  const pre = el("pre",{class:"mono", style:"max-height:520px;overflow:auto"}, JSON.stringify(ctx.state, (k,v)=>{
    if(v instanceof Set) return Array.from(v);
    return v;
  }, 2));

  root.appendChild(el("div",{class:"card"},[
    el("div",{style:"font-weight:700"},"Debug (panel state)"),
    el("div",{class:"muted"},"Useful for UI-side issues (dead buttons, missing views)."),
    pre,
  ]));
  return root;
}
