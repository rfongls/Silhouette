// Enhanced interoperability UI helpers
// - Populate trigger typeaheads across panels
// - Coordinate feature cards + pipeline transitions
// - Maintain shared HL7 version + sample utilities

(function () {
  const LS_PRIMARY_VER = "interop.primary.version";

  function q(id) { return document.getElementById(id); }
  function byId(id) { return document.getElementById(id); }
  function textValue(el) { return (el && (el.innerText || el.textContent) || "").trim(); }
  function rootPath(path) {
    const baseRaw = (typeof window !== "undefined" && typeof window.ROOT === "string") ? window.ROOT : "";
    const base = baseRaw && baseRaw !== "/" ? baseRaw.replace(/\/+$/, "") : baseRaw;
    if (!path) return base || "";
    const suffix = path.startsWith("/") ? path : "/" + path.replace(/^\/+/, "");
    return (base || "") + suffix;
  }

  function sendDebugEvent(name, payload) {
    try {
      const body = JSON.stringify({
        event: name,
        ts: new Date().toISOString(),
        ...(payload || {}),
      });
      const url = rootPath("/api/diag/debug/event");
      if (navigator.sendBeacon) {
        const blob = new Blob([body], { type: "application/json" });
        navigator.sendBeacon(url, blob);
      } else if (window.fetch) {
        fetch(url, {
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
      if (sel.dataset && sel.dataset.hxRefreshTarget) {
        sel.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });
    try {
      fillDatalist("qs");
      fillDatalist("ds");
      fillDatalist("gen");
      fillDatalist("pipe");
    } catch {}
  }
  function getPrimaryVersion() {
    try {
      return localStorage.getItem(LS_PRIMARY_VER) || "hl7-v2-4";
    } catch {
      return "hl7-v2-4";
    }
  }

  async function fillDatalist(prefix) {
    const versionSel = q(prefix + "-version") || q("sample-version") || q("gen-version");
    const version = versionSel ? versionSel.value : getPrimaryVersion();
    const dl = q(prefix + "-trigger-datalist");
    if (!dl) return;
    dl.innerHTML = "";
    dl.dataset.ver = version;
    sendDebugEvent("interop.datalist.load", { prefix, version });
    try {
      const r = await fetch(rootPath(`/api/interop/triggers?version=${encodeURIComponent(version)}`), { cache: "no-cache" });
      const data = await r.json();
      const seen = new Set();
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
      sendDebugEvent("interop.templates.load", { prefix, version });
      const r = await fetch(rootPath(`/api/interop/samples?version=${encodeURIComponent(version)}&limit=2000`), { cache: "no-cache" });
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
    // Reserved for future parity between select + datalist inputs.
  }

  function setActivePill(feature) {
    const pills = document.querySelectorAll('#interop-feature-bar .feature-pill');
    pills.forEach(p => {
      if (p.dataset.feature === feature) p.classList.add('active');
      else p.classList.remove('active');
    });
  }
  function collapseAll() {
    ['gen', 'deid', 'val', 'mllp'].forEach(k => {
      const card = byId(k + '-card');
      if (card) card.classList.add('collapsed');
    });
  }
  function expand(feature) {
    const card = byId(feature + '-card');
    if (card) card.classList.remove('collapsed');
    setActivePill(feature);
  }
  function showFeature(feature) {
    collapseAll();
    expand(feature);
  }

  document.addEventListener('click', (e) => {
    const pill = e.target.closest('.feature-pill');
    if (!pill || !pill.dataset) return;
    const feature = pill.dataset.feature;
    if (!feature) return;
    if (feature === 'pipe') {
      window.location.href = rootPath('/ui/interop/pipeline');
      sendDebugEvent('interop.feature.navigate', { feature });
      return;
    }
    showFeature(feature);
    sendDebugEvent('interop.feature.show', { feature });
  });

  function renderPre(targetId, text) {
    const host = byId(targetId);
    if (!host) return;
    const pre = document.createElement('pre');
    pre.className = 'codepane scrollbox tall';
    pre.textContent = text || '';
    host.innerHTML = '';
    host.appendChild(pre);
  }

  function getGenText() { return textValue(byId('gen-output')); }
  function setDeidText(v) {
    const ta = byId('deid-text');
    if (ta) {
      ta.value = v || '';
      ta.dispatchEvent(new Event('input', { bubbles: true }));
    }
    renderPre('deid-output', v || '');
  }
  function getDeidText() { const ta = byId('deid-text'); return ta ? ta.value : ''; }
  function setValText(v) {
    const ta = byId('val-text');
    if (ta) {
      ta.value = v || '';
      ta.dispatchEvent(new Event('input', { bubbles: true }));
    }
  }
  function getValText() { const ta = byId('val-text'); return ta ? ta.value : ''; }
  function getMllpText() { const ta = byId('mllp-messages'); return ta ? ta.value : ''; }

  async function loadFileIntoTextarea(fileInputId, textareaId) {
    const inp = byId(fileInputId);
    const ta = byId(textareaId);
    if (!inp || !ta || !inp.files || !inp.files.length) return;
    const file = inp.files[0];
    const text = await file.text();
    ta.value = text;
    ta.dispatchEvent(new Event('input', { bubbles: true }));
    sendDebugEvent('interop.mllp.file_loaded', { name: file.name, bytes: text.length });
    showFeature('mllp');
  }

  async function postJSON(path, payload) {
    const r = await fetch(rootPath(path), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify(payload || {}),
    });
    if (!r.ok) {
      throw new Error('HTTP ' + r.status);
    }
    return r.json();
  }

  async function runDeidFromGenerate() {
    const hl7 = getGenText();
    if (!hl7) {
      alert('Please generate a message first.');
      return;
    }
    try {
      const data = await postJSON('/api/interop/deidentify', { text: hl7 });
      const outText = data && data.text ? data.text : '';
      setDeidText(outText);
      collapseAll();
      expand('deid');
      sendDebugEvent('interop.flow.deid_from_generate', { ok: true, bytes: outText.length });
    } catch (err) {
      alert('De‑Identify failed: ' + err.message);
      sendDebugEvent('interop.flow.deid_from_generate', { ok: false, error: String(err) });
    }
  }

  async function runValidateFromGenerate() {
    const hl7 = getGenText();
    if (!hl7) {
      alert('Please generate a message first.');
      return;
    }
    try {
      const data = await postJSON('/api/interop/validate', { text: hl7 });
      setValText(hl7);
      const out = byId('val-output');
      if (out) {
        out.textContent = JSON.stringify(data, null, 2);
      }
      collapseAll();
      expand('val');
      sendDebugEvent('interop.flow.validate_from_generate', { ok: true });
    } catch (err) {
      alert('Validate failed: ' + err.message);
      sendDebugEvent('interop.flow.validate_from_generate', { ok: false, error: String(err) });
    }
  }

  async function runValidateFromDeid() {
    const hl7 = getDeidText();
    if (!hl7) {
      alert('No de‑identified HL7 yet.');
      return;
    }
    try {
      const data = await postJSON('/api/interop/validate', { text: hl7 });
      setValText(hl7);
      const out = byId('val-output');
      if (out) {
        out.textContent = JSON.stringify(data, null, 2);
      }
      collapseAll();
      expand('val');
      sendDebugEvent('interop.flow.validate_from_deid', { ok: true });
    } catch (err) {
      alert('Validate failed: ' + err.message);
      sendDebugEvent('interop.flow.validate_from_deid', { ok: false, error: String(err) });
    }
  }

  async function runMllpFrom(source) {
    let hl7 = '';
    if (source === 'deid') hl7 = getDeidText();
    else if (source === 'val') hl7 = getValText();
    else hl7 = getGenText();
    if (!hl7) {
      alert('No HL7 content to send.');
      return;
    }
    const host = (byId('mllp-host') && byId('mllp-host').value || '').trim();
    const port = parseInt(byId('mllp-port') && byId('mllp-port').value || '0', 10) || 0;
    const timeout = parseFloat(byId('mllp-timeout') && byId('mllp-timeout').value || '5') || 5;
    if (!host || !port) {
      alert('Please fill MLLP host and port.');
      showFeature('mllp');
      return;
    }
    try {
      const data = await postJSON('/api/interop/mllp/send', { host, port, timeout, messages: hl7 });
      const out = byId('mllp-out');
      if (out) {
        out.textContent = JSON.stringify(data, null, 2);
      }
      collapseAll();
      expand('mllp');
      sendDebugEvent('interop.flow.mllp_send', { ok: true, sent: data && data.sent });
    } catch (err) {
      alert('MLLP send failed: ' + err.message);
      sendDebugEvent('interop.flow.mllp_send', { ok: false, error: String(err) });
    }
  }

  async function runFullHl7PipelineFromMllp() {
    const hl7 = getMllpText();
    if (!hl7) {
      alert('Paste or load HL7 first.');
      return;
    }
    try {
      const form = new FormData();
      form.set('version', getPrimaryVersion());
      form.set('text', hl7);
      form.set('ensure_unique', 'on');
      const out = byId('pipeline-output-global');
      const resp = await fetch(rootPath('/api/interop/pipeline/run'), { method: 'POST', body: form });
      const html = await resp.text();
      if (out) {
        out.innerHTML = html;
      }
      sendDebugEvent('interop.flow.full_hl7_pipeline_from_mllp', { ok: resp.ok });
    } catch (err) {
      alert('Pipeline failed: ' + err.message);
      sendDebugEvent('interop.flow.full_hl7_pipeline_from_mllp', { ok: false, error: String(err) });
    }
  }

  function openPipelineWithText(text) {
    try { sessionStorage.setItem('interop.pipeline.input', text || ''); } catch {}
    window.location.href = rootPath('/ui/interop/pipeline');
  }

  document.addEventListener('DOMContentLoaded', () => {
    setPrimaryVersion(getPrimaryVersion());
    fillDatalist('qs');
    fillDatalist('ds');
    fillDatalist('gen');
    fillDatalist('pipe');

    document.body.addEventListener('htmx:afterSwap', (e) => {
      if (!e || !e.target) return;
      if (e.target.id === 'qs-trigger') fillDatalist('qs');
      if (e.target.id === 'ds-trigger-select') fillDatalist('ds');
      if (e.target.id === 'pipe-trigger-select') fillDatalist('pipe');
    });

    document.body.addEventListener('click', (e) => {
      const chip = e.target.closest('.chip-version');
      if (chip && chip.dataset && chip.dataset.version) {
        setPrimaryVersion(chip.dataset.version);
      }
    });

    const saved = (() => {
      try { return sessionStorage.getItem('interop.pipeline.input') || ''; }
      catch { return ''; }
    })();
    if (saved) {
      const inp = document.querySelector('#pipe-form textarea[name="text"], #pipeline-form textarea[name="text"], textarea#pipe-text');
      if (inp) {
        inp.value = saved;
        inp.dispatchEvent(new Event('input', { bubbles: true }));
      }
      try { sessionStorage.removeItem('interop.pipeline.input'); } catch {}
      sendDebugEvent('interop.pipeline.prefill_from_session', { bytes: saved.length });
    }
  });

  window.InteropUI = Object.assign(window.InteropUI || {}, {
    syncTyped,
    fillDatalist,
    fillTemplates,
    syncTemplateRelpath,
    useSample,
    setPrimaryVersion,
    getPrimaryVersion,
    sendDebugEvent,
    showFeature,
    runDeidFromGenerate,
    runValidateFromGenerate,
    runValidateFromDeid,
    runMllpFrom,
    runFullHl7PipelineFromMllp,
    openPipelineWithText,
    getGenText,
    loadFileIntoTextarea,
  });
})();
