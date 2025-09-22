// static/js/pipeline_bus.js
(() => {
  'use strict';
  const D = document;
  const $$ = (selector, root = D) => Array.from(root.querySelectorAll(selector));
  const $ = (selector, root = D) => root.querySelector(selector);

  const PipelineBus = window.PipelineBus || {
    payload: null,
    set(stage, text, meta = {}) {
      this.payload = { stage, text: String(text || ''), meta, ts: Date.now() };
    },
    take() {
      const current = this.payload;
      this.payload = null;
      return current;
    },
    peek() {
      return this.payload;
    }
  };
  window.PipelineBus = PipelineBus;

  const NAME_MAP = {
    samples: 'samples-panel',
    generate: 'generate-panel',
    deid: 'deid-panel',
    'de-identify': 'deid-panel',
    deidentify: 'deid-panel',
    validate: 'validate-panel',
    translate: 'translate-panel',
    fhir: 'translate-panel',
    'hl7-to-fhir': 'translate-panel',
    mllp: 'mllp-panel',
    send: 'mllp-panel',
    'send-mllp': 'mllp-panel',
    pipeline: 'pipeline-panel'
  };

  function toPanelId(name) {
    if (!name) return null;
    const raw = String(name).trim();
    if (!raw) return null;
    const lowered = raw.toLowerCase();
    if (NAME_MAP[lowered]) return NAME_MAP[lowered];
    if (lowered.endsWith('-panel')) return lowered;
    return `${lowered}-panel`;
  }

  function hideAllTrays() {
    $$('.action-tray').forEach((tray) => {
      tray.classList.remove('visible');
      if ('hidden' in tray) tray.hidden = true;
    });
  }

  function getCurrentPanel() {
    return window.InteropUI?.panelManager?.currentPanel
      || window.InteropUI?.currentPanel
      || $$('.module-btn.active[data-panel]')[0]?.dataset.panel
      || null;
  }

  function applyPanelState(panelId) {
    if (!panelId) return;
    const panels = $$('.panel');
    panels.forEach((panel) => {
      const active = panel.id === panelId;
      panel.classList.toggle('active', active);
      if ('hidden' in panel) {
        panel.hidden = !active;
      }
      if (active) {
        const parentDetails = panel.closest('details');
        if (parentDetails && typeof parentDetails.open === 'boolean') {
          parentDetails.open = true;
        }
      }
    });

    const targetPanel = D.getElementById(panelId);
    if (targetPanel && 'hidden' in targetPanel) {
      targetPanel.hidden = false;
    }

    $$('.module-btn').forEach((btn) => {
      const active = btn.dataset.panel === panelId;
      btn.classList.toggle('active', active);
      if (btn.dataset.panel) {
        btn.setAttribute('aria-expanded', String(active));
        btn.setAttribute('aria-controls', btn.dataset.panel);
      }
      btn.setAttribute('aria-current', active ? 'page' : 'false');
      if (active) {
        btn.classList.remove('completed');
      }
    });

    hideAllTrays();

    window.InteropUI = window.InteropUI || {};
    window.InteropUI.currentPanel = panelId;
  }

  function setActivePanel(name) {
    const panelId = toPanelId(name);
    if (!panelId) return;

    const manager = window.InteropUI?.panelManager;
    if (manager) {
      if (typeof manager.runPipeline === 'function') {
        try {
          manager.runPipeline(panelId);
        } catch (err) {
          /* ignore legacy errors */
        }
      } else if (typeof manager.showPanel === 'function') {
        try {
          manager.showPanel(panelId);
        } catch (err) {
          /* ignore legacy errors */
        }
      }
    }

    applyPanelState(panelId);

    return panelId;
  }

  function markCurrentCompleted() {
    const current = getCurrentPanel();
    if (!current) return;
    const chip = D.querySelector(`.module-btn[data-panel="${current}"]`);
    chip?.classList.add('completed');
  }

  function inferPanelFromText(el) {
    const text = (el && el.textContent ? el.textContent : '').toLowerCase();
    if (!text) return null;
    if (text.includes('validate')) return 'validate-panel';
    if (text.includes('mllp') || text.includes('send')) return 'mllp-panel';
    if (text.includes('fhir') || text.includes('translate')) return 'translate-panel';
    if (text.includes('de-id') || text.includes('deidentify') || text.includes('de-identify')) return 'deid-panel';
    if (text.includes('generate')) return 'generate-panel';
    if (text.includes('sample')) return 'samples-panel';
    return null;
  }

  function resolveTarget(el) {
    if (!el) return { panelId: null, raw: null };

    const explicit = el.getAttribute('data-target-panel') || el.getAttribute('data-panel');
    if (explicit) {
      const panelId = toPanelId(explicit);
      return { panelId, raw: explicit };
    }

    const runTo = el.getAttribute('data-run-to') || el.getAttribute('data-run') || el.dataset.runTo || el.dataset.run;
    if (runTo) {
      const panelId = toPanelId(runTo);
      return { panelId, raw: runTo };
    }

    const href = el.getAttribute('href');
    if (href && href.startsWith('#')) {
      const raw = href.slice(1);
      return { panelId: toPanelId(raw), raw };
    }

    const inferred = inferPanelFromText(el);
    if (inferred) {
      return { panelId: inferred, raw: inferred };
    }

    return { panelId: null, raw: null };
  }

  function bindModuleButtons() {
    $$('.module-btn[data-panel]').forEach((btn) => {
      if (btn.dataset.pipelineNavBound === 'true') return;
      btn.dataset.pipelineNavBound = 'true';
      btn.addEventListener('click', (event) => {
        event.preventDefault();
        const panelId = event.currentTarget?.dataset?.panel;
        if (!panelId) return;
        setActivePanel(panelId);
      }, true);
    });
  }

  function handleDelegatedClick(event) {
    const trigger = event.target.closest('[data-run-to],[data-run],[data-target-panel],[data-panel],[data-open-pipeline-from],.pipeline-run,.js-run-to,.js-run-next,a[href^="#"]');
    if (!trigger) return;
    if (trigger.getAttribute('aria-disabled') === 'true' || trigger.hasAttribute('disabled')) return;

    if (trigger.tagName === 'BUTTON' && !trigger.hasAttribute('type')) {
      trigger.setAttribute('type', 'button');
    }

    const { panelId } = resolveTarget(trigger);
    const openFrom = trigger.getAttribute('data-open-pipeline-from') || trigger.dataset.openPipelineFrom;

    const isAnchor = trigger.matches('a[href]') || trigger.closest('a[href]');

    if (openFrom && typeof window.InteropUI?.openPipelineFrom === 'function') {
      if (isAnchor) event.preventDefault();
      markCurrentCompleted();
      window.InteropUI.openPipelineFrom(openFrom);
      return;
    }

    if (!panelId) return;

    const current = getCurrentPanel();
    if (current && current !== panelId) {
      markCurrentCompleted();
    }

    event.preventDefault();
    setActivePanel(panelId);
  }

  function handleDelegatedKeydown(event) {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    const trigger = event.target.closest('[data-run-to],[data-run],[data-target-panel],[data-open-pipeline-from],.pipeline-run');
    if (!trigger) return;
    if (trigger.tagName === 'BUTTON' || trigger.tagName === 'A') return;
    event.preventDefault();
    trigger.click();
  }

  function enhanceCompletionHooks(panelId) {
    const tray = panelId ? $(`#${panelId} .action-tray`) : null;
    if (!tray) return () => {};
    return () => {
      tray.hidden = false;
      tray.classList.add('visible');
    };
  }

  bindModuleButtons();
  D.addEventListener('click', handleDelegatedClick, true);
  D.addEventListener('keydown', handleDelegatedKeydown);

  const Interop = window.InteropUI = window.InteropUI || {};
  const previousSetActive = Interop.setActivePanel;
  Interop.setActivePanel = function(panelId) {
    const normalized = setActivePanel(panelId);
    if (typeof previousSetActive === 'function' && previousSetActive !== Interop.setActivePanel) {
      try {
        previousSetActive.call(this, normalized || panelId);
      } catch (err) {
        /* ignore legacy errors */
      }
    }
    return normalized;
  };

  if (typeof Interop.runTo !== 'function') {
    Interop.runTo = (name) => setActivePanel(name);
  }

  if (typeof Interop.runNextFromDeid !== 'function') {
    Interop.runNextFromDeid = (name) => {
      markCurrentCompleted();
      setActivePanel(name);
    };
  }

  const wrapComplete = (key, panelKey) => {
    const previous = Interop[key];
    const reveal = enhanceCompletionHooks(panelKey);
    Interop[key] = function(...args) {
      reveal();
      if (typeof previous === 'function') {
        return previous.apply(this, args);
      }
      return undefined;
    };
  };

  wrapComplete('onGenerateComplete', 'generate-panel');
  wrapComplete('onDeidentifyComplete', 'deid-panel');
  wrapComplete('onValidateComplete', 'validate-panel');
  wrapComplete('onMllpComplete', 'mllp-panel');

  if (!D.querySelector('.panel.active')) {
    const initial = D.querySelector('.module-btn.active[data-panel]')?.dataset.panel;
    if (initial) {
      setActivePanel(initial);
    }
  }
})();
