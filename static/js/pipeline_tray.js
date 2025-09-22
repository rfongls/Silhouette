// static/js/pipeline_tray.js
// Universal pipeline nav: move payload, collapse others, expand target panel.
(() => {
  'use strict';
  const D = document;
  const $  = (s, r = D) => r.querySelector(s);
  const $$ = (s, r = D) => Array.from(r.querySelectorAll(s));

  // Known panels and their DOM ids / output selectors
  const PANELS = {
    samples:  { panel: 'samples-panel',  outputs: ['.codepane','#sample-preview'] },
    generate: { panel: 'generate-panel', outputs: ['#gen-output','[data-role="gen-output"]','textarea[name="message"]','pre','.gen-output'] },
    deid:     { panel: 'deid-panel',     outputs: ['#deid-output','[data-role="deid-output"]','#deidentify-output','pre','.deid-output'] },
    validate: { panel: 'validate-panel',  outputs: ['#validate-output','#validation-results','[data-role="validate-output"]','.validate-output','pre'] },
    translate:{ panel: 'translate-panel', outputs: ['#translate-output','.translate-output','pre','code'] },
    mllp:     { panel: 'mllp-panel',      outputs: ['#ack-output','#mllp-output','.mllp-output','pre'] },
    pipeline: { panel: 'pipeline-panel',  outputs: [] }
  };
  const PANEL_IDS = new Set(Object.values(PANELS).map(p => p.panel));

  // ---------- helpers ----------
  function panelIdFromKey(key) {
    return PANELS[key]?.panel || key; // allow callers to pass "validate" or "validate-panel"
  }

  function findPanel(el) {
    return el.closest('.panel') || el.closest('[id$="-panel"]');
  }

  function keyFromElement(el) {
    const id = (findPanel(el) || {}).id || '';
    return id.replace(/-panel$/, '') || null;
  }

  function findOutput(key) {
    const pid = panelIdFromKey(key);
    const wrap = $('#'+pid);
    if (!wrap) return null;
    for (const s of PANELS[key]?.outputs || []) {
      const el = $(s, wrap);
      if (el) return el;
    }
    return $('textarea,pre,code,output', wrap);
  }

  function textOf(el) {
    if (!el) return '';
    if ('value' in el) return String(el.value || '').trim();
    return String(el.textContent || '').trim();
  }

  function revealTrayFor(key) {
    const pid  = panelIdFromKey(key);
    const wrap = $('#'+pid);
    const tray = wrap && $('.action-tray', wrap);
    if (tray) { tray.hidden = false; tray.classList.add('visible'); }
  }

  function activateNavFor(panelId) {
    // Update module chips/buttons (active + aria)
    $$('.module-btn').forEach(btn => {
      const on = btn.dataset.panel === panelId;
      btn.classList.toggle('active', on);
      if (on) {
        btn.classList.remove('completed');
      }
      if (btn.dataset.panel) {
        btn.setAttribute('aria-expanded', String(on));
        btn.setAttribute('aria-controls', btn.dataset.panel);
      }
      btn.setAttribute('aria-current', on ? 'page' : 'false');
    });
  }

  function setActivePanel(panelId, { scroll = true } = {}) {
    if (!panelId) return;

    // Collapse all, expand target
    $$('.panel, .interop-panel').forEach(p => {
      const active = p.id === panelId;
      const known = PANEL_IDS.has(p.id);
      p.classList.toggle('active', active);
      if (known) {
        p.hidden = !active;
      } else if (active) {
        p.hidden = false;
      }
      if (active) {
        const parentDetails = p.closest('details');
        if (parentDetails && typeof parentDetails.open === 'boolean') {
          parentDetails.open = true;
        }
      }
    });
    activateNavFor(panelId);

    // hide all trays when switching
    $$('.action-tray').forEach(t => {
      t.classList.remove('visible');
      t.hidden = true;
    });

    window.InteropUI = window.InteropUI || {};
    window.InteropUI.currentPanel = panelId;

    // Keep PanelManager in sync if present
    if (window.InteropUI?.panelManager) {
      window.InteropUI.panelManager.currentPanel = panelId;
    }

    // Make sure users *see* the target panel
    const target = $('#'+panelId);
    if (target && scroll) {
      try {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } catch (_) {
        /* ignore scroll errors */
      }
    }
  }

  function prefillTarget(targetKey, text) {
    const pid = panelIdFromKey(targetKey);
    const wrap = $('#'+pid);
    if (!wrap) return;

    // Input preferences per target
    const candidatesByKey = {
      validate: ['#validate-input','textarea[name="validate-message"]','.validate-input','textarea'],
      mllp:     ['#mllp-input','textarea[name="mllp-message"]','.mllp-input','textarea'],
      translate:['#translate-input','textarea[name="translate-message"]','.translate-input','textarea']
    };
    const candidates = candidatesByKey[targetKey] || ['textarea','.codepane', 'pre'];

    let input = null;
    for (const s of candidates) { input = $(s, wrap); if (input) break; }
    if (input && 'value' in input) input.value = text;
    else if (input) input.textContent = text;
    else (wrap.querySelector('.codepane') || wrap).textContent = text;
  }

  // ---------- public universal nav API ----------
  function goToPanel(key, { scroll = true } = {}) {
    const pid = panelIdFromKey(key);
    // If the app exposes PanelManager.showPanel, use it first
    if (window.InteropUI?.panelManager?.showPanel) {
      window.InteropUI.panelManager.showPanel(pid);
    }
    // Enforce collapse/expand universally as a safety net
    setActivePanel(pid, { scroll });
  }

  // expose for any inline calls
  window.InteropUI = window.InteropUI || {};
  window.InteropUI.goToPanel = goToPanel;
  window.InteropUI.setActivePanel = setActivePanel;

  // Also wrap any existing run helpers so they collapse/expand too
  ['runTo','runNextFromDeid'].forEach(fn => {
    if (typeof window.InteropUI[fn] === 'function') {
      const orig = window.InteropUI[fn];
      window.InteropUI[fn] = function(target /* 'validate' | 'mllp' | 'translate' ... */) {
        const key = String(target).replace(/-panel$/,'');
        goToPanel(key);
        return orig.apply(this, arguments);
      };
    }
  });

  // ---------- intercept pipeline cards ----------
  D.addEventListener('click', (e) => {
    const card = e.target.closest('[data-run-to], .action-card');
    if (!card) return;

    const runTarget = (card.getAttribute('data-run-to') || '').trim();
    const legacy = card.dataset.next || card.dataset.action || '';
    const raw = runTarget || legacy;
    if (!raw) return;

    const targetKeyRaw = String(raw).replace(/^next-/, '').trim();
    if (!targetKeyRaw) return;

    const normalizedKey = targetKeyRaw.replace(/-panel$/,'');
    const destKey = (normalizedKey === 'fhir') ? 'translate' : normalizedKey;
    if (!PANELS[destKey] && !PANELS[normalizedKey] && destKey !== 'pipeline') return;

    const currentPanelId = window.InteropUI?.currentPanel || (findPanel(card)?.id || '');
    if (currentPanelId) {
      const chip = document.querySelector(`.module-btn[data-panel="${currentPanelId}"]`);
      chip?.classList.add('completed');
    }

    const srcKey = keyFromElement(card) || (currentPanelId ? currentPanelId.replace(/-panel$/,'') : null);
    const srcOut = srcKey && findOutput(srcKey);
    const text   = textOf(srcOut);

    e.preventDefault();

    if (text && window.PipelineBus?.set) {
      window.PipelineBus.set(srcKey, text, { from: srcKey });
    }

    goToPanel(destKey, { scroll: true });

    if (text) {
      prefillTarget(destKey, text);
      revealTrayFor(destKey);
    }
  });

  D.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const card = e.target.closest('[data-run-to]');
    if (!card) return;
    if (card.tagName === 'BUTTON' || card.tagName === 'A') return;
    e.preventDefault();
    card.click();
  });

  $$('.module-btn[data-panel]').forEach(btn => {
    const panelId = btn.dataset.panel;
    if (!panelId) return;
    if (!btn.getAttribute('aria-controls')) {
      btn.setAttribute('aria-controls', panelId);
    }
    btn.setAttribute('aria-expanded', String(btn.classList.contains('active')));
    btn.addEventListener('click', (event) => {
      const targetPanel = event.currentTarget.dataset.panel;
      if (!targetPanel) return;
      event.preventDefault();
      setActivePanel(targetPanel);
    });
  });

  const initialActiveBtn = $('.module-btn.active[data-panel]');
  if (initialActiveBtn?.dataset.panel) {
    setActivePanel(initialActiveBtn.dataset.panel, { scroll: false });
  }

  // ---------- optional: reveal trays when outputs fill asynchronously ----------
  function watchOutput(key) {
    const out = findOutput(key);
    if (!out) return;
    const update = () => { if (textOf(out)) revealTrayFor(key); };
    if ('value' in out) out.addEventListener('input', update);
    new MutationObserver(update).observe(out, { childList: true, characterData: true, subtree: true });
  }
  ['generate','deid','validate','mllp','translate'].forEach(watchOutput);
})();
