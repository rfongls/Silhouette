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
  const pathBadge = $('#m-path-badge');
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
  [seg,fld,cmp,sub].forEach(el => el && el.addEventListener('input', updatePath));
  const testBtn = root.querySelector('[data-deid-test]');
  if (testBtn) testBtn.addEventListener('click', testDeidRule);

  // first render
  updatePath();
};

/* ========== HTMX hook ==========
   Any time HTMX swaps in content that includes a De-ID modal,
   this will run the initializer automatically. */
document.addEventListener('htmx:afterSwap', (evt) => {
  const modal = document.querySelector('#deid-modal');
  if (modal) window.initDeidModal(modal);
});
