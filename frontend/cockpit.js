/**
 * Real-Time Streaming Events - Orchestration
 * Frontend Controller (Light Mode, Multi-Process, Time Snapshots, Last Update, Conformance & SLA Monitoring)
 */

let appState = null;
let activeView = null;                  // null | 'view-monitor' | 'view-last-update' | 'view-process-overview' | 'view-case-overview' | 'view-create-process' | 'view-settings'
let selectedCategory = null;            // null | 'GREEN' | 'ORANGE' | 'RED'
let selectedCaseId = null;              // null | string (in Deviation Monitor)
let selectedLastUpdateCaseId = null;    // null | string (in Last Update View)
let selectedProcessId = null;           // null | string (in Process Overview)
let selectedProcessCaseId = null;       // null | string (side list case in Process Overview)
let selectedDetectionMethod = "CONFORMANCE"; // 'CONFORMANCE' | 'SLA'
let selectedProcessFilter = "ALL";      // 'ALL' | 'PROC-001' | 'PROC-002' | 'PROC-003'

document.addEventListener("DOMContentLoaded", () => {
  loadState();

  // Click outside active panels returns to Main Menu
  document.addEventListener("click", (e) => {
    if (activeView === null) return;
    const path = e.composedPath ? e.composedPath() : [];
    const clickedInsideInteractiveArea = path.some(
      (el) =>
        el &&
        el.classList &&
        (el.classList.contains("panel") ||
          el.classList.contains("app-header") ||
          el.classList.contains("time-status-bar") ||
          el.classList.contains("status-tile") ||
          el.classList.contains("menu-field-tile"))
    );
    if (!clickedInsideInteractiveArea) {
      deselectAll();
    }
  });
});

async function loadState() {
  try {
    const res = await fetch("/api/state");
    appState = await res.json();
    populateProcessFilters();
    syncSettingsInputs();
    renderAllViews();
  } catch (err) {
    console.error("Failed to load application state:", err);
  }
}

async function selectTimeSnapshot(timeId) {
  try {
    const res = await fetch("/api/time", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ time_id: timeId }),
    });
    appState = await res.json();
    renderAllViews();
  } catch (err) {
    console.error("Failed to switch stream time:", err);
  }
}

function setDetectionMethod(method) {
  if (method !== "CONFORMANCE" && method !== "SLA") return;
  selectedDetectionMethod = method;

  document.querySelectorAll("#globalMethodSelector .seg-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.getAttribute("data-method") === method);
  });

  renderAllViews();
}

function onChangeProcessFilter(procId) {
  selectedProcessFilter = procId || "ALL";
  const f1 = document.getElementById("monitorProcessFilter");
  const f2 = document.getElementById("overviewProcessFilter");
  if (f1) f1.value = selectedProcessFilter;
  if (f2) f2.value = selectedProcessFilter;
  renderAllViews();
}

function populateProcessFilters() {
  if (!appState || !appState.processes) return;
  const optionsHtml = [
    `<option value="ALL">All Processes (${appState.cases.length} Cases)</option>`,
    ...appState.processes.map((p) => {
      const cnt = p.counts_by_method?.[selectedDetectionMethod]?.TOTAL ?? 0;
      return `<option value="${p.process_id}">${p.name} (${cnt})</option>`;
    }),
  ].join("");

  ["monitorProcessFilter", "overviewProcessFilter"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) {
      el.innerHTML = optionsHtml;
      el.value = selectedProcessFilter;
    }
  });
}

function renderAllViews() {
  if (!appState) return;
  populateProcessFilters();
  renderTimeSelectorAndBanner();
  renderMainMenuCounts();
  renderProcessOverview();
  renderProcessDetailPanel();
  renderCaseOverview();
  if (activeView === "view-monitor") {
    renderCategoryCaseList();
    renderSelectedCaseInspector();
  }
  if (activeView === "view-last-update") {
    renderLastUpdateView();
  }
  updateViewVisibility();
}

/* ============================================================================
   HELPER FUNCTIONS FOR METHOD-DEPENDENT CASE STATUS & UPDATE BADGES
   ============================================================================ */
function getCaseMethodStatus(c, method = selectedDetectionMethod) {
  if (method === "SLA") {
    return {
      category: c.sla_category,
      label: c.sla_label,
      reason: c.sla_reason,
      deviatingEvents: c.sla_deviating_events || [],
    };
  }
  return {
    category: c.conformance_category,
    label: c.conformance_label,
    reason: c.conformance_reason,
    deviatingEvents: c.conformance_deviating_events || [],
  };
}

function getUpdateStatusBadgeHtml(c) {
  if (c.is_from_last_update) {
    return `<span class="badge badge-NEW" title="Arrived in the currently selected stream update">🆕 From Last Update</span>`;
  }
  return `<span class="badge badge-BATCH" title="Arrived in earlier stream batch ${c.arrival_batch}">Earlier (${c.arrival_batch})</span>`;
}

function getProcessById(processId) {
  if (!appState || !appState.processes) return null;
  return appState.processes.find((p) => p.process_id === processId) || appState.processes[0];
}

/* ============================================================================
   HEADER TIME SNAPSHOT SELECTOR & SETTINGS
   ============================================================================ */
function renderTimeSelectorAndBanner() {
  const container = document.getElementById("timeSnapshotSelector");
  if (container && appState.time_snapshots) {
    container.innerHTML = appState.time_snapshots
      .map((snap) => {
        const isActive = snap.id === appState.selected_time_id;
        return `
          <button type="button" class="seg-btn ${isActive ? "active" : ""}"
                  onclick="selectTimeSnapshot('${snap.id}')">
            ${snap.short_label}
          </button>
        `;
      })
      .join("");
  }

  const snap = appState.active_snapshot;
  if (snap) {
    const badge = document.getElementById("activeTimeBadge");
    if (badge) badge.innerText = `🕒 ${snap.short_label}`;
  }

  const totalEl = document.getElementById("headerTotalCasesCount");
  const lastUpdEl = document.getElementById("headerLastUpdateCount");

  const totalCases = (appState.cases || []).length;
  const lastUpdCount = appState.last_update_count || 0;

  if (totalEl) totalEl.innerText = totalCases;
  if (lastUpdEl) lastUpdEl.innerText = `+${lastUpdCount} Cases`;
}

