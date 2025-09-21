// static/js/pipeline_tray.js
(() => {
  'use strict';
  const D = document;
  const $ = (s, r = D) => r.querySelector(s);
  const $$ = (s, r = D) => Array.from(r.querySelectorAll(s));

  const PANELS = {
    generate: {
      panel: 'generate-panel',
      outputs: ['#gen-output', '[data-role="gen-output"]', 'textarea[name="message"]', 'pre', '.gen-output']
    },
    deid: {
      panel: 'deid-panel',
      outputs: ['#deid-output', '[data-role="deid-output"]', '#deidentify-output', 'pre', '.deid-output']
    },
    validate: {
      panel: 'validate-panel',
      outputs: ['#validate-output', '#validation-results', '[data-role="validate-output"]', 'pre']
    },
    mllp: {
      panel: 'mllp-panel',
      outputs: ['#ack-output', '#mllp-output', '[data-role="ack-output"]', 'pre']
    }
  };

  function findPanel(el) {
    return el?.closest('.panel') || el?.closest('[id$="-panel"]') || null;
  }

  function panelKeyFromEl(el) {
    const wrap = findPanel(el);
    const id = wrap?.id || '';
    return id.replace(/-panel$/, '');
  }

  function textOf(el) {
    if (!el) return '';
    if ('value' in el) return String(el.value || '').trim();
    return String(el.textContent || '').trim();
  }

  function findOutput(key) {
    const cfg = PANELS[key];
    if (!cfg) return null;
    const wrap = $('#' + cfg.panel);
    if (!wrap) return null;
    for (const selector of cfg.outputs) {
      const candidate = $(selector, wrap);
      if (candidate) return candidate;
    }
    return $('textarea,pre,code,output', wrap);
  }

  function revealTray(key) {
    const cfg = PANELS[key];
    if (!cfg) return;
    const wrap = $('#' + cfg.panel);
    if (!wrap) return;
    const tray = $('.action-tray', wrap);
    if (!tray) return;
    tray.hidden = false;
    tray.classList.add('visible');
  }

  function showPanel(key) {
    if (window.InteropUI?.panelManager?.showPanel) {
      window.InteropUI.panelManager.showPanel(PANELS[key]?.panel);
      return;
    }
    $$('.panel').forEach((panel) => panel.classList.remove('active'));
    $('#' + PANELS[key]?.panel)?.classList.add('active');
  }

  function prefillTarget(key, text) {
    const wrap = $('#' + PANELS[key]?.panel);
    if (!wrap) return;
    const candidates = {
      validate: ['#validate-input', '#val-text', 'textarea[name="validate-message"]', 'textarea', '.validate-input'],
      mllp: ['#mllp-input', '#mllp-messages', 'textarea[name="mllp-message"]', 'textarea', '.mllp-input'],
      translate: ['#translate-input', 'textarea[name="translate-message"]', 'textarea', '.translate-input']
    }[key] || ['textarea'];
    let input = null;
    for (const selector of candidates) {
      input = $(selector, wrap);
      if (input) break;
    }
    if (input && 'value' in input) {
      input.value = text;
    } else if (wrap) {
      (wrap.querySelector('.codepane') || wrap).textContent = text;
    }
  }

  D.addEventListener('click', (event) => {
    const card = event.target.closest('.action-card');
    if (!card) return;
    const action = card.dataset.next || card.dataset.action;
    if (!action) return;

    const norm = String(action).replace(/^next-/, '');
    if (!['validate', 'mllp', 'fhir', 'translate'].includes(norm)) return;

    const sourceKey = panelKeyFromEl(card);
    const output = findOutput(sourceKey);
    const payload = textOf(output);
    if (!payload) return;

    event.preventDefault();

    if (window.PipelineBus?.set) {
      window.PipelineBus.set(sourceKey, payload, { from: sourceKey });
    }

    const targetKey = norm === 'fhir' ? 'translate' : norm;
    showPanel(targetKey);
    prefillTarget(targetKey, payload);
    revealTray(targetKey);
  });

  function watch(key) {
    const output = findOutput(key);
    if (!output) return;
    const update = () => {
      if (textOf(findOutput(key))) {
        revealTray(key);
      }
    };
    if ('value' in output) {
      output.addEventListener('input', update);
    }
    new MutationObserver(update).observe(output, {
      childList: true,
      characterData: true,
      subtree: true
    });
  }

  const init = () => {
    ['generate', 'deid', 'validate', 'mllp'].forEach(watch);
  };

  if (D.readyState === 'loading') {
    D.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
