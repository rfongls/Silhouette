// static/js/pipeline_tray.js
// Pipeline payload helpers: capture tray clicks, move text between panels, reveal trays.
(() => {
  'use strict';
  const D = document;
  const $ = (selector, root = D) => root.querySelector(selector);
  const $$ = (selector, root = D) => Array.from(root.querySelectorAll(selector));

  const PANELS = {
    samples:  { panel: 'samples-panel',  outputs: ['.codepane', '#sample-preview'] },
    generate: { panel: 'generate-panel', outputs: ['#gen-output', '[data-role="gen-output"]', 'textarea[name="message"]', 'pre', '.gen-output'] },
    deid:     { panel: 'deid-panel',     outputs: ['#deid-output', '[data-role="deid-output"]', '#deidentify-output', 'pre', '.deid-output'] },
    validate: { panel: 'validate-panel',  outputs: ['#validate-output', '#validation-results', '[data-role="validate-output"]', '.validate-output', 'pre'] },
    translate:{ panel: 'translate-panel', outputs: ['#translate-output', '.translate-output', 'pre', 'code'] },
    mllp:     { panel: 'mllp-panel',      outputs: ['#ack-output', '#mllp-output', '.mllp-output', 'pre'] },
    pipeline: { panel: 'pipeline-panel',  outputs: [] }
  };
  const PANEL_IDS = new Set(Object.values(PANELS).map(p => p.panel));

  function panelIdFromKey(key) {
    if (!key) return null;
    const raw = String(key).trim();
    if (!raw) return null;
    if (PANELS[raw]) return PANELS[raw].panel;
    if (PANELS[raw.replace(/-panel$/, '')]) return PANELS[raw.replace(/-panel$/, '')].panel;
    if (raw.endsWith('-panel')) return raw;
    return raw;
  }

  function keyFromPanelId(panelId) {
    const entry = Object.entries(PANELS).find(([, meta]) => meta.panel === panelId);
    return entry ? entry[0] : null;
  }

  function findPanel(el) {
    return el.closest('.panel') || el.closest('[id$="-panel"]');
  }

  function keyFromElement(el) {
    const panel = findPanel(el);
    return panel ? keyFromPanelId(panel.id) : null;
  }

  function findOutput(key) {
    const pid = panelIdFromKey(key);
    if (!pid) return null;
    const wrap = D.getElementById(pid);
    if (!wrap) return null;
    const selectors = (PANELS[key]?.outputs) || [];
    for (const sel of selectors) {
      const node = $(sel, wrap);
      if (node) return node;
    }
    return $('textarea,pre,code,output', wrap);
  }

  function textOf(el) {
    if (!el) return '';
    if ('value' in el) return String(el.value || '').trim();
    return String(el.textContent || '').trim();
  }

  function revealTrayFor(key) {
    const pid = panelIdFromKey(key);
    if (!pid) return;
    const wrap = D.getElementById(pid);
    if (!wrap) return;
    const tray = $('.action-tray', wrap);
    if (!tray) return;
    tray.hidden = false;
    tray.classList.add('visible');
  }

  function prefillTarget(targetKey, text) {
    const pid = panelIdFromKey(targetKey);
    if (!pid) return;
    const wrap = D.getElementById(pid);
    if (!wrap) return;

    const candidatesByKey = {
      validate: ['#validate-input', 'textarea[name="validate-message"]', '.validate-input', 'textarea'],
      mllp:     ['#mllp-input', 'textarea[name="mllp-message"]', '.mllp-input', 'textarea'],
      translate:['#translate-input', 'textarea[name="translate-message"]', '.translate-input', 'textarea']
    };
    const candidates = candidatesByKey[targetKey] || ['textarea', '.codepane', 'pre'];

    let input = null;
    for (const selector of candidates) {
      input = $(selector, wrap);
      if (input) break;
    }
    if (!input) {
      const fallback = $('.codepane', wrap) || wrap;
      fallback.textContent = text;
      return;
    }
    if ('value' in input) {
      input.value = text;
      input.dispatchEvent(new Event('input', { bubbles: true }));
    } else {
      input.textContent = text;
    }
  }

  function goToPanel(key, { scroll = true } = {}) {
    const pid = panelIdFromKey(key);
    if (!pid) return;
    if (window.InteropUI?.setActivePanel) {
      window.InteropUI.setActivePanel(pid);
    }
    if (scroll) {
      const target = D.getElementById(pid);
      if (target) {
        try {
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } catch (_) {
          /* ignore scroll issues */
        }
      }
    }
  }

  window.InteropUI = window.InteropUI || {};
  if (typeof window.InteropUI.goToPanel !== 'function') {
    window.InteropUI.goToPanel = goToPanel;
  }

  D.addEventListener('click', (event) => {
    const card = event.target.closest('[data-run-to],[data-run],[data-target-panel],[data-panel],.pipeline-run');
    if (!card) return;

    const runTarget = card.getAttribute('data-run-to') || card.getAttribute('data-run') || card.dataset.next || card.dataset.action || card.getAttribute('data-target-panel') || card.getAttribute('data-panel');
    if (!runTarget) return;

    const rawKey = String(runTarget).replace(/^next-/, '').trim();
    if (!rawKey) return;
    const normalizedKey = rawKey.replace(/-panel$/, '');
    const destKey = normalizedKey === 'fhir' ? 'translate' : normalizedKey;
    if (!PANELS[destKey] && destKey !== 'pipeline') return;

    const srcKey = keyFromElement(card) || keyFromPanelId(window.InteropUI?.currentPanel || '') || null;
    const sourceOutput = srcKey && findOutput(srcKey);
    const payload = textOf(sourceOutput);

    if (payload && window.PipelineBus?.set) {
      window.PipelineBus.set(srcKey, payload, { from: srcKey });
    }

    if (payload) {
      prefillTarget(destKey, payload);
      revealTrayFor(destKey);
    }
  });

  D.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    const card = event.target.closest('[data-run-to]');
    if (!card) return;
    if (card.tagName === 'BUTTON' || card.tagName === 'A') return;
    event.preventDefault();
    card.click();
  });

  function watchOutput(key) {
    const out = findOutput(key);
    if (!out) return;
    const update = () => {
      if (textOf(out)) revealTrayFor(key);
    };
    if ('value' in out) {
      out.addEventListener('input', update);
    }
    new MutationObserver(update).observe(out, { childList: true, characterData: true, subtree: true });
  }

  ['generate', 'deid', 'validate', 'mllp', 'translate'].forEach(watchOutput);
})();