function syncSettingsInputs() {
  if (!appState || !appState.settings) return;
  const yellowEl = document.getElementById("settingNotifyYellow");
  const redEl = document.getElementById("settingNotifyRed");
  if (yellowEl) yellowEl.checked = !!appState.settings.notify_yellow;
  if (redEl) redEl.checked = !!appState.settings.notify_red;
}

async function saveNotificationSettings() {
  const notifyYellow = document.getElementById("settingNotifyYellow")?.checked || false;
  const notifyRed = document.getElementById("settingNotifyRed")?.checked || false;

  try {
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        notify_yellow: notifyYellow,
        notify_red: notifyRed,
      }),
    });
    appState = await res.json();
    syncSettingsInputs();
    deselectAll();
  } catch (err) {
    console.error("Failed to save notification settings:", err);
  }
}

function renderMainMenuCounts() {
  if (!appState) return;
  const counts = appState.counts_by_method?.[selectedDetectionMethod] || {
    GREEN: 0,
    ORANGE: 0,
    RED: 0,
  };
  document.getElementById("count-GREEN").innerText = counts.GREEN;
  document.getElementById("count-ORANGE").innerText = counts.ORANGE;
  document.getElementById("count-RED").innerText = counts.RED;

  if (selectedDetectionMethod === "SLA") {
    document.getElementById("tileTitle-GREEN").innerText = "🟢 Within SLA Deadlines";
    document.getElementById("tileTitle-ORANGE").innerText = "🟡 Minor Deadline Delay";
    document.getElementById("tileTitle-RED").innerText = "🔴 Severe SLA Breach";
  } else {
    document.getElementById("tileTitle-GREEN").innerText = "🟢 No Deviations";
    document.getElementById("tileTitle-ORANGE").innerText = "🟡 Minor Deviations";
    document.getElementById("tileTitle-RED").innerText = "🔴 Severe Deviations";
  }
}

/* ============================================================================
   NAVIGATION & TOGGLE LOGIC
   ============================================================================ */
function toggleCategoryField(category) {
  if (activeView === "view-monitor" && selectedCategory === category) {
    deselectAll();
    return;
  }

  activeView = "view-monitor";
  selectedCategory = category;
  selectedCaseId = null;

  updateViewVisibility();
  renderCategoryCaseList();
  renderSelectedCaseInspector();
}

function toggleMenuField(viewId) {
  if (activeView === viewId) {
    deselectAll();
    return;
  }

  activeView = viewId;
  selectedCategory = null;
  selectedCaseId = null;
  selectedLastUpdateCaseId = null;

  if (viewId === "view-process-overview") {
    selectedProcessId = null;
    selectedProcessCaseId = null;
    renderProcessOverview();
    renderProcessDetailPanel();
  } else if (viewId === "view-last-update") {
    renderLastUpdateView();
  }

  updateViewVisibility();
}

function toggleCase(caseId) {
  if (selectedCaseId === caseId) {
    deselectCase();
    return;
  }
  selectedCaseId = caseId;
  renderCategoryCaseList();
  renderSelectedCaseInspector();
}

function deselectCase() {
  selectedCaseId = null;
  renderCategoryCaseList();
  renderSelectedCaseInspector();
}

function toggleLastUpdateCase(caseId) {
  if (selectedLastUpdateCaseId === caseId) {
    selectedLastUpdateCaseId = null;
  } else {
    selectedLastUpdateCaseId = caseId;
  }
  renderLastUpdateView();
}

