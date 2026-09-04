// PadSpan Bright — BLE Room-Presence Tracking for Home Assistant
// Copyright (C) 2026 Garry Broeckling
// Licensed under the GNU General Public License v3.0
// See LICENSE file or https://www.gnu.org/licenses/gpl-3.0.html
/**
 * History view — temporal record of session activity and object movement.
 * Sub-tabs: Session Events | Movement.
 * Session Events shows the filtered event log (delegates to events-style rendering).
 * Movement shows per-object room transition history from the live snapshot.
 */

export function render(ctx){
  const { el, helpBtn } = ctx.helpers;
  const root = el("section",{id:"history"});

  // Header
  root.appendChild(el("div",{class:"row",style:"align-items:center;gap:8px;margin-bottom:14px"},[
    el("h2",{},"History"),
    helpBtn("history"),
  ]));

  // ── Sub-tab bar ──
  if(!ctx.state._historyTab) ctx.state._historyTab = "events";
  const activeTab = ctx.state._historyTab;
  const setTab = (t) => { ctx.state._historyTab = t; ctx.actions.renderRooms(); };

  const TABS = [["events","Session Events"],["movement","Movement"]];
  const tabBar = el("div",{class:"tabs",style:"margin-bottom:14px;flex-wrap:wrap;gap:4px"});
  for(const [id,label] of TABS){
    tabBar.appendChild(el("button",{
      class:"tab"+(activeTab===id?" active":""),
      onclick:()=>setTab(id),
    },label));
  }
  root.appendChild(tabBar);

  if(activeTab === "movement"){ root.appendChild(_movement(ctx, el)); return root; }

  // ═══════════════════════════════════════════════════════════════════════════
  // SESSION EVENTS TAB (default)
  // ═══════════════════════════════════════════════════════════════════════════
  const events = ctx.state._sessionEvents || [];

  if(events.length === 0){
    root.appendChild(el("div",{class:"card"},[
      el("div",{class:"muted"},"Session history will appear as you interact with the panel."),
      el("div",{class:"muted",style:"font-size:12px;margin-top:6px"},"Navigate views, refresh data, and tag objects to generate events."),
    ]));
    return root;
  }

  // Type colors & labels
  const TYPE_COLORS = {
    view_change: "#5eead4",
    snapshot: "#52b788",
    tag: "#ff8a65",
    ws_call: "#90a4ae",
  };
  const TYPE_LABELS = {
    view_change: "View",
    snapshot: "Data",
    tag: "Tag",
    ws_call: "WS",
  };

  // Filter state — persist across re-renders
  const allTypes = [...new Set(events.map(e=>e.type))].sort();
  if(!ctx.state._historyFilters){
    ctx.state._historyFilters = new Set(allTypes);
  }
  for(const t of allTypes){
    if(!ctx.state._historyFilters.has(t)) ctx.state._historyFilters.add(t);
  }
  const activeFilters = ctx.state._historyFilters;

  // Toolbar: filters + clear
  const toolbar = el("div",{style:"display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:12px"});

  for(const type of allTypes){
    const color = TYPE_COLORS[type] || "#94a3b8";
    const label = TYPE_LABELS[type] || type;
    const isActive = activeFilters.has(type);
    const count = events.filter(e=>e.type===type).length;
    const btn = el("button",{
      style:`font-size:11px;padding:3px 10px;border-radius:12px;border:1px solid ${color};cursor:pointer;font-weight:600;transition:all 0.15s;`
        + (isActive
          ? `background:${color}22;color:${color};`
          : `background:transparent;color:#64748b;border-color:#333;text-decoration:line-through;opacity:0.5;`)
    }, `${label} (${count})`);
    btn.addEventListener("click", ()=>{
      if(activeFilters.has(type)) activeFilters.delete(type);
      else activeFilters.add(type);
      ctx.actions.renderRooms();
    });
    toolbar.appendChild(btn);
  }

  toolbar.appendChild(el("div",{style:"flex:1"}));
  const clearBtn = el("button",{class:"btn inline",style:"font-size:11px;padding:2px 8px"}, "Clear History");
  clearBtn.addEventListener("click", ()=>ctx.actions.clearSessionEvents());
  toolbar.appendChild(clearBtn);

  root.appendChild(toolbar);

  const filtered = events.filter(e => activeFilters.has(e.type));

  root.appendChild(el("div",{class:"muted",style:"font-size:11px;margin-bottom:8px"},
    filtered.length === events.length
      ? `${events.length} events`
      : `Showing ${filtered.length} of ${events.length} events`
  ));

  if(filtered.length === 0){
    root.appendChild(el("div",{class:"card"},[
      el("div",{class:"muted"},"All event types are filtered out. Click a filter button above to show events."),
    ]));
    return root;
  }

  const listContainer = el("div",{class:"list-scroll",style:"max-height:500px;overflow-y:auto;display:flex;flex-direction:column;gap:2px"});

  const sorted = [...filtered].reverse();
  for(const ev of sorted){
    const time = new Date(ev.ts);
    const hh = String(time.getHours()).padStart(2, "0");
    const mm = String(time.getMinutes()).padStart(2, "0");
    const ss = String(time.getSeconds()).padStart(2, "0");
    const timeStr = `${hh}:${mm}:${ss}`;

    const typeColor = TYPE_COLORS[ev.type] || "#94a3b8";
    const typeLabel = TYPE_LABELS[ev.type] || ev.type;

    const row = el("div",{style:"display:flex;align-items:center;gap:8px;padding:4px 8px;border-radius:4px;background:rgba(255,255,255,0.02)"});

    row.appendChild(el("span",{style:"font-family:monospace;font-size:11px;color:#64748b;flex-shrink:0;width:56px"}, timeStr));
    row.appendChild(el("span",{style:`font-size:10px;font-weight:700;padding:1px 6px;border-radius:3px;background:${typeColor}22;color:${typeColor};flex-shrink:0;min-width:36px;text-align:center`}, typeLabel));
    row.appendChild(el("span",{style:"font-size:12px;color:#cbd5e1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"}, ev.detail || ""));

    listContainer.appendChild(row);
  }

  root.appendChild(listContainer);
  return root;
}


