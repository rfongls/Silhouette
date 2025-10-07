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

  function ensurePanelVisible(panel) {
    if (!panel || !panel.querySelector) return;
    const body = panel.querySelector('.panel-body')
      || panel.querySelector('[data-acc-body]')
      || panel.querySelector('.module-body');
    if (!body) return;
    try { body.hidden = false; } catch (_) {}
    if (body.hasAttribute && body.hasAttribute('hidden')) body.removeAttribute('hidden');
    if (body.style) {
      if (body.style.display === 'none') body.style.removeProperty('display');
      if (body.style.visibility === 'hidden') body.style.removeProperty('visibility');
    }
    body.querySelectorAll('[hidden]').forEach((child) => {
      try { child.hidden = false; } catch (_) {}
      if (child.hasAttribute && child.hasAttribute('hidden')) child.removeAttribute('hidden');
      if (child.style) {
        if (child.style.display === 'none') child.style.removeProperty('display');
        if (child.style.visibility === 'hidden') child.style.removeProperty('visibility');
      }
    });
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
      card.setAttribute('data-open', '1');
      const header = card.querySelector('[data-acc-toggle]');
      if (header) header.setAttribute('aria-expanded', 'true');
      const label = card.querySelector('[data-acc-label]') || card.querySelector('.acc-label');
      if (label) label.textContent = 'collapse';
      ensurePanelVisible(card);
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
    const pills = document.querySelectorAll('#interop-feature-bar .feature-pill, .feature-tabs .tab, .module-nav .module-btn');
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
        card.setAttribute('data-open', '0');
        const header = card.querySelector('[data-acc-toggle]');
        if (header) header.setAttribute('aria-expanded', 'false');
        const label = card.querySelector('[data-acc-label]') || card.querySelector('.acc-label');
        if (label) label.textContent = 'expand';
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
    const pill = e.target.closest('.feature-pill, .feature-tabs .tab, .module-nav .module-btn');
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

  function onGenerateComplete() {
    const text = getGenText();
    if (text) {
      setActivePill('gen');
    }
  }

  function onDeidentifyComplete() {
    const text = getDeidText();
    if (text) {
      setActivePill('deid');
    }
  }

  function onValidateComplete() {
    const text = getValText();
    if (text) {
      setActivePill('val');
    }
  }

  function onMllpComplete() {
    if (getMllpText()) {
      setActivePill('mllp');
    }
  }

  function openPipelineWithText(text) {
    try { sessionStorage.setItem('interop.pipeline.input', text || ''); } catch {}
    sendDebugEvent('interop.pipeline.open_with_text', { bytes: (text || '').length });
    window.location.href = rootPath('/ui/interop/pipeline');
  }

  function openPipelineFrom(source) {
    const normalized = (source || '').toLowerCase();
    let text = '';
    if (normalized === 'deid') {
      text = getDeidText();
    } else if (normalized === 'validate' || normalized === 'val') {
      text = getValText();
    } else if (normalized === 'mllp') {
      text = getMllpText();
    } else {
      text = getGenText();
    }

    if (!text) {
      alert('No HL7 content available. Generate or paste a message first.');
      const map = { generate: 'gen', gen: 'gen', deid: 'deid', validate: 'val', val: 'val', mllp: 'mllp' };
      const target = map[normalized] || 'gen';
      collapseAll();
      expand(target, true);
      return;
    }

    sendDebugEvent('interop.pipeline.launch_from_panel', { source: normalized || 'generate', bytes: text.length });
    openPipelineWithText(text);
  }

  // --- Run-next tray visibility -------------------------------------------------
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

  });

  

  // Ensure dynamic sections (oob swaps) are initialized
  function _primeDynamicReports(target) {
    try {
      initDeidCoverage(target || document);
    } catch {}
    try {
      initValidateReport(target || document);
    } catch {}
  }

  document.addEventListener('DOMContentLoaded', function(){ _primeDynamicReports(document); });
  window.addEventListener('load', function(){ _primeDynamicReports(document); });

  if (document && document.body) {
    document.body.addEventListener('htmx:afterSwap', function(e){
      _primeDynamicReports(e && e.target ? e.target : document);
    });
    document.body.addEventListener('htmx:afterSettle', function(e){
      _primeDynamicReports(e && e.target ? e.target : document);
    });
    document.body.addEventListener('htmx:oobAfterSwap', function(e){
      _primeDynamicReports(document);
    });
  }
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
    openPipelineFrom,
    openPipelineWithText,
    getGenText,
    copyFromGenerate,
    loadFileIntoTextarea,
    onGenerateComplete,
    onDeidentifyComplete,
    onValidateComplete,
    onMllpComplete,
  });
})();


