// static/js/pipeline_bus.js
(function () {
  'use strict';
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const $ = (selector, root = document) => root.querySelector(selector);

  const nameMap = {
    samples: 'samples-panel',
    generate: 'generate-panel',
    deid: 'deid-panel', 'de-identify': 'deid-panel', deidentify: 'deid-panel',
    validate: 'validate-panel',
    translate: 'translate-panel', fhir: 'translate-panel', 'hl7-to-fhir': 'translate-panel',
    mllp: 'mllp-panel', send: 'mllp-panel', 'send-mllp': 'mllp-panel'
  };

  function setActivePanel(panelId) {
    if (!panelId) return;
    const pm = window.InteropUI?.panelManager;
    if (pm && typeof pm.runPipeline === 'function') {
      pm.runPipeline(panelId);
      return;
    }
    if (pm && typeof pm.showPanel === 'function') {
      pm.showPanel(panelId);
      return;
    }

    $$('.panel').forEach((panel) => {
      panel.classList.toggle('active', panel.id === panelId);
    });
    $$('.module-btn').forEach((btn) => {
      const on = btn.dataset.panel === panelId;
      btn.classList.toggle('active', on);
      btn.setAttribute('aria-expanded', String(on));
    });
    $$('.action-tray').forEach((tray) => tray.classList.remove('visible'));

    window.InteropUI = window.InteropUI || {};
    window.InteropUI.currentPanel = panelId;
  }

  function markCurrentCompleted() {
    const pm = window.InteropUI?.panelManager;
    const current = pm?.currentPanel || window.InteropUI?.currentPanel;
    if (!current) return;
    if (pm && typeof pm.markPanelCompleted === 'function') {
      pm.markPanelCompleted(current);
      return;
    }
    document.querySelector(`[data-panel="${current}"]`)?.classList.add('completed');
  }

  function resolveTarget(el) {
    if (!el) return null;

    const explicit = el.getAttribute('data-target-panel') || el.getAttribute('data-panel');
    if (explicit) {
      return explicit.endsWith('-panel') ? explicit : `${explicit}-panel`;
    }

    const runTo = el.getAttribute('data-run-to') || el.getAttribute('data-run') || el.dataset.runTo || el.dataset.run;
    if (runTo) {
      const key = runTo.toLowerCase();
      if (nameMap[key]) return nameMap[key];
      return key.endsWith('-panel') ? key : `${key}-panel`;
    }

    const href = el.getAttribute('href');
    if (href && href.startsWith('#')) {
      const key = href.slice(1);
      if (nameMap[key]) return nameMap[key];
      return key.endsWith('-panel') ? key : `${key}-panel`;
    }

    const text = (el.textContent || '').toLowerCase();
    if (text.includes('validate')) return 'validate-panel';
    if (text.includes('mllp') || text.includes('send')) return 'mllp-panel';
    if (text.includes('fhir') || text.includes('translate')) return 'translate-panel';
    if (text.includes('de-id') || text.includes('deidentify') || text.includes('de-identify')) return 'deid-panel';
    if (text.includes('generate')) return 'generate-panel';
    return null;
  }

  document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-run-to],[data-run],[data-target-panel],[data-panel],.pipeline-run,a[href^="#"]');
    if (!trigger) return;

    if (trigger.tagName === 'BUTTON' && !trigger.hasAttribute('type')) {
      trigger.setAttribute('type', 'button');
    }

    if (trigger.tagName === 'A' || trigger.closest('a')) {
      event.preventDefault();
    }

    if (trigger.getAttribute('aria-disabled') === 'true' || trigger.hasAttribute('disabled')) {
      return;
    }

    const targetId = resolveTarget(trigger);
    if (!targetId) return;

    markCurrentCompleted();
    setActivePanel(targetId);
  }, true);

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    const trigger = event.target.closest('[data-run-to],[data-run],[data-target-panel],[data-panel],.pipeline-run');
    if (!trigger) return;
    if (trigger.tagName === 'BUTTON' || trigger.tagName === 'A') return;
    event.preventDefault();
    trigger.click();
  });

  window.InteropUI = window.InteropUI || {};
  window.InteropUI.setActivePanel = setActivePanel;
  window.InteropUI.runTo = (name) => {
    const key = String(name || '').toLowerCase();
    const target = nameMap[key] || (key.endsWith('-panel') ? key : `${key}-panel`);
    if (target) {
      markCurrentCompleted();
      setActivePanel(target);
    }
  };
  window.InteropUI.runNextFromDeid = (name) => window.InteropUI.runTo(name);
})();
