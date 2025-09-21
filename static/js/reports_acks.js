(() => {
  const $ = (sel) => document.querySelector(sel);
  const root = document.querySelector('meta[name="root-path"]')?.content || '';
  const resultsBox = $('#results');
  const searchBtn = $('#search');

  async function runSearch() {
    if (!resultsBox) return;
    const base = new URL(root + '/api/metrics/search', window.location.origin);
    const since = parseInt($('#since')?.value || '86400', 10);
    [['stage', 'mllp'], ['since', since], ['ack_code', $('#ack_code')?.value],
     ['hl7_type', $('#hl7_type')?.value], ['msh10', $('#msh10')?.value], ['q', $('#q')?.value]]
      .forEach(([key, value]) => {
        if (value) base.searchParams.set(key, value);
      });

    resultsBox.innerHTML = '<div class="sample-row"><span class="muted">Searching…</span></div>';
    try {
      const response = await fetch(base.toString(), { cache: 'no-cache' });
      if (!response.ok) throw new Error('Search failed');
      const data = await response.json();
      const items = Array.isArray(data.items) ? data.items : [];
      if (!items.length) {
        resultsBox.innerHTML = '<div class="sample-row"><span class="muted">No results.</span></div>';
        return;
      }
      resultsBox.innerHTML = items.map((item) => {
        const parsed = (() => { try { return JSON.parse(item.payload || '{}'); } catch (_) { return {}; } })();
        const timestamp = new Date((item.ts || 0) * 1000).toLocaleString();
        const ack = parsed.ack_code || '—';
        const msh10 = parsed.msh10 || '—';
        const latency = (item.elapsed_ms ?? 0) + ' ms';
        const mllpHref = root + '/ui/interop/pipeline#mllp-panel';
        const fhirHref = root + '/ui/interop/pipeline#translate-panel';
        return `
          <div class="sample-row">
            <div class="sample-title"><strong>${ack}</strong> <span class="muted">ACK</span></div>
            <div class="sample-actions">
              <a class="btn btn-xs" href="${mllpHref}">Open MLLP</a>
              <a class="btn btn-xs" href="${fhirHref}">Open FHIR</a>
            </div>
            <div class="sample-meta">
              <span class="muted">When:</span> <code>${timestamp}</code>
              <span class="muted">Type:</span> <code>${item.hl7_type || '—'}</code>
              <span class="muted">MSH-10:</span> <code>${msh10}</code>
              <span class="muted">ACK latency:</span> <code>${latency}</code>
            </div>
          </div>`;
      }).join('');
    } catch (err) {
      resultsBox.innerHTML = `<div class="sample-row"><span class="muted">${err.message || 'Unable to load results.'}</span></div>`;
    }
  }

  searchBtn?.addEventListener('click', (event) => {
    event.preventDefault();
    runSearch();
  });

  document.querySelector('.controls-section')?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      runSearch();
    }
  });
})();