// --- Added: dynamic wiring for De-ID & Validation reports (robust to HTMX OOB swaps) ---
function _selectAll(root, sel) { return Array.from((root && root.querySelectorAll) ? root.querySelectorAll(sel) : []); }
function _asNumberish(a,b){ const na=parseInt(a,10); const nb=parseInt(b,10); if(!isNaN(na) && !isNaN(nb)) return na-nb; return String(a).localeCompare(String(b)); }

function initDeidCoverage(context){
  const scopes = [];
  if (context && context.matches && context.matches('[data-deid-root]')) scopes.push(context);
  scopes.push(..._selectAll(context || document, '[data-deid-root]'));
  const seen = new Set();
  scopes.forEach((root)=>{
    if(!root || seen.has(root)) return; seen.add(root);
    if (root.dataset.jsDeidInit === '1') return;
    const segSel = root.querySelector('[data-role="deid-filter-seg"]');
    const fieldSel = root.querySelector('[data-role="deid-filter-field"]');
    const actionSel = root.querySelector('[data-role="deid-filter-action"]');
    const valueInput = root.querySelector('[data-role="deid-filter-value"]');
    const resetBtn = root.querySelector('[data-role="deid-filter-reset"]');
    const rows = Array.from(root.querySelectorAll('[data-role="deid-row"]'));
    const emptyRow = root.querySelector('[data-role="deid-empty"]');
    const noteEl = root.querySelector('[data-role="deid-note"]');
    if(!segSel || !fieldSel || !actionSel || !valueInput || !rows.length) { root.dataset.jsDeidInit = '1'; return; }
    // Build row state and field maps
    const fieldsBySeg = new Map();
    const allFields = new Set();
    const rowState = rows.map((tr)=>{
      const segment = (tr.dataset.segment || '').trim();
      const field = (tr.dataset.field || '').trim();
      const action = (tr.dataset.action || '').trim();
      const logic = (tr.dataset.logic || '').trim();
      const segNorm = segment.toLowerCase();
      const fieldNorm = field.toLowerCase();
      const actionNorm = action.toLowerCase();
      if (segment && field) {
        if (!fieldsBySeg.has(segNorm)) fieldsBySeg.set(segNorm, new Set());
        fieldsBySeg.get(segNorm).add(field);
      }
      if (field) allFields.add(field);
      const search = [segment, field, action, logic, tr.textContent||''].join(' ').toLowerCase();
      return {el: tr, segment, field, action, logic: logic.toLowerCase(), segNorm, fieldNorm, actionNorm, search};
    });
    function rebuildFieldOptions(){
      const segKey = (segSel.value || 'all').trim().toLowerCase();
      const values = ['all'];
      if (segKey && segKey !== 'all' && fieldsBySeg.has(segKey)) {
        const arr = Array.from(fieldsBySeg.get(segKey));
        arr.sort(_asNumberish);
        arr.forEach(v => values.push(v));
      } else {
        const arr = Array.from(allFields);
        arr.sort(_asNumberish);
        arr.forEach(v => values.push(v));
      }
      const prev = fieldSel.value;
      fieldSel.innerHTML = '';
      values.forEach(v=>{
        const opt = document.createElement('option');
        opt.value = v;
        opt.textContent = (v === 'all') ? 'All' : v;
        fieldSel.appendChild(opt);
      });
      if (values.includes(prev)) fieldSel.value = prev;
    }
    function apply(){
      const wantSeg = (segSel.value || 'all').trim().toLowerCase();
      const wantField = (fieldSel.value || 'all').trim().toLowerCase();
      const wantAction = (actionSel.value || 'all').trim().toLowerCase();
      const query = (valueInput.value || '').trim().toLowerCase();
      let visible = 0;
      rowState.forEach(row=>{
         let show = true;
         if (wantSeg !== 'all' && row.segNorm !== wantSeg) show = false;
         if (show && wantField !== 'all' && row.fieldNorm !== wantField) show = false;
         if (show && wantAction !== 'all' && row.actionNorm !== wantAction) show = false;
         if (show && query && !row.search.includes(query)) show = false;
         row.el.style.display = show ? '' : 'none';
         if (show) visible++;
      });
      if (emptyRow) emptyRow.style.display = visible ? 'none' : '';
      if (noteEl) noteEl.style.display = visible ? 'none' : '';
    }
    segSel.addEventListener('change', ()=>{ rebuildFieldOptions(); apply(); });
    fieldSel.addEventListener('change', apply);
    actionSel.addEventListener('change', apply);
    valueInput.addEventListener('input', apply);
    if (resetBtn) resetBtn.addEventListener('click', ()=>{
      segSel.value = 'all';
      rebuildFieldOptions();
      fieldSel.value = 'all';
      actionSel.value = 'all';
      valueInput.value = '';
      apply();
    });
    rebuildFieldOptions();
    apply();
    root.dataset.jsDeidInit = '1';
  });
}