// ═══════════════════════════════════════════════════════════════════════════
// MOVEMENT TAB
// ═══════════════════════════════════════════════════════════════════════════
function _movement(ctx, el){
  const wrap = el("div",{});

  // Load movement data on first render (cached in state)
  if(!ctx.state._movementLoaded){
    ctx.state._movementLoaded = true;
    ctx.state._movementEntries = [];
    ctx.actions.wsCall("padspan_bright/movement_history_get", {limit: 200}).then(r => {
      ctx.state._movementEntries = (r && r.entries) || [];
      ctx.actions.renderRooms();
    }).catch(() => {});
  }

  const entries = ctx.state._movementEntries || [];

  if(entries.length === 0){
    wrap.appendChild(el("div",{class:"card"},[
      el("div",{class:"muted"},"No movement history recorded yet."),
      el("div",{class:"muted",style:"font-size:12px;margin-top:6px"},"Room transitions are automatically recorded when tracked devices move between rooms."),
    ]));
    // Refresh button
    const refreshBtn = el("button",{class:"btn inline",style:"margin-top:10px;font-size:11px"}, "Refresh");
    refreshBtn.addEventListener("click", ()=>{
      ctx.state._movementLoaded = false;
      ctx.actions.renderRooms();
    });
    wrap.appendChild(refreshBtn);
    return wrap;
  }

  // Toolbar
  const toolbar = el("div",{style:"display:flex;align-items:center;gap:8px;margin-bottom:12px"});
  toolbar.appendChild(el("div",{class:"muted",style:"font-size:11px"}, `${entries.length} transitions`));
  toolbar.appendChild(el("div",{style:"flex:1"}));
  const refreshBtn = el("button",{class:"btn inline",style:"font-size:11px;padding:2px 8px"}, "Refresh");
  refreshBtn.addEventListener("click", ()=>{
    ctx.state._movementLoaded = false;
    ctx.actions.renderRooms();
  });
  toolbar.appendChild(refreshBtn);
  wrap.appendChild(toolbar);

  // Timeline (newest first)
  const listContainer = el("div",{class:"list-scroll",style:"max-height:500px;overflow-y:auto;display:flex;flex-direction:column;gap:2px"});

  const sorted = [...entries].reverse();
  for(const entry of sorted){
    const ts = entry.ts ? new Date(entry.ts * 1000) : null;
    let timeStr = "\u2014";
    let dateStr = "";
    if(ts){
      const hh = String(ts.getHours()).padStart(2, "0");
      const mm = String(ts.getMinutes()).padStart(2, "0");
      const ss = String(ts.getSeconds()).padStart(2, "0");
      timeStr = `${hh}:${mm}:${ss}`;
      const today = new Date();
      if(ts.toDateString() !== today.toDateString()){
        dateStr = `${ts.getMonth()+1}/${ts.getDate()} `;
      }
    }

    const label = entry.label || entry.device || "Unknown";
    const fromRoom = entry.from || "unknown";
    const toRoom = entry.to || "unknown";
    const rc = ctx.helpers.roomColor ? ctx.helpers.roomColor(toRoom) : "#52b788";

    const row = el("div",{style:"display:flex;align-items:center;gap:8px;padding:5px 8px;border-radius:4px;background:rgba(255,255,255,0.02);border-left:3px solid " + rc});

    row.appendChild(el("span",{style:"font-family:monospace;font-size:11px;color:#64748b;flex-shrink:0;width:72px"}, dateStr + timeStr));
    row.appendChild(el("span",{style:"font-size:12px;font-weight:600;color:#e2e8f0;min-width:80px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex-shrink:0"}, label));
    row.appendChild(el("span",{style:"font-size:11px;color:#94a3b8;flex-shrink:0"}, fromRoom));
    row.appendChild(el("span",{style:"font-size:11px;color:#5eead4"}, "\u2192"));
    row.appendChild(el("span",{style:`font-size:11px;color:${rc};font-weight:600`}, toRoom));

    listContainer.appendChild(row);
  }

  wrap.appendChild(listContainer);
  return wrap;
}
