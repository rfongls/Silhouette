// interop_ui.js — streamlined interoperability helpers
//
// Responsibilities:
//  • Populate trigger selectors/datalists for Generate + Pipeline panels
//  • Keep template relpath hints in sync with the chosen trigger
//  • Provide helper APIs for sample usage + file loading
//  • Wire de-identification coverage + validation report filters (resilient to HTMX swaps)
//  • Remain idempotent so it can be invoked after HTMX out-of-band swaps

(function(){
  'use strict';

  // ------------------------------
  // DOM helpers
  // ------------------------------
  const $$ = (root, sel) => Array.from((root || document).querySelectorAll(sel));
  const $1 = (root, sel) => (root || document).querySelector(sel);

  // Resolve the application root prefix once; used for fetch/beacon calls.
  function rootPath(path){
    const doc = typeof document !== 'undefined' ? document : null;
    const win = typeof window !== 'undefined' ? window : null;
    let base = '';
    if (doc?.body?.dataset?.root) {
      base = doc.body.dataset.root;
    } else if (doc) {
      const meta = doc.querySelector('meta[name="root-path"]');
      if (meta) base = meta.getAttribute('content') || '';
    }
    if (!base && win && typeof win.ROOT === 'string') base = win.ROOT;
    base = base === '/' ? '' : (base || '').replace(/\/+$/, '');
    if (!path) return base;
    const suffix = path.startsWith('/') ? path : `/${path.replace(/^\/+/, '')}`;
    return `${base}${suffix}`;
  }

  function sendDebug(name, payload){
    try {
      const body = JSON.stringify({ event: name, ts: new Date().toISOString(), ...(payload || {}) });
      const url = rootPath('/api/diag/debug/event');
      if (navigator.sendBeacon) {
        navigator.sendBeacon(url, new Blob([body], { type: 'application/json' }));
      } else if (window.fetch) {
        fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body });
      }
    } catch (_) {
      /* ignore */
    }
  }

  // Maintain a single global namespace for interoperability helpers.
  const InteropUI = (window.InteropUI = window.InteropUI || {});

  // ------------------------------
  // Trigger template helpers
  // ------------------------------
  function setTemplateHint(prefix, relpath){
    const hint = $1(document, `#${prefix}-template-hint`);
    if (!hint) return;
    const empty = hint.getAttribute('data-empty') || hint.dataset?.empty || 'No template selected.';
    if (relpath) {
      hint.textContent = relpath;
      hint.classList.remove('muted');
    } else {
      hint.textContent = empty;
      hint.classList.add('muted');
    }
  }

  function syncTemplateRelpath(prefix){
    const input = $1(document, `#${prefix}-trigger-typed`);
    const hidden = $1(document, `#${prefix}-template-relpath`) || input?.form?.querySelector('input[name="template_relpath"]');
    const dl = $1(document, `#${prefix}-trigger-datalist`);
    if (!input || !hidden || !dl) {
      setTemplateHint(prefix, hidden ? hidden.value : '');
      return;
    }

    const want = (input.value || '').trim().toUpperCase();
    const options = dl.options ? Array.from(dl.options) : $$(dl, 'option');
    let rel = '';
    if (want) {
      for (const opt of options) {
        const value = (opt.value || '').trim().toUpperCase();
        if (value === want) {
          rel = opt.getAttribute('data-relpath') || opt.dataset?.relpath || '';
          break;
        }
      }
    }
    hidden.value = rel;
    setTemplateHint(prefix, rel);
  }
  InteropUI.syncTemplateRelpath = syncTemplateRelpath;

  function syncTyped(prefix){
    const input = $1(document, `#${prefix}-trigger-typed`);
    if (!input) return;
    const select = $1(document, `#${prefix}-trigger-select`);
    const want = (input.value || '').trim().toUpperCase();
    let matchedValue = null;
    if (select) {
      for (const opt of Array.from(select.options || [])) {
        const value = (opt.value || '').trim().toUpperCase();
        if (value === want) {
          matchedValue = opt.value;
          break;
        }
      }
      if (matchedValue !== null) select.value = matchedValue;
    }
    syncTemplateRelpath(prefix);
    const hidden = $1(document, `#${prefix}-template-relpath`) || input.form?.querySelector('input[name="template_relpath"]');
    if (hidden && matchedValue !== null && select) {
      const chosen = Array.from(select.options).find(opt => opt.value === select.value);
      const rel = chosen ? (chosen.getAttribute('data-relpath') || chosen.dataset?.relpath || '') : '';
      if (rel) {
        hidden.value = rel;
        setTemplateHint(prefix, rel);
      }
    }
  }
  InteropUI.syncTyped = syncTyped;

  async function fillDatalist(prefix){
    const dl = $1(document, `#${prefix}-trigger-datalist`);
    const select = $1(document, `#${prefix}-trigger-select`);
    if (!dl && !select) return;

    const versionSel = $1(document, `#${prefix}-version`) || $1(document, '#gen-version') || $1(document, '#pipe-version');
    const version = versionSel ? versionSel.value : 'hl7-v2-4';

    try {
      const resp = await fetch(rootPath(`/api/interop/triggers?version=${encodeURIComponent(version)}`), { cache: 'no-cache' });
      const data = await resp.json();
      const items = Array.isArray(data?.items) ? data.items : [];

      if (dl) {
        dl.innerHTML = '';
        const seen = new Set();
        for (const it of items) {
          const trigger = String(it.trigger || '').trim();
          if (!trigger) continue;
          const key = trigger.toUpperCase();
          if (seen.has(key)) continue;
          seen.add(key);
          const opt = document.createElement('option');
          opt.value = trigger;
          if (it.relpath) opt.setAttribute('data-relpath', it.relpath);
          if (it.description) opt.label = `${trigger} — ${it.description}`;
          dl.appendChild(opt);
        }
      }

      if (select) {
        const previous = select.value;
        select.innerHTML = '';
        const seen = new Set();
        for (const it of items) {
          const trigger = String(it.trigger || '').trim();
          if (!trigger) continue;
          const key = trigger.toUpperCase();
          if (seen.has(key)) continue;
          seen.add(key);
          const opt = document.createElement('option');
          opt.value = trigger;
          opt.textContent = trigger;
          if (it.relpath) opt.setAttribute('data-relpath', it.relpath);
          select.appendChild(opt);
        }
        if (Array.from(select.options).some(opt => opt.value === previous)) {
          select.value = previous;
        }
      }

      sendDebug('interop.triggers.loaded', { prefix, version, count: items.length });
    } catch (err) {
      console.warn('fillDatalist error', err);
      sendDebug('interop.triggers.error', { prefix, version, message: String(err) });
    }
  }
  InteropUI.fillDatalist = fillDatalist;

  function useSample(prefix, payload){
    const data = payload || {};
    const versionSel = $1(document, `#${prefix}-version`) || $1(document, '#gen-version');
    if (versionSel && data.version) versionSel.value = data.version;
    const triggerInput = $1(document, `#${prefix}-trigger-typed`);
    if (triggerInput && data.trigger) triggerInput.value = data.trigger;
    const hidden = $1(document, `#${prefix}-template-relpath`) || triggerInput?.form?.querySelector('input[name="template_relpath"]');
    if (hidden && data.relpath) hidden.value = data.relpath;
    setTemplateHint(prefix, data.relpath || '');
    syncTemplateRelpath(prefix);
  }
  InteropUI.useSample = useSample;

  // File loader used in the MLLP panel.
  function loadFileIntoTextarea(inputEl, targetId){
    try {
      const fileInput = typeof inputEl === 'string' ? $1(document, inputEl) : inputEl;
      const textarea = $1(document, targetId ? `#${targetId}` : '#mllp-messages');
      const file = fileInput?.files?.[0];
      if (!file || !textarea) return;
      const reader = new FileReader();
      reader.onload = () => {
        textarea.value = reader.result || '';
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
      };
      reader.readAsText(file);
    } catch (_) {
      /* noop */
    }
  }
  InteropUI.loadFileIntoTextarea = loadFileIntoTextarea;

  // Stubs for panels that listen for completion events.
  InteropUI.onGenerateComplete = function(){};
  InteropUI.onDeidentifyComplete = function(){};
  InteropUI.onValidateComplete = function(){};
  InteropUI.onMllpComplete = function(){};

  // ------------------------------
  // De-identification report filtering
  // ------------------------------
  function initDeidCoverage(context){
    const scopes = [];
    if (context?.matches?.('[data-deid-root]')) scopes.push(context);
    scopes.push(...$$((context || document), '[data-deid-root]'));

    for (const root of scopes) {
      if (!root || root.dataset.deidInit === '1') continue;
      const segSel = $1(root, '[data-role="deid-filter-seg"]');
      const fieldSel = $1(root, '[data-role="deid-filter-field"]');
      const actionSel = $1(root, '[data-role="deid-filter-action"]');
      const valueInput = $1(root, '[data-role="deid-filter-value"]');
      const resetBtn = $1(root, '[data-role="deid-filter-reset"]');
      const noteEl = $1(root, '[data-role="deid-note"]');
      const emptyRow = $1(root, '[data-role="deid-empty"]');
      const rows = $$ (root, '[data-role="deid-row"]');
      if (!segSel || !fieldSel || !actionSel || !valueInput || !rows.length) {
        root.dataset.deidInit = '1';
        continue;
      }
      root.dataset.deidInit = '1';

      const state = rows.map(tr => {
        const seg = (tr.dataset.segment || '').trim();
        const field = (tr.dataset.field || '').trim();
        const action = (tr.dataset.action || '').trim();
        const logic = (tr.dataset.logic || '').trim();
        return {
          el: tr,
          segment: seg,
          field,
          action,
          segNorm: seg.toLowerCase(),
          fieldNorm: field.toLowerCase(),
          actionNorm: action.toLowerCase(),
          search: [seg, field, action, logic, tr.textContent || ''].join(' ').toLowerCase()
        };
      });

      const fieldsBySeg = new Map();
      const allFields = new Set();
      for (const row of state) {
        if (row.segment && row.field) {
          const key = row.segment.toLowerCase();
          if (!fieldsBySeg.has(key)) fieldsBySeg.set(key, new Set());
          fieldsBySeg.get(key).add(row.field);
        }
        if (row.field) allFields.add(row.field);
      }

      function sortedFields(values){
        return values.sort((a, b) => {
          const na = parseInt(a, 10);
          const nb = parseInt(b, 10);
          if (!Number.isNaN(na) && !Number.isNaN(nb) && na !== nb) return na - nb;
          return String(a).localeCompare(String(b));
        });
      }

      function rebuildFieldOptions(){
        const segValue = segSel.value;
        const prev = fieldSel.value;
        fieldSel.innerHTML = '<option value="all">All</option>';
        let fields;
        if (!segValue || segValue === 'all') {
          fields = sortedFields(Array.from(allFields));
        } else {
          fields = sortedFields(Array.from(fieldsBySeg.get(segValue.toLowerCase()) || []));
        }
        fields.forEach(field => {
          const opt = document.createElement('option');
          opt.value = field;
          opt.textContent = field;
          fieldSel.appendChild(opt);
        });
        if (Array.from(fieldSel.options).some(opt => opt.value === prev)) fieldSel.value = prev;
      }

      function rebuildActionOptions(){
        const segValue = (segSel.value || '').toLowerCase();
        const fieldValue = (fieldSel.value || '').toLowerCase();
        const prev = actionSel.value;
        actionSel.innerHTML = '<option value="all">All</option>';
        const actions = new Set();
        for (const row of state) {
          if (segValue && segValue !== 'all' && row.segNorm !== segValue) continue;
          if (fieldValue && fieldValue !== 'all' && row.fieldNorm !== fieldValue) continue;
          if (row.action) actions.add(row.action);
        }
        Array.from(actions).sort().forEach(action => {
          const opt = document.createElement('option');
          opt.value = action;
          opt.textContent = action;
          actionSel.appendChild(opt);
        });
        if (Array.from(actionSel.options).some(opt => opt.value === prev)) actionSel.value = prev;
      }

      function apply(){
        const seg = (segSel.value || 'all').toLowerCase();
        const field = (fieldSel.value || 'all').toLowerCase();
        const action = (actionSel.value || 'all').toLowerCase();
        const query = (valueInput.value || '').trim().toLowerCase();
        let visible = 0;
        for (const row of state) {
          let show = true;
          if (seg !== 'all' && row.segNorm !== seg) show = false;
          if (show && field !== 'all' && row.fieldNorm !== field) show = false;
          if (show && action !== 'all' && row.actionNorm !== action) show = false;
          if (show && query && !row.search.includes(query)) show = false;
          row.el.style.display = show ? '' : 'none';
          if (show) visible += 1;
        }
        if (emptyRow) emptyRow.style.display = visible ? 'none' : '';
        if (noteEl) noteEl.style.display = visible ? 'none' : '';
      }

      segSel.addEventListener('change', () => {
        rebuildFieldOptions();
        rebuildActionOptions();
        apply();
      });
      fieldSel.addEventListener('change', () => {
        rebuildActionOptions();
        apply();
      });
      actionSel.addEventListener('change', apply);
      valueInput.addEventListener('input', apply);
      if (resetBtn) {
        resetBtn.addEventListener('click', () => {
          segSel.value = 'all';
          rebuildFieldOptions();
          fieldSel.value = 'all';
          rebuildActionOptions();
          actionSel.value = 'all';
          valueInput.value = '';
          apply();
        });
      }

      rebuildFieldOptions();
      rebuildActionOptions();
      apply();
    }
  }
  InteropUI.initDeidCoverage = initDeidCoverage;

  // ------------------------------
  // Validation report helper
  // ------------------------------
  function initValidateReport(context){
    const scopes = [];
    if (context?.matches?.('[data-val-root]')) scopes.push(context);
    scopes.push(...$$((context || document), '[data-val-root]'));

    for (const root of scopes) {
      if (!root || root.dataset.valInit === '1') continue;
      const dataEl = $1(root, '[data-role="val-issues"]');
      const body = $1(root, '[data-role="val-summary-body"]');
      const emptyRow = $1(root, '[data-role="val-empty"]');
      const severitySelect = $1(root, '[data-role="val-filter-sev"]');
      const segmentSelect = $1(root, '[data-role="val-filter-seg"]');
      const searchInput = $1(root, '[data-role="val-filter-text"]');
      const resetBtn = $1(root, '[data-role="val-filter-reset"]');
      const chips = $$ (root, '.validate-report__counts .chip[data-vf]');
      if (!dataEl || !body || !severitySelect || !segmentSelect || !searchInput) {
        root.dataset.valInit = '1';
        continue;
      }
      root.dataset.valInit = '1';

      let issues = [];
      try {
        issues = JSON.parse(dataEl.textContent || '[]') || [];
      } catch (_) {
        issues = [];
      }
      const TOTAL = Math.max(parseInt(dataEl.dataset.total || '0', 10) || issues.length || 0, 1);

      const clean = value => (value === null || value === undefined ? '' : String(value).trim());
      const cleanZeroable = value => (value === 0 ? '0' : clean(value));
      const normSeverity = value => {
        const s = clean(value).toLowerCase();
        if (s.includes('warn')) return 'warning';
        if (s.includes('pass') || s.includes('ok') || s.includes('info')) return 'passed';
        return 'error';
      };

      const normalized = (Array.isArray(issues) ? issues : []).map(item => ({
        severity: normSeverity(item?.severity ?? item?.status ?? 'error'),
        code: clean(item?.code ?? item?.rule ?? item?.id ?? ''),
        segment: clean(item?.segment ?? item?.seg ?? ''),
        field: cleanZeroable(item?.field),
        component: cleanZeroable(item?.component ?? item?.comp),
        subcomponent: cleanZeroable(item?.subcomponent ?? item?.subcomp),
        value: clean(item?.value ?? item?.actual ?? item?.received ?? item?.bad_value ?? ''),
        message: clean(item?.message ?? item?.msg ?? '')
      }));

      const bucketsMap = new Map();
      normalized.forEach(issue => {
        const key = [
          issue.severity,
          issue.code,
          issue.segment.toLowerCase(),
          (issue.field || '').toLowerCase(),
          (issue.component || '').toLowerCase(),
          (issue.subcomponent || '').toLowerCase()
        ].join('|');
        let bucket = bucketsMap.get(key);
        if (!bucket) {
          bucket = {
            severity: issue.severity,
            code: issue.code,
            segment: issue.segment,
            field: issue.field || '',
            component: issue.component || '',
            subcomponent: issue.subcomponent || '',
            message: issue.message,
            values: new Set(),
            count: 0
          };
          bucketsMap.set(key, bucket);
        }
        if (issue.value) {
          bucket.values.add(issue.value);
        } else {
          const match = issue.message.match(/'([^']+)'/g);
          if (match) match.forEach(v => bucket.values.add(v.replace(/'/g, '')));
        }
        bucket.count += 1;
      });

      body.innerHTML = '';
      const severityOrder = severity => (severity === 'error' ? 0 : severity === 'warning' ? 1 : 2);
      const buckets = Array.from(bucketsMap.values()).sort((a, b) => {
        const sev = severityOrder(a.severity) - severityOrder(b.severity);
        if (sev !== 0) return sev;
        if (a.segment !== b.segment) return a.segment.localeCompare(b.segment);
        const na = parseInt(a.field || '0', 10);
        const nb = parseInt(b.field || '0', 10);
        if (!Number.isNaN(na) && !Number.isNaN(nb) && na !== nb) return na - nb;
        return a.code.localeCompare(b.code);
      });

      const rows = buckets.map(bucket => {
        const values = Array.from(bucket.values);
        const shown = values.slice(0, 8);
        const extra = values.length > shown.length ? ` (+${values.length - shown.length} more)` : '';
        const tr = document.createElement('tr');
        tr.dataset.role = 'val-row';
        tr.dataset.severity = bucket.severity;
        tr.dataset.segment = (bucket.segment || '').trim().toLowerCase();
        tr.dataset.text = [bucket.code, bucket.segment, bucket.field, bucket.component, bucket.subcomponent, values.join(' '), bucket.message].join(' ').toLowerCase();
        tr.innerHTML = [
          `<td style="padding:0.5rem">${bucket.severity === 'passed' ? 'Passed' : bucket.severity === 'warning' ? 'Warning' : 'Error'}</td>`,
          `<td style="padding:0.5rem"><code class="mono">${bucket.code || '—'}</code></td>`,
          `<td style="padding:0.5rem"><code class="mono">${bucket.segment || '—'}</code></td>`,
          `<td style="padding:0.5rem"><code class="mono">${bucket.field || '—'}</code></td>`,
          `<td style="padding:0.5rem"><code class="mono">${bucket.component || '—'}</code></td>`,
          `<td style="padding:0.5rem"><code class="mono">${bucket.subcomponent || '—'}</code></td>`,
          `<td style="padding:0.5rem">${shown.length ? shown.join(', ') : '—'}${extra}</td>`,
          `<td style="padding:0.5rem">${bucket.message || '—'}</td>`,
          `<td style="padding:0.5rem">${bucket.count}</td>`,
          `<td style="padding:0.5rem">${TOTAL}</td>`,
          `<td style="padding:0.5rem">${Math.round((bucket.count / TOTAL) * 100)}%</td>`
        ].join('');
        body.appendChild(tr);
        return tr;
      });

      if (!rows.length && emptyRow) emptyRow.style.display = '';

      const normalizeMode = value => {
        const v = String(value || '').toLowerCase();
        if (v.includes('warn')) return 'warning';
        if (v.includes('pass') || v.includes('ok') || v.includes('info')) return 'passed';
        if (v === 'all') return 'all';
        return 'error';
      };

      let chipMode = normalizeMode(severitySelect.dataset.initial || severitySelect.value || 'error');

      function syncChips(){
        chips.forEach(chip => {
          const mode = normalizeMode(chip.dataset.vf);
          const active = mode === chipMode;
          chip.classList.toggle('active', active);
          chip.setAttribute('aria-pressed', active ? 'true' : 'false');
        });
      }

      function apply(){
        const wantSev = normalizeMode(severitySelect.value || chipMode);
        const wantSeg = (segmentSelect.value || '').trim().toLowerCase();
        const query = (searchInput.value || '').trim().toLowerCase();
        let visible = 0;
        rows.forEach(tr => {
          const sev = (tr.dataset.severity || '').trim().toLowerCase();
          const seg = (tr.dataset.segment || '').trim().toLowerCase();
          const text = tr.dataset.text || '';
          let show = true;
          if (chipMode !== 'all') show = show && sev === chipMode;
          if (show && wantSev && wantSev !== 'all') show = show && sev === wantSev;
          if (show && wantSeg && wantSeg !== 'all') show = show && seg === wantSeg;
          if (show && query) show = show && text.includes(query);
          tr.style.display = show ? '' : 'none';
          if (show) visible += 1;
        });
        if (emptyRow) emptyRow.style.display = visible ? 'none' : '';
        syncChips();
      }

      const segInitial = segmentSelect.dataset.initial || 'all';
      if (Array.from(segmentSelect.options).some(opt => opt.value === segInitial)) segmentSelect.value = segInitial;
      const sevInitial = severitySelect.dataset.initial || 'error';
      severitySelect.value = sevInitial;
      const searchInitial = searchInput.dataset.initial || '';
      searchInput.value = searchInitial;

      severitySelect.addEventListener('change', () => {
        chipMode = normalizeMode(severitySelect.value);
        apply();
      });
      segmentSelect.addEventListener('change', apply);
      searchInput.addEventListener('input', apply);
      chips.forEach(chip => {
        chip.addEventListener('click', () => {
          chipMode = normalizeMode(chip.dataset.vf);
          severitySelect.value = chipMode === 'all' ? 'all' : chipMode;
          apply();
        });
      });
      if (resetBtn) {
        resetBtn.addEventListener('click', () => {
          chipMode = 'error';
          severitySelect.value = 'error';
          segmentSelect.value = 'all';
          searchInput.value = '';
          apply();
        });
      }

      apply();
    }
  }
  InteropUI.initValidateReport = initValidateReport;

  // ------------------------------
  // Bootstrapping + HTMX integration
  // ------------------------------
  function prime(context){
    try { initDeidCoverage(context || document); } catch (_) {}
    try { initValidateReport(context || document); } catch (_) {}
  }

  function onReady(){
    prime(document);
    fillDatalist('gen');
    fillDatalist('pipe');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', onReady);
  } else {
    onReady();
  }

  if (typeof document !== 'undefined' && document.body) {
    const handler = evt => {
      const target = (evt?.detail && (evt.detail.elt || evt.detail.target)) || evt?.target || document;
      prime(target);
    };
    document.body.addEventListener('htmx:afterSwap', handler);
    document.body.addEventListener('htmx:oobAfterSwap', handler);
    document.body.addEventListener('htmx:afterSettle', handler);
  }
})();
