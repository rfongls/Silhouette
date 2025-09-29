/* ========== Global utilities ========== */
window.esc = s => (s ?? "").toString()
  .replace(/&/g,"&amp;").replace(/</g,"&lt;")
  .replace(/>/g,"&gt;").replace(/"/g,"&quot;");

/* Minimal diffs (swap with your fuller versions if you already have them) */
window.diffChars = (a,b) => ({ beforeHTML: esc(a ?? ""), afterHTML: esc(b ?? "") });
window.diffLines = (a,b) => ({ beforeHTML: esc(a ?? ""), afterHTML: esc(b ?? "") });

// Minimal diff renderer (character-level by default)
// Uses jsdiff if present; otherwise falls back to a simple char compare.
window.renderDiff = function renderDiff(before, after) {
  const escHtml = window.esc || ((s) => (s ?? "").toString()
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"));
  const JsDiff = window.Diff || window.JsDiff || window.jsdiff || null;

  if (JsDiff && typeof JsDiff.diffChars === 'function') {
    const parts = JsDiff.diffChars(before || '', after || '');
    let beforeHTML = '', afterHTML = '';
    for (const part of parts) {
      const value = escHtml(part.value);
      if (part.added) {
        afterHTML += `<ins class="added">${value}</ins>`;
      } else if (part.removed) {
        beforeHTML += `<del class="removed">${value}</del>`;
      } else {
        beforeHTML += `<span class="same">${value}</span>`;
        afterHTML  += `<span class="same">${value}</span>`;
      }
    }
    return { beforeHTML, afterHTML };
  }

  // Fallback (no jsdiff): naive char compare
  const a = String(before || '');
  const b = String(after || '');
  let i = 0, j = 0;
  let beforeHTML = '', afterHTML = '';
  while (i < a.length || j < b.length) {
    if (a[i] === b[j]) {
      const value = escHtml(a[i] || '');
      beforeHTML += `<span class="same">${value}</span>`;
      afterHTML  += `<span class="same">${value}</span>`;
      i += 1; j += 1;
    } else {
      if (a[i] !== undefined) {
        beforeHTML += `<del class="removed">${escHtml(a[i])}</del>`;
        i += 1;
      }
      if (b[j] !== undefined) {
        afterHTML  += `<ins class="added">${escHtml(b[j])}</ins>`;
        j += 1;
      }
    }
  }
  return { beforeHTML, afterHTML };
};

/* ========== De-ID modal initializer ========== */
/* Call this AFTER the modal HTML is inserted (after HTMX settles). */
window.initDeidModal = function initDeidModal(sel) {
  const root = (typeof sel === 'string') ? document.querySelector(sel) : sel;
  if (!root) return;
  if (root.dataset.paramDebug === '1') {
    try { window.attachParamDebug(root); } catch (e) { console.warn(e); }
  } else {
    const dbg = root.querySelector('#param-debug');
    if (dbg) dbg.remove();
  }

  const alreadyInit = root.dataset.deidInit === '1';
  root.dataset.deidInit = '1';

  const $ = id => root.querySelector(id);

  const seg = $('#m-seg'), fld = $('#m-field'), cmp = $('#m-comp'), sub = $('#m-sub');
  const pathBadge = $('#m-path-badge');
  const beforeField = $('#m-before-diff'), afterField = $('#m-after-diff');
  const msgBefore   = $('#m-msg-before'),  msgAfter   = $('#m-msg-after');
  const sampleArea  = $('#m-sample');
  const form        = root.querySelector('form');
  const testBtn     = root.querySelector('[data-deid-test]');
  const card        = root.querySelector('.modal-card');
  const btnDown     = root.querySelector('#deid-scroll-down');
  const btnTop      = root.querySelector('#deid-scroll-top');
  const hiddenParamMode = () => form?.querySelector('input[type="hidden"][name="param_mode"]') || null;

  function fitModalToViewport() {
    const card = root.querySelector('.modal-card');
    if (!card) return;
    card.style.transformOrigin = 'top center';
    card.style.transform = '';
    const margin = 24;
    const available = window.innerHeight - margin * 2;
    if (available <= 0) return;
    const rect = card.getBoundingClientRect();
    if (rect.height > available) {
      const scale = Math.max(0.75, available / rect.height);
      card.style.transform = `scale(${scale})`;
    }
  }

  const resizeHandler = () => {
    if (!document.body.contains(root)) {
      window.removeEventListener('resize', resizeHandler);
      return;
    }
    fitModalToViewport();
  };

  const syncParamModeFromSelect = () => {
    const select = root.querySelector('#m-param-mode');
    const hidden = hiddenParamMode();
    if (hidden) hidden.value = (select && select.value) ? select.value : (hidden.value || 'preset');
  };

  function formatPath(){
    const s=(seg?.value||'').trim().toUpperCase();
    const f=(fld?.value||'').trim(), c=(cmp?.value||'').trim(), u=(sub?.value||'').trim();
    if(!s||!f) return '—';
    return s + ':' + f + (c?'.'+c:'') + (u?'.'+u:'');
  }
  function updatePath(){ if(pathBadge) pathBadge.textContent = formatPath(); }

  async function testDeidRule(){
    try{
      const ep = root.getAttribute('data-test-endpoint') || root.dataset.testEndpoint;
      if (!ep) {
        afterField.innerHTML = esc('Missing test endpoint');
        fitModalToViewport();

        return;
      }

      const actionSel = root.querySelector('#m-action');
      const payload = {
        text: sampleArea?.value || "",
        segment: (seg?.value || "").trim(),
        field: parseInt(fld?.value || "0", 10) || 0,
        component: cmp?.value ? parseInt(cmp.value, 10) : null,
        subcomponent: sub?.value ? parseInt(sub.value, 10) : null,
        action: actionSel?.value || "redact",
        param_mode: (form?.querySelector('input[name="param_mode"]')?.value
                  || form?.querySelector('#m-param-mode')?.value || 'preset'),
        param_preset: form?.querySelector('select[name="param_preset"]')?.value
                   || form?.querySelector('input[name="param_preset"]')?.value || null,
        param_free: form?.querySelector('input[name="param_free"]')?.value || null,
        pattern: form?.querySelector('input[name="pattern"]')?.value || null,
        repl: form?.querySelector('input[name="repl"]')?.value || null,
      };

      beforeField.innerHTML = ""; afterField.innerHTML = "";
      msgBefore.innerHTML = "";  msgAfter.innerHTML = "";

      const res = await fetch(ep, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok || !data.ok) {
        const err = (data && (data.message || data.error || data.detail)) || ('HTTP ' + res.status);
        afterField.innerHTML = esc('[Test failed] ' + err);
        fitModalToViewport();
        return;
      }

      {
        const diff = window.renderDiff(data.before?.field || '', data.after?.field || '');
        beforeField.innerHTML = diff.beforeHTML;
        afterField.innerHTML  = diff.afterHTML;
      }

      {
        const beforeMsg = (data.before && (data.before.message || data.before.line)) || '';
        const afterMsg  = (data.after && (data.after.message || data.after.line)) || '';
        const diff = window.renderDiff(beforeMsg, afterMsg);
        msgBefore.innerHTML = diff.beforeHTML;
        msgAfter.innerHTML  = diff.afterHTML;
      }
      fitModalToViewport();
    }catch(e){
      afterField.innerHTML = esc('Test error: ' + e);
      fitModalToViewport();
    }
  }

  // wire events (scoped to this modal)
  if (!alreadyInit) {
    [seg,fld,cmp,sub].forEach(el => el && el.addEventListener('input', updatePath));
    if (testBtn && !testBtn.dataset.deidBound) {
      testBtn.addEventListener('click', testDeidRule);
      testBtn.dataset.deidBound = '1';
    }
    if (btnDown && btnTop && card && !btnDown.dataset.scrollBound) {
      btnDown.addEventListener('click', () => {
        card.scrollBy({ top: Math.round(card.clientHeight * 0.9), behavior: 'smooth' });
      });
      btnTop.addEventListener('click', () => {
        card.scrollTo({ top: 0, behavior: 'smooth' });
      });
      card.addEventListener('scroll', () => {
        btnTop.hidden = card.scrollTop < 32;
      }, { passive: true });
      btnDown.dataset.scrollBound = '1';
      btnTop.hidden = card.scrollTop < 32;
    }
    root.addEventListener('change', (evt) => {
      const target = evt.target;
      if (!target || typeof target.matches !== 'function') return;
      if (target.id === 'm-param-mode') {
        const hidden = hiddenParamMode();
        if (hidden) hidden.value = target.value || 'preset';
      } else if (target.id === 'm-action') {
        const hidden = hiddenParamMode();
        if (!hidden) return;
        if ((target.value || '').toLowerCase() !== 'preset') {
          hidden.value = 'preset';
        } else {
          syncParamModeFromSelect();
        }
        const harness = root.querySelector('#param-harness');
        if (harness && window.htmx) {
          try {
            window.htmx.trigger(harness, 'load');
          } catch (err) {
            console.warn('Failed to trigger param controls refresh', err);
          }
        }
      }
    });
    window.addEventListener('resize', resizeHandler, { passive: true });
  }

  // first render
  updatePath();
  syncParamModeFromSelect();
  fitModalToViewport();
};

window.initValModal = function initValModal(sel) {
  const root = (typeof sel === 'string') ? document.querySelector(sel) : sel;
  if (!root || root.dataset.valInit === '1') return;
  root.dataset.valInit = '1';

  const $ = (selector) => root.querySelector(selector);
  const sampleArea = $('#vc-sample');
  const segmentInput = $('#vc-seg');
  const fieldInput = $('#vc-field');
  const requiredInput = $('#vc-required');
  const patternInput = $('#vc-pattern');
  const allowedInput = $('#vc-allowed');
  const beforeField = $('#val-before-field');
  const afterField = $('#val-after-field');
  const msgBefore = $('#val-msg-before');
  const msgAfter = $('#val-msg-after');
  const report = $('#vc-report');
  const testBtn = root.querySelector('[data-val-test]');
  const card = root.querySelector('.modal-card');
  const btnDown = root.querySelector('#val-scroll-down');
  const btnTop = root.querySelector('#val-scroll-top');
  const endpoint = root.getAttribute('data-test-endpoint') || root.dataset.testEndpoint || '';

  const setDiff = (el, html, fallback) => {
    if (!el) return;
    if (html && html.length) {
      el.innerHTML = html;
    } else if (fallback != null) {
      el.textContent = fallback;
    } else {
      el.textContent = '—';
    }
  };

  const findLine = (sample, seg) => {
    if (!sample || !seg) return '';
    const lines = sample.split(/\r?\n|\r/g);
    const target = seg.trim().toUpperCase();
    if (!target) return '';
    for (const line of lines) {
      if (!line) continue;
      if (line.trim().toUpperCase().startsWith(target + '|')) return line;
    }
    return '';
  };

  const getFieldValue = (line, seg, idx) => {
    if (!line || !idx) return '';
    const parts = line.split('|');
    const tokenIdx = (String(seg).toUpperCase() === 'MSH') ? (idx - 1) : idx;
    return tokenIdx >= 0 ? (parts[tokenIdx] ?? '') : '';
  };

  const formatIssues = (reportData) => {
    if (!reportData || typeof reportData !== 'object') return '—';
    const issues = Array.isArray(reportData.issues) ? reportData.issues : [];
    if (!issues.length) return 'No issues detected.';
    return issues
      .map((issue, index) => {
        const code = issue.code ? `[${issue.code}]` : 'Issue';
        const location = [issue.segment, issue.field].filter(Boolean).join('-');
        const occurrence = issue.occurrence != null ? ` (#${issue.occurrence + 1})` : '';
        const message = issue.message || JSON.stringify(issue);
        return `${index + 1}. ${code} ${location}${occurrence}: ${message}`;
      })
      .join('\n');
  };

  async function runValidationTest() {
    if (report) report.textContent = 'Testing…';
    setDiff(beforeField, '', '—');
    setDiff(afterField, '', '—');
    setDiff(msgBefore, '', '—');
    setDiff(msgAfter, '', '—');

    if (!endpoint) {
      if (report) report.textContent = 'Error: Missing test endpoint';
      return;
    }

    const fd = new FormData();
    fd.append('message_text', sampleArea?.value || '');
    fd.append('segment', segmentInput?.value || '');
    fd.append('field', fieldInput?.value || '');
    fd.append('required', requiredInput && requiredInput.checked ? 'true' : 'false');
    fd.append('pattern', patternInput?.value || '');
    fd.append('allowed_values', allowedInput?.value || '');

    try {
      const res = await fetch(endpoint, { method: 'POST', body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.ok) {
        const err = (data && (data.error || data.detail || data.message)) || ('HTTP ' + res.status);
        if (report) report.textContent = 'Error: ' + err;
        return;
      }

      const sample = sampleArea?.value || '';
      const segment = (segmentInput?.value || '').trim().toUpperCase();
      const fieldIndex = parseInt(fieldInput?.value || '0', 10) || 0;
      const beforeLine = findLine(sample, segment);
      const afterLine = beforeLine;
      const fieldValue = getFieldValue(beforeLine, segment, fieldIndex);
      const afterFieldValue = fieldValue;

      const fieldDiff = window.renderDiff(fieldValue, afterFieldValue);
      setDiff(beforeField, fieldDiff.beforeHTML, fieldValue || '—');
      setDiff(afterField, fieldDiff.afterHTML, afterFieldValue || '—');

      const lineDiff = window.renderDiff(beforeLine || '', afterLine || '');
      const fallbackLine = beforeLine ? beforeLine : 'Segment not found in sample';
      setDiff(msgBefore, lineDiff.beforeHTML, fallbackLine);
      setDiff(msgAfter, lineDiff.afterHTML, afterLine || fallbackLine);

      if (report) {
        const formatted = formatIssues(data.report);
        report.textContent =
          (formatted && formatted !== '—')
            ? formatted
            : (typeof data.report === 'string'
                ? data.report
                : JSON.stringify(data.report ?? {}, null, 2));
      }
    } catch (err) {
      if (report) report.textContent = 'Error: ' + err;
    }
  }

  if (testBtn && !testBtn.dataset.valBound) {
    testBtn.addEventListener('click', runValidationTest);
    testBtn.dataset.valBound = '1';
  }

  if (btnDown && btnTop && card && !btnDown.dataset.scrollBound) {
    btnDown.addEventListener('click', () => {
      card.scrollBy({ top: Math.round(card.clientHeight * 0.9), behavior: 'smooth' });
    });
    btnTop.addEventListener('click', () => {
      card.scrollTo({ top: 0, behavior: 'smooth' });
    });
    card.addEventListener('scroll', () => {
      btnTop.hidden = card.scrollTop < 32;
    }, { passive: true });
    btnDown.dataset.scrollBound = '1';
    btnTop.hidden = card.scrollTop < 32;
  }
};

/* --- Debug wiring for param controls --- */
window.attachParamDebug = function attachParamDebug(root){
  try{
    const panel = root.querySelector('#param-controls');
    const harness = root.querySelector('#param-harness');
    const actionSelect = root.querySelector('#m-action');
    const debugKey = panel || harness;
    if (!debugKey || debugKey.dataset.debugBound === '1') return;
    debugKey.dataset.debugBound = '1';
    const logArea = document.createElement('pre');
    logArea.id = 'param-debug';
    logArea.style.whiteSpace = 'pre-wrap';
    logArea.style.background = 'rgba(148,163,184,.15)';
    logArea.style.padding = '.5rem';
    logArea.style.borderRadius = '.5rem';
    logArea.style.marginTop = '.5rem';
    logArea.textContent = '[param-debug] init';
    (panel || harness).insertAdjacentElement('afterend', logArea);
    const log = (msg) => {
      const now = new Date().toISOString().slice(11,19);
      logArea.textContent += "\n" + now + " " + msg;
      const lines = logArea.textContent.split(/\n/);
      if (lines.length > 200) logArea.textContent = lines.slice(-200).join("\n");
    };
    if (window.htmx){
      const bind = (elt) => {
        if (!elt) return;
        elt.addEventListener('htmx:configRequest', (e)=> log('configRequest url='+(e.detail.path||'')+' params='+(new URLSearchParams(e.detail.parameters)).toString())) ;
        elt.addEventListener('htmx:beforeRequest', (e)=> log('beforeRequest '+(e.detail.path||'')));
        elt.addEventListener('htmx:sendError',     (e)=> log('sendError '+(e.detail.xhr && e.detail.xhr.status)));
        elt.addEventListener('htmx:responseError', (e)=> log('responseError '+(e.detail.xhr && e.detail.xhr.status)));
        elt.addEventListener('htmx:afterOnLoad',   (e)=> log('afterOnLoad status='+(e.detail.xhr && e.detail.xhr.status)));
        elt.addEventListener('htmx:afterSwap',     ()=> log('afterSwap'));
      };
      bind(panel);
      bind(harness);
      bind(actionSelect);
    }
  }catch(e){ console.error(e); }
};

/* ========== HTMX hook ==========
   Any time HTMX swaps in content that includes a De-ID modal,
   this will run the initializer automatically. */
document.addEventListener('htmx:afterSettle', () => {
  const deidModal = document.querySelector('#deid-modal');
  if (deidModal) window.initDeidModal(deidModal);
  const valModal = document.querySelector('#val-modal');
  if (valModal && typeof window.initValModal === 'function') {
    window.initValModal(valModal);
  }
});
