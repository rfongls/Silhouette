// static/js/validate_panel.js
(() => {
  'use strict';
  const $ = (sel) => document.querySelector(sel);
  const basePath = document.body?.dataset?.root || '';

  window.InteropUI = window.InteropUI || {};
  const original = window.InteropUI.onValidateComplete;

  window.InteropUI.onValidateComplete = function (event) {
    try {
      const meta = (event && event.detail?.meta) || event?.meta || {};
      const version = meta.hl7_version || meta.version || 'v2.x';
      const profile = meta.profile || meta.schema || 'base';
      const target = `${version}${profile ? ' · ' + profile : ''}`;
      const targetEl = $('#validate-target');
      if (targetEl) targetEl.textContent = target;

      if (meta && (meta.top_errors || meta.error_count != null || meta.warning_count != null)) {
        const payload = {
          stage: 'validate',
          status: meta.error_count > 0 ? 'fail' : 'success',
          elapsed_ms: meta.elapsed_ms || 0,
          hl7_type: meta.hl7_type,
          hl7_version: version,
          top_errors: meta.top_errors,
          error_count: meta.error_count,
          warning_count: meta.warning_count
        };
        try {
          fetch(`${basePath}/api/metrics/event`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          }).catch(() => {});
        } catch (err) {
          /* ignore */
        }
      }
    } catch (err) {
      /* ignore */
    }

    if (typeof original === 'function') {
      return original.apply(this, arguments);
    }
    return undefined;
  };

  document.addEventListener('click', (event) => {
    if (event.target && event.target.id === 'print-validate-report') {
      event.preventDefault();
      const meta = $('#validate-target')?.textContent || '';
      const body = $('#validation-results')?.innerHTML || '';
      const popup = window.open('', '_blank', 'width=900,height=700');
      if (!popup) return;
      popup.document.write(`<!DOCTYPE html><html><head><title>Validation Report</title>
        <style>body{font:14px system-ui;margin:24px;color:#111}h1{font-size:18px}
        .meta{margin-bottom:12px;color:#555}pre,code{white-space:pre-wrap;word-break:break-word}
        .box{border:1px solid #ddd;border-radius:8px;padding:12px}</style></head>
        <body><h1>Validation Report</h1>
        <div class="meta"><strong>Validated against:</strong> ${meta}</div>
        <div class="box">${body}</div></body></html>`);
      popup.document.close();
      popup.focus();
      popup.print();
    }
  });
})();
