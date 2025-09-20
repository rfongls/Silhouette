async function loadSummary() {
  const windowSel = document.getElementById('window');
  if (!windowSel) {
    return;
  }
  const win = parseInt(windowSel.value, 10) || 86400;
  const res = await fetch(`/api/metrics/summary?window=${win}`);
  const data = await res.json();

  const pct = `${(data.success_rate * 100).toFixed(1)}%`;
  document.getElementById('k_total').textContent = data.total.toLocaleString();
  document.getElementById('k_sr').textContent = pct;
  document.getElementById('k_avg').textContent = `${data.avg_ms} ms`;
  document.getElementById('k_types').textContent =
    (data.top_types || []).map((t) => `${t.hl7_type}:${t.count}`).join(', ') || '—';

  document.getElementById('by_stage').textContent = JSON.stringify(data.by_stage, null, 2);
  document.getElementById('by_status').textContent = JSON.stringify(data.by_status, null, 2);
}

const refreshBtn = document.getElementById('refresh');
if (refreshBtn) {
  refreshBtn.addEventListener('click', loadSummary);
}
loadSummary();