function deselectAll() {
  activeView = null;
  selectedCategory = null;
  selectedCaseId = null;
  selectedLastUpdateCaseId = null;
  selectedProcessId = null;
  selectedProcessCaseId = null;
  updateViewVisibility();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function inspectCaseFromOverview(caseId) {
  const c = (appState.cases || []).find((item) => item.case_id === caseId);
  if (!c) return;
  const st = getCaseMethodStatus(c);
  activeView = "view-monitor";
  selectedCategory = st.category;
  selectedCaseId = c.case_id;
  updateViewVisibility();
  renderCategoryCaseList();
  renderSelectedCaseInspector();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function updateViewVisibility() {
  const mainMenuEl = document.getElementById("mainMenuContainer");
  if (mainMenuEl) {
    mainMenuEl.style.display = activeView === null ? "block" : "none";
  }

  ["GREEN", "ORANGE", "RED"].forEach((cat) => {
    const tile = document.getElementById(`tile-${cat}`);
    const isSelected = activeView === "view-monitor" && selectedCategory === cat;
    if (tile) tile.classList.toggle("selected-tile", isSelected);
  });

  [
    "view-create-process",
    "view-process-overview",
    "view-case-overview",
    "view-settings",
  ].forEach((vid) => {
    const tile = document.getElementById(`tile-${vid}`);
    if (tile) tile.classList.toggle("selected-tile", activeView === vid);
  });

  document.querySelectorAll(".view-section").forEach((sec) => {
    sec.classList.toggle("active", sec.id === activeView);
  });
}

/* ============================================================================
   RENDER CASE LIST & PETRI NET INSPECTOR (MAIN DEVIATION MONITOR)
   ============================================================================ */
function renderCategoryCaseList() {
  if (!selectedCategory || !appState) return;

  const isSla = selectedDetectionMethod === "SLA";
  const titleMap = isSla
    ? {
        GREEN: "Cases — Within SLA Deadlines",
        ORANGE: "Cases — Minor Deadline Delay",
        RED: "Cases — Severe SLA Breach",
      }
    : {
        GREEN: "Cases — No Deviations",
        ORANGE: "Cases — Minor Deviations",
        RED: "Cases — Severe Deviations",
      };

  const labelMap = isSla
    ? {
        GREEN: "WITHIN SLA",
        ORANGE: "MINOR DELAY",
        RED: "SLA BREACH",
      }
    : {
        GREEN: "NO DEVIATIONS",
        ORANGE: "MINOR DEVIATIONS",
        RED: "SEVERE DEVIATIONS",
      };

  document.getElementById("categoryListTitle").innerText = titleMap[selectedCategory];
  const badgeEl = document.getElementById("categoryListBadge");
  badgeEl.className = `badge badge-${selectedCategory}`;
  badgeEl.innerText = `${labelMap[selectedCategory]} (${isSla ? "SLA & Timestamp" : "Conformance"})`;

  const listEl = document.getElementById("categoryCasesList");
  const filtered = (appState.cases || []).filter((c) => {
    const st = getCaseMethodStatus(c);
    const matchesCat = st.category === selectedCategory;
    const matchesProc = selectedProcessFilter === "ALL" || c.process_id === selectedProcessFilter;
    return matchesCat && matchesProc;
  });

  if (filtered.length === 0) {
    listEl.innerHTML = `<div style="padding:14px; color:var(--text-secondary); font-size:13px;">No cases in this category for the current filter.</div>`;
    return;
  }

  listEl.innerHTML = filtered
    .map((c) => renderCaseCardHtml(c, c.case_id === selectedCaseId, `toggleCase('${c.case_id}')`))
    .join("");
}

function renderCaseCardHtml(c, isSelected, onClickAttr) {
  const st = getCaseMethodStatus(c);
  const otherMethod = selectedDetectionMethod === "CONFORMANCE" ? "SLA" : "CONFORMANCE";
  const otherSt = getCaseMethodStatus(c, otherMethod);
  const devCount = st.deviatingEvents.length;

  return `
    <div class="case-list-item cat-${st.category} ${isSelected ? "active" : ""}"
         onclick="${onClickAttr}">
      <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; flex-wrap:wrap; margin-bottom:5px;">
        <div style="display:flex; align-items:center; gap:6px;">
          <strong style="font-size:14px;">${c.case_id}</strong>
          ${getUpdateStatusBadgeHtml(c)}
        </div>
        <span class="badge badge-${st.category}">${isSelected ? "✓ Selected" : st.label}</span>
      </div>
      <div style="font-size:12px; color:var(--text-secondary); margin-bottom:3px;">
        Process: <strong style="color:var(--text-primary);">${c.process_name}</strong>
      </div>
      <div style="font-size:12px; color:var(--text-secondary); margin-bottom:3px;">
        Last Event: <strong>${c.last_timestamp}</strong> • Position: <strong style="color:var(--blue);">${c.current_place_label}</strong>
      </div>
      <div style="display:flex; justify-content:space-between; align-items:center; font-size:11.5px; color:var(--text-secondary); margin-top:5px; padding-top:5px; border-top:1px dashed var(--border);">
        <span>Events: <strong>${c.events.length}</strong> | Flagged (${selectedDetectionMethod === "SLA" ? "SLA" : "Conf"}): <strong>${devCount}</strong></span>
        <span>${otherMethod === "SLA" ? "SLA" : "Conf"}: <span class="badge badge-${otherSt.category}" style="font-size:10px; padding:1px 6px;">${otherSt.label}</span></span>
      </div>
    </div>
  `;
}

function buildMethodSwitcherHtml(c) {
  const confSt = getCaseMethodStatus(c, "CONFORMANCE");
  const slaSt = getCaseMethodStatus(c, "SLA");

  return `
    <button type="button" class="method-switch-card ${selectedDetectionMethod === "CONFORMANCE" ? "active" : ""}"
            onclick="setDetectionMethod('CONFORMANCE')">
      <div>
        <div style="font-size:12.5px; font-weight:800; color:var(--text-primary);">🔍 Petri-Net Conformance Checking</div>
        <div style="font-size:11.5px; color:var(--text-secondary);">${c.conformance_deviating_events.length} deviating step(s)</div>
      </div>
      <span class="badge badge-${confSt.category}">${confSt.label}</span>
    </button>

    <button type="button" class="method-switch-card ${selectedDetectionMethod === "SLA" ? "active" : ""}"
            onclick="setDetectionMethod('SLA')">
      <div>
        <div style="font-size:12.5px; font-weight:800; color:var(--text-primary);">⏱️ SLA &amp; Timestamp Monitoring</div>
        <div style="font-size:11.5px; color:var(--text-secondary);">${c.total_elapsed_min}m / ${c.case_sla_limit_min}m deadline (${c.sla_deviating_events.length} delayed)</div>
      </div>
      <span class="badge badge-${slaSt.category}">${slaSt.label}</span>
    </button>
  `;
}

function buildSlaOverviewBoxHtml(c) {
  const pct = Math.min(100, Math.round((c.total_elapsed_min / Math.max(1, c.case_sla_limit_min)) * 100));
  const overMin = Math.max(0, c.total_elapsed_min - c.case_sla_limit_min);
  const barColor =
    c.sla_category === "RED"
      ? "#dc2626"
      : c.sla_category === "ORANGE"
      ? "#d97706"
      : "#059669";

  return `
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
      <div>
        <strong style="font-size:13px; color:var(--text-primary);">⏱️ Case SLA &amp; Deadline Tracker</strong>
        <span style="font-size:12px; color:var(--text-secondary); margin-left:8px;">
          Delayed Steps: <strong>${c.sla_deviating_events.length}</strong> of ${c.events.length}
        </span>
      </div>
      <div style="font-size:12.5px; font-weight:800; color:${barColor};">
        Elapsed: ${c.total_elapsed_min} min / Allowed SLA: ${c.case_sla_limit_min} min
        ${overMin > 0 ? `(🚨 +${overMin} min Overdue!)` : `(✓ Within Case Deadline)`}
      </div>
    </div>
    <div class="sla-progress-track">
      <div class="sla-progress-fill" style="width:${pct}%; background:${barColor};"></div>
    </div>
  `;
}

function styleReasonBox(boxEl, category, reasonText, methodLabel) {
  if (category === "GREEN") {
    boxEl.style.background = "var(--green-bg)";
    boxEl.style.border = "1px solid var(--green-border)";
    boxEl.style.color = "var(--green-text)";
  } else if (category === "ORANGE") {
    boxEl.style.background = "var(--orange-bg)";
    boxEl.style.border = "1px solid var(--orange-border)";
    boxEl.style.color = "var(--orange-text)";
  } else {
    boxEl.style.background = "var(--red-bg)";
    boxEl.style.border = "1px solid var(--red-border)";
    boxEl.style.color = "var(--red-text)";
  }
  boxEl.innerHTML = `<strong>${methodLabel}:</strong> ${reasonText}`;
}

function renderSelectedCaseInspector() {
  const grid = document.getElementById("casesInspectorGrid");
  const panel = document.getElementById("traceInspectorPanel");
  const c = (appState.cases || []).find((item) => item.case_id === selectedCaseId);

  if (!c) {
    panel.style.display = "none";
    grid.classList.add("single-col");
    return;
  }

  panel.style.display = "block";
  grid.classList.remove("single-col");

  const st = getCaseMethodStatus(c);
  const proc = getProcessById(c.process_id);

  document.getElementById("traceInspectorTitle").innerText = c.case_id;
  document.getElementById("traceInspectorUpdateBadge").innerHTML = getUpdateStatusBadgeHtml(c);

  document.getElementById("traceInspectorSubtitle").innerText =
    `Process: ${c.process_name} • Arrived: ${c.arrival_timestamp} • Last Event: ${c.last_timestamp}`;

  const badge = document.getElementById("traceInspectorBadge");
  badge.className = `badge badge-${st.category}`;
  badge.innerText = st.label;

  document.getElementById("caseMethodSwitcher").innerHTML = buildMethodSwitcherHtml(c);

  const reasonBox = document.getElementById("traceClassificationReason");
  const methodLabel =
    selectedDetectionMethod === "SLA"
      ? "SLA & Timestamp Monitoring"
      : "Petri-Net Conformance Checking";
  styleReasonBox(reasonBox, st.category, st.reason, methodLabel);

  const slaBox = document.getElementById("traceSlaOverviewBox");
  if (selectedDetectionMethod === "SLA") {
    slaBox.style.display = "block";
    slaBox.innerHTML = buildSlaOverviewBoxHtml(c);
  } else {
    slaBox.style.display = "none";
  }

  document.getElementById("currentMarkingLabel").innerText =
    `📍 Current Position: ${c.current_place_label}`;

  document.getElementById("traceMetricsLabel").innerText =
    `Total Events: ${c.events.length} | Flagged Events (${selectedDetectionMethod === "SLA" ? "SLA" : "Conformance"}): ${st.deviatingEvents.length}`;

  document.getElementById("petriNetSvgContainer").innerHTML = generatePetriNetSvg(proc, c);
  document.getElementById("traceEventsContainer").innerHTML = generateTraceEventsHtml(c);
}

/* ============================================================================
   LAST UPDATE VIEW (NEWLY ARRIVED CASES IN SELECTED STREAM TIME)
   ============================================================================ */
function renderLastUpdateView() {
  if (!appState) return;
  const newCases = (appState.cases || []).filter((c) => c.is_from_last_update);
  const snap = appState.active_snapshot;

  document.getElementById("lastUpdateCountBadge").innerText = `${newCases.length} New Cases`;
  if (snap) {
    document.getElementById("lastUpdateSubtitle").innerText =
      `Showing all ${newCases.length} newly arrived cases in the selected update (${snap.prev_timestamp.split(" ")[1]} – ${snap.timestamp.split(" ")[1]}). Click a case to inspect it.`;
  }

  const listEl = document.getElementById("lastUpdateCasesList");
  if (newCases.length === 0) {
    listEl.innerHTML = `<div style="padding:14px; color:var(--text-secondary); font-size:13px;">No newly arrived cases in this update window.</div>`;
  } else {
    listEl.innerHTML = newCases
      .map((c) =>
        renderCaseCardHtml(
          c,
          c.case_id === selectedLastUpdateCaseId,
          `toggleLastUpdateCase('${c.case_id}')`
        )
      )
      .join("");
  }

  const grid = document.getElementById("lastUpdateInspectorGrid");
  const tracePanel = document.getElementById("lastUpdateTracePanel");
  const selectedCase = newCases.find((c) => c.case_id === selectedLastUpdateCaseId) || null;

  if (!selectedCase) {
    tracePanel.style.display = "none";
    grid.classList.add("single-col");
    return;
  }

  tracePanel.style.display = "block";
  grid.classList.remove("single-col");

  const st = getCaseMethodStatus(selectedCase);
  const proc = getProcessById(selectedCase.process_id);
  const methodLabel =
    selectedDetectionMethod === "SLA"
      ? "SLA & Timestamp Monitoring"
      : "Petri-Net Conformance Checking";

  const reasonBg =
    st.category === "GREEN"
      ? "var(--green-bg)"
      : st.category === "ORANGE"
      ? "var(--orange-bg)"
      : "var(--red-bg)";
  const reasonBorder =
    st.category === "GREEN"
      ? "var(--green-border)"
      : st.category === "ORANGE"
      ? "var(--orange-border)"
      : "var(--red-border)";
  const reasonColor =
    st.category === "GREEN"
      ? "var(--green-text)"
      : st.category === "ORANGE"
      ? "var(--orange-text)"
      : "var(--red-text)";

  document.getElementById("lastUpdateTraceContent").innerHTML = `
    <div class="panel-header">
      <div style="flex:1; min-width:0;">
        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
          <div class="panel-title">${selectedCase.case_id}</div>
          ${getUpdateStatusBadgeHtml(selectedCase)}
          <span class="badge badge-${st.category}">${st.label}</span>
        </div>
        <div style="font-size:12.5px; color:var(--text-secondary); margin-top:4px;">
          Process: ${selectedCase.process_name} • Arrived: ${selectedCase.arrival_timestamp} • Last Event: ${selectedCase.last_timestamp}
        </div>
      </div>
      <div style="display:flex; align-items:center; gap:8px; flex-shrink:0; margin-left:auto;">
        <button class="btn" onclick="toggleLastUpdateCase('${selectedCase.case_id}')">✕ Deselect Case</button>
        <button class="btn" onclick="deselectAll()">← Back to Main Menu</button>
      </div>
    </div>

    <div style="margin-bottom:8px; font-size:12px; font-weight:700; color:var(--text-secondary);">
      Select Detection Method Status to Display:
    </div>
    <div class="method-switcher-grid">
      ${buildMethodSwitcherHtml(selectedCase)}
    </div>

    <div style="padding:12px 15px; border-radius:9px; margin-bottom:16px; font-size:13px; background:${reasonBg}; border:1px solid ${reasonBorder}; color:${reasonColor};">
      <strong>${methodLabel}:</strong> ${st.reason}
    </div>

    ${
      selectedDetectionMethod === "SLA"
        ? `<div class="sla-overview-box">${buildSlaOverviewBoxHtml(selectedCase)}</div>`
        : ""
    }

    <div style="margin-bottom:20px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <strong style="font-size:13.5px; color:var(--blue);">Petri Net — Current Case Position</strong>
        <span style="font-size:12.5px; font-weight:700; color:var(--blue);">📍 Current Position: ${selectedCase.current_place_label}</span>
      </div>
      <div style="background:var(--bg-card); border:1px solid var(--border); border-radius:10px; padding:12px; overflow-x:auto;">
        ${generatePetriNetSvg(proc, selectedCase)}
      </div>
    </div>

    <div>
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
        <strong style="font-size:13.5px; color:var(--blue);">Recorded Events in Trace</strong>
        <span style="font-size:12px; color:var(--text-secondary);">Total Events: ${selectedCase.events.length}</span>
      </div>
      <div class="trace-events-list">
        ${generateTraceEventsHtml(selectedCase)}
      </div>
    </div>
  `;
}

/* ============================================================================
   PETRI NET SVG GENERATOR (SUPPORTS PROCESS EVENT COUNTS & CASE INSPECTION)
   ============================================================================ */
function generatePetriNetSvg(proc, c = null) {
  const wfNet = proc?.wf_net;
  const transCounts = proc?.transition_case_counts || {};
  const placeCounts = proc?.place_case_counts || {};

  const activePlaces = new Set(c ? c.current_marking || [] : []);

  const syncTransIds = new Set();
  const reworkTransIds = new Set();
  const skippedModelTransIds = new Set();
  const stepSlaByTransId = {};

  if (c) {
    (c.alignment_moves || []).forEach((m) => {
      if (m.move_type === "SYNC" && m.transition_id) syncTransIds.add(m.transition_id);
      if (m.move_type === "REWORK" && m.transition_id) reworkTransIds.add(m.transition_id);
      if (m.move_type === "MODEL_VISIBLE" && m.transition_id) skippedModelTransIds.add(m.transition_id);
    });
    (c.events || []).forEach((ev) => {
      if (ev.transition_id) {
        stepSlaByTransId[ev.transition_id] = ev;
      }
    });
  }

  const placeMeta = {};
  (wfNet?.places || []).forEach((p) => {
    placeMeta[p.id] = p.short_label || p.name;
  });

  const transMeta = {};
  (wfNet?.transitions || []).forEach((t) => {
    transMeta[t.id] = {
      label: t.short_label || t.name,
      sla_limit_min: t.sla_limit_min,
    };
  });

  const placeCoords = {
    p1: { x: 52, y: 95, label: placeMeta.p1 || "p1 (Start)" },
    p2: { x: 200, y: 95, label: placeMeta.p2 || "p2" },
    p3: { x: 350, y: 95, label: placeMeta.p3 || "p3" },
    p4: { x: 500, y: 95, label: placeMeta.p4 || "p4" },
    p5: { x: 650, y: 95, label: placeMeta.p5 || "p5" },
    p6: { x: 800, y: 95, label: placeMeta.p6 || "p6" },
    p7: { x: 920, y: 95, label: placeMeta.p7 || "p7 (Sink)" },
  };

  const transCoords = {
    t1: { x: 125, y: 95, label: transMeta.t1?.label || "Step 1", short: "t1" },
    t2: { x: 275, y: 95, label: transMeta.t2?.label || "Step 2", short: "t2" },
    t3: { x: 425, y: 95, label: transMeta.t3?.label || "Step 3", short: "t3" },
    t4: { x: 575, y: 95, label: transMeta.t4?.label || "Step 4", short: "t4" },
    t5: { x: 725, y: 95, label: transMeta.t5?.label || "Step 5", short: "t5" },
    t6: { x: 862, y: 95, label: transMeta.t6?.label || "Step 6", short: "t6" },
    t7: { x: 275, y: 168, label: transMeta.t7?.label || "Rework", short: "t7" },
  };

  let svg = `<svg viewBox="0 0 975 208" width="100%" height="205" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <marker id="pn-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1 L 10 5 L 0 9 z" fill="#64748b" />
      </marker>
    </defs>`;

  const mainArcs = [
    ["p1", "t1"], ["t1", "p2"],
    ["p2", "t2"], ["t2", "p3"],
    ["p3", "t3"], ["t3", "p4"],
    ["p4", "t4"], ["t4", "p5"],
    ["p5", "t5"], ["t5", "p6"],
    ["p6", "t6"], ["t6", "p7"],
  ];

  mainArcs.forEach(([src, dst]) => {
    const s = placeCoords[src] || transCoords[src];
    const d = placeCoords[dst] || transCoords[dst];
    const x1 = src.startsWith("p") ? s.x + 20 : s.x + 38;
    const x2 = dst.startsWith("p") ? d.x - 20 : d.x - 38;
    svg += `<line x1="${x1}" y1="${s.y}" x2="${x2}" y2="${d.y}" stroke="#64748b" stroke-width="2" marker-end="url(#pn-arrow)" />`;
  });

  svg += `<path d="M 350 115 Q 350 168 313 168" fill="none" stroke="#64748b" stroke-width="1.8" marker-end="url(#pn-arrow)" />`;
  svg += `<path d="M 237 168 Q 200 168 200 115" fill="none" stroke="#64748b" stroke-width="1.8" marker-end="url(#pn-arrow)" />`;

  Object.entries(transCoords).forEach(([tid, tc]) => {
    let fill = "#ffffff";
    let stroke = "#64748b";
    let dash = "";
    let subText = tc.short;
    let subColor = "#475569";

    if (!c) {
      // No case selected: show how many cases had this event so far
      const count = transCounts[tid] ?? 0;
      fill = count > 0 ? "#eff6ff" : "#ffffff";
      stroke = count > 0 ? "#2563eb" : "#94a3b8";
      subText = `${count} ${count === 1 ? "Case" : "Cases"}`;
      subColor = count > 0 ? "#1d4ed8" : "#64748b";
    } else if (selectedDetectionMethod === "SLA") {
      // Case selected in SLA & Timestamp mode
      const ev = stepSlaByTransId[tid];
      if (ev) {
        if (ev.sla_status === "RED") {
          fill = "#fef2f2";
          stroke = "#dc2626";
          subText = `🚨 ${ev.duration_min}m / ${ev.sla_limit_min}m`;
          subColor = "#b91c1c";
        } else if (ev.sla_status === "ORANGE") {
          fill = "#fffbeb";
          stroke = "#d97706";
          subText = `⚠ ${ev.duration_min}m / ${ev.sla_limit_min}m`;
          subColor = "#b45309";
        } else {
          fill = "#ecfdf5";
          stroke = "#059669";
          subText = `✓ ${ev.duration_min}m / ${ev.sla_limit_min}m`;
          subColor = "#047857";
        }
      } else {
        const limit = transMeta[tid]?.sla_limit_min || 30;
        subText = `SLA ≤ ${limit}m`;
      }
    } else {
      // Case selected in Petri-Net Conformance mode
      const isSync = syncTransIds.has(tid);
      const isRework = reworkTransIds.has(tid);
      const isSkipped = skippedModelTransIds.has(tid);

      if (isSkipped) {
        fill = "#fef2f2";
        stroke = "#dc2626";
        dash = 'stroke-dasharray="4,2"';
        subText = "⚠ SKIPPED";
        subColor = "#b91c1c";
      } else if (isRework) {
        fill = "#fffbeb";
        stroke = "#d97706";
        subText = "↻ REWORK";
        subColor = "#b45309";
      } else if (isSync) {
        fill = "#ecfdf5";
        stroke = "#059669";
        subText = "✓ DONE";
        subColor = "#047857";
      }
    }

    svg += `
      <g>
        <rect x="${tc.x - 38}" y="${tc.y - 20}" width="76" height="40" rx="6"
              fill="${fill}" stroke="${stroke}" stroke-width="2" ${dash} />
        <text x="${tc.x}" y="${tc.y - 3}" text-anchor="middle" fill="#0f172a" font-size="9.5" font-weight="800">${tc.label}</text>
        <text x="${tc.x}" y="${tc.y + 12}" text-anchor="middle" fill="${subColor}" font-size="8.8" font-weight="800">
          ${subText}
        </text>
      </g>
    `;
  });

  Object.entries(placeCoords).forEach(([pid, pc]) => {
    const isCurrent = c ? activePlaces.has(pid) : false;
    const stroke = isCurrent ? "#0284c7" : "#64748b";
    const fill = isCurrent ? "#e0f2fe" : "#ffffff";
    const hereCount = placeCounts[pid] ?? 0;

    svg += `
      <g>
        ${
          isCurrent
            ? `<circle cx="${pc.x}" cy="${pc.y}" r="25" fill="none" stroke="#0284c7" stroke-width="2" stroke-dasharray="3,3" />
               <rect x="${pc.x - 42}" y="${pc.y - 54}" width="84" height="18" rx="4" fill="#0284c7" />
               <text x="${pc.x}" y="${pc.y - 42}" text-anchor="middle" fill="#ffffff" font-size="9" font-weight="800">CASE IS HERE</text>`
            : ""
        }
        <circle cx="${pc.x}" cy="${pc.y}" r="19" fill="${fill}" stroke="${stroke}" stroke-width="${isCurrent ? 3 : 1.8}" />
        <text x="${pc.x}" y="${pc.y - 25}" text-anchor="middle" fill="${isCurrent ? "#0369a1" : "#334155"}" font-size="9.5" font-weight="700">${pc.label}</text>
        ${
          isCurrent
            ? `<circle cx="${pc.x}" cy="${pc.y}" r="7.5" fill="#0284c7" />`
            : `<text x="${pc.x}" y="${pc.y + 3}" text-anchor="middle" fill="#475569" font-size="9" font-weight="700">${!c && hereCount > 0 ? hereCount : pid}</text>`
        }
      </g>
    `;
  });

  svg += `</svg>`;
  return svg;
}

function generateTraceEventsHtml(c) {
  const events = c.events || [];
  const isSla = selectedDetectionMethod === "SLA";

  return events
    .map((ev) => {
      if (isSla) {
        const rowClass =
          ev.sla_status === "RED"
            ? "deviation-RED"
            : ev.sla_status === "ORANGE"
            ? "deviation-ORANGE"
            : "";
        const pct = Math.min(100, Math.round((ev.duration_min / Math.max(1, ev.sla_limit_min)) * 100));
        const barColor =
          ev.sla_status === "RED"
            ? "#dc2626"
            : ev.sla_status === "ORANGE"
            ? "#d97706"
            : "#059669";

        return `
          <div class="trace-event-row ${rowClass}">
            <div>
              <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:4px;">
                <span style="font-size:12px; font-weight:700; color:var(--text-secondary);">Event #${ev.step} • ${ev.timestamp}</span>
                <strong style="font-size:14px; color:var(--text-primary);">${ev.activity}</strong>
                <span style="font-size:12px; color:var(--text-secondary);">(${ev.unit})</span>
              </div>
              <div style="font-size:12.5px; color:var(--text-secondary);">
                ${ev.sla_explanation}
              </div>
              <div class="step-deadline-bar-wrap">
                <div class="step-deadline-track">
                  <div class="step-deadline-fill" style="width:${pct}%; background:${barColor};"></div>
                </div>
                <span style="font-size:11.5px; font-weight:700; color:${barColor};">
                  Actual: ${ev.duration_min} min / Deadline: ${ev.sla_limit_min} min (Cumulative: ${ev.cumulative_min} min)
                </span>
              </div>
            </div>
            <div style="text-align:right; flex-shrink:0;">
              <span class="badge badge-${ev.sla_status}">${ev.sla_badge}</span>
              <div style="font-size:11px; color:var(--text-secondary); margin-top:5px;">
                Position After Event: <strong>[${ev.marking_after.join(", ")}]</strong>
              </div>
            </div>
          </div>
        `;
      }

      // Petri-Net Conformance Mode
      const isDev = ev.is_deviation;
      const rowClass = isDev ? `deviation-${ev.deviation_severity}` : "";
      const badgeClass = isDev ? `badge-${ev.deviation_severity}` : "badge-GREEN";

      return `
        <div class="trace-event-row ${rowClass}">
          <div>
            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:4px;">
              <span style="font-size:12px; font-weight:700; color:var(--text-secondary);">Event #${ev.step} • ${ev.timestamp}</span>
              <strong style="font-size:14px; color:var(--text-primary);">${ev.activity}</strong>
              <span style="font-size:12px; color:var(--text-secondary);">(${ev.unit})</span>
            </div>
            <div style="font-size:12.5px; color:var(--text-secondary);">
              ${ev.deviation_explanation}
            </div>
          </div>
          <div style="text-align:right; flex-shrink:0;">
            ${
              isDev
                ? `<span class="badge ${badgeClass}">⚠ ${ev.deviation_type.toUpperCase()}</span>`
                : `<span class="badge badge-GREEN">✓ VALID STEP</span>`
            }
            <div style="font-size:11px; color:var(--text-secondary); margin-top:5px;">
              Position After Event: <strong>[${ev.marking_after.join(", ")}]</strong>
            </div>
          </div>
        </div>
      `;
    })
    .join("");
}

/* ============================================================================
   PROCESS OVERVIEW (CLICK PROCESS -> SHOW PETRI NET WITH EVENT CASE COUNTS + SIDE LIST)
   ============================================================================ */
function toggleProcessDetail(processId) {
  if (selectedProcessId === processId) {
    closeProcessDetail();
    return;
  }
  selectedProcessId = processId;
  selectedProcessCaseId = null;
  renderProcessOverview();
  renderProcessDetailPanel();
  setTimeout(() => {
    const detailWrap = document.getElementById("processDetailContainer");
    if (detailWrap) {
      detailWrap.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, 30);
}

function closeProcessDetail() {
  selectedProcessId = null;
  selectedProcessCaseId = null;
  renderProcessOverview();
  renderProcessDetailPanel();
}

function toggleProcessSideCase(caseId) {
  if (!caseId || selectedProcessCaseId === caseId) {
    selectedProcessCaseId = null;
  } else {
    selectedProcessCaseId = caseId;
  }
  renderProcessDetailPanel();
}

function renderProcessOverview() {
  if (!appState) return;
  const container = document.getElementById("processOverviewList");

  container.innerHTML = (appState.processes || [])
    .map((p) => {
      const isSelected = selectedProcessId === p.process_id;
      const counts = p.counts_by_method?.[selectedDetectionMethod] || {
        GREEN: 0,
        ORANGE: 0,
        RED: 0,
        TOTAL: 0,
      };
      return `
      <div class="panel"
           style="background:var(--bg-card); margin-bottom:14px; cursor:pointer; border:${isSelected ? "2px solid var(--blue)" : "1px solid var(--border)"};"
           onclick="toggleProcessDetail('${p.process_id}')">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:14px;">
          <div>
            <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:10px;">
              <h3 style="font-size:16.5px; font-weight:800; color:var(--text-primary);">${p.name}</h3>
              <span class="badge badge-GREEN">${p.status}</span>
              <span class="badge badge-NEW">+${p.last_update_count || 0} in Last Update</span>
              <span style="font-size:12px; color:var(--text-secondary);">ID: ${p.process_id} • Created: ${p.created_date} • Log: ${p.log_file}</span>
            </div>
            <div style="margin-bottom:10px;">
              <strong style="font-size:12px; color:var(--blue);">Active Detection Methods:</strong>
              <div style="display:flex; flex-wrap:wrap; gap:6px; margin-top:5px;">
                ${p.detection_methods
                  .map(
                    (m) =>
                      `<span style="font-size:11.5px; font-weight:600; padding:3px 9px; border-radius:6px; background:var(--bg-surface); border:1px solid var(--border);">${m}</span>`
                  )
                  .join("")}
              </div>
            </div>
            <div style="display:flex; align-items:center; gap:10px; font-size:12.5px; color:var(--text-secondary); flex-wrap:wrap;">
              <span>Active Cases: <strong style="color:var(--text-primary);">${counts.TOTAL}</strong></span>
              <span class="badge badge-GREEN">🟢 ${counts.GREEN} No Deviations</span>
              <span class="badge badge-ORANGE">🟡 ${counts.ORANGE} Minor Deviations</span>
              <span class="badge badge-RED">🔴 ${counts.RED} Severe Deviations</span>
            </div>
          </div>

          <div style="display:flex; gap:10px; align-items:center;" onclick="event.stopPropagation();">
            <button type="button" class="btn">
              ⚙️ Change Settings (Detection Methods)
            </button>
            <button type="button" class="btn btn-danger-outline">
              🗑 Delete
            </button>
          </div>
        </div>
      </div>
    `;
    })
    .join("");
}

function renderProcessDetailPanel() {
  const detailWrap = document.getElementById("processDetailContainer");
  if (!detailWrap) return;

  if (!selectedProcessId || !appState) {
    detailWrap.style.display = "none";
    return;
  }

  const proc = getProcessById(selectedProcessId);
  if (!proc) {
    detailWrap.style.display = "none";
    return;
  }

  detailWrap.style.display = "block";
  const procCases = (appState.cases || []).filter((c) => c.process_id === proc.process_id);
  document.getElementById("processSideListHeader").innerText = `${proc.process_id} Cases`;
  document.getElementById("processSideCasesCount").innerText = `${procCases.length} Cases`;

  // Render Side List of Cases
  const sideListEl = document.getElementById("processSideCasesList");
  sideListEl.innerHTML = procCases
    .map((c) => {
      const isSelected = c.case_id === selectedProcessCaseId;
      const st = getCaseMethodStatus(c);
      return `
        <div class="case-list-item cat-${st.category} ${isSelected ? "active" : ""}"
             onclick="toggleProcessSideCase('${c.case_id}')">
          <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; flex-wrap:wrap; margin-bottom:4px;">
            <div style="display:flex; align-items:center; gap:6px;">
              <strong style="font-size:13.5px;">${c.case_id}</strong>
              ${getUpdateStatusBadgeHtml(c)}
            </div>
            <span class="badge badge-${st.category}">${st.label}</span>
          </div>
          <div style="font-size:11.5px; color:var(--text-secondary);">
            Last Event: <strong>${c.last_timestamp}</strong>
          </div>
          <div style="font-size:11.5px; color:var(--text-secondary);">
            Position: <strong style="color:var(--blue);">${c.current_place_label}</strong>
          </div>
        </div>
      `;
    })
    .join("");

  const selectedCase = procCases.find((c) => c.case_id === selectedProcessCaseId) || null;
  const svgContainer = document.getElementById("processPetriNetSvgContainer");
  svgContainer.innerHTML = generatePetriNetSvg(proc, selectedCase);

  const eventsWrap = document.getElementById("processSelectedCaseEventsWrap");
  const methodWrap = document.getElementById("processCaseMethodWrap");
  const deselectBtn = document.getElementById("processDeselectCaseBtn");
  const updatePetriBtn = document.getElementById("updatePetriNetBtn");
  const updateBadge = document.getElementById("processPetriUpdateBadge");

  if (selectedCase) {
    const st = getCaseMethodStatus(selectedCase);
    const methodLabel =
      selectedDetectionMethod === "SLA"
        ? "SLA & Timestamp Monitoring"
        : "Petri-Net Conformance Checking";

    deselectBtn.style.display = "inline-block";
    if (updatePetriBtn) updatePetriBtn.style.display = "none";
    updateBadge.style.display = "inline-block";
    updateBadge.innerHTML = getUpdateStatusBadgeHtml(selectedCase);

    document.getElementById("processPetriTitle").innerText =
      `Petri Net — ${selectedCase.case_id}`;
    document.getElementById("processPetriSubtitle").innerText =
      `Arrived: ${selectedCase.arrival_timestamp} • Last Event: ${selectedCase.last_timestamp}`;
    document.getElementById("processMarkingLabel").innerText =
      `📍 Case Position: ${selectedCase.current_place_label}`;
    document.getElementById("processCaseMetricsLabel").innerText =
      `Total Events: ${selectedCase.events.length} | Flagged: ${st.deviatingEvents.length}`;

    methodWrap.style.display = "block";
    document.getElementById("processCaseMethodSwitcher").innerHTML = buildMethodSwitcherHtml(selectedCase);
    styleReasonBox(
      document.getElementById("processCaseReasonBox"),
      st.category,
      st.reason,
      methodLabel
    );

    const pSlaBox = document.getElementById("processCaseSlaBox");
    if (selectedDetectionMethod === "SLA") {
      pSlaBox.style.display = "block";
      pSlaBox.innerHTML = buildSlaOverviewBoxHtml(selectedCase);
    } else {
      pSlaBox.style.display = "none";
    }

    document.getElementById("processTraceEventsContainer").innerHTML =
      generateTraceEventsHtml(selectedCase);
    eventsWrap.style.display = "block";
  } else {
    deselectBtn.style.display = "none";
    if (updatePetriBtn) updatePetriBtn.style.display = "inline-block";
    updateBadge.style.display = "none";
    methodWrap.style.display = "none";
    eventsWrap.style.display = "none";

    document.getElementById("processPetriTitle").innerText =
      `${proc.name} — Process Petri Net (Event Case Counts)`;
    document.getElementById("processPetriSubtitle").innerText = "";
    document.getElementById("processMarkingLabel").innerText = "";
  }
}

/* ============================================================================
   CASE OVERVIEW TABLE
   ============================================================================ */
function renderCaseOverview() {
  if (!appState) return;
  const filtered = (appState.cases || []).filter(
    (c) => selectedProcessFilter === "ALL" || c.process_id === selectedProcessFilter
  );

  let greenCnt = 0;
  let orangeCnt = 0;
  let redCnt = 0;
  let newCnt = 0;

  filtered.forEach((c) => {
    const st = getCaseMethodStatus(c);
    if (st.category === "GREEN") greenCnt++;
    else if (st.category === "ORANGE") orangeCnt++;
    else redCnt++;
    if (c.is_from_last_update) newCnt++;
  });

  document.getElementById("overviewCountGreen").innerText = `${greenCnt} No Deviations`;
  document.getElementById("overviewCountOrange").innerText = `${orangeCnt} Minor Deviations`;
  document.getElementById("overviewCountRed").innerText = `${redCnt} Severe Deviations`;
  document.getElementById("overviewCountNew").innerText = `${newCnt} From Last Update`;

  const tbody = document.getElementById("caseOverviewTableBody");
  tbody.innerHTML = filtered
    .map((c) => {
      return `
        <tr>
          <td><strong>${c.case_id}</strong></td>
          <td>${getUpdateStatusBadgeHtml(c)}</td>
          <td>${c.last_timestamp}</td>
          <td>${c.process_name}</td>
          <td>
            <span class="badge badge-${c.conformance_category}">${c.conformance_label}</span>
          </td>
          <td>
            <span class="badge badge-${c.sla_category}">${c.sla_label} (${c.total_elapsed_min}m/${c.case_sla_limit_min}m)</span>
          </td>
          <td><strong style="color:var(--blue);">${c.current_place_label}</strong></td>
          <td>
            <button class="btn" style="padding:5px 10px; font-size:12px;"
                    onclick="inspectCaseFromOverview('${c.case_id}')">
              Inspect Case →
            </button>
          </td>
        </tr>
      `;
    })
    .join("");
}
