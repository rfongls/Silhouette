(() => {
  const ROOT = document.body?.dataset?.root || '';
  const windowSel = document.getElementById('window');
  const refreshBtn = document.getElementById('refresh');

  const recentContainer = document.getElementById('recent_activity');
  const issuesContainer = document.getElementById('issues_activity');
  const validateStats = document.getElementById('validate_stats');
  const mllpStats = document.getElementById('mllp_stats');

  function withRoot(path) {
    if (!path.startsWith('/')) return ROOT + '/' + path;
    return ROOT + path;
  }

  async function fetchJSON(url) {
    try {
      const res = await fetch(url, { cache: 'no-cache' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn('reports: fetch failed', url, err);
      return null;
    }
  }

  function stageLabel(stage) {
    if (!stage) return '—';
    const key = String(stage).toLowerCase();
    const special = { mllp: 'MLLP', hl7: 'HL7', fhir: 'FHIR' };
    if (special[key]) return special[key];
    return key
      .split(/[_\s-]+/)
      .map((part) => part ? part[0].toUpperCase() + part.slice(1) : part)
      .join(' ');
  }

  function prettyStatus(status) {
    if (!status) return 'Unknown';
    const key = String(status).toLowerCase();
    if (key === 'success') return 'Success';
    if (key === 'fail') return 'Failed';
    if (key === 'error') return 'Error';
    return status[0].toUpperCase() + status.slice(1);
  }

  function parsePayload(raw) {
    if (!raw) return {};
    try {
      return JSON.parse(raw);
    } catch (err) {
      return {};
    }
  }

  function renderEvents(container, items, emptyMessage) {
    if (!container) return;
    if (!items || !items.length) {
      container.innerHTML = `<div class="sample-row"><span class="muted">${emptyMessage}</span></div>`;
      return;
    }
    container.innerHTML = items
      .map((item) => {
        const ts = item.ts ? new Date(item.ts * 1000).toLocaleString() : '—';
        const stage = stageLabel(item.stage);
        const status = prettyStatus(item.status);
        const payload = parsePayload(item.payload);
        const parts = [`<span class="muted">When:</span> <code>${ts}</code>`];
        if (item.hl7_type) {
          parts.push(`<span class="muted">Type:</span> <code>${item.hl7_type}</code>`);
        }
        if (item.msg_id) {
          parts.push(`<span class="muted">Msg:</span> <code>${item.msg_id}</code>`);
        }
        if (payload.ack_code) {
          parts.push(`<span class="muted">ACK:</span> <code>${payload.ack_code}</code>`);
        }
        return `
        <div class="sample-row">
          <div class="sample-title"><strong>${stage}</strong> <span class="muted">(${status})</span></div>
          <div class="sample-meta">${parts.join(' ')}</div>
        </div>`;
      })
      .join('');
  }

  function updateValidateCard(data) {
    if (!validateStats) return;
    if (!data) {
      validateStats.innerHTML = '<div class="muted">Unable to load validation summary.</div>';
      return;
    }
    const total = data.total || 0;
    const successRate = ((data.success_rate || 0) * 100).toFixed(1);
    const avg = data.avg_ms || 0;
    const top = (data.top_errors || []).map((e) => e.code).filter(Boolean).slice(0, 3).join(', ') || '—';
    const lines = [
      `<div><span class="muted">Total validations</span> <strong>${total.toLocaleString()}</strong></div>`,
      `<div><span class="muted">Success rate</span> <strong>${successRate}%</strong></div>`,
      `<div><span class="muted">Avg latency</span> <strong>${avg} ms</strong></div>`,
      `<div><span class="muted">Top errors</span> <code>${top}</code></div>`,
    ];
    if (!total) {
      lines.push('<div class="muted">No validation activity in this window.</div>');
    }
    validateStats.innerHTML = lines.join('');
  }

  function updateMllpCard(items) {
    if (!mllpStats) return;
    if (!items || !items.length) {
      mllpStats.innerHTML = '<div class="muted">No MLLP sends in this window.</div>';
      return;
    }
    let success = 0;
    let failure = 0;
    const ackCounts = {};
    const latencies = [];
    items.forEach((item) => {
      const status = String(item.status || '').toLowerCase();
      if (status === 'success') success += 1;
      else failure += 1;
      const payload = parsePayload(item.payload);
      const ack = String(payload.ack_code || '').toUpperCase();
      if (ack) {
        ackCounts[ack] = (ackCounts[ack] || 0) + 1;
      }
      const elapsed = Number(item.elapsed_ms || payload.ack_latency || 0);
      if (!Number.isNaN(elapsed) && elapsed > 0) {
        latencies.push(elapsed);
      }
    });
    const total = success + failure;
    const rate = total ? ((success / total) * 100).toFixed(1) : '0.0';
    const avgLatency = latencies.length
      ? Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length)
      : 0;
    const ackSummary = Object.entries(ackCounts)
      .sort((a, b) => b[1] - a[1])
      .map(([code, count]) => `${code}:${count}`)
      .join(', ') || '—';
    mllpStats.innerHTML = [
      `<div><span class="muted">Total sends</span> <strong>${total.toLocaleString()}</strong></div>`,
      `<div><span class="muted">Success rate</span> <strong>${rate}%</strong></div>`,
      `<div><span class="muted">Avg ACK latency</span> <strong>${avgLatency} ms</strong></div>`,
      `<div><span class="muted">ACK codes</span> <code>${ackSummary}</code></div>`,
    ].join('');
  }

  async function loadSummary(windowSeconds) {
    const data = await fetchJSON(withRoot(`/api/metrics/summary?window=${windowSeconds}`));
    if (!data) {
      document.getElementById('k_total').textContent = '—';
      document.getElementById('k_sr').textContent = '—';
      document.getElementById('k_avg').textContent = '—';
      document.getElementById('k_types').textContent = '—';
      if (document.getElementById('by_stage')) {
        document.getElementById('by_stage').textContent = '[]';
      }
      if (document.getElementById('by_status')) {
        document.getElementById('by_status').textContent = '[]';
      }
      return;
    }

    const pct = `${((data.success_rate || 0) * 100).toFixed(1)}%`;
    document.getElementById('k_total').textContent = (data.total || 0).toLocaleString();
    document.getElementById('k_sr').textContent = pct;
    document.getElementById('k_avg').textContent = `${data.avg_ms || 0} ms`;
    document.getElementById('k_types').textContent =
      (data.top_types || []).map((t) => `${t.hl7_type}:${t.count}`).join(', ') || '—';

    if (document.getElementById('by_stage')) {
      document.getElementById('by_stage').textContent = JSON.stringify(data.by_stage || [], null, 2);
    }
    if (document.getElementById('by_status')) {
      document.getElementById('by_status').textContent = JSON.stringify(data.by_status || [], null, 2);
    }
  }

  async function loadActivity(windowSeconds) {
    const url = new URL(withRoot('/api/metrics/search'), window.location.origin);
    url.searchParams.set('since', String(windowSeconds));
    url.searchParams.set('limit', '100');
    const data = await fetchJSON(url.toString());
    const items = (data && data.items) || [];
    renderEvents(recentContainer, items.slice(0, 5), 'No activity in this window.');
    const issues = items.filter((item) => String(item.status || '').toLowerCase() !== 'success');
    renderEvents(issuesContainer, issues.slice(0, 5), 'No issues flagged.');
    const mllpItems = items.filter((item) => String(item.stage || '').toLowerCase() === 'mllp');
    updateMllpCard(mllpItems);
  }

  async function loadValidateSummary(windowSeconds) {
    const data = await fetchJSON(withRoot(`/api/metrics/validate_summary?window=${windowSeconds}`));
    updateValidateCard(data);
  }

  async function refreshAll() {
    const win = parseInt(windowSel?.value || '86400', 10) || 86400;
    await Promise.all([
      loadSummary(win),
      loadActivity(win),
      loadValidateSummary(win),
    ]);
  }

  refreshBtn?.addEventListener('click', (event) => {
    event.preventDefault();
    refreshAll();
  });

  windowSel?.addEventListener('change', () => {
    refreshAll();
  });

  document.addEventListener('DOMContentLoaded', () => {
    refreshAll();
  });

  refreshAll();
})();
