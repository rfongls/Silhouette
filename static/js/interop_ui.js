// Enhanced interoperability UI helpers
// - Populate trigger typeaheads across panels
// - Coordinate feature cards + pipeline transitions
// - Maintain shared HL7 version + sample utilities

(function () {
  const LS_PRIMARY_VER = "interop.primary.version";

  function q(id) { return document.getElementById(id); }
  function byId(id) { return document.getElementById(id); }
  function textValue(el) { return (el && (el.innerText || el.textContent) || "").trim(); }
  function resolveRootBase() {
    const body = typeof document !== "undefined" ? document.body : null;
    if (body && body.dataset && typeof body.dataset.root === "string") {
      return body.dataset.root;
    }
    const meta = typeof document !== "undefined" ? document.querySelector('meta[name="root-path"]') : null;
    if (meta && typeof meta.getAttribute === "function") {
      const val = meta.getAttribute("content");
      if (typeof val === "string") return val;
    }
    if (typeof window !== "undefined" && typeof window.ROOT === "string") {
      return window.ROOT;
    }
    return "";
  }

  function rootPath(path) {
    const baseRaw = resolveRootBase();
    const base = baseRaw && baseRaw !== "/" ? baseRaw.replace(/\/+$/, "") : (baseRaw === "/" ? "" : baseRaw);
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

  const FEATURE_IDS = {
    gen: 'card-gen',
    deid: 'card-deid',
    val: 'card-validate',
    validate: 'card-validate',
    mllp: 'card-mllp'
  };

  function normalizedFeatureKey(feature) {
    if (feature === 'validate') return 'val';
    return feature;
  }

  function cardEl(feature) {
    const id = FEATURE_IDS[feature] || `card-${feature}`;
    return byId(id);
  }

  function expandCard(feature, highlight) {
    const card = cardEl(feature);
    if (!card) return;
    if (card.tagName === 'DETAILS') {
      card.open = true;
      if (highlight) {
        card.classList.add('highlight');
        setTimeout(() => card.classList.remove('highlight'), 900);
      }
    } else {
      card.classList.remove('collapsed');
      if (highlight) {
        card.classList.add('highlight');
        setTimeout(() => card.classList.remove('highlight'), 900);
      }
    }
    try {
      card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (_) {}
  }

  function setActivePill(feature) {
    const pills = document.querySelectorAll('#interop-feature-bar .feature-pill, .feature-tabs .tab');
    pills.forEach(p => {
      const featureMatch = p.dataset && p.dataset.feature === feature;
      const openMatch = p.dataset && p.dataset.openCard === (FEATURE_IDS[feature] || feature);
      if (featureMatch || openMatch) p.classList.add('active'); else p.classList.remove('active');
    });
  }
  function collapseAll() {
    const seen = new Set();
    Object.values(FEATURE_IDS).forEach(id => {
      if (!id || seen.has(id)) return;
      seen.add(id);
      const card = byId(id);
      if (!card) return;
      if (card.tagName === 'DETAILS') {
        card.open = false;
      } else {
        card.classList.add('collapsed');
      }
    });
  }
  function expand(feature, highlight) {
    expandCard(feature, highlight);
    setActivePill(normalizedFeatureKey(feature));
  }
  function showFeature(feature) {
    collapseAll();
    expand(feature);
  }

  document.addEventListener('click', (e) => {
    const pill = e.target.closest('.feature-pill, .feature-tabs .tab');
    if (!pill || !pill.dataset) return;
    const feature = pill.dataset.feature || pill.dataset.openCard;
    if (!feature) return;
    if (FEATURE_IDS[feature]) {
      showFeature(feature);
      sendDebugEvent('interop.feature.show', { feature });
      return;
    }
    if (feature === 'card-gen' || feature === 'card-deid' || feature === 'card-validate' || feature === 'card-mllp') {
      collapseAll();
      const idFeature = Object.keys(FEATURE_IDS).find(key => FEATURE_IDS[key] === feature);
      expand(idFeature || feature);
      return;
    }
    if (feature === 'pipe') {
      window.location.href = rootPath('/ui/interop/pipeline');
      sendDebugEvent('interop.feature.navigate', { feature });
      return;
    }
  });

  function getGenText() { return textValue(byId('gen-output')); }
  function getDeidText() {
    const pre = byId('deid-output');
    const fromPre = pre ? (pre.textContent || pre.innerText || '').trim() : '';
    if (fromPre) return fromPre;
    const ta = byId('deid-text');
    return ta ? ta.value : '';
  }
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

  function copyFromGenerate(target) {
    const normalized = normalizedFeatureKey(target);
    const text = getGenText();
    const selectors = {
      deid: '#deid-text',
      val: '#val-text',
      validate: '#val-text',
      mllp: '#mllp-messages'
    };
    const selector = selectors[normalized] || selectors[target];
    if (selector) {
      const ta = document.querySelector(selector);
      if (ta && text) {
        ta.value = text;
        ta.dispatchEvent(new Event('input', { bubbles: true }));
      }
    }
    sendDebugEvent('interop.generate.copy', { target: normalized, hasText: !!text });
    return text;
  }

  function openManual(target) {
    const normalized = normalizedFeatureKey(target);
    const text = copyFromGenerate(target);
    collapseAll();
    expand(normalized, true);
    sendDebugEvent('interop.generate.manual_open', { target: normalized, hasText: !!text });
  }

  function runNextDeid() {
    runTo('deid');
  }

  function runValidationFromGen() {
    runTo('validate');
  }

  function runDeidFromGenerate() {
    runNextDeid();
  }

  function runValidateFromGenerate() {
    runValidationFromGen();
  }

  async function runValidateFromDeid() {
    runNextFromDeid('validate');
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

  function runFullFhirFromGen() {
    const text = getGenText();
    if (!text) {
      alert('Please generate a message first.');
      expand('gen');
      return;
    }
    try {
      sessionStorage.setItem('sil.lastGen', text);
      sessionStorage.setItem('interop.pipeline.input', text);
    } catch (_) {}
    sendDebugEvent('interop.flow.full_pipeline_from_generate', { bytes: text.length });
    window.location.href = rootPath('/ui/interop/pipeline');
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

  function escapeHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function openCard(id) {
    if (!id) return;
    collapseAll();
    const card = typeof id === 'string' ? document.getElementById(id) : id;
    if (!card) return;
    if (card.tagName === 'DETAILS') {
      card.open = true;
    } else {
      card.classList.remove('collapsed');
    }
    const featureKey = Object.keys(FEATURE_IDS).find(key => FEATURE_IDS[key] === (card.id || id));
    if (featureKey) {
      setActivePill(normalizedFeatureKey(featureKey));
    }
  }

  function runTo(target) {
    const normalizedTarget = target === 'fhir' ? 'mllp' : target;
    const normalized = normalizedFeatureKey(normalizedTarget);
    const text = getGenText();
    if (!text) {
      alert('Please generate a message first.');
      expand('gen');
      return;
    }
    copyFromGenerate(normalizedTarget);
    if (target === 'fhir') {
      const toggle = byId('run-pipeline-fhir');
      if (toggle) toggle.checked = true;
      const post = byId('run-pipeline-fhir-post');
      if (post) post.checked = true;
    }
    if (normalized === 'deid') {
      const mini = document.querySelector('#deid-report details, details.mini-report');
      if (mini && typeof mini.open === 'boolean') {
        mini.open = true;
      }
    }
    collapseAll();
    expand(normalized, true);
  }

  function setRunTrayVisibility(show) {
    const tray = byId('gen-run-tray');
    if (!tray) {
      return;
    }
    if (show) {
      tray.classList.remove('hidden');
      tray.removeAttribute('hidden');
    } else {
      tray.classList.add('hidden');
      tray.setAttribute('hidden', '');
    }
  }

  function runNextFromDeid(next) {
    const hl7 = (getDeidText() || '').trim();
    if (!hl7) {
      alert('Run de-identify first.');
      expand('deid');
      return;
    }
    if (next === 'validate') {
      setValText(hl7);
      collapseAll();
      expand('val', true);
    } else if (next === 'mllp') {
      const ta = byId('mllp-messages');
      if (ta) {
        ta.value = hl7;
        ta.dispatchEvent(new Event('input', { bubbles: true }));
      }
      collapseAll();
      expand('mllp', true);
    }
  }

  function onGenerateComplete(evt) {
    const text = getGenText();
    setRunTrayVisibility(!!text);
    if (text) {
      setActivePill('gen');
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

    let saved = '';
    let source = 'interop.pipeline.input';
    try {
      saved = sessionStorage.getItem('sil.lastGen') || '';
      if (saved) {
        source = 'sil.lastGen';
      } else {
        saved = sessionStorage.getItem('interop.pipeline.input') || '';
      }
    } catch { saved = ''; }
    if (saved) {
      const inp = document.querySelector('#pipe-form textarea[name="text"], #pipeline-form textarea[name="text"], textarea#pipe-text, form[action$="/api/interop/pipeline/run"] textarea[name="text"]');
      if (inp && !inp.value) {
        inp.value = saved;
        inp.dispatchEvent(new Event('input', { bubbles: true }));
      }
      try {
        sessionStorage.removeItem('sil.lastGen');
        sessionStorage.removeItem('interop.pipeline.input');
      } catch {}
      sendDebugEvent('interop.pipeline.prefill_from_session', { bytes: saved.length, source });
    }

    setRunTrayVisibility(!!getGenText());
    const genOutput = byId('gen-output');
    if (genOutput) {
      if ('value' in genOutput) {
        genOutput.addEventListener('input', () => setRunTrayVisibility(!!getGenText()));
      }
      if (typeof MutationObserver !== 'undefined') {
        const observer = new MutationObserver(() => setRunTrayVisibility(!!getGenText()));
        observer.observe(genOutput, { childList: true, characterData: true, subtree: true });
      }
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
    openCard,
    openManual,
    runTo,
    runNextDeid,
    runValidationFromGen,
    runDeidFromGenerate,
    runValidateFromGenerate,
    runValidateFromDeid,
    runNextFromDeid,
    runMllpFrom,
    runFullFhirFromGen,
    runFullHl7PipelineFromMllp,
    openPipelineWithText,
    getGenText,
    copyFromGenerate,
    loadFileIntoTextarea,
    onGenerateComplete,
    setRunTrayVisibility,
  });
})();