function initValidateReport(context){
  const scopes = [];
  if (context && context.matches && context.matches('[data-val-root]')) scopes.push(context);
  scopes.push(..._selectAll(context || document, '[data-val-root]'));
  const seen = new Set();
  scopes.forEach((root)=>{
    if(!root || seen.has(root)) return; seen.add(root);
    if (root.dataset.jsValInit === '1') return;
    const body = root.querySelector('[data-role="val-summary-body"]');
    const emptyRow = root.querySelector('[data-role="val-empty"]');
    const dataEl = root.querySelector('[data-role="val-issues"]');
    const severitySelect = root.querySelector('[data-role="val-filter-sev"]');
    const segmentSelect = root.querySelector('[data-role="val-filter-seg"]');
    const searchInput = root.querySelector('[data-role="val-filter-text"]');
    const chips = Array.from(root.querySelectorAll('.validate-report__counts [data-vf]'));
    if (!body || !dataEl || !severitySelect || !segmentSelect || !searchInput) { root.dataset.jsValInit = '1'; return; }
    let issues = [];
    try { issues = JSON.parse(dataEl.textContent || '[]') || []; } catch(_e){ issues = []; }
    const TOTAL = parseInt(dataEl.dataset.total || '1', 10) || 1;
    // Helper cleaners
    const clean = (v)=> String(v ?? '').trim();
    const cleanZero = (v)=> { const s = clean(v); if (s === '' || s === '—') return ''; return (''+s); };
    const normSev = (s)=>{
      s = clean(s).toLowerCase();
      if (s.includes('warn')) return 'warning';
      if (s.includes('ok') || s.includes('pass') || s.includes('info')) return 'passed';
      return 'error';
    };
    const normalize = (item)=>{
      if (!item || typeof item !== 'object') return {severity:'error', code:'', segment:'', field:'', component:'', subcomponent:'', value:'', message:''};
      return {
        severity: normSev(item.severity || item.status || 'error'),
        code: clean(item.code || item.rule || item.id || ''),
        segment: clean(item.segment || ''),
        field: cleanZero(item.field ?? ''),
        component: cleanZero(item.component ?? ''),
        subcomponent: cleanZero(item.subcomponent ?? ''),
        value: clean(item.value || item.actual || item.expected || item.received || ''),
        message: clean(item.message || '')
      };
    };
    const rowsMap = new Map();
    const segmentsSet = new Set();
    issues.forEach((raw)=>{
      const row = normalize(raw);
      const key = [
        row.severity,
        row.code,
        row.segment,
        row.field,
        row.component,
        row.subcomponent
      ].map(s => (s || '')).join('|'); // intentionally exclude message & value to bucket by rule/location only
      const b = rowsMap.get(key) || {
        severity: row.severity,
        code: row.code,
        segment: row.segment,
        field: row.field,
        component: row.component,
        subcomponent: row.subcomponent,
        message: row.message, // first one wins
        values: new Set(),
        count: 0
      };
      // extract value if not explicitly provided
      let v = row.value;
      if (!v && row.message) {
        const m = row.message.match(/Value\s+'([^']+)'/) || row.message.match(/'([^']+)'/);
        if (m) v = m[1];
      }
      if (v) b.values.add(v);
      b.count += 1;
      rowsMap.set(key, b);
      if (row.segment) segmentsSet.add(row.segment);
    });
    // Build rows
    body.innerHTML = '';
    const buckets = Array.from(rowsMap.values()).sort((a,b)=>{
      const sevOrd = (s)=> s==='error'?0 : s==='warning'?1 : 2;
      return sevOrd(a.severity) - sevOrd(b.severity)
        || (a.segment || '').localeCompare(b.segment || '')
        || (parseInt(a.field || '0',10) - parseInt(b.field || '0',10))
        || (a.code || '').localeCompare(b.code || '');
    });
    const builtRows = buckets.map((bucket)=>{
      const values = Array.from(bucket.values);
      const shown = values.slice(0,8);
      const extraCount = values.length - shown.length;
      const extra = extraCount > 0 ? ` (+${extraCount} more)` : '';
      const tr = document.createElement('tr');
      tr.dataset.role = 'val-row';
      tr.dataset.severity = bucket.severity;
      tr.dataset.segment = (bucket.segment || '').trim().toLowerCase();
      tr.dataset.segmentRaw = bucket.segment || '';
      tr.dataset.text = [
        bucket.code, bucket.segment, bucket.field, bucket.component, bucket.subcomponent, values.join(' '), bucket.message
      ].join(' ').toLowerCase();
      tr.innerHTML = `
        <td style="padding:0.5rem">${bucket.severity==='passed' ? 'Passed' : bucket.severity==='warning' ? 'Warning' : 'Error'}</td>
        <td style="padding:0.5rem"><code class="mono">${bucket.code || '—'}</code></td>
        <td style="padding:0.5rem"><code class="mono">${bucket.segment || '—'}</code></td>
        <td style="padding:0.5rem"><code class="mono">${bucket.field || '—'}</code></td>
        <td style="padding:0.5rem"><code class="mono">${bucket.component || '—'}</code></td>
        <td style="padding:0.5rem"><code class="mono">${bucket.subcomponent || '—'}</code></td>
        <td style="padding:0.5rem">${shown.length ? shown.join(', ') : '—'}${extra}</td>
        <td style="padding:0.5rem">${bucket.message || '—'}</td>
        <td style="padding:0.5rem">${bucket.count}</td>
        <td style="padding:0.5rem">${bucket.count}/${TOTAL}</td>
        <td style="padding:0.5rem">${TOTAL ? Math.round((bucket.count / TOTAL) * 100) : 0}%</td>`;
      body.appendChild(tr);
      return tr;
    });
    // Populate Segment select with actual segments
    const existingSegments = new Set(Array.from(segmentSelect.options).map(o=>o.value));
    Array.from(segmentsSet).sort((a,b)=>a.localeCompare(b)).forEach(seg=>{
      if (!seg || existingSegments.has(seg)) return;
      const opt=document.createElement('option'); opt.value=seg; opt.textContent=seg; segmentSelect.appendChild(opt);
    });
    if (emptyRow) emptyRow.style.display = builtRows.length ? 'none' : '';
    // Filtering behavior + chip controls
    let chipMode = 'error'; // default required
    function normalizeMode(x){ const s=(x||'').toLowerCase(); return s.includes('warn') ? 'warning' : (s.includes('pass')||s.includes('ok')||s.includes('info')) ? 'passed' : (s.includes('all')?'all': 'error'); }
    function syncChips(){
      chips.forEach((btn)=>{
        const active = (chipMode==='all' && btn.dataset.vf==='all') || btn.dataset.vf===chipMode;
        btn.style.outline = active ? '2px solid var(--color-border, #94a3b8)' : 'none';
        btn.setAttribute('aria-pressed', active ? 'true' : 'false');
      });
    }
    function applyFilter(){
      const wantSev = (severitySelect.value || '').trim().toLowerCase();
      const wantSeg = (segmentSelect.value || '').trim().toLowerCase();
      const query = (searchInput.value || '').trim().toLowerCase();
      let visible=0;
      builtRows.forEach((tr)=>{
        const sev = (tr.dataset.severity || '').trim().toLowerCase();
        const seg = (tr.dataset.segment || '').trim().toLowerCase();
        const text = (tr.dataset.text || '').toLowerCase();
        let show = true;
        if (chipMode !== 'all') show = show && (sev === chipMode);
        if (wantSev && wantSev !== 'all') show = show && sev === wantSev;
        if (wantSeg && wantSeg !== 'all') show = show && seg === wantSeg;
        if (query) show = show && text.includes(query);
        tr.style.display = show ? '' : 'none';
        if (show) visible++;
      });
      if (emptyRow) emptyRow.style.display = visible ? 'none' : '';
      syncChips();
    }
    // Set initial select values (defaults)
    const segmentInitial = segmentSelect.dataset.initial || 'all';
    const severityInitial = severitySelect.dataset.initial || 'error';
    const searchInitial = searchInput.dataset.initial || '';
    if (Array.from(segmentSelect.options).some(opt => opt.value === segmentInitial)) segmentSelect.value = segmentInitial;
    severitySelect.value = severityInitial;
    searchInput.value = searchInitial;
    // Wire events
    severitySelect.addEventListener('change', ()=>{ chipMode = normalizeMode(severitySelect.value); applyFilter(); });
    segmentSelect.addEventListener('change', applyFilter);
    searchInput.addEventListener('input', applyFilter);
    chips.forEach((chip)=>{
      chip.addEventListener('click', ()=>{
        chipMode = normalizeMode(chip.dataset.vf);
        if (chipMode !== 'all') severitySelect.value = chipMode;
        applyFilter();
      });
    });
    // Initial render
    applyFilter();
    root.dataset.jsValInit = '1';
  });
}

