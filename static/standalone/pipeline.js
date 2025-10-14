(function () {
  const urls = window.STANDALONE_PIPELINE_URLS || {};
  const $1 = (root, selector) => (root || document).querySelector(selector);

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
      const items = (data?.items || []).map((item) => item.trigger || '').filter(Boolean);
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
      select.innerHTML = ['<option value="">— Select a sample —</option>']
        .concat(
          items.map((item) => {
            const rel = item.relpath || '';
            const label = item.trigger ? `${item.trigger}${item.description ? ' — ' + item.description : ''}` : rel;
            return `<option value="${escapeHtml(rel)}">${escapeHtml(label)}</option>`;
          }),
        )
        .join('');
    } catch (err) {
      console.warn('standalone-pipeline: sample list failed', err);
    }
  }

  async function loadSample() {
    const select = $1(document, '#std-sample');
    if (!select) return;
    const relpath = select.value;
    if (!relpath) return;
    try {
      const text = await fetchText(urlFor('sample', { relpath }));
      const output = $1(document, '#gen-output');
      if (output) {
        output.textContent = text || '';
      }
    } catch (err) {
      console.warn('standalone-pipeline: sample fetch failed', err);
    }
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
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', onReady);
  } else {
    onReady();
  }

  document.body?.addEventListener('htmx:afterSwap', autoSendPipelineResult);
})();
