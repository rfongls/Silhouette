(async () => {
  const $ = (sel) => document.querySelector(sel);
  const basePath = document.body?.dataset?.root || '';

  async function run() {
    const endpoint = new URL(basePath + '/api/metrics/search', window.location.origin);
    const since = parseInt($('#since')?.value || '86400', 10);
    [
      ['stage', 'mllp'],
      ['since', since],
      ['ack_code', $('#ack_code')?.value],
      ['hl7_type', $('#hl7_type')?.value],
      ['msh10', $('#msh10')?.value],
      ['q', $('#q')?.value]
    ].forEach(([key, value]) => {
      if (value) endpoint.searchParams.set(key, value);
    });

    const response = await fetch(endpoint.toString(), { cache: 'no-cache' });
    const data = await response.json();
    const box = $('#results');
    if (!box) return;

    if (!data.items || data.items.length === 0) {
      box.innerHTML = '<div class="sample-row"><span class="muted">No results.</span></div>';
      return;
    }

    box.innerHTML = data.items
      .map((item) => {
        const parsed = (() => {
          try {
            return JSON.parse(item.payload || '{}');
          } catch (err) {
            return {};
          }
        })();
        const timestamp = new Date((item.ts || 0) * 1000).toLocaleString();
        const ack = parsed.ack_code || '—';
        const mcid = parsed.msh10 || '—';
        const latency = (item.elapsed_ms ?? 0) + ' ms';
        return `
        <div class="sample-row">
          <div class="sample-title"><strong>${ack}</strong> <span class="muted">ACK</span></div>
          <div class="sample-actions">
            <a class="btn btn-xs" href="${basePath}/ui/interop/pipeline#mllp-panel">Open MLLP</a>
            <a class="btn btn-xs" href="${basePath}/ui/interop/pipeline#translate-panel">Open FHIR</a>
          </div>
          <div class="sample-meta">
            <span class="muted">When:</span> <code>${timestamp}</code>
            <span class="muted">Type:</span> <code>${item.hl7_type || '—'}</code>
            <span class="muted">MSH-10:</span> <code>${mcid}</code>
            <span class="muted">ACK latency:</span> <code>${latency}</code>
          </div>
        </div>`;
      })
      .join('');
  }

  document.getElementById('search')?.addEventListener('click', (event) => {
    event.preventDefault();
    run();
  });
})();