// Expose globals for manual calls and make robust to HTMX swaps
if (!window.InteropUI) window.InteropUI = {};
window.InteropUI.initDeidCoverage = initDeidCoverage;
window.InteropUI.initValidateReport = initValidateReport;

// Prime on load and after HTMX swaps
function _primeAll(ctx){ try{ initDeidCoverage(ctx||document); initValidateReport(ctx||document); }catch(e){ /* ignore */ } }
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', ()=> _primeAll(document));
} else { _primeAll(document); }
document.body && document.body.addEventListener && document.body.addEventListener('htmx:afterSwap', (e)=> _primeAll(e && (e.detail && (e.detail.elt || e.detail.target)) || e.target || document));
document.body && document.body.addEventListener && document.body.addEventListener('htmx:oobAfterSwap', (e)=> _primeAll(e && (e.detail && (e.detail.elt || e.detail.target)) || e.target || document));
document.body && document.body.addEventListener && document.body.addEventListener('htmx:afterSettle', (e)=> _primeAll(e && (e.detail && (e.detail.elt || e.detail.target)) || e.target || document));

// --- end added block ---


// --- De-identification report (filters) -------------------------------------
function initDeidCoverage(root) {
  try {
    root = root && root.querySelector ? root : document;
    const host = root.querySelector('section.deid-coverage[data-deid-root]') || root.closest && root.closest('section.deid-coverage[data-deid-root]');
    const container = host || root.querySelector('section.deid-coverage[data-deid-root]');
    if (!container || container.dataset.deidJsInit === '1') return;
    container.dataset.deidJsInit = '1';

    const segSel = container.querySelector('[data-role="deid-filter-seg"]');
    const fieldSel = container.querySelector('[data-role="deid-filter-field"]');
    const actionSel = container.querySelector('[data-role="deid-filter-action"]');
    const valueInput = container.querySelector('[data-role="deid-filter-value"]');
    const resetBtn = container.querySelector('[data-role="deid-filter-reset"]');
    const noteEl = container.querySelector('[data-role="deid-note"]');
    const emptyRow = container.querySelector('[data-role="deid-empty"]');

    if (!segSel || !fieldSel || !actionSel || !valueInput) return;

    const rowState = Array.from(container.querySelectorAll('[data-role="deid-row"]')).map((tr) => {
      const segment = (tr.dataset.segment || '').trim();
      const field = (tr.dataset.field || '').trim();
      const action = (tr.dataset.action || '').trim();
      const logic = (tr.dataset.logic || '').toLowerCase();
      const search = [segment, field, action, logic].join(' ').toLowerCase();
      return {
        el: tr,
        segment,
        segmentNorm: segment.toLowerCase(),
        field,
        fieldNorm: field.toLowerCase(),
        action,
        actionNorm: action.toLowerCase(),
        logic,
        search,
      };
    });

    function collectFields(segValue) {
      const segNorm = segValue === 'all' ? '' : (segValue || '').trim().toLowerCase();
      const fields = new Map();
      rowState.forEach((row) => {
        if (segNorm && row.segmentNorm !== segNorm) return;
        if (!row.field) return;
        fields.set(row.field, true);
      });
      return Array.from(fields.keys());
    }
    function sortFields(fields) {
      return fields.sort((a, b) => {
        const ta = parseInt(a || '0', 10);
        const tb = parseInt(b || '0', 10);
        if (!Number.isNaN(ta) && !Number.isNaN(tb) && ta !== tb) return ta - tb;
        return String(a || '').localeCompare(String(b || ''));
      });
    }
    function populateSegments() {
      const current = segSel.value;
      const segs = new Map();
      rowState.forEach((row) => {
        if (row.segment) segs.set(row.segment, true);
      });
      segSel.innerHTML = '<option value="all">All</option>';
      Array.from(segs.keys()).sort().forEach((seg) => {
        const opt = document.createElement('option');
        opt.value = seg;
        opt.textContent = seg;
        segSel.appendChild(opt);
      });
      if (Array.from(segSel.options).some((o) => o.value === current)) segSel.value = current;
    }
    function populateFields() {
      const current = fieldSel.value;
      const segValue = segSel.value;
      fieldSel.innerHTML = '<option value="all">All</option>';
      sortFields(collectFields(segValue)).forEach((field) => {
        const opt = document.createElement('option');
        opt.value = field;
        opt.textContent = field;
        fieldSel.appendChild(opt);
      });
      if (Array.from(fieldSel.options).some((opt) => opt.value === current)) {
        fieldSel.value = current;
      } else {
        fieldSel.value = 'all';
      }
    }
    function populateActions() {
      const current = actionSel.value;
      const segNorm = segSel.value === 'all' ? '' : (segSel.value || '').trim().toLowerCase();
      const fieldNorm = fieldSel.value === 'all' ? '' : (fieldSel.value || '').trim().toLowerCase();
      const actions = new Map();
      rowState.forEach((row) => {
        if (segNorm && row.segmentNorm !== segNorm) return;
        if (fieldNorm && row.fieldNorm !== fieldNorm) return;
        if (!row.action) return;
        actions.set(row.action, true);
      });
      actionSel.innerHTML = '<option value="all">All</option>';
      Array.from(actions.keys()).sort().forEach((action) => {
        const opt = document.createElement('option');
        opt.value = action;
        opt.textContent = action;
        actionSel.appendChild(opt);
      });
      if (Array.from(actionSel.options).some((o) => o.value === current)) {
        actionSel.value = current;
      } else {
        actionSel.value = 'all';
      }
    }
    function applyFilters() {
      const wantSeg = segSel.value;
      const wantSegNorm = wantSeg === 'all' ? '' : (wantSeg || '').trim().toLowerCase();
      const wantField = fieldSel.value;
      const wantFieldNorm = wantField === 'all' ? '' : (wantField || '').trim().toLowerCase();
      const wantAction = actionSel.value;
      const wantActionNorm = wantAction === 'all' ? '' : (wantAction || '').trim().toLowerCase();
      const query = (valueInput.value || '').trim().toLowerCase();
      let visible = 0;
      rowState.forEach((row) => {
        let show = true;
        if (wantSegNorm && row.segmentNorm !== wantSegNorm) show = false;
        if (show && wantFieldNorm && row.fieldNorm !== wantFieldNorm) show = false;
        if (show && wantActionNorm && row.actionNorm !== wantActionNorm) show = false;
        if (show && query && !row.search.includes(query)) show = false;
        row.el.style.display = show ? '' : 'none';
        if (show) visible += 1;
      });
      if (emptyRow) emptyRow.style.display = visible ? 'none' : '';
      if (noteEl) noteEl.style.display = visible ? 'none' : '';
    }
    segSel.addEventListener('change', () => {
      populateFields();
      populateActions();
      applyFilters();
    });
    fieldSel.addEventListener('change', () => {
      populateActions();
      applyFilters();
    });
    actionSel.addEventListener('change', applyFilters);
    valueInput.addEventListener('input', applyFilters);
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        segSel.value = 'all';
        populateFields();
        fieldSel.value = 'all';
        populateActions();
        actionSel.value = 'all';
        valueInput.value = '';
        applyFilters();
      });
    }
    populateSegments();
    populateFields();
    populateActions();
    applyFilters();
  } catch (e) {
    console.warn('initDeidCoverage error', e);
  }
}

