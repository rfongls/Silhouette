// static/js/pipeline_tray.js
// Show "Run next pipeline" trays per panel when that panel has output.
(() => {
  'use strict';

  const DOC = document;
  const qs  = (s, r = DOC) => r.querySelector(s);
  const qsa = (s, r = DOC) => Array.from(r.querySelectorAll(s));

  const PANEL_SELECTORS = {
    generate: ['#generate-panel', '#card-gen', '[data-panel="generate"]', '.interop-panel-generate'],
    deid: ['#deid-panel', '#card-deid', '[data-panel="deid"]', '.interop-panel-deid'],
    validate: ['#validate-panel', '#card-validate', '[data-panel="validate"]', '.interop-panel-validate'],
    mllp: ['#mllp-panel', '#card-mllp', '[data-panel="mllp"]', '.interop-panel-mllp']
  };

  const PANELS = {
    generate: {
      tray: 'gen-run-tray',
      outputs: ['#gen-output', '[data-role="gen-output"]', '#generated-message', '#hl7-output', '.gen-output', 'textarea[name="gen-output"]', 'textarea[name="message"]']
    },
    deid: {
      tray: 'deid-run-tray',
      outputs: ['#deid-output', '[data-role="deid-output"]', '#deidentify-output', 'pre', '.deid-output']
    },
    validate: {
      tray: 'validate-run-tray',
      outputs: ['#validate-output', '#val-output', '[data-role="validate-output"]', 'pre', '.validate-output']
    },
    mllp: {
      tray: 'mllp-run-tray',
      outputs: ['#mllp-output', '#ack-output', '[data-role="ack-output"]', 'pre', '.mllp-output']
    }
  };

  function hasText(el) {
    if (!el) return false;
    if ('value' in el) return !!String(el.value).trim();
    return !!String(el.textContent).trim();
  }

  function findFirst(root, sels) {
    if (!root) return null;
    for (const sel of sels) {
      try {
        const el = root.querySelector(sel);
        if (el) return el;
      } catch (_) {}
    }
    return root.querySelector('textarea, pre, code, output');
  }

  function resolvePanelEl(key) {
    const sels = PANEL_SELECTORS[key] || [];
    for (const sel of sels) {
      const el = qs(sel);
      if (el) return el;
    }
    return null;
  }

  function setTrayVisible(panelKey, on) {
    const cfg  = PANELS[panelKey];
    const wrap = resolvePanelEl(panelKey);
    if (!cfg || !wrap) return;
    let tray = wrap.querySelector(`#${cfg.tray}`) || wrap.querySelector('[data-role="gen-run-tray"], .action-tray');
    if (!tray) {
      tray = qs(`#${cfg.tray}`);
    }
    if (!tray) return;
    tray.hidden = !on;
    tray.classList.toggle('visible', !!on);
  }

  function watchPanel(panelKey) {
    const cfg = PANELS[panelKey];
    const root = resolvePanelEl(panelKey);
    if (!cfg || !root) return;

    setTrayVisible(panelKey, false);

    const out = findFirst(root, cfg.outputs);
    if (out) {
      if ('value' in out) {
        out.addEventListener('input', () => setTrayVisible(panelKey, hasText(out)));
      }
      if (typeof MutationObserver !== 'undefined') {
        new MutationObserver(() => setTrayVisible(panelKey, hasText(out)))
          .observe(out, { childList: true, characterData: true, subtree: true });
      }
    }

    const triggers = qsa('[data-action="generate"], [data-action="deidentify"], [data-action="validate"], [data-action="mllp-send"]', root);
    triggers.forEach(btn => btn.addEventListener('click', () => {
      setTimeout(() => setTrayVisible(panelKey, hasText(findFirst(resolvePanelEl(panelKey), cfg.outputs))), 50);
      setTimeout(() => setTrayVisible(panelKey, hasText(findFirst(resolvePanelEl(panelKey), cfg.outputs))), 500);
      setTimeout(() => setTrayVisible(panelKey, hasText(findFirst(resolvePanelEl(panelKey), cfg.outputs))), 1500);
    }));
  }

  function init() {
    Object.keys(PANELS).forEach(watchPanel);

    if (window.InteropUI) {
      const IU = window.InteropUI;
      const wrap = (fn, panelKey) => (...args) => {
        try { setTrayVisible(panelKey, true); } catch (_) {}
        return fn ? fn.apply(IU, args) : undefined;
      };
      if (typeof IU.onGenerateComplete === 'function') IU.onGenerateComplete = wrap(IU.onGenerateComplete, 'generate');
      if (typeof IU.onDeidentifyComplete === 'function') IU.onDeidentifyComplete = wrap(IU.onDeidentifyComplete, 'deid');
      if (typeof IU.onValidateComplete === 'function') IU.onValidateComplete = wrap(IU.onValidateComplete, 'validate');
      if (typeof IU.onMllpComplete === 'function') IU.onMllpComplete = wrap(IU.onMllpComplete, 'mllp');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
