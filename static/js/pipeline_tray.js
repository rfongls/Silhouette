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
      btn.setAttribute('aria-expanded', on ? 'true' : 'false');
      btn.setAttribute('aria-current', on ? 'page' : 'false');
    });
  }

  function collapseOthersAndShow(panelId, { scroll = true } = {}) {
    // Collapse all, expand target
    $$('.panel').forEach(p => p.classList.toggle('active', p.id === panelId));
    activateNavFor(panelId);

    // Keep PanelManager in sync if present
    if (window.InteropUI?.panelManager) {
      window.InteropUI.panelManager.currentPanel = panelId;
    }

    // Make sure users *see* the target panel
    const target = $('#'+panelId);
    if (target && scroll) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
    collapseOthersAndShow(pid, { scroll });
  }

  // expose for any inline calls
  window.InteropUI = window.InteropUI || {};
  window.InteropUI.goToPanel = goToPanel;

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
    const card = e.target.closest('.action-card');
    if (!card) return;

    // supports data-next="validate" or data-action="next-validate"
    const raw = card.dataset.next || card.dataset.action || '';
    if (!raw) return;

    const targetKey = String(raw).replace(/^next-/, '').replace(/-panel$/,''); // 'validate' | 'mllp' | 'fhir' | 'translate'
    if (!PANELS[targetKey] && targetKey !== 'fhir') return;

    // Source payload = current panel’s output
    const srcKey = keyFromElement(card);
    const srcOut = srcKey && findOutput(srcKey);
    const text   = textOf(srcOut);

    // If no payload yet, let the default link (if any) proceed
    if (!text) return;

    // We take over routing
    e.preventDefault();

    // Put payload on bus (consume-once semantics if present)
    if (window.PipelineBus?.set) window.PipelineBus.set(srcKey, text, { from: srcKey });

    // Normalize 'fhir' → 'translate' (UI label vs panel id)
    const destKey = (targetKey === 'fhir') ? 'translate' : targetKey;

    // Navigate universally (collapse others, expand dest)
    goToPanel(destKey, { scroll: true });

    // Prefill the destination panel with the payload and reveal its tray
    prefillTarget(destKey, text);
    revealTrayFor(destKey);
  });

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
