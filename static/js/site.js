/* ========== Global utilities ========== */
window.esc = s => (s ?? "").toString()
  .replace(/&/g,"&amp;").replace(/</g,"&lt;")
  .replace(/>/g,"&gt;").replace(/"/g,"&quot;");

/* Minimal diffs (swap with your fuller versions if you already have them) */
window.diffChars = (a,b) => ({ beforeHTML: esc(a ?? ""), afterHTML: esc(b ?? "") });
window.diffLines = (a,b) => ({ beforeHTML: esc(a ?? ""), afterHTML: esc(b ?? "") });

/* ========== De-ID modal initializer ========== */
/* Call this AFTER the modal HTML is inserted (HTMX after-swap). */
window.initDeidModal = function initDeidModal(sel) {
  const root = (typeof sel === 'string') ? document.querySelector(sel) : sel;
  if (!root) return;

  const $ = id => root.querySelector(id);

  const seg = $('#m-seg'), fld = $('#m-field'), cmp = $('#m-comp'), sub = $('#m-sub');
  const actionSel = $('#m-action');
  const modeWrap  = $('#m-param-mode-wrap');
  const modeSel   = $('#m-param-mode');
  const presetW   = $('#m-preset-wrap'), presetSel = $('#m-preset');
  const freeW     = $('#m-free-wrap'),   freeInp    = $('#m-free');
  const regexW    = $('#m-regex-wrap'),  rxPat      = $('#m-rx-pattern'), rxReplW = $('#m-rx-repl-wrap'), rxRepl = $('#m-rx-repl');
  const pathBadge = $('#m-path-badge');
  const hiddenParam = $('#m-param-hidden');
  const beforeField = $('#m-before-diff'), afterField = $('#m-after-diff');
  const msgBefore   = $('#m-msg-before'),  msgAfter   = $('#m-msg-after');
  const sampleArea  = $('#m-sample');
  const form        = root.querySelector('form');

  function formatPath(){
    const s=(seg?.value||'').trim().toUpperCase();
    const f=(fld?.value||'').trim(), c=(cmp?.value||'').trim(), u=(sub?.value||'').trim();
    if(!s||!f) return '—';
    return s + ':' + f + (c?'.'+c:'') + (u?'.'+u:'');
  }
  function updatePath(){ if(pathBadge) pathBadge.textContent = formatPath(); }

  function updateHiddenParam() {
    if (!hiddenParam) return;
    const action = actionSel?.value || '';
    hiddenParam.name = ''; hiddenParam.value = '';
    [presetSel, freeInp, rxPat, rxRepl].forEach(el => { if (el) el.name = ''; });

    if (action === 'preset') {
      if (modeSel?.value === 'preset') { presetSel.name = 'param'; }
      else { freeInp.name = 'param'; }
      return;
    }
    if (action === 'replace' || action === 'mask' || action === 'hash') {
      freeInp.name = 'param'; return;
    }
    if (action === 'regex_redact') {
      rxPat.name = 'param'; return;
    }
    if (action === 'regex_replace') {
      // We serialize to JSON as the single param carrier
      hiddenParam.name = 'param';
      hiddenParam.value = JSON.stringify({ pattern: rxPat?.value || '', repl: rxRepl?.value || '' });
    }
  }

  function syncParamUI(){
    const act = actionSel?.value || '';
    // hide all blocks
    if (modeWrap) modeWrap.style.display = 'none';
    if (presetW)  presetW.style.display  = 'none';
    if (freeW)    freeW.style.display    = 'none';
    if (regexW)   regexW.style.display   = 'none';
    if (rxReplW)  rxReplW.style.display  = 'none';

    if (act === 'preset') {
      modeWrap.style.display = '';
      if (modeSel.value === 'preset') presetW.style.display = '';
      else freeW.style.display = '';
    } else if (act === 'replace' || act === 'mask' || act === 'hash') {
      freeW.style.display = '';
    } else if (act === 'regex_redact') {
      regexW.style.display = '';
    } else if (act === 'regex_replace') {
      regexW.style.display = ''; rxReplW.style.display = '';
    }
    updateHiddenParam();
  }

  async function testDeidRule(){
    try{
      beforeField.innerHTML = esc('…'); afterField.innerHTML = esc('…');
      msgBefore.innerHTML   = esc('…'); msgAfter.innerHTML   = esc('…');

      const fd = new FormData();
      fd.append('message_text', sampleArea?.value || '');
      fd.append('segment', seg?.value || '');
      fd.append('field',   fld?.value || '');
      fd.append('component', cmp?.value || '');
      fd.append('subcomponent', sub?.value || '');
      const act = actionSel?.value || ''; fd.append('action', act);

      updateHiddenParam();
      let param = '';
      if (act === 'preset'){
        param = (modeSel.value === 'preset') ? (presetSel?.value || '') : (freeInp?.value || '');
      } else if (act === 'replace' || act === 'mask' || act === 'hash'){
        param = freeInp?.value || '';
      } else if (act === 'regex_redact'){
        param = rxPat?.value || '';
      } else if (act === 'regex_replace'){
        param = JSON.stringify({ pattern: rxPat?.value || '', repl: rxRepl?.value || '' });
      }
      fd.append('param', param);

      const url = root.getAttribute('data-test-endpoint');
      const resp = await fetch(url, { method:'POST', body: fd });
      let data; try { data = await resp.json(); } catch { data = { ok:false, error:'Non-JSON response' }; }

      if (!data.ok) {
        beforeField.innerHTML = '—';
        afterField.innerHTML  = esc('Error: ' + (data.error || 'unknown'));
        msgBefore.innerHTML   = esc(sampleArea?.value || '');
        msgAfter.innerHTML    = esc(sampleArea?.value || '');
        return;
      }

      const beforeVal = data.preview.before ?? '';
      const afterVal  = data.preview.after  ?? '';
      const dField    = window.diffChars(beforeVal, afterVal);
      beforeField.innerHTML = dField.beforeHTML; afterField.innerHTML = dField.afterHTML;

      const lineB = data.preview.line_before ?? sampleArea?.value || '';
      const lineA = data.preview.line_after  ?? data.preview.message_after ?? sampleArea?.value || '';
      const dMsg  = window.diffLines(lineB, lineA);
      msgBefore.innerHTML = dMsg.beforeHTML; msgAfter.innerHTML = dMsg.afterHTML;
    }catch(e){
      afterField.innerHTML = esc('JS error: '+e);
    }
  }

  // wire events (scoped to this modal)
  if (actionSel) actionSel.addEventListener('change', syncParamUI);
  if (modeSel)   modeSel.addEventListener('change', syncParamUI);
  [seg,fld,cmp,sub].forEach(el => el && el.addEventListener('input', updatePath));
  if (form) form.addEventListener('submit', updateHiddenParam);
  const testBtn = root.querySelector('[data-deid-test]');
  if (testBtn) testBtn.addEventListener('click', testDeidRule);

  // first render
  updatePath(); syncParamUI();
};

/* ========== HTMX hook ==========
   Any time HTMX swaps in content that includes a De-ID modal,
   this will run the initializer automatically. */
document.addEventListener('htmx:afterSwap', (evt) => {
  const modal = document.querySelector('#deid-modal');
  if (modal) window.initDeidModal(modal);
});
