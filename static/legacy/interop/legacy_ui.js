(function () {
  const $1 = (r, s) => r.querySelector(s);
  const $$ = (r, s) => Array.from(r.querySelectorAll(s));

  // Copy helpers
  window.InteropUI = window.InteropUI || {};
  window.InteropUI.copyFrom = function (fromSelector, toSelector) {
    try {
      const src = $1(document, fromSelector);
      const dest = $1(document, toSelector);
      if (!src || !dest) return;
      const text = src.tagName === 'PRE' ? src.textContent : (src.value ?? src.textContent ?? '');
      dest.value = (text || '').trim();
      dest.dispatchEvent(new Event('input', { bubbles: true }));
    } catch (_) {}
  };
  window.InteropUI.loadFileIntoTextarea = function(inputEl, targetId){
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
    } catch (_) {}
  };

  // Extract text from pipeline result container and auto-send via MLLP
  function extractText(container) {
    if (!container) return '';
    const pre = container.querySelector('pre');
    if (pre && pre.textContent) return pre.textContent.trim();
    return (container.textContent || '').trim();
  }
  function autoSendPipelineResult(evt){
    if (!evt || !evt.target || evt.target.id !== 'pipeline-output') return;
    const text = extractText(evt.target);
    if (!text || !text.startsWith('MSH')) return;
    const msg = $1(document, '#mllp-messages');
    if (msg) { msg.value = text; msg.dispatchEvent(new Event('input', { bubbles: true })); }
    const form = $1(document, '#mllp-form');
    if (form && window.htmx) {
      const panel = $1(document, '#mllp-panel');
      try { panel?.scrollIntoView?.({ behavior:'smooth', block:'start' }); } catch(_){ }
      window.htmx.trigger(form, 'submit');
    }
  }

  // Hook HTMX
  if (document.body) {
    document.body.addEventListener('htmx:afterSwap', autoSendPipelineResult);
  }
})();
