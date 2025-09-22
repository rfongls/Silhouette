// static/js/pipeline_bus.js
(() => {
  'use strict';
  const D = document;
  const $$ = (selector, root = D) => Array.from(root.querySelectorAll(selector));

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

  const nameMap = {
    samples: 'samples-panel',
    generate: 'generate-panel',
    deid: 'deid-panel', 'de-identify': 'deid-panel', deidentify: 'deid-panel',
    validate: 'validate-panel',
    translate: 'translate-panel', fhir: 'translate-panel', 'hl7-to-fhir': 'translate-panel',
    mllp: 'mllp-panel', send: 'mllp-panel', 'send-mllp': 'mllp-panel',
    pipeline: 'pipeline-panel'
  };

  function toPanelId(name) {
    if (!name) return null;
    const raw = String(name).trim();
    if (!raw) return null;
    const lowered = raw.toLowerCase();
    if (nameMap[lowered]) return nameMap[lowered];
    if (lowered.endsWith('-panel')) return lowered;
    return `${lowered}-panel`;
  }

  function getManager() {
    return window.InteropUI?.panelManager || null;
  }

  function getCurrentPanel() {
    const manager = getManager();
    if (manager?.currentPanel) return manager.currentPanel;
    return window.InteropUI?.currentPanel
      || D.querySelector('.module-btn.active[data-panel]')?.dataset.panel
      || null;
  }

  function markCurrentCompleted() {
    const manager = getManager();
    const current = getCurrentPanel();
    if (!current) return;
    if (manager && typeof manager.markPanelCompleted === 'function') {
      manager.markPanelCompleted(current);
      return;
    }
    const chip = D.querySelector(`.module-btn[data-panel="${current}"]`);
    chip?.classList.add('completed');
  }

  function fallbackShow(panelId) {
    if (!panelId) return;
    $$('.panel').forEach((panel) => {
      const active = panel.id === panelId;
      panel.classList.toggle('active', active);
      if ('hidden' in panel) panel.hidden = !active;
    });
    $$('.module-btn[data-panel]').forEach((btn) => {
      const active = btn.dataset.panel === panelId;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-expanded', String(active));
      btn.setAttribute('aria-current', active ? 'page' : 'false');
    });
    $$('.action-tray').forEach((tray) => {
      tray.classList.remove('visible');
      if ('hidden' in tray) tray.hidden = true;
    });
    window.InteropUI = window.InteropUI || {};
    window.InteropUI.currentPanel = panelId;
    try { window.PanelStateCache?.restore(panelId); } catch (_) {}
  }

  function switchTo(panelId) {
    if (!panelId) return;
    const manager = getManager();
    if (manager && typeof manager.showPanel === 'function') {
      manager.showPanel(panelId);
      return;
    }
    fallbackShow(panelId);
  }

  function resolvePanelIdFrom(el) {
    if (!el) return null;
    const explicit = el.getAttribute('data-target-panel') || el.getAttribute('data-panel');
    if (explicit) {
      return toPanelId(explicit);
    }
    const runTo = el.getAttribute('data-run-to') || el.getAttribute('data-run') || el.dataset.runTo || el.dataset.run;
    if (runTo) {
      return toPanelId(runTo);
    }
    const href = el.getAttribute('href');
    if (href && href.startsWith('#')) {
      return toPanelId(href.slice(1));
    }
    const text = (el.textContent || '').toLowerCase();
    if (text.includes('validate')) return 'validate-panel';
    if (text.includes('mllp') || text.includes('send')) return 'mllp-panel';
    if (text.includes('fhir') || text.includes('translate')) return 'translate-panel';
    if (text.includes('de-id') || text.includes('deidentify') || text.includes('de-identify')) return 'deid-panel';
    if (text.includes('generate')) return 'generate-panel';
    if (text.includes('sample')) return 'samples-panel';
    return null;
  }

  function saveCurrentPanelState() {
    const current = getCurrentPanel();
    if (!current) return;
    try { window.PanelStateCache?.save(current); } catch (_) {}
  }

  function restorePanelState(panelId) {
    if (!panelId) return;
    try { window.PanelStateCache?.restore(panelId); } catch (_) {}
  }

  function ensureButtonType(el) {
    if (!el) return;
    if (el.tagName === 'BUTTON' && !el.hasAttribute('type')) {
      el.setAttribute('type', 'button');
    }
  }

  function enhanceCompletionHooks(panelId) {
    const tray = panelId ? D.querySelector(`#${panelId} .action-tray`) : null;
    if (!tray) return () => {};
    return () => {
      tray.hidden = false;
      tray.classList.add('visible');
    };
  }

  let pendingTarget = null;

  $$('.module-btn[data-panel]').forEach((btn) => {
    if (btn.dataset.pipelineNavBound === 'true') return;
    btn.dataset.pipelineNavBound = 'true';
    btn.addEventListener('click', (event) => {
      const panelId = event.currentTarget?.dataset?.panel;
      if (!panelId) return;
      saveCurrentPanelState();
      switchTo(panelId);
    }, true);
  });

  function handleDelegatedClick(event) {
    const trigger = event.target.closest('[data-run-to],[data-run],[data-target-panel],[data-panel],[data-open-pipeline-from],.pipeline-run,.js-run-to,.js-run-next,a[href^="#"]');
    if (!trigger) return;
    if (trigger.getAttribute('aria-disabled') === 'true' || trigger.hasAttribute('disabled')) return;

    ensureButtonType(trigger);

    const openFrom = trigger.getAttribute('data-open-pipeline-from') || trigger.dataset.openPipelineFrom;
    const isAnchor = trigger.matches('a[href]') || trigger.closest('a[href]');

    if (openFrom && typeof window.InteropUI?.openPipelineFrom === 'function') {
      if (isAnchor) event.preventDefault();
      markCurrentCompleted();
      saveCurrentPanelState();
      window.InteropUI.openPipelineFrom(openFrom);
      return;
    }

    const targetId = resolvePanelIdFrom(trigger);
    if (!targetId) return;

    const manager = getManager();
    const current = getCurrentPanel();
    if (manager?.currentPanel) {
      saveCurrentPanelState();
    }

    const hasHTMX = !!trigger.closest('[hx-get],[hx-post],[hx-put],[hx-delete]');

    if (hasHTMX) {
      pendingTarget = targetId;
      return;
    }

    if (current && current !== targetId) {
      markCurrentCompleted();
    }

    event.preventDefault();
    switchTo(targetId);
    restorePanelState(targetId);
  }

  function handleDelegatedKeydown(event) {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    const trigger = event.target.closest('[data-run-to],[data-run],[data-target-panel],[data-open-pipeline-from],.pipeline-run');
    if (!trigger) return;
    if (trigger.tagName === 'BUTTON' || trigger.tagName === 'A') return;
    event.preventDefault();
    trigger.click();
  }

  D.addEventListener('click', handleDelegatedClick, true);
  D.addEventListener('keydown', handleDelegatedKeydown);

  D.addEventListener('htmx:afterSwap', () => {
    if (!pendingTarget) return;
    const target = pendingTarget;
    const current = getCurrentPanel();
    if (current && current !== target) {
      markCurrentCompleted();
    }
    switchTo(target);
    restorePanelState(target);
    if (target === 'mllp-panel' && window.PipelineContext?.setMessage) {
      try {
        window.PipelineContext.setMessage(window.PipelineContext.message || '');
      } catch (_) {
        /* ignore */
      }
    }
    pendingTarget = null;
  });

  D.addEventListener('htmx:responseError', () => {
    pendingTarget = null;
  });

  const Interop = window.InteropUI = window.InteropUI || {};
  const previousSetActive = Interop.setActivePanel;
  Interop.setActivePanel = function(panelId) {
    const normalized = toPanelId(panelId);
    if (normalized) {
      saveCurrentPanelState();
      switchTo(normalized);
    }
    if (typeof previousSetActive === 'function' && previousSetActive !== Interop.setActivePanel) {
      try {
        previousSetActive.call(this, normalized || panelId);
      } catch (_) {}
    }
    return normalized;
  };

  if (typeof Interop.runTo !== 'function') {
    Interop.runTo = (name) => {
      const target = toPanelId(name);
      if (!target) return;
      saveCurrentPanelState();
      markCurrentCompleted();
      switchTo(target);
      restorePanelState(target);
    };
  }

  if (typeof Interop.runNextFromDeid !== 'function') {
    Interop.runNextFromDeid = (name) => {
      markCurrentCompleted();
      const target = toPanelId(name);
      if (!target) return;
      saveCurrentPanelState();
      switchTo(target);
      restorePanelState(target);
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
      switchTo(initial);
    }
  }
})();
