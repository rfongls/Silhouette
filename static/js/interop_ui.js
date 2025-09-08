// Lightweight UI helpers for Interop dashboard
// - Manage Features vs Reports view
// - Populate trigger or template typeaheads for various panels
// - Maintain a primary HL7 version shared across panels

(function () {
  const LS_FEATURES = "interop.features.visible";
  const LS_REPORTS = "interop.view.reports";
  const LS_PRIMARY_VER = "interop.primary.version";

  function q(id) { return document.getElementById(id); }

  function saveVisible() {
    const toggles = Array.from(document.querySelectorAll(".feature-toggle"));
    const state = {};
    toggles.forEach(t => state[t.dataset.target] = t.checked);
    localStorage.setItem(LS_FEATURES, JSON.stringify(state));
    applyVisible(state);
  }
  function loadVisible() {
    try { return JSON.parse(localStorage.getItem(LS_FEATURES) || "{}"); }
    catch { return {}; }
  }
  function applyVisible(state) {
    Object.entries(state).forEach(([k, v]) => {
      document.querySelectorAll(`[data-feature="${k}"]`).forEach(el => el.hidden = !v);
    });
  }
  function saveReportsMode(on) {
    localStorage.setItem(LS_REPORTS, on ? "1" : "0");
    applyReportsMode(on);
  }
  function loadReportsMode() {
    return localStorage.getItem(LS_REPORTS) === "1";
  }
  function applyReportsMode(on) {
    // In a real split, we'd hide feature cards and show report cards.
    // For now, only hide elements with [data-feature] when reports is ON.
    document.querySelectorAll("[data-feature]").forEach(el => el.hidden = on ? true : el.hidden && false);
  }

  function setPrimaryVersion(v) {
    try { localStorage.setItem(LS_PRIMARY_VER, v); } catch {}
    document.querySelectorAll(".hl7-version-select").forEach(sel => {
      if (sel && sel.value !== v) sel.value = v;
      if (sel.dataset.hxRefreshTarget) {
        sel.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });
    // refresh typeaheads
    try {
      fillDatalist("qs");
      fillDatalist("ds");
      fillDatalist("gen");
      fillDatalist("pipe");
    } catch {}
  }
  function getPrimaryVersion() {
    return localStorage.getItem(LS_PRIMARY_VER) || "hl7-v2-4";
  }

  async function fillDatalist(prefix) {
    const versionSel = q(prefix + "-version") || q("sample-version") || q("gen-version");
    const version = versionSel ? versionSel.value : getPrimaryVersion();
    const dl = q(prefix + "-trigger-datalist");
    if (!dl) return;
    // If the version didn’t change we’ll still rebuild, but make sure we clear first
    dl.innerHTML = "";
    dl.dataset.ver = version;
    try {
      const r = await fetch(`/api/interop/triggers?version=${encodeURIComponent(version)}`, {cache: "no-cache"});
      const data = await r.json();
      const seen = new Set();
      (data.items || []).forEach(it => {
        // Only show one per trigger and only for this version
        const trig = (it.trigger || "").toUpperCase().trim();
        if (!trig || seen.has(trig)) return;
        seen.add(trig);
        // (We keep relpath in the payload server-side, but we display triggers only)
        const opt = document.createElement("option");
        opt.value = trig;
        opt.label = it.description ? `${it.trigger} — ${it.description}` : it.trigger;
        dl.appendChild(opt);
      });
    } catch (e) {
      // swallow
    }
  }

  async function fillTemplates(prefix) {
    const versionSel = q(prefix + "-version") || q("sample-version") || q("gen-version");
    const version = versionSel ? versionSel.value : getPrimaryVersion();
    try {
      // endpoint caps limit at 2000, so stay within that bound
      const r = await fetch(`/api/interop/samples?version=${encodeURIComponent(version)}&limit=2000`, {cache: "no-cache"});
      const data = await r.json();
      const dl = q(prefix + "-template-datalist");
      if (!dl) return;
      dl.innerHTML = "";
      (data.items || []).forEach(it => {
        const opt = document.createElement("option");
        opt.value = it.relpath;
        const label = it.description ? `${it.relpath} — ${it.description}` : it.relpath;
        opt.label = label;
        dl.appendChild(opt);
      });
    } catch (e) {
      // swallow
    }
  }

  function syncTyped(prefix) {
    // For now, a pure datalist only (no backing <select>) is used on Generate.
    // Kept for parity with other panels if you re-add a <select> later.
  }

  // wire up after load
  window.addEventListener("DOMContentLoaded", () => {
    // Feature toggles
    const initial = loadVisible();
    if (Object.keys(initial).length) applyVisible(initial);
    document.querySelectorAll(".feature-toggle").forEach(t => {
      if (initial.hasOwnProperty(t.dataset.target)) t.checked = !!initial[t.dataset.target];
      t.addEventListener("change", saveVisible);
    });
    // Reports toggle
    const rep = q("view-reports-toggle");
    if (rep) {
      rep.checked = loadReportsMode();
      applyReportsMode(rep.checked);
      rep.addEventListener("change", () => saveReportsMode(rep.checked));
    }
    // Global version chip clicks
    document.body.addEventListener("click", (e) => {
      const chip = e.target.closest('.chip-version');
      if (chip && chip.dataset && chip.dataset.version) {
        setPrimaryVersion(chip.dataset.version);
      }
    });

    // Initialize version selects
    setPrimaryVersion(getPrimaryVersion());

    // seed datalists
    fillDatalist("qs");
    fillDatalist("ds");
    fillDatalist("gen");
    fillDatalist("pipe");

    // refresh datalists after HTMX replaces the trigger <select>s
    document.body.addEventListener("htmx:afterSwap", (e) => {
      if (e && e.target && e.target.id === "qs-trigger") fillDatalist("qs");
      if (e && e.target && e.target.id === "ds-trigger-select") fillDatalist("ds");
      if (e && e.target && e.target.id === "pipe-trigger-select") fillDatalist("pipe");
    });
  });

  // expose a tiny API
  window.InteropUI = {
    syncTyped,
    fillDatalist,
    fillTemplates,
    setPrimaryVersion,
    getPrimaryVersion
  };
})();
