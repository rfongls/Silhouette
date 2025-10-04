// ------------------------------
// Interop UI helpers and global utilities
// ------------------------------

window.InteropUI = window.InteropUI || {};

/* ========== Global utilities ========== */
window.esc = s => (s ?? "").toString()
  .replace(/&/g,"&amp;").replace(/</g,"&lt;")
  .replace(/>/g,"&gt;").replace(/"/g,"&quot;");

/* Minimal diffs (swap with your fuller versions if you already have them) */
window.diffChars = (a,b) => ({ beforeHTML: esc(a ?? ""), afterHTML: esc(b ?? "") });
window.diffLines = (a,b) => ({ beforeHTML: esc(a ?? ""), afterHTML: esc(b ?? "") });

const __fallbackEsc = (s) => (s ?? "").toString()
  .replace(/&/g, "&amp;")
  .replace(/</g, "&lt;")
  .replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;");
const htmlEscape = (value) => {
  const escFn = window.esc || __fallbackEsc;
  return escFn(value);
};

function detectSeps(text) {
  let fieldSep = '|';
  let compSep = '^';
  let subSep = '&';
  const lines = (text || '').split(/\r?\n|\r/g);
  const msh = lines.find(line => typeof line === 'string' && line.startsWith('MSH') && line.length >= 4);
  if (msh) {
    fieldSep = msh[3] || fieldSep;
    const parts = msh.split(fieldSep);
    const enc = parts[1] || '';
    if (enc.length >= 1) compSep = enc[0];
    if (enc.length >= 4) subSep = enc[3];
  }
  return { fieldSep, compSep, subSep };
}

function tokenIndexFor(segment, fieldNumber) {
  return (String(segment).toUpperCase() === 'MSH') ? (fieldNumber - 1) : fieldNumber;
}

function renderLineWithFieldHTML(line, segment, fieldNumber, fieldSep, fieldHTML, fallbackValue) {
  if (!line) return '';
  const idx = tokenIndexFor(segment, fieldNumber);
  const sep = fieldSep || '|';
  const parts = line.split(sep);
  if (idx < 0 || idx >= parts.length) {
    return htmlEscape(line);
  }
  return parts
    .map((token, tokenIdx) => {
      if (tokenIdx !== idx) {
        return htmlEscape(token);
      }
      if (fieldHTML && fieldHTML.length) {
        return fieldHTML;
      }
      return htmlEscape(fallbackValue ?? token);
    })
    .join(sep);
}

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

      const segVal = (seg?.value || '').trim().toUpperCase();
      const fldNum = parseInt(fld?.value || '0', 10) || 0;
      const sampleText = sampleArea?.value || '';
      const beforeLineRaw = data.before?.line || '';
      const afterLineRaw = data.after?.line || '';
      const beforeMsgRaw = data.before?.message || '';
      const afterMsgRaw = data.after?.message || '';
      const seps = detectSeps(beforeLineRaw || beforeMsgRaw || afterLineRaw || afterMsgRaw || sampleText);

      const fieldDiff = window.renderDiff(data.before?.field || '', data.after?.field || '');
      if (beforeField) {
        if (fieldDiff.beforeHTML) {
          beforeField.innerHTML = fieldDiff.beforeHTML;
        } else {
          beforeField.textContent = '—';
        }
      }
      if (afterField) {
        if (fieldDiff.afterHTML) {
          afterField.innerHTML = fieldDiff.afterHTML;
        } else {
          afterField.textContent = '—';
        }
      }

      if (msgBefore) {
        if (beforeLineRaw) {
          msgBefore.innerHTML = renderLineWithFieldHTML(
            beforeLineRaw,
            segVal,
            fldNum,
            seps.fieldSep,
            fieldDiff.beforeHTML,
            data.before?.field
          );
        } else {
          const fallbackBefore = beforeMsgRaw || (segVal ? `Segment ${segVal} not found in sample` : '—');
          msgBefore.textContent = fallbackBefore || '—';
        }
      }

      if (msgAfter) {
        if (afterLineRaw) {
          msgAfter.innerHTML = renderLineWithFieldHTML(
            afterLineRaw,
            segVal,
            fldNum,
            seps.fieldSep,
            fieldDiff.afterHTML,
            data.after?.field
          );
        } else {
          const fallbackAfter = afterMsgRaw || (segVal ? `Segment ${segVal} not found in sample` : '—');
          msgAfter.textContent = fallbackAfter || '—';
        }
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
  const actionSelect = $('#vc-action');
  const modeSelect = $('#vc-param-mode');
  const requiredInput = $('#vc-required');
  const patternInput = $('#vc-pattern');
  const allowedInput = $('#vc-allowed');
  const foundEl   = $('#val-found');
  const resultEl  = $('#val-result');
  const reasonEl  = $('#val-reason');
  const report = $('#vc-report');
  const testBtn = root.querySelector('[data-val-test]');
  const card = root.querySelector('.modal-card');
  const btnDown = root.querySelector('#val-scroll-down');
  const btnTop = root.querySelector('#val-scroll-top');
  const form = root.querySelector('form');
  const endpoint = root.getAttribute('data-test-endpoint') || root.dataset.testEndpoint || '';
  const hiddenRequired = root.querySelector('input[name="required"]');
  const hiddenPattern  = root.querySelector('input[name="pattern"]');
  const hiddenAllowed  = root.querySelector('input[name="allowed_values"]');
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

  const showParamPane = (kind) => {
    root.querySelectorAll('#vc-param-controls [data-pane]').forEach((pane) => {
      const matches = pane.getAttribute('data-pane') === kind;
      pane.hidden = !matches;
    });
  };

  const syncHiddenFromUI = () => {
    const kind = (actionSelect?.value || 'required');
    if (hiddenRequired) hiddenRequired.value = '';
    if (hiddenPattern) hiddenPattern.value = '';
    if (hiddenAllowed) hiddenAllowed.value = '';

    if (kind === 'required') {
      if (hiddenRequired) hiddenRequired.value = requiredInput && requiredInput.checked ? 'true' : 'false';
    } else if (kind === 'matches_regex') {
      if (hiddenPattern) hiddenPattern.value = patternInput?.value || '';
      if (hiddenRequired) hiddenRequired.value = 'false';
    } else if (kind === 'in_allowed') {
      const mode = modeSelect?.value || 'single';
      const raw = (allowedInput?.value || '').trim();
      const values = raw
        .split(/[;,\n]/)
        .map((token) => token.trim())
        .filter(Boolean);
      if (hiddenAllowed) {
        hiddenAllowed.value = mode === 'single'
          ? (values[0] || '')
          : values.join(',');
      }
      if (hiddenRequired) hiddenRequired.value = 'false';
    }
    return kind;
  };

  if (actionSelect && !actionSelect.dataset.bound) {
    actionSelect.addEventListener('change', () => {
      showParamPane(actionSelect.value);
      syncHiddenFromUI();
    });
    actionSelect.dataset.bound = '1';
  }

  if (modeSelect && !modeSelect.dataset.bound) {
    modeSelect.addEventListener('change', () => {
      syncHiddenFromUI();
    });
    modeSelect.dataset.bound = '1';
  }

  if (requiredInput && !requiredInput.dataset.bound) {
    requiredInput.addEventListener('change', () => {
      syncHiddenFromUI();
    });
    requiredInput.dataset.bound = '1';
  }

  if (patternInput && !patternInput.dataset.bound) {
    patternInput.addEventListener('input', () => {
      syncHiddenFromUI();
    });
    patternInput.dataset.bound = '1';
  }

  if (allowedInput && !allowedInput.dataset.bound) {
    allowedInput.addEventListener('input', () => {
      syncHiddenFromUI();
    });
    allowedInput.dataset.bound = '1';
  }

  if (form && !form.dataset.valSubmitBound) {
    form.addEventListener('submit', () => {
      syncHiddenFromUI();
    });
    form.dataset.valSubmitBound = '1';
  }

  async function runValidationTest() {
    if (report) report.textContent = 'Testing…';
    if (foundEl) foundEl.textContent = '—';
    if (resultEl) { resultEl.textContent = '—'; resultEl.className = 'result-badge'; }
    if (reasonEl) reasonEl.textContent = '';

    const kind = syncHiddenFromUI();

    if (!endpoint) {
      if (report) report.textContent = 'Error: Missing test endpoint';
      return;
    }

    const fd = new FormData();
    fd.append('message_text', sampleArea?.value || '');
    fd.append('segment', segmentInput?.value || '');
    fd.append('field', fieldInput?.value || '');
    fd.append('required', hiddenRequired?.value || '');
    fd.append('pattern', hiddenPattern?.value || '');
    fd.append('allowed_values', hiddenAllowed?.value || '');

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
      const fieldValue = getFieldValue(beforeLine, segment, fieldIndex);
      if (foundEl) foundEl.textContent = fieldValue || '—';

      let pass = true;
      let reasons = [];
      if (data && data.report && Array.isArray(data.report.issues)) {
        pass = data.report.issues.length === 0;
        reasons = data.report.issues.map((issue) => issue.message || issue.code || JSON.stringify(issue));
      } else {
        const requiredFlag = (hiddenRequired?.value || '').toLowerCase() === 'true';
        const patternText = (hiddenPattern?.value || '').trim();
        const allowedValues = (hiddenAllowed?.value || '')
          .split(',')
          .map((token) => token.trim())
          .filter(Boolean);

        if (requiredFlag && !fieldValue) {
          pass = false;
          reasons.push('Required but empty');
        }

        if (patternText) {
          try {
            const regex = new RegExp(patternText);
            if (!regex.test(fieldValue || '')) {
              pass = false;
              reasons.push('Pattern not matched');
            }
          } catch (regexErr) {
            pass = false;
            reasons.push('Invalid regex');
          }
        }

        if (allowedValues.length) {
          if (!allowedValues.includes(fieldValue || '')) {
            pass = false;
            reasons.push('Value not in allowed list');
          }
        }

        if (!patternText && kind === 'matches_regex') {
          pass = false;
          reasons.push('Pattern is required for regex checks');
        }
      }

      if (!pass && reasons.length === 0) {
        reasons.push('Validation failed.');
      }

      if (resultEl) {
        resultEl.textContent = pass ? 'MATCH' : 'FAIL';
        resultEl.className = 'result-badge ' + (pass ? 'pass' : 'fail');
      }
      if (reasonEl) {
        reasonEl.textContent = pass ? 'All checks passed.' : reasons.join('\n');
      }

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

  showParamPane(actionSelect?.value || 'required');
  syncHiddenFromUI();
};

window.initValChecksPanel = function initValChecksPanel(sel) {
  const root = (typeof sel === 'string') ? document.querySelector(sel) : sel;
  if (!root || root.dataset.valChecksInit === '1') return;
  root.dataset.valChecksInit = '1';

  const select = root.querySelector('[data-val-rule-select]');
  const editForm = root.querySelector('[data-val-edit-form]');
  const deleteForm = root.querySelector('[data-val-delete-form]');
  const editInput = editForm?.querySelector('input[name="index"]') || null;
  const deleteInput = deleteForm?.querySelector('input[name="index"]') || null;

  const syncIndex = () => {
    const value = select ? select.value : '0';
    if (editInput) editInput.value = value;
    if (deleteInput) deleteInput.value = value;
  };

  if (select) {
    select.addEventListener('change', syncIndex);
    syncIndex();
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

/* ========= Accordion system (robust to HTMX swaps; single source of truth) ========= */
(function () {
  // Try several selectors so outer interop cards can control inner module content.
  function findBody(acc) {
    return (
      acc.querySelector(':scope > [data-acc-body], :scope > .module-body, :scope > .panel-body, :scope > .card-body') ||
      acc.querySelector('[data-acc-body]') ||
      (function () {
        const ids = ['gen-form', 'deid-form', 'validate-form', 'mllp-form'];
        for (const id of ids) {
          const form = acc.querySelector('#' + id);
          if (form) {
            return form.closest('.module-body') || form.closest('.card-body') || form.parentElement;
          }
        }
        return null;
      })()
    );
  }
  function setAccOpen(acc, open) {
    const body = findBody(acc);
    if (acc && typeof acc.setAttribute === 'function') {
      acc.setAttribute('data-open', open ? '1' : '0');
    }
    const toggle = acc.querySelector('[data-acc-toggle]');
    if (toggle) toggle.setAttribute('aria-expanded', String(!!open));
    const label = acc.querySelector('[data-acc-label]') || acc.querySelector('.acc-label');
    if (label) label.textContent = open ? 'collapse' : 'expand';
    if (body) {
      body.hidden = !open;
      if (body.style) body.style.display = open ? '' : 'none';
    }
  }
  function bindAccordion(acc) {
    if (!acc || acc.dataset.accordionBound === '1') return;
    acc.dataset.accordionBound = '1';
    const toggle = acc.querySelector('[data-acc-toggle]');
    const body = findBody(acc);
    if (!toggle || !body) return;
    const initialAttr = acc.getAttribute('data-open');
    const initialOpen = (initialAttr === '1') || (initialAttr !== '0' && !body.hasAttribute('hidden'));
    setAccOpen(acc, initialOpen);
    toggle.addEventListener('click', (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      const isOpen = acc.getAttribute('data-open') === '1';
      setAccOpen(acc, !isOpen);
    });
  }
  window.openAccordion = function (acc) { setAccOpen(acc, true); };
  window.initAccordions = function initAccordions(rootSel) {
    const root = rootSel ? document.querySelector(rootSel) : document;
    if (!root) return;
    root.querySelectorAll('[data-accordion]').forEach(bindAccordion);
  };
})();


// Called after #deid-form swaps its output
(function enhanceDeidHandlers(){
  const prior = window.InteropUI.onDeidentifyComplete;
  window.InteropUI.onDeidentifyComplete = function onDeidentifyComplete(event) {
    const out = document.getElementById('deid-output');
    const text = out ? (out.textContent || '').trim() : '';
    if (text) {
      const message = out.textContent || '';
      window.PipelineContext = window.PipelineContext || {};
      window.PipelineContext.message = message;
      let updatedViaHelper = false;
      if (typeof window.PipelineContext.setMessage === 'function') {
        try {
          window.PipelineContext.setMessage(message);
          updatedViaHelper = true;
        } catch (err) {
          console.warn('PipelineContext.setMessage failed', err);
        }
      }
      if (!updatedViaHelper) {
        document.querySelectorAll('[data-bind="pipeline.message"]').forEach((el) => {
          if (!el) return;
          if ('value' in el) {
            if (el.value !== message) {
              el.value = message;
              try { el.dispatchEvent(new Event('input', { bubbles: true })); } catch (_) { /* ignore */ }
            }
          } else {
            el.textContent = message;
          }
        });
      }
      const tray = document.getElementById('deid-run-tray');
      if (tray) {
        try { tray.hidden = false; } catch (_) { /* noop */ }
        if (tray.hasAttribute?.('hidden')) tray.removeAttribute('hidden');
      }
    }
    if (typeof prior === 'function') {
      try { prior.apply(this, arguments); } catch (err) { console.warn(err); }
    }
    return undefined;
  };
})();

const bootValPanels = () => {
  document.querySelectorAll('[data-val-checks-panel]').forEach((panel) => {
    window.initValChecksPanel(panel);
  });
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
  bootValPanels();
  if (typeof window.initAccordions === 'function') {
    window.initAccordions();
  }
});

document.addEventListener('DOMContentLoaded', () => {
  if (typeof window.initAccordions === 'function') {
    window.initAccordions();
  }
  bootValPanels();
  const valModal = document.querySelector('#val-modal');
  if (valModal && typeof window.initValModal === 'function') {
    window.initValModal(valModal);
  }

  /* Pipeline step buttons expand the right OUTER interop card immediately */
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.pipeline-run');
    if (!btn) return;
    e.preventDefault();
    const to = (btn.getAttribute('data-run-to') || '').toLowerCase();
    if (!to) return;
    const formByName = {
      generate: 'gen-form',
      deid: 'deid-form',
      deidentify: 'deid-form',
      validate: 'validate-form',
      mllp: 'mllp-form'
    };
    function findOuterCard(name) {
      const fid = formByName[name];
      if (fid) {
        const form = document.getElementById(fid);
        if (form) {
          const outer = form.closest('[data-accordion], details.card, .card[data-accordion]');
          if (outer) return outer;
        }
      }
      const guesses = [
        '#' + name + '-panel',
        '#' + name + '-card',
        '#interop-' + name,
        '.interop-card-' + name,
        '.interop-panel-' + name
      ];
      for (const sel of guesses) {
        const el = document.querySelector(sel);
        if (el) {
          return el.closest('[data-accordion], details.card, .card[data-accordion]') || el;
        }
      }
      return null;
    }
    const acc = findOuterCard(to);
    if (!acc) return;
    if (acc.matches && acc.matches('details')) {
      acc.open = true;
    } else {
      window.openAccordion(acc);
    }
    try { acc.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (err) {}
    const focusMap = {
      validate: 'val-text',
      deid: 'deid-text',
      deidentify: 'deid-text',
      mllp: 'mllp-messages',
      generate: 'gen-text'
    };
    const focusId = focusMap[to];
    if (focusId) {
      const field = document.getElementById(focusId);
      if (field) {
        try { field.focus(); } catch (err) {}
      }
    }
  }, { passive: false });
});

/* ========= Interop: open cards from header buttons ========= */
document.addEventListener('click', (event) => {
  const trigger = event.target && event.target.closest('[data-open-card]');
  if (!trigger) return;
  const selector = trigger.getAttribute('data-open-card');
  if (!selector) return;
  const card = document.querySelector(selector);
  if (!card) return;
  event.preventDefault();
  try {
    if (card.matches('details')) {
      card.open = true;
    } else if (card.matches('[data-accordion]')) {
      if (typeof window.openAccordion === 'function') {
        window.openAccordion(card);
      } else {
        card.setAttribute('data-open', '1');
      }
    } else {
      card.classList?.remove('collapsed');
      card.hidden = false;
      if (card.style && card.style.display === 'none') {
        card.style.display = '';
      }
    }
  } catch (_) {}
  try { card.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (_) {}
  window.requestAnimationFrame?.(() => {
    const focusTarget = card.querySelector('textarea, input, select, button');
    if (focusTarget) {
      try { focusTarget.focus({ preventScroll: true }); } catch (_) {}
    }
  });
});

/* ========= Interop: ensure Validate button submits via HTMX ========= */
document.addEventListener('click', (event) => {
  const btn = event.target && event.target.closest('button[data-action="validate"]');
  if (!btn) return;
  const form = btn.closest('form#validate-form') || document.getElementById('validate-form');
  if (!form) return;
  event.preventDefault();
  if (window.htmx && typeof window.htmx.trigger === 'function') {
    window.htmx.trigger(form, 'submit');
  } else if (typeof form.requestSubmit === 'function') {
    form.requestSubmit(btn);
  } else {
    form.submit();
  }
});
