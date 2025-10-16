(function () {
  const urls = window.STANDALONE_PIPELINE_URLS || {};
  const $1 = (root, selector) => (root || document).querySelector(selector);
  const $$ = (root, selector) => Array.from((root || document).querySelectorAll(selector));

  const PANEL_IDS = {
    generate: 'generate-panel',
    deid: 'deid-panel',
    validate: 'validate-panel',
    mllp: 'mllp-panel',
    pipeline: 'pipeline-panel',
  };

  const TRIGGER_INPUT_ID = 'std-trigger-input';
  const TRIGGER_LIST_ID = 'std-trigger-list';
  const VERSION_SELECT_ID = 'std-version';
  const COUNT_INPUT_ID = 'std-count';
  const SEED_CHECK_ID = 'std-seed';
  const ENRICH_CHECK_ID = 'std-enrich';

  const ACTION_TARGETS = {
    deid: { panel: PANEL_IDS.deid, textarea: '#deid-msg' },
    validate: { panel: PANEL_IDS.validate, textarea: '#validate-form textarea[name="message"]' },
    mllp: { panel: PANEL_IDS.mllp, textarea: '#mllp-msg' },
    pipeline: { panel: PANEL_IDS.pipeline, textarea: '#pipeline-form textarea[name="text"]' },
  };

  const triggerSampleMap = new Map();
  let lastTriggerVersion = '';

  const panelEntries = Object.entries(PANEL_IDS);

  function panelKeyFromId(id) {
    if (!id) return null;
    const match = panelEntries.find(([, value]) => value === id);
    return match ? match[0] : null;
  }

  function expandPanel(id) {
    if (!id) return;
    const el = document.getElementById(id);
    if (!el) return;
    if (el.tagName.toLowerCase() === 'details') {
      el.setAttribute('open', '');
    } else {
      el.classList.add('panel-open');
    }
  }

  function collapsePanel(id) {
    if (!id) return;
    const el = document.getElementById(id);
    if (!el) return;
    if (el.tagName.toLowerCase() === 'details') {
      el.removeAttribute('open');
    } else {
      el.classList.remove('panel-open');
    }
  }

  function collapseAllExcept(idToKeep) {
    panelEntries.forEach(([, panelId]) => {
      if (panelId !== idToKeep) {
        collapsePanel(panelId);
      }
    });
  }

  function scrollPanelIntoView(id) {
    if (!id) return;
    const el = document.getElementById(id);
    if (!el) return;
    try {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
      console.debug('standalone-pipeline: scroll failed', err);
    }
  }

  function prefill(selector, text) {
    if (!selector) return;
    const el = $1(document, selector);
    if (!el) return;
    if (typeof el.value === 'string') {
      el.value = text;
    } else {
      el.textContent = text;
    }
    try {
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    } catch (err) {
      console.debug('standalone-pipeline: prefill dispatch failed', err);
    }
  }

  function activateModule(action, text, opts = {}) {
    const target = ACTION_TARGETS[action];
    if (!target) return;
    if (opts.collapseFrom && PANEL_IDS[opts.collapseFrom]) {
      collapsePanel(PANEL_IDS[opts.collapseFrom]);
    }
    collapseAllExcept(target.panel);
    expandPanel(target.panel);
    if (text) {
      prefill(target.textarea, text);
    }
    scrollPanelIntoView(target.panel);
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function urlFor(key, params) {
    const base = urls[key];
    if (!base) return '';
    try {
      const u = new URL(base, window.location.origin);
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          if (v === undefined || v === null) return;
          u.searchParams.set(k, String(v));
        });
      }
      return u.toString();
    } catch (err) {
      console.warn('standalone-pipeline: invalid URL for', key, err);
      return base;
    }
  }

  async function fetchJSON(url) {
    if (!url) return null;
    const resp = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!resp.ok) throw new Error(resp.statusText);
    return resp.json();
  }

  async function fetchText(url) {
    if (!url) return '';
    const resp = await fetch(url, { headers: { Accept: 'text/plain' } });
    if (!resp.ok) throw new Error(resp.statusText);
    return resp.text();
  }

  function normalizeTrigger(value) {
    return (value || '')
      .toString()
      .trim()
      .toUpperCase()
      .replace(/\s+/g, '')
      .replace(/\^/g, '_');
  }

  function parseCount() {
    const input = $1(document, `#${COUNT_INPUT_ID}`);
    const raw = input?.value;
    const value = Number.parseInt(raw ?? '1', 10);
    const clamped = Number.isFinite(value) ? Math.min(Math.max(value, 1), 50) : 1;
    if (input && String(clamped) !== String(raw ?? '')) {
      input.value = String(clamped);
    }
    return clamped;
  }

  function repeatMessage(text, count) {
    const trimmed = (text || '').trim();
    if (!trimmed || count <= 1) {
      return trimmed;
    }
    return Array.from({ length: count }, () => trimmed).join('\n\n');
  }

  function getFlags() {
    const seed = !!$1(document, `#${SEED_CHECK_ID}`)?.checked;
    const enrich = !!$1(document, `#${ENRICH_CHECK_ID}`)?.checked;
    return { seed, enrich };
  }

  async function fillTriggers() {
    const select = $1(document, `#${VERSION_SELECT_ID}`);
    const datalist = $1(document, `#${TRIGGER_LIST_ID}`);
    if (!select || !datalist) return;
    const version = select.value || 'hl7-v2-4';
    try {
      const data = await fetchJSON(urlFor('triggers', { version }));
      const items = Array.isArray(data?.items) ? data.items : [];
      triggerSampleMap.clear();
      const options = items
        .map((item) => ({
          trigger: (item?.trigger || '').trim(),
          description: (item?.description || '').trim(),
          relpath: item?.relpath || '',
        }))
        .filter((item) => item.trigger);
      datalist.innerHTML = options
        .map((item) => {
          const normalized = normalizeTrigger(item.trigger);
          if (normalized) {
            triggerSampleMap.set(normalized, item.relpath || '');
          }
          triggerSampleMap.set(item.trigger.toUpperCase(), item.relpath || '');
          const label = item.description ? `${item.trigger} — ${item.description}` : item.trigger;
          return `<option value="${escapeHtml(item.trigger)}" label="${escapeHtml(label)}"></option>`;
        })
        .join('');
      lastTriggerVersion = version;
    } catch (err) {
      console.warn('standalone-pipeline: trigger load failed', err);
    }
  }

  async function resolveSampleRelpath(version, triggerValue) {
    const normalized = normalizeTrigger(triggerValue);
    if (!normalized) return '';
    if (triggerSampleMap.has(normalized)) {
      return triggerSampleMap.get(normalized) || '';
    }
    try {
      const data = await fetchJSON(urlFor('samples', { version, q: triggerValue }));
      const items = Array.isArray(data?.items) ? data.items : [];
      for (const item of items) {
        const trig = (item?.trigger || '').trim();
        const relpath = item?.relpath || '';
        if (!trig || !relpath) continue;
        const norm = normalizeTrigger(trig);
        if (norm) {
          triggerSampleMap.set(norm, relpath);
          triggerSampleMap.set(trig.toUpperCase(), relpath);
        }
        if (norm === normalized) {
          return relpath;
        }
      }
      const fallback = items[0]?.relpath;
      if (fallback) {
        return fallback;
      }
    } catch (err) {
      console.warn('standalone-pipeline: sample lookup failed', err);
    }
    return '';
  }

  async function loadSample() {
    const versionSelect = $1(document, `#${VERSION_SELECT_ID}`);
    const version = versionSelect?.value || 'hl7-v2-4';
    const triggerInput = $1(document, `#${TRIGGER_INPUT_ID}`);
    const triggerValue = triggerInput?.value || '';
    if (!triggerValue) {
      return;
    }
    const count = parseCount();
    const { seed, enrich } = getFlags();

    if (lastTriggerVersion !== version) {
      await fillTriggers();
    }
    if (!triggerSampleMap.size) {
      await fillTriggers();
    }
    const relpath = (await resolveSampleRelpath(version, triggerValue)) || '';
    if (!relpath) {
      console.warn('standalone-pipeline: no sample for trigger', triggerValue, 'version', version);
      return;
    }
    try {
      const text = await fetchText(
        urlFor('sample', {
          relpath,
          seed: seed ? '1' : undefined,
          enrich: enrich ? '1' : undefined,
        })
      );
      const output = $1(document, '#gen-output');
      if (output) {
        output.textContent = repeatMessage(text, count);
      }
    } catch (err) {
      console.warn('standalone-pipeline: sample fetch failed', err);
    }
    toggleAllActionTrays();
  }

  function ensureInteropHelpers() {
    window.InteropUI = window.InteropUI || {};
    window.InteropUI.copyFrom = function copyFrom(fromSelector, toSelector) {
      try {
        const src = $1(document, fromSelector);
        const dest = $1(document, toSelector);
        if (!src || !dest) return;
        const text = src.tagName === 'PRE' ? src.textContent : src.value ?? src.textContent ?? '';
        dest.value = (text || '').trim();
        dest.dispatchEvent(new Event('input', { bubbles: true }));
      } catch (err) {
        console.warn('standalone-pipeline: copyFrom failed', err);
      }
    };
    window.InteropUI.loadFileIntoTextarea = function loadFile(inputId, targetId) {
      try {
        const input = typeof inputId === 'string' ? $1(document, `#${inputId}`) : inputId;
        const textarea = typeof targetId === 'string' ? $1(document, `#${targetId}`) : targetId;
        const file = input?.files?.[0];
        if (!file || !textarea) return;
        const reader = new FileReader();
        reader.onload = () => {
          textarea.value = reader.result || '';
          textarea.dispatchEvent(new Event('input', { bubbles: true }));
        };
        reader.readAsText(file);
      } catch (err) {
        console.warn('standalone-pipeline: loadFileIntoTextarea failed', err);
      }
    };
  }

  function extractMessage(container) {
    if (!container) return '';
    const pre = container.querySelector('pre');
    if (pre?.textContent) return pre.textContent.trim();
    return (container.textContent || '').trim();
  }

  function hasMessageLike(text) {
    const value = (text || '').trim();
    return value.startsWith('MSH');
  }

  function toggleActionTrayFor(trayEl) {
    if (!trayEl) return;
    const sourceSelector = trayEl.getAttribute('data-source') || '#gen-output';
    const sourceNode = $1(document, sourceSelector);
    const text = extractMessage(sourceNode);
    if (hasMessageLike(text) || (text && text.trim().length)) {
      trayEl.classList.add('visible');
    } else {
      trayEl.classList.remove('visible');
    }
  }

  function toggleAllActionTrays() {
    $$(document, '.action-tray').forEach((tray) => toggleActionTrayFor(tray));
  }

  function setReportPlaceholder(container, text) {
    if (!container) return;
    container.innerHTML = '';
    const note = document.createElement('p');
    note.className = 'muted small';
    note.textContent = text;
    container.appendChild(note);
  }

  function populateDeidReportForm() {
    const form = $1(document, '#deid-report-form');
    if (!form) return null;
    const message = $1(document, '#deid-msg')?.value || '';
    const template = $1(document, '#deid-template')?.value || '';
    const textField = form.querySelector('#deid-report-text');
    const tplField = form.querySelector('#deid-report-template');
    if (textField) textField.value = message;
    if (tplField) tplField.value = template;
    return { message };
  }

  function refreshDeidReport({ auto = false } = {}) {
    const form = $1(document, '#deid-report-form');
    const container = $1(document, '#deid-report');
    if (!form || !container || !window.htmx) return;
    const info = populateDeidReportForm();
    if (!info) return;
    const hasRequired = info.message.trim();
    if (!hasRequired) {
      if (!auto) {
        setReportPlaceholder(container, 'Run De-identify to generate a processed-errors report.');
      }
      return;
    }
    window.htmx.trigger(form, 'submit');
  }

  function clearDeidReport() {
    const container = $1(document, '#deid-report');
    setReportPlaceholder(container, 'Processed-errors coverage will appear after you run De-identify.');
    ['#deid-filter-seg', '#deid-filter-action', '#deid-filter-param'].forEach((sel) => {
      const input = $1(document, sel);
      if (input) input.value = '';
    });
    ['#deid-report-seg', '#deid-report-action', '#deid-report-parameter', '#deid-report-status'].forEach((sel) => {
      const hidden = $1(document, sel);
      if (hidden) hidden.value = '';
    });
    $$(document, '[data-role="deid-filter"]').forEach((chip) => chip.setAttribute('aria-pressed', 'false'));
  }

  function refreshValidateReport() {
    const form = $1(document, '#validate-form');
    if (!form || !window.htmx) return;
    const message = $1(document, '#validate-msg')?.value || '';
    if (!message.trim()) {
      clearValidateReport();
      return;
    }
    window.htmx.trigger(form, 'submit');
  }

  function clearValidateReport() {
    const container = $1(document, '#validate-report');
    setReportPlaceholder(container, 'Validation results will appear here after running Validate.');
    ['#val-filter-seg', '#val-filter-rule'].forEach((sel) => {
      const input = $1(document, sel);
      if (input) input.value = '';
    });
    ['#val-report-seg', '#val-report-rule', '#val-report-status'].forEach((sel) => {
      const hidden = $1(document, sel);
      if (hidden) hidden.value = '';
    });
    $$(document, '[data-role="val-filter"]').forEach((chip) => chip.setAttribute('aria-pressed', 'false'));
  }

  function wireDeidFilters() {
    document.addEventListener('click', (event) => {
      const chip = event.target.closest?.('[data-role="deid-filter"]');
      if (chip) {
        const key = chip.dataset.k;
        const value = chip.dataset.v;
        const active = chip.getAttribute('aria-pressed') === 'true';
        $$(document, `[data-role="deid-filter"][data-k="${key}"]`).forEach((node) =>
          node.setAttribute('aria-pressed', 'false')
        );
        chip.setAttribute('aria-pressed', active ? 'false' : 'true');
        const statusField = $1(document, '#deid-report-status');
        if (statusField) statusField.value = active ? '' : value || '';
        event.preventDefault();
        return;
      }

      if (event.target.matches('[data-role="deid-report-refresh"]')) {
        event.preventDefault();
        const seg = $1(document, '#deid-filter-seg')?.value || '';
        const action = $1(document, '#deid-filter-action')?.value || '';
        const param = $1(document, '#deid-filter-param')?.value || '';
        const segField = $1(document, '#deid-report-seg');
        if (segField) segField.value = seg;
        const actionField = $1(document, '#deid-report-action');
        if (actionField) actionField.value = action;
        const paramField = $1(document, '#deid-report-parameter');
        if (paramField) paramField.value = param;
        refreshDeidReport();
        return;
      }

      if (event.target.matches('[data-role="deid-report-clear"]')) {
        event.preventDefault();
        clearDeidReport();
      }
    });
  }

  function wireValFilters() {
    document.addEventListener('click', (event) => {
      const chip = event.target.closest?.('[data-role="val-filter"]');
      if (chip) {
        const key = chip.dataset.k;
        const value = chip.dataset.v;
        const active = chip.getAttribute('aria-pressed') === 'true';
        $$(document, `[data-role="val-filter"][data-k="${key}"]`).forEach((node) =>
          node.setAttribute('aria-pressed', 'false')
        );
        chip.setAttribute('aria-pressed', active ? 'false' : 'true');
        const statusField = $1(document, '#val-report-status');
        if (statusField) statusField.value = active ? '' : value || '';
        event.preventDefault();
        return;
      }

      if (event.target.matches('[data-role="validate-report-refresh"]')) {
        event.preventDefault();
        const seg = $1(document, '#val-filter-seg')?.value || '';
        const rule = $1(document, '#val-filter-rule')?.value || '';
        const segField = $1(document, '#val-report-seg');
        if (segField) segField.value = seg;
        const ruleField = $1(document, '#val-report-rule');
        if (ruleField) ruleField.value = rule;
        refreshValidateReport();
        return;
      }

      if (event.target.matches('[data-role="validate-report-clear"]')) {
        event.preventDefault();
        clearValidateReport();
      }
    });
  }

  function attachOutputObservers() {
    const observe = (selector) => {
      const node = $1(document, selector);
      if (!node) return;
      const observer = new MutationObserver(() => toggleAllActionTrays());
      observer.observe(node, { childList: true, subtree: true, characterData: true });
    };
    ['#gen-output', '#deid-output', '#validate-output', '#mllp-output', '#pipeline-output'].forEach(observe);
  }

  function getSourceText(selector) {
    const node = selector ? $1(document, selector) : null;
    if (!node) return '';
    if (node.tagName === 'PRE') {
      return (node.textContent || '').trim();
    }
    const pre = node.querySelector?.('pre');
    if (pre) {
      return (pre.textContent || '').trim();
    }
    if (typeof node.value === 'string') {
      return node.value.trim();
    }
    return (node.textContent || '').trim();
  }

  function attachActionTrayHandlers() {
    document.body?.addEventListener('click', (event) => {
      const button = event.target.closest?.('.action-tray .action-card');
      if (!button) return;
      event.preventDefault();
      const tray = button.closest('.action-tray');
      const action = button.getAttribute('data-action');
      if (!action) return;
      const source = tray?.getAttribute('data-source') || '#gen-output';
      const text = getSourceText(source);
      if (!text || !text.trim()) return;

      const stage = tray?.getAttribute('data-stage') || '';
      let collapseFrom = '';
      if (stage === 'gen') collapseFrom = 'generate';
      else if (stage === 'deid') collapseFrom = 'deid';
      else if (stage === 'validate') collapseFrom = 'validate';
      else if (stage === 'pipeline') collapseFrom = 'pipeline';

      activateModule(action, text, { collapseFrom });
    });
  }

  let navHandlersBound = false;
  let moduleNavBound = false;

  function attachModuleNavHandlers() {
    if (moduleNavBound) return;
    document.addEventListener('click', (event) => {
      const nav = event.target.closest?.('.module-btn');
      if (!nav) return;
      const href = nav.getAttribute('href') || '';
      if (!href.startsWith('#')) return;
      const targetId = href.slice(1);
      if (!panelEntries.some(([, id]) => id === targetId)) return;
      event.preventDefault();
      collapseAllExcept(targetId);
      expandPanel(targetId);
      scrollPanelIntoView(targetId);
    });
    moduleNavBound = true;
  }

  function attachStandaloneCardNavigation() {
    if (navHandlersBound) return;
    document.addEventListener('click', (event) => {
      const button = event.target.closest?.('.action-card');
      if (!button) return;
      if (button.closest('.action-tray')) return;
      const action = button.dataset?.action;
      if (!action || !ACTION_TARGETS[action]) return;
      event.preventDefault();
      activateModule(action, '', {});
    });
    navHandlersBound = true;
  }

  function onReady() {
    ensureInteropHelpers();
    fillTriggers();

    $1(document, '#std-version')?.addEventListener('change', () => {
      fillTriggers();
    });
    const triggerInputEl = $1(document, `#${TRIGGER_INPUT_ID}`);
    if (triggerInputEl) {
      triggerInputEl.addEventListener('change', () => {
        if (!triggerSampleMap.size) {
          fillTriggers();
        }
      });
    }
    $1(document, '#std-load-sample')?.addEventListener('click', loadSample);
    toggleAllActionTrays();
    attachOutputObservers();
    attachModuleNavHandlers();
    attachActionTrayHandlers();
    attachStandaloneCardNavigation();
    setupValidateForm();
    wireDeidFilters();
    wireValFilters();
    clearDeidReport();
    clearValidateReport();
  }

  function setupValidateForm() {
    const form = $1(document, '#validate-form');
    if (!form) return;
    form.addEventListener('submit', () => {
      const message = $1(form, 'textarea[name="message"]')?.value || '';
      const output = $1(document, '#validate-output');
      if (output) {
        output.textContent = message.trim();
      }
      toggleAllActionTrays();
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    try {
      toggleAllActionTrays();
      attachOutputObservers();
    } catch (err) {
      console.warn('standalone-pipeline: init failed', err);
    }
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', onReady);
  } else {
    onReady();
  }

  document.body?.addEventListener('htmx:afterSwap', (evt) => {
    toggleAllActionTrays();
    const targetId = evt?.target?.id || '';
    if (targetId === 'deid-output') {
      refreshDeidReport({ auto: true });
    }
  });
})();