// --- Validation report (buckets + filters) ----------------------------------
function initValidateReport(root) {
  try {
    root = root && root.querySelector ? root : document;
    const container = root.querySelector('section.validate-report[data-val-root]') || root.getElementById && root.getElementById('validate-report');
    if (!container || container.dataset.valJsInit === '1') return;
    container.dataset.valJsInit = '1';

    const dataEl = container.querySelector('[data-role="val-issues"]');
    const body = container.querySelector('[data-role="val-summary-body"]');
    const emptyRow = container.querySelector('[data-role="val-empty"]');
    if (!dataEl || !body) return;

    let issues = [];
    try { issues = JSON.parse(dataEl.textContent || '[]') || []; } catch { issues = []; }
    const TOTAL = parseInt(dataEl.dataset.total || '1', 10) || 1;

    const severitySelect = container.querySelector('[data-role="val-filter-sev"]');
    const segmentSelect = container.querySelector('[data-role="val-filter-seg"]');
    const searchInput = container.querySelector('[data-role="val-filter-text"]');
    const resetButton = container.querySelector('[data-role="val-filter-reset"]');
    const chips = Array.from(container.querySelectorAll('.validate-report__counts .chip[data-vf]'));
    if (!severitySelect || !segmentSelect || !searchInput) return;

    const clean = (v) => (v === null || v === undefined ? '' : String(v).trim());
    const cleanZeroable = (value) => (value === 0 ? '0' : clean(value));
    const normalize = (item) => {
      if (!item || typeof item !== 'object') {
        return { severity: 'error', code: '', segment: '', field: '', component: '', subcomponent: '', value: '', message: '' };
      }
      const severity = clean(item.severity || item.status || 'error').toLowerCase();
      const normalizedSeverity = severity.includes('warn') ? 'warning' : (severity.includes('ok') || severity.includes('pass')) ? 'passed' : 'error';
      return {
        severity: normalizedSeverity,
        code: clean(item.code || item.rule || ''),
        segment: clean(item.segment || item.seg || ''),
        field: cleanZeroable(item.field),
        component: cleanZeroable(item.comp || item.component),
        subcomponent: cleanZeroable(item.subcomp || item.subcomponent),
        value: clean(item.value || item.bad_value || ''),
        message: clean(item.message || item.msg || ''),
      };
    };

    const normIssues = (Array.isArray(issues) ? issues : []).map(normalize);
    const rowsMap = new Map();
    normIssues.forEach((it) => {
      const key = [
        it.severity,
        it.segment.toLowerCase(),
        it.field,
        it.component,
        it.subcomponent,
        it.code,
        it.message,
      ].join('|');
      let bucket = rowsMap.get(key);
      if (!bucket) {
        bucket = {
          severity: it.severity || 'error',
          code: it.code || '',
          segment: it.segment || '',
          field: it.field || '',
          component: it.component || '',
          subcomponent: it.subcomponent || '',
          message: it.message || '',
          values: new Set(),
          count: 0,
        };
        rowsMap.set(key, bucket);
      }
      const v = it.value || '';
      if (v) bucket.values.add(v);
      bucket.count += 1;
    });

    body.innerHTML = '';
    const sortedBuckets = Array.from(rowsMap.values()).sort((a, b) => {
      const order = (sev) => (sev === 'error' ? 0 : sev === 'warning' ? 1 : 2);
      return order(a.severity) - order(b.severity)
        || (a.segment || '').localeCompare(b.segment || '')
        || (parseInt(a.field || '0', 10) - parseInt(b.field || '0', 10))
        || (a.code || '').localeCompare(b.code || '');
    });

    const builtRows = sortedBuckets.map((bucket) => {
      const values = Array.from(bucket.values);
      const shown = values.slice(0, 8);
      const extraCount = values.length - shown.length;
      const extra = extraCount > 0 ? ` (+${extraCount} more)` : '';
      const severityLabel = bucket.severity === 'passed' ? 'Passed' : bucket.severity === 'warning' ? 'Warning' : 'Error';
      const tr = document.createElement('tr');
      tr.dataset.role = 'val-row';
      tr.dataset.severity = bucket.severity;
      tr.dataset.segment = (bucket.segment || '').trim().toLowerCase();
      tr.dataset.segmentRaw = bucket.segment || '';
      tr.dataset.text = [
        bucket.code,
        bucket.segment,
        bucket.field,
        bucket.component,
        bucket.subcomponent,
        values.join(', '),
        bucket.message,
      ].join(' ').toLowerCase();

      tr.innerHTML = [
        `<td style="padding:0.5rem">${severityLabel}</td>`,
        `<td style="padding:0.5rem"><code class="mono">${bucket.code || ''}</code></td>`,
        `<td style="padding:0.5rem"><code class="mono">${bucket.segment || ''}</code></td>`,
        `<td style="padding:0.5rem"><code class="mono">${bucket.field || ''}</code></td>`,
        `<td style="padding:0.5rem"><code class="mono">${bucket.component || ''}</code></td>`,
        `<td style="padding:0.5rem"><code class="mono">${bucket.subcomponent || ''}</code></td>`,
        `<td style="padding:0.5rem"><code class="mono">${shown.join(', ')}${extra}</code></td>`,
        `<td style="padding:0.5rem">${bucket.message || ''}</td>`,
        `<td style="padding:0.5rem">${bucket.count}</td>`,
        `<td style="padding:0.5rem">${TOTAL}</td>`,
        `<td style="padding:0.5rem">${((bucket.count / TOTAL) * 100).toFixed(0)}%</td>`,
      ].join('');
      body.appendChild(tr);
      return tr;
    });

    const normalizeMode = (value) => {
      const v = String(value || '').toLowerCase();
      if (v.includes('pass') || v === 'ok' || v === 'info') return 'passed';
      if (v.includes('warn')) return 'warning';
      if (v.includes('error') || v === 'err') return 'error';
      if (v === 'all' || !v) return 'all';
      return 'error';
    };
    const syncChips = () => {
      const mode = normalizeMode(severitySelect.value || 'error');
      chips.forEach((chip) => {
        const vf = normalizeMode(chip.dataset.vf);
        chip.style.opacity = vf === mode ? '1' : '.7';
        chip.style.transform = vf === mode ? 'scale(1.0)' : 'scale(.98)';
      });
    };

    let chipMode = normalizeMode('error');
    function applyFilter() {
      const wantSev = normalizeMode(severitySelect.value);
      const wantSeg = (segmentSelect.value || '').trim().toLowerCase();
      const query = (searchInput.value || '').trim().toLowerCase();
      let visible = 0;
      builtRows.forEach((tr) => {
        const sev = (tr.dataset.severity || '').trim().toLowerCase();
        const seg = (tr.dataset.segment || '').trim().toLowerCase();
        const text = (tr.dataset.text || '').toLowerCase();
        let show = true;
        if (chipMode !== 'all') show = show && sev === chipMode;
        if (wantSev && wantSev !== 'all') show = show && sev === wantSev;
        if (wantSeg && wantSeg !== 'all') show = show && seg === wantSeg;
        if (query) show = show && text.includes(query);
        tr.style.display = show ? '' : 'none';
        if (show) visible += 1;
      });
      if (emptyRow) emptyRow.style.display = visible ? 'none' : '';
      syncChips();
    }

    severitySelect.addEventListener('change', () => {
      chipMode = normalizeMode(severitySelect.value);
      applyFilter();
    });
    segmentSelect.addEventListener('change', applyFilter);
    searchInput.addEventListener('input', applyFilter);
    chips.forEach((chip) => {
      chip.addEventListener('click', () => {
        chipMode = normalizeMode(chip.dataset.vf);
        severitySelect.value = chipMode === 'all' ? 'all' : chipMode;
        applyFilter();
      });
    });
    if (resetButton) {
      resetButton.addEventListener('click', () => {
        chipMode = normalizeMode('error');
        severitySelect.value = 'error';
        segmentSelect.value = 'all';
        searchInput.value = '';
        applyFilter();
      });
    }
    chipMode = normalizeMode(chipMode || 'error');
    applyFilter();
  } catch (e) {
    console.warn('initValidateReport error', e);
  }
}
