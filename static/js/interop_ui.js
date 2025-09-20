// Lightweight UI helpers for Interop dashboard
// - Manage Features vs Reports view
// - Populate trigger or template typeaheads for various panels
// - Maintain a primary HL7 version shared across panels

(function () {
  const LS_FEATURES = "interop.features.visible";
  const LS_REPORTS = "interop.view.reports";
  const LS_PRIMARY_VER = "interop.primary.version";

  function q(id) { return document.getElementById(id); }

  function sendDebugEvent(name, payload) {
    try {
      const body = JSON.stringify({
        event: name,
        ts: new Date().toISOString(),
        ...(payload || {}),
      });
      if (navigator.sendBeacon) {
        const blob = new Blob([body], { type: "application/json" });
        navigator.sendBeacon("/api/diag/debug/event", blob);
      } else if (window.fetch) {
        fetch("/api/diag/debug/event", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body,
          keepalive: true,
        });
      }
    } catch (err) {
      /* ignore */
    }
  }

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

  function setTemplateHint(prefix, relpath) {
    const hint = q(prefix + "-template-hint");
    if (!hint) return;
    const empty = hint.dataset ? hint.dataset.empty || "" : "";
    if (relpath) {
      hint.textContent = `Selected template: ${relpath}`;
      hint.classList.remove("muted");
    } else {
      hint.textContent = empty || "No template selected.";
      if (!hint.classList.contains("muted")) hint.classList.add("muted");
    }
  }

  function syncTemplateRelpath(prefix) {
    const input = q(prefix + "-trigger-typed");
    const hidden = q(prefix + "-template-relpath");
    const dl = q(prefix + "-trigger-datalist");
    if (!input || !hidden || !dl) {
      return;
    }
    const want = (input.value || "").toUpperCase().trim();
    const options = dl.options ? Array.from(dl.options) : Array.from(dl.querySelectorAll("option"));
    if (!options.length) {
      setTemplateHint(prefix, hidden.value || "");
      return;
    }
    let rel = "";
    if (want) {
      for (const opt of options) {
        const v = (opt.value || "").toUpperCase().trim();
        if (v === want) {
          rel = opt.dataset && opt.dataset.relpath ? opt.dataset.relpath : "";
          if (!rel && opt.getAttribute) {
            rel = opt.getAttribute("data-relpath") || "";
          }
          break;
        }
      }
    }
    hidden.value = rel;
    setTemplateHint(prefix, rel);
    if (hidden && hidden.dataset) {
      const prev = hidden.dataset.prevRelpath || "";
      if (rel && rel !== prev) {
        hidden.dataset.prevRelpath = rel;
        sendDebugEvent("interop.template.resolved", { prefix, trigger: want, relpath: rel });
      } else if (!rel) {
        hidden.dataset.prevRelpath = "";
      }
    }
  }

  function useSample(prefix, payload) {
    const data = payload || {};
    const versionSel = q(prefix + "-version") || q("gen-version");
    if (versionSel && data.version) {
      versionSel.value = data.version;
      if (versionSel.dataset && versionSel.dataset.hxRefreshTarget) {
        versionSel.dispatchEvent(new Event("change", { bubbles: true }));
      }
    }
    const triggerInput = q(prefix + "-trigger-typed");
    if (triggerInput && data.trigger) {
      triggerInput.value = data.trigger;
    }
    const hidden = q(prefix + "-template-relpath");
    if (hidden && data.relpath) {
      hidden.value = data.relpath;
    }
    setTemplateHint(prefix, data.relpath || "");
    syncTemplateRelpath(prefix);
    sendDebugEvent("interop.sample.use", {
      prefix,
      relpath: data.relpath || "",
      trigger: data.trigger || "",
      version: data.version || "",
    });
  }

  function setPrimaryVersion(v) {
    try { localStorage.setItem(LS_PRIMARY_VER, v); } catch {}
    sendDebugEvent("interop.version.set", { version: v });
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

  async function fillDatalist(prefix) {  // e.g. prefix === 'gen'
    const versionSel = q(prefix + "-version") || q("sample-version") || q("gen-version");
    const version = versionSel ? versionSel.value : getPrimaryVersion();
    const dl = q(prefix + "-trigger-datalist");  // e.g., gen-trigger-datalist
    if (!dl) return;
    // clear and tag with version to avoid races
    dl.innerHTML = "";
    dl.dataset.ver = version;
    sendDebugEvent("interop.datalist.load", { prefix, version });
    try {
      const r = await fetch(`/api/interop/triggers?version=${encodeURIComponent(version)}`, {cache: "no-cache"});
      const data = await r.json();
      const seen = new Set(); // de-dupe by trigger (per version)
      (data.items || []).forEach(it => {
        const trig = (it.trigger || "").toUpperCase().trim();
        if (!trig || seen.has(trig)) return;
        seen.add(trig);
        const opt = document.createElement("option");
        opt.value = trig;
        opt.label = it.description ? `${it.trigger} — ${it.description}` : it.trigger;
        if (it.relpath) {
          opt.dataset.relpath = it.relpath;
        }
        dl.appendChild(opt);
      });
      sendDebugEvent("interop.datalist.loaded", { prefix, version, count: (data.items || []).length });
    } catch (e) {
      sendDebugEvent("interop.datalist.error", { prefix, version, message: e && e.message ? e.message : String(e) });
    }
    syncTemplateRelpath(prefix);
  }

  async function fillTemplates(prefix) {
    const versionSel = q(prefix + "-version") || q("sample-version") || q("gen-version");
    const version = versionSel ? versionSel.value : getPrimaryVersion();
    try {
      // endpoint caps limit at 2000, so stay within that bound
      sendDebugEvent("interop.templates.load", { prefix, version });
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
      sendDebugEvent("interop.templates.loaded", { prefix, version, count: (data.items || []).length });
    } catch (e) {
      sendDebugEvent("interop.templates.error", { prefix, version, message: e && e.message ? e.message : String(e) });
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

    injectPipelinePresetUI();
  });

  // Shared pipeline presets used across dashboard + standalone pipeline page.
  const PIPELINE_PRESETS = {
    "local-2575": {
      host: "127.0.0.1",
      port: 2575,
      timeout: 5,
      includeFhir: false,
      fhirEndpoint: "http://127.0.0.1:8080/fhir",
      postFhir: false,
    },
    "docker-2575": {
      host: "localhost",
      port: 2575,
      timeout: 5,
      includeFhir: false,
      fhirEndpoint: "http://localhost:8080/fhir",
      postFhir: false,
    },
    "partner-a": {
      host: "10.0.0.10",
      port: 2575,
      timeout: 10,
      includeFhir: true,
      fhirEndpoint: "https://partner-a.example/fhir",
      postFhir: true,
    },
  };

  function applyPreset(key) {
    const preset = PIPELINE_PRESETS[key];
    const host = q("mllp-host");
    const port = q("mllp-port");
    const timeout = q("mllp-timeout");
    const toggle = q("run-pipeline-fhir");
    const postToggle = q("run-pipeline-fhir-post");
    const pipelineEndpoint =
      document.getElementById("pipeline-fhir-endpoint") ||
      document.getElementById("fhir-endpoint") ||
      document.querySelector('input[name="fhir_endpoint"]');
    const pipelinePost =
      document.getElementById("pipeline-post-fhir") ||
      document.querySelector('input[name="post_fhir"][type="checkbox"]');
    if (!preset) {
      if (toggle) {
        toggle.checked = false;
        if (toggle.dataset) delete toggle.dataset.endpoint;
      }
      if (postToggle) postToggle.checked = false;
      if (pipelinePost) pipelinePost.checked = false;
      sendDebugEvent("interop.pipeline.preset.clear", {});
      return;
    }
    if (host && preset.host !== undefined) host.value = preset.host;
    if (port && preset.port !== undefined) port.value = preset.port;
    if (timeout && preset.timeout !== undefined) timeout.value = preset.timeout;
    if (toggle) {
      toggle.checked = !!preset.includeFhir;
    }
    if (postToggle) {
      postToggle.checked = !!(preset.includeFhir && preset.postFhir);
    }
    if (pipelineEndpoint && preset.fhirEndpoint !== undefined) {
      pipelineEndpoint.value = preset.fhirEndpoint || "";
    }
    if (pipelinePost) {
      pipelinePost.checked = !!preset.postFhir;
    }
    const endpointValue =
      (pipelineEndpoint && pipelineEndpoint.value) ||
      (preset.fhirEndpoint || "");
    if (toggle && toggle.dataset) {
      if (endpointValue) {
        toggle.dataset.endpoint = endpointValue;
      } else {
        delete toggle.dataset.endpoint;
      }
    }
    const out = q("pipeline-output");
    if (out && out.closest && preset.includeFhir) {
      const wrap = out.closest("details");
      if (wrap) wrap.open = true;
    }
    sendDebugEvent("interop.pipeline.preset", {
      key,
      includeFhir: !!preset.includeFhir,
      postFhir: !!preset.postFhir,
      hasEndpoint: !!endpointValue,
    });
  }

  function injectPipelinePresetUI() {
    const form =
      document.getElementById("pipe-form") ||
      document.getElementById("pipeline-form") ||
      document.querySelector('form[action$="/api/interop/pipeline/run"]');
    if (!form || document.getElementById("pipeline-preset-standalone")) {
      return;
    }
    const wrap = document.createElement("div");
    wrap.className = "row gap mb";
    wrap.innerHTML =
      '<label class="label small" for="pipeline-preset-standalone">Preset</label>' +
      '<select id="pipeline-preset-standalone" class="input" style="max-width:22rem">' +
      '  <option value="">— Select preset —</option>' +
      '  <option value="local-2575">Local MLLP (127.0.0.1:2575)</option>' +
      '  <option value="docker-2575">Docker MLLP (localhost:2575)</option>' +
      '  <option value="partner-a">Partner Sandbox A (+FHIR)</option>' +
      "</select>" +
      '<span class="micro muted">Prefills FHIR endpoint (and POST) on this page; also used on the Generate/MLLP cards.</span>';
    form.insertBefore(wrap, form.firstChild);
  }

  document.addEventListener("change", (e) => {
    if (!e || !e.target) return;
    const id = e.target.id;
    if (id === "pipeline-preset" || id === "pipeline-preset-standalone") {
      applyPreset(e.target.value);
    } else if (id === "run-pipeline-fhir" && !e.target.checked) {
      const postToggle = q("run-pipeline-fhir-post");
      if (postToggle) postToggle.checked = false;
    }
  });

  function getGenText() {
    const el = document.getElementById("gen-output");
    return (el && (el.innerText || el.textContent) || "").trim();
  }

  function copyFromGenerate(target) {
    const text = getGenText();
    if (!text) return;
    const map = { deid: "#deid-text", validate: "#val-text", mllp: "#mllp-messages" };
    const ta = document.querySelector(map[target]);
    if (ta) {
      ta.value = text;
      ta.dispatchEvent(new Event("input", { bubbles: true }));
    }
    sendDebugEvent("interop.generate.copy", { target, hasText: !!text });
    if (target === "deid") {
      const run = document.getElementById("run-pipeline");
      if (run && run.checked) {
        const form = document.getElementById("deid-form");
        if (form && form.requestSubmit) {
          form.requestSubmit();
        } else if (form) {
          form.submit();
        }
      }
    }
  }

  async function runFhirPipeline(hl7) {
    if (!hl7) {
      const outEmpty = q("pipeline-output");
      if (outEmpty) {
        outEmpty.classList.remove("muted");
        outEmpty.textContent = "Pipeline error: no HL7 content available.";
      }
      sendDebugEvent("interop.pipeline.fhir.error", { message: "no hl7 content" });
      return;
    }
    const out = q("pipeline-output");
    if (out) {
      out.classList.remove("muted");
      out.textContent = "Running HL7→FHIR pipeline…";
      if (out.closest) {
        const wrap = out.closest("details");
        if (wrap) wrap.open = true;
      }
    }
    if (!window.fetch) {
      if (out) out.textContent = "Pipeline error: fetch() is not available in this browser.";
      sendDebugEvent("interop.pipeline.fhir.error", { message: "fetch unsupported" });
      return;
    }
    const postToggle = q("run-pipeline-fhir-post");
    const toggle = q("run-pipeline-fhir");
    const wantPost = !!(postToggle && postToggle.checked);
    const endpoint = toggle && toggle.dataset ? toggle.dataset.endpoint || "" : "";
    sendDebugEvent("interop.pipeline.fhir.start", { post: wantPost, hasEndpoint: !!endpoint });
    const payload = { text: hl7, post_fhir: wantPost };
    if (endpoint) payload.fhir_endpoint = endpoint;
    try {
      const resp = await fetch("/api/interop/pipeline/run", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/plain, text/html",
        },
        body: JSON.stringify(payload),
      });
      const ctype = resp.headers.get("content-type") || "";
      let message = "";
      if (ctype.includes("application/json")) {
        const data = await resp.json();
        message = JSON.stringify(data, null, 2);
      } else {
        const text = await resp.text();
        if (ctype.includes("text/html")) {
          try {
            const parser = new DOMParser();
            const doc = parser.parseFromString(text, "text/html");
            message = doc && doc.body && doc.body.textContent ? doc.body.textContent.trim() : text;
          } catch (err) {
            message = text;
          }
        } else {
          message = text;
        }
      }
      if (out) out.textContent = message || "(no response)";
      sendDebugEvent("interop.pipeline.fhir.done", { ok: resp.ok, status: resp.status });
    } catch (err) {
      const msg = err && err.message ? err.message : String(err);
      if (out) out.textContent = "Pipeline error: " + msg;
      sendDebugEvent("interop.pipeline.fhir.error", { message: msg });
    }
  }

  document.addEventListener("htmx:afterSwap", (e) => {
    if (!e || !e.target) return;
    if (e.target.id === "deid-output") {
      const run = q("run-pipeline");
      if (!run || !run.checked) return;
      const text = (e.target.innerText || e.target.textContent || "").trim();
      if (!text) return;
      const vta = document.querySelector("#val-text");
      if (vta) {
        vta.value = text;
        vta.dispatchEvent(new Event("input", { bubbles: true }));
      }
      const ml = document.querySelector("#mllp-messages");
      if (ml) {
        ml.value = text;
        ml.dispatchEvent(new Event("input", { bubbles: true }));
      }
      const vf = document.getElementById("val-form");
      if (vf && vf.requestSubmit) {
        vf.requestSubmit();
      } else if (vf) {
        vf.submit();
      }
    } else if (e.target.id === "val-output" || e.target.id === "validate-output") {
      const run = q("run-pipeline");
      if (!run || !run.checked) return;
      const useFhir = !!(q("run-pipeline-fhir") && q("run-pipeline-fhir").checked);
      const text = (q("val-text") && q("val-text").value ? q("val-text").value : "").trim();
      if (!text) return;
      if (useFhir) {
        runFhirPipeline(text);
      } else {
        const mf = document.getElementById("mllp-form");
        if (mf && mf.requestSubmit) {
          mf.requestSubmit();
        } else if (mf) {
          mf.submit();
        }
      }
    }
  });

  // expose a tiny API
  window.InteropUI = {
    syncTyped,
    fillDatalist,
    fillTemplates,
    syncTemplateRelpath,
    useSample,
    setPrimaryVersion,
    getPrimaryVersion,
    sendDebugEvent,
    copyFromGenerate,
    applyPreset,
  };
})();
