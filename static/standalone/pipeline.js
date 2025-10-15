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
    const output = $1(document, '#deid-output')?.textContent || '';
    const template = $1(document, '#deid-template')?.value || '';
    const textField = form.querySelector('#deid-report-text');
    const afterField = form.querySelector('#deid-report-after');
    const tplField = form.querySelector('#deid-report-template');
    if (textField) textField.value = message;
    if (afterField) afterField.value = output;
    if (tplField) tplField.value = template;
    return { message, output };
  }

  function refreshDeidReport({ auto = false } = {}) {
    const form = $1(document, '#deid-report-form');
    const container = $1(document, '#deid-report');
    if (!form || !container || !window.htmx) return;
    const info = populateDeidReportForm();
    if (!info) return;
    const hasRequired = info.message.trim() && info.output.trim();
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

  function autoSendPipelineResult(evt) {
    if (!evt?.target || evt.target.id !== 'pipeline-output') return;
    const auto = $1(document, '#pipe-mllp-auto');
    if (auto && !auto.checked) return;
    const transport = $1(document, '#pipe-transport');
    if (transport && (transport.value || '').toLowerCase() !== 'mllp') return;
    const text = extractMessage(evt.target);
    if (!text || !text.startsWith('MSH')) return;
    const textarea = $1(document, '#mllp-msg');
    if (textarea) {
      textarea.value = text;
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
    }
    const form = $1(document, '#mllp-form');
    if (form && window.htmx) {
      try {
        $1(document, '#mllp-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } catch (err) {
        console.debug('standalone-pipeline: scroll failed', err);
      }
      window.htmx.trigger(form, 'submit');
    }
  }

  function updateTransportVisibility() {
    const select = $1(document, '#pipe-transport');
    const config = $1(document, '#pipe-mllp-config');
    if (!select || !config) return;
    const shouldShow = (select.value || '').toLowerCase() === 'mllp';
    config.style.display = shouldShow ? 'flex' : 'none';
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

  function submitForm(form, textarea, text) {
    if (!form || !textarea) return;
    textarea.value = text;
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
    try {
      form.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
      console.debug('standalone-pipeline: scroll failed', err);
    }
    if (window.htmx) {
      window.htmx.trigger(form, 'submit');
    }
  }

  function attachActionTrayHandlers() {
    document.body?.addEventListener('click', (event) => {
      const button = event.target.closest?.('.action-tray .action-card');
      if (!button) return;
      const tray = button.closest('.action-tray');
      const action = button.getAttribute('data-action');
      if (!action) return;
      const source = tray?.getAttribute('data-source') || '#gen-output';
      const text = getSourceText(source);
      if (!hasMessageLike(text)) return;

      const fromPanelId = tray?.closest('[id]')?.id;
      const fromKey = panelKeyFromId(fromPanelId);

      activateModule(action, text, { collapseFrom: fromKey });

      if (action === 'validate') {
        const form = $1(document, '#validate-form');
        const textarea = form?.querySelector('textarea[name="message"]');
        submitForm(form, textarea, text);
        return;
      }

      if (action === 'mllp') {
        const form = $1(document, '#mllp-form');
        const textarea = $1(document, '#mllp-msg');
        submitForm(form, textarea, text);
        return;
      }

      if (action === 'pipeline') {
        const form = $1(document, '#pipeline-form');
        const textarea = form?.querySelector('textarea[name="text"]');
        submitForm(form, textarea, text);
      }
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
    $1(document, '#pipe-transport')?.addEventListener('change', updateTransportVisibility);

    updateTransportVisibility();
    toggleAllActionTrays();
    attachOutputObservers();
    attachModuleNavHandlers();
    attachActionTrayHandlers();
    attachStandaloneCardNavigation();
    setupValidateForm();
    setupReportButtons();
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

  function setupReportButtons() {
    document.body?.addEventListener('click', (event) => {
      const refreshDeid = event.target.closest?.('[data-role="deid-report-refresh"]');
      if (refreshDeid) {
        event.preventDefault();
        refreshDeidReport();
        return;
      }
      const clearDeid = event.target.closest?.('[data-role="deid-report-clear"]');
      if (clearDeid) {
        event.preventDefault();
        clearDeidReport();
        return;
      }
      const refreshValidate = event.target.closest?.('[data-role="validate-report-refresh"]');
      if (refreshValidate) {
        event.preventDefault();
        refreshValidateReport();
        return;
      }
      const clearValidate = event.target.closest?.('[data-role="validate-report-clear"]');
      if (clearValidate) {
        event.preventDefault();
        clearValidateReport();
      }
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
    autoSendPipelineResult(evt);
    const targetId = evt?.target?.id || '';
    if (targetId === 'deid-output') {
      refreshDeidReport({ auto: true });
    }
  });
})();
