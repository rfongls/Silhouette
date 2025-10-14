(function () {
  const urls = window.STANDALONE_PIPELINE_URLS || {};
  const $1 = (root, selector) => (root || document).querySelector(selector);
  const $$ = (root, selector) => Array.from((root || document).querySelectorAll(selector));

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

  async function fillTriggers() {
    const select = $1(document, '#std-version');
    const datalist = $1(document, '#std-trigger-dl');
    if (!select || !datalist) return;
    const version = select.value || 'hl7-v2-4';
    try {
      const data = await fetchJSON(urlFor('triggers', { version }));
      const items = (data?.items || [])
        .map((item) => (typeof item === 'string' ? item : item?.trigger || ''))
        .filter(Boolean);
      datalist.innerHTML = items.map((item) => `<option value="${escapeHtml(item)}"></option>`).join('');
    } catch (err) {
      console.warn('standalone-pipeline: trigger load failed', err);
    }
  }

  async function fillSamples() {
    const select = $1(document, '#std-sample');
    const versionEl = $1(document, '#std-version');
    if (!select) return;
    const version = versionEl?.value || 'hl7-v2-4';
    try {
      const data = await fetchJSON(urlFor('samples', { version }));
      const items = data?.items || [];
      const options = items.map((item) => {
        if (typeof item === 'string') {
          return { value: item, label: item, relpath: item, name: item };
        }
        const relpath = item?.relpath || '';
        const name = item?.name || '';
        const label = item?.trigger
          ? `${item.trigger}${item.description ? ' — ' + item.description : ''}`
          : name || relpath;
        return {
          value: relpath || name,
          label: label || relpath || name,
          relpath,
          name,
        };
      });
      select.innerHTML = ['<option value="">— Select a sample —</option>']
        .concat(
          options.map((opt) =>
            `<option value="${escapeHtml(opt.value)}" data-relpath="${escapeHtml(opt.relpath)}" data-name="${escapeHtml(opt.name)}">${escapeHtml(opt.label)}</option>`,
          ),
        )
        .join('');
    } catch (err) {
      console.warn('standalone-pipeline: sample list failed', err);
    }
  }

  async function loadSample() {
    const select = $1(document, '#std-sample');
    if (!select) return;
    const option = select.selectedOptions?.[0];
    const relpath = option?.dataset?.relpath || select.value || '';
    const name = option?.dataset?.name || '';
    if (!relpath && !name) return;
    try {
      let text = '';
      let lastError = null;
      if (relpath) {
        try {
          text = await fetchText(urlFor('sample', { relpath }));
        } catch (err) {
          lastError = err;
        }
      }
      if ((!text || !text.trim()) && name) {
        try {
          text = await fetchText(urlFor('sample', { name }));
        } catch (err) {
          lastError = err;
        }
      }
      const output = $1(document, '#gen-output');
      if (output) {
        output.textContent = text || '';
      }
      if (!text && lastError) {
        throw lastError;
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
    if (hasMessageLike(text)) {
      trayEl.classList.add('visible');
    } else {
      trayEl.classList.remove('visible');
    }
  }

  function toggleAllActionTrays() {
    $$(document, '.action-tray').forEach((tray) => toggleActionTrayFor(tray));
  }

  function attachOutputObservers() {
    const observe = (selector) => {
      const node = $1(document, selector);
      if (!node) return;
      const observer = new MutationObserver(() => toggleAllActionTrays());
      observer.observe(node, { childList: true, subtree: true, characterData: true });
    };
    ['#gen-output', '#deid-output', '#pipeline-output'].forEach(observe);
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
      const source = tray?.getAttribute('data-source') || '#gen-output';
      const text = getSourceText(source);
      if (!hasMessageLike(text)) return;

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

  function onReady() {
    ensureInteropHelpers();
    fillTriggers();
    fillSamples();

    $1(document, '#std-version')?.addEventListener('change', () => {
      fillTriggers();
      fillSamples();
    });
    $1(document, '#std-load-sample')?.addEventListener('click', loadSample);
    $1(document, '#pipe-transport')?.addEventListener('change', updateTransportVisibility);

    updateTransportVisibility();
    toggleAllActionTrays();
    attachOutputObservers();
    attachActionTrayHandlers();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', onReady);
  } else {
    onReady();
  }

  document.body?.addEventListener('htmx:afterSwap', (evt) => {
    toggleAllActionTrays();
    autoSendPipelineResult(evt);
  });
})();
