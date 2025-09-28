/* ========== Global utilities ========== */
window.esc = s => (s ?? "").toString()
  .replace(/&/g,"&amp;").replace(/</g,"&lt;")
  .replace(/>/g,"&gt;").replace(/"/g,"&quot;");

/* Minimal diffs (swap with your fuller versions if you already have them) */
window.diffChars = (a,b) => ({ beforeHTML: esc(a ?? ""), afterHTML: esc(b ?? "") });
window.diffLines = (a,b) => ({ beforeHTML: esc(a ?? ""), afterHTML: esc(b ?? "") });

/* ========== De-ID modal initializer ========== */
/* Call this AFTER the modal HTML is inserted (after HTMX settles). */
window.initDeidModal = function initDeidModal(sel) {
  const root = (typeof sel === 'string') ? document.querySelector(sel) : sel;
  if (!root) return;
  try { window.attachParamDebug(root); } catch (e) { console.warn(e); }

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
  const hiddenParamMode = () => form?.querySelector('input[type="hidden"][name="param_mode"]') || null;
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
      beforeField.innerHTML = esc('…'); afterField.innerHTML = esc('…');
      msgBefore.innerHTML   = esc('…'); msgAfter.innerHTML   = esc('…');

      const fd = form ? new FormData(form) : new FormData();
      fd.set('message_text', sampleArea?.value || '');
      if (!fd.has('segment')) fd.set('segment', seg?.value || '');
      if (!fd.has('field')) fd.set('field', fld?.value || '');
      if (!fd.has('component')) fd.set('component', cmp?.value || '');
      if (!fd.has('subcomponent')) fd.set('subcomponent', sub?.value || '');
      const hiddenMode = hiddenParamMode();
      if (hiddenMode) fd.set('param_mode', hiddenMode.value || 'preset');

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
  if (!alreadyInit) {
    [seg,fld,cmp,sub].forEach(el => el && el.addEventListener('input', updatePath));
    if (testBtn && !testBtn.dataset.deidBound) {
      testBtn.addEventListener('click', testDeidRule);
      testBtn.dataset.deidBound = '1';
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
  }

  // first render
  updatePath();
  syncParamModeFromSelect();
};

/* --- Debug wiring for param controls --- */
window.attachParamDebug = function attachParamDebug(root){
  try{
    const owner = root.querySelector('#param-harness');
    const panel = root.querySelector('#param-controls');
    const actionSelect = root.querySelector('#m-action');
    if (!owner || owner.dataset.debugBound === '1') return;
    owner.dataset.debugBound = '1';
    const logArea = document.createElement('pre');
    logArea.id = 'param-debug';
    logArea.style.whiteSpace = 'pre-wrap';
    logArea.style.background = 'rgba(148,163,184,.15)';
    logArea.style.padding = '.5rem';
    logArea.style.borderRadius = '.5rem';
    logArea.style.marginTop = '.5rem';
    logArea.textContent = '[param-debug] init';
    (panel || owner).insertAdjacentElement('afterend', logArea);
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
      bind(owner);
      bind(actionSelect);
    }
  }catch(e){ console.error(e); }
};

/* ========== HTMX hook ==========
   Any time HTMX swaps in content that includes a De-ID modal,
   this will run the initializer automatically. */
document.addEventListener('htmx:afterSettle', (evt) => {
  const modal = document.querySelector('#deid-modal');
  if (modal) window.initDeidModal(modal);
});
