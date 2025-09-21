(async () => {
  const $ = (sel) => document.querySelector(sel);
  const basePath = document.body?.dataset?.root || '';

  async function loadSummary() {
    const win = parseInt($('#v_window')?.value || '86400', 10);
    const res = await fetch(`${basePath}/api/metrics/validate_summary?window=${win}`);
    const data = await res.json();
    const box = $('#v_summary');
    if (!box) return;
    box.innerHTML = `
      <div>Total validations: <strong>${(data.total || 0).toLocaleString()}</strong></div>
      <div>Success rate: <strong>${((data.success_rate || 0) * 100).toFixed(1)}%</strong></div>
      <div>Avg latency: <strong>${data.avg_ms || 0} ms</strong></div>
      <div>Top errors: <code>${(data.top_errors || []).map((e) => e.code).join(', ') || '—'}</code></div>`;
  }

  async function search() {
    const win = parseInt($('#v_window')?.value || '86400', 10);
    const q = $('#v_q')?.value || '';
    const res = await fetch(`${basePath}/api/metrics/validate_search?window=${win}&q=${encodeURIComponent(q)}`);
    const data = await res.json();
    const box = $('#v_results');
    if (!box) return;
    if (!data.items || !data.items.length) {
      box.innerHTML = '<div class="sample-row">No results.</div>';
      return;
    }

    box.innerHTML = data.items
      .map((item) => {
        const ts = new Date((item.ts || 0) * 1000).toLocaleString();
        const meta = item.payload || {};
        const errors = meta.error_count ?? '—';
        const warns = meta.warning_count ?? '—';
        return `
        <div class="sample-row">
          <div class="sample-title"><strong>${item.hl7_type || '—'}</strong> <span class="muted">(${item.status})</span></div>
          <div class="sample-meta">
            <span class="muted">When:</span> <code>${ts}</code>
            <span class="muted">Errors:</span> <code>${errors}</code>
            <span class="muted">Warnings:</span> <code>${warns}</code>
            <span class="muted">Profile:</span> <code>${meta.profile || 'base'}</code>
          </div>
          <details><summary>Details</summary><pre class="codepane">${JSON.stringify(meta.top_errors || meta, null, 2)}</pre></details>
        </div>`;
      })
      .join('');
  }

  $('#v_search')?.addEventListener('click', (event) => {
    event.preventDefault();
    search();
  });

  $('#v_window')?.addEventListener('change', () => {
    loadSummary();
    search();
  });

  document.addEventListener('DOMContentLoaded', () => {
    loadSummary();
  });

  loadSummary();
})();
