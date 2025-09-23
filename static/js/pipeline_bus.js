// static/js/pipeline_bus.js
(function () {
  'use strict';
  const D = document;
  const $$ = (selector, root = D) => Array.from(root.querySelectorAll(selector));
  const SELECTOR = '[data-run-to],[data-run],[data-target-panel],[data-panel],.pipeline-run,a[href^="#"]';
  const HX_SELECTOR = '[hx-get],[hx-post],[hx-put],[hx-delete],[hx-patch]';

  const nameMap = {
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
    'send-mllp': 'mllp-panel'
  };

  function normalizePanelId(value) {
    if (!value) return null;
    const raw = String(value).trim();
    if (!raw) return null;
    return raw.endsWith('-panel') ? raw : `${raw}-panel`;
  }

  function panelIdFromName(name) {
    if (!name) return null;
    const key = String(name).trim().toLowerCase();
    if (!key) return null;
    return normalizePanelId(nameMap[key] || key);
  }

  function resolvePanelId(trigger) {
    if (!trigger) return null;

    const explicit = trigger.getAttribute('data-target-panel') || trigger.getAttribute('data-panel');
    if (explicit) {
      return normalizePanelId(explicit);
    }

    const runTo = trigger.getAttribute('data-run-to')
      || trigger.getAttribute('data-run')
      || trigger.dataset.runTo
      || trigger.dataset.run;
    if (runTo) {
      return panelIdFromName(runTo);
    }

    const href = trigger.getAttribute('href');
    if (href && href.startsWith('#')) {
      return normalizePanelId(href.slice(1));
    }

    const text = (trigger.textContent || '').toLowerCase();
    if (!text) return null;
    if (text.includes('validate')) return 'validate-panel';
    if (text.includes('mllp') || text.includes('send')) return 'mllp-panel';
    if (text.includes('fhir') || text.includes('translate')) return 'translate-panel';
    if (text.includes('de-id') || text.includes('deidentify') || text.includes('de-identify')) return 'deid-panel';
    if (text.includes('generate')) return 'generate-panel';
    if (text.includes('sample')) return 'samples-panel';
    return null;
  }

  function fallbackShow(panelId, { mark = false } = {}) {
    const normalized = normalizePanelId(panelId);
    if (!normalized) return;

    const current = window.InteropUI?.currentPanel;
    if (mark && current && current !== normalized) {
      const chip = D.querySelector(`.module-btn[data-panel="${current}"]`);
      if (chip) {
        chip.classList.add('completed');
        chip.setAttribute('aria-current', 'step');
      }
    }

    $$('.panel').forEach((panel) => {
      const isActive = panel.id === normalized;
      panel.classList.toggle('active', isActive);
      if ('hidden' in panel) {
        panel.hidden = !isActive;
      }
    });

    $$('.module-btn[data-panel]').forEach((btn) => {
      const isActive = btn.dataset.panel === normalized;
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-expanded', String(isActive));
      btn.setAttribute('aria-current', isActive ? 'page' : (btn.classList.contains('completed') ? 'step' : 'false'));
    });

    $$('.action-tray').forEach((tray) => {
      tray.classList.remove('visible');
      if ('hidden' in tray) tray.hidden = true;
    });

    window.InteropUI = window.InteropUI || {};
    window.InteropUI.currentPanel = normalized;

    try {
      window.PanelStateCache?.restore(normalized);
    } catch (_) {
      /* ignore */
    }
  }

  function gotoPanel(panelId, { mark = false } = {}) {
    const normalized = normalizePanelId(panelId);
    if (!normalized) return;

    const pm = window.InteropUI?.panelManager;
    if (pm) {
      if (pm.currentPanel && pm.currentPanel !== normalized) {
        try { window.PanelStateCache?.save(pm.currentPanel); } catch (_) { /* ignore */ }
      }
      if (mark && typeof pm.runPipeline === 'function') {
        pm.runPipeline(normalized);
        return;
      }
      if (mark && typeof pm.markPanelCompleted === 'function' && pm.currentPanel && pm.currentPanel !== normalized) {
        pm.markPanelCompleted(pm.currentPanel);
      }
      if (typeof pm.showPanel === 'function') {
        pm.showPanel(normalized);
        return;
      }
    }

    fallbackShow(normalized, { mark });
  }

  let pending = null;

  document.addEventListener('click', (event) => {
    const trigger = event.target.closest(SELECTOR);
    if (!trigger || trigger.classList.contains('module-btn')) return;

    if (trigger.tagName === 'BUTTON' && !trigger.hasAttribute('type')) {
      trigger.setAttribute('type', 'button');
    }

    const targetId = resolvePanelId(trigger);
    if (!targetId) return;

    const shouldMark = trigger.matches('.pipeline-run')
      || trigger.hasAttribute('data-run-to')
      || trigger.hasAttribute('data-run');

    const pm = window.InteropUI?.panelManager;
    const currentPanel = pm?.currentPanel || window.InteropUI?.currentPanel || null;
    if (currentPanel && currentPanel !== targetId) {
      try { window.PanelStateCache?.save(currentPanel); } catch (_) { /* ignore */ }
    }

    const hxRoot = trigger.closest(HX_SELECTOR);
    if (hxRoot) {
      pending = { id: targetId, mark: shouldMark };
      return;
    }

    if (trigger.tagName === 'A' || trigger.closest('a')) {
      event.preventDefault();
    }

    gotoPanel(targetId, { mark: shouldMark });
  }, true);

  document.addEventListener('htmx:afterSwap', () => {
    if (!pending) return;
    gotoPanel(pending.id, { mark: pending.mark });
    pending = null;
  });

  document.addEventListener('htmx:responseError', () => {
    pending = null;
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    const trigger = event.target.closest('[data-run-to],[data-run],[data-target-panel],[data-panel],.pipeline-run');
    if (!trigger || trigger.classList.contains('module-btn')) return;
    if (trigger.tagName === 'BUTTON' || trigger.tagName === 'A') return;
    event.preventDefault();
    trigger.click();
  });

  window.InteropUI = window.InteropUI || {};
  window.InteropUI.setActivePanel = (panelId) => gotoPanel(panelId, { mark: false });
  window.InteropUI.runTo = (name) => {
    const targetId = panelIdFromName(name);
    if (targetId) {
      gotoPanel(targetId, { mark: true });
    }
  };
  window.InteropUI.runNextFromDeid = window.InteropUI.runTo;
})();
