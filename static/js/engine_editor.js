const ROOT_META = document.querySelector('meta[name="app-root"]');
const ROOT_PATH = (document.querySelector('section.dashboard')?.dataset?.root || (ROOT_META?.getAttribute('content') || '')).replace(/\/$/, '');

const pipelineListEl = document.getElementById('engine-pl-list');
const profileListEl = document.getElementById('engine-profile-list');
const stepsListEl = document.getElementById('engine-pl-steps');
const nameInput = document.getElementById('engine-pl-name');
const descInput = document.getElementById('engine-pl-desc');
const scopeInput = document.getElementById('engine-pl-scope');
const endpointInput = document.getElementById('engine-pl-endpoint');

let currentPipelineId = null;
let pipelines = [];
let steps = [];
let dragIndex = null;
let dropIndex = null;
const profileCache = new Map();

function escapeHtml(value) {
  return (value ?? '')
    .toString()
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderPipelines() {
  if (!pipelineListEl) return;
  pipelineListEl.innerHTML = '';
  if (!pipelines.length) {
    pipelineListEl.innerHTML = '<p class="text-body muted">No pipelines yet.</p>';
    return;
  }
  const list = document.createElement('ul');
  list.className = 'list';
  pipelines.forEach((pipeline) => {
    const item = document.createElement('li');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'button ghost';
    button.textContent = pipeline.name || `Pipeline #${pipeline.id}`;
    button.addEventListener('click', () => selectPipeline(pipeline.id));
    item.appendChild(button);
    list.appendChild(item);
  });
  pipelineListEl.appendChild(list);
}

function renderSteps() {
  if (!stepsListEl) return;
  stepsListEl.innerHTML = '';
  if (!steps.length) {
    const empty = document.createElement('li');
    empty.className = 'text-body muted';
    empty.textContent = 'No steps selected.';
    stepsListEl.appendChild(empty);
    return;
  }
  steps.forEach((step, index) => {
    const item = document.createElement('li');
    item.className = 'row small';
    item.dataset.profileId = String(step.profileId);
    item.dataset.index = String(index);
    item.setAttribute('draggable', 'true');

    const label = document.createElement('span');
    label.className = 'text-body';
    label.innerHTML = `<strong>${index + 1}.</strong> ${escapeHtml(step.name || `Profile ${step.profileId}`)} <span class="text-caption muted">(${escapeHtml(step.kind || '')})</span>`;

    const up = document.createElement('button');
    up.type = 'button';
    up.className = 'button ghost small';
    up.textContent = '↑';
    up.disabled = index === 0;
    up.addEventListener('click', () => {
      if (index === 0) return;
      const tmp = steps[index - 1];
      steps[index - 1] = steps[index];
      steps[index] = tmp;
      renderSteps();
    });

    const down = document.createElement('button');
    down.type = 'button';
    down.className = 'button ghost small';
    down.textContent = '↓';
    down.disabled = index === steps.length - 1;
    down.addEventListener('click', () => {
      if (index === steps.length - 1) return;
      const tmp = steps[index + 1];
      steps[index + 1] = steps[index];
      steps[index] = tmp;
      renderSteps();
    });

    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'button danger small';
    remove.textContent = 'Remove';
    remove.addEventListener('click', () => {
      steps.splice(index, 1);
      renderSteps();
    });

    item.append(label, up, down, remove);

    item.addEventListener('dragstart', (event) => {
      dragIndex = Number(item.dataset.index);
      item.classList.add('dnd-dragging');
      try {
        event.dataTransfer?.setData('text/plain', String(dragIndex));
      } catch (err) {
        // Ignore inability to set data (e.g., Firefox + file://)
      }
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = 'move';
      }
    });

    item.addEventListener('dragend', () => {
      item.classList.remove('dnd-dragging');
      document.querySelectorAll('#engine-pl-steps li.dnd-over').forEach((el) => el.classList.remove('dnd-over'));
      dragIndex = null;
      dropIndex = null;
    });

    item.addEventListener('dragover', (event) => {
      event.preventDefault();
      const targetIndex = Number(item.dataset.index);
      if (!Number.isFinite(targetIndex)) return;
      document.querySelectorAll('#engine-pl-steps li.dnd-over').forEach((el) => el.classList.remove('dnd-over'));
      item.classList.add('dnd-over');
      dropIndex = targetIndex;
      if (event.dataTransfer) {
        event.dataTransfer.dropEffect = 'move';
      }
    });

    item.addEventListener('dragleave', () => {
      item.classList.remove('dnd-over');
    });

    item.addEventListener('drop', (event) => {
      event.preventDefault();
      item.classList.remove('dnd-over');
      if (dragIndex == null || dropIndex == null || dragIndex === dropIndex) {
        dragIndex = null;
        dropIndex = null;
        return;
      }
      const moved = steps.splice(dragIndex, 1)[0];
      steps.splice(dropIndex, 0, moved);
      dragIndex = null;
      dropIndex = null;
      renderSteps();
    });

    stepsListEl.appendChild(item);
  });
}

function resetForm() {
  currentPipelineId = null;
  steps = [];
  if (nameInput) nameInput.value = '';
  if (descInput) descInput.value = '';
  if (scopeInput) scopeInput.value = 'engine';
  if (endpointInput) endpointInput.value = '';
  renderSteps();
}

function selectPipeline(id) {
  const pipeline = pipelines.find((p) => p.id === id);
  if (!pipeline) return;
  currentPipelineId = id;
  if (nameInput) nameInput.value = pipeline.name || '';
  if (descInput) descInput.value = pipeline.description || '';
  if (scopeInput) scopeInput.value = pipeline.scope || 'engine';
  if (endpointInput) endpointInput.value = pipeline.endpoint_id || '';
  steps = (pipeline.steps || []).map((step) => ({
    profileId: step.profile_id,
    name: step.name,
    kind: step.kind,
  }));
  renderSteps();
}

async function loadPipelines() {
  if (!pipelineListEl) return;
  pipelineListEl.innerHTML = '<p class="text-body muted">Loading pipelines…</p>';
  try {
    const response = await fetch(`${ROOT_PATH}/api/engine/pipelines`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    pipelines = Array.isArray(data.items) ? data.items : [];
    renderPipelines();
    if (currentPipelineId) {
      selectPipeline(currentPipelineId);
    }
  } catch (err) {
    console.error('Failed to load pipelines', err);
    pipelineListEl.innerHTML = '<p class="text-body muted">Unable to load pipelines.</p>';
  }
}

function renderProfiles(kind, items) {
  if (!profileListEl) return;
  profileListEl.innerHTML = '';
  if (!items.length) {
    profileListEl.innerHTML = `<p class="text-body muted">No ${kind} profiles yet.</p>`;
    return;
  }
  const list = document.createElement('ul');
  list.className = 'list';
  items.forEach((profile) => {
    profileCache.set(profile.id, profile);
    const item = document.createElement('li');
    const row = document.createElement('div');
    row.className = 'row small';
    row.style.alignItems = 'center';

    const text = document.createElement('div');
    text.innerHTML = `<strong>${escapeHtml(profile.name)}</strong><br><span class="text-caption muted">${escapeHtml(profile.description || '')}</span>`;

    const add = document.createElement('button');
    add.type = 'button';
    add.className = 'button small';
    add.textContent = 'Add step';
    add.addEventListener('click', () => {
      steps.push({
        profileId: profile.id,
        name: profile.name,
        kind: profile.kind,
      });
      renderSteps();
    });

    row.append(text, add);
    item.appendChild(row);
    list.appendChild(item);
  });
  profileListEl.appendChild(list);
}

async function loadProfiles(kind) {
  if (!profileListEl) return;
  profileListEl.innerHTML = `<p class="text-body muted">Loading ${kind} profiles…</p>`;
  try {
    const response = await fetch(`${ROOT_PATH}/api/engine/profiles?kind=${encodeURIComponent(kind)}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const items = Array.isArray(data.items) ? data.items : [];
    renderProfiles(kind, items);
  } catch (err) {
    console.error('Failed to load profiles', err);
    profileListEl.innerHTML = `<p class="text-body muted">Unable to load ${kind} profiles.</p>`;
  }
}

async function savePipeline() {
  if (!nameInput || !scopeInput) return;
  const payload = {
    name: nameInput.value.trim(),
    description: descInput?.value.trim() || null,
    scope: scopeInput.value || 'engine',
    endpoint_id: endpointInput && endpointInput.value ? Number(endpointInput.value) : null,
    steps: steps.map((step) => step.profileId),
  };
  if (!payload.name) {
    alert('Name is required.');
    return;
  }
  try {
    if (currentPipelineId) {
      const response = await fetch(`${ROOT_PATH}/api/engine/pipelines/${currentPipelineId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error(await response.text());
    } else {
      const response = await fetch(`${ROOT_PATH}/api/engine/pipelines`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error(await response.text());
      const data = await response.json();
      currentPipelineId = data.id || null;
    }
    await loadPipelines();
    alert('Pipeline saved.');
  } catch (err) {
    console.error('Failed to save pipeline', err);
    const message = err instanceof Error ? err.message : String(err);
    alert(`Failed to save pipeline: ${message}`);
  }
}

function wireEvents() {
  document.getElementById('engine-pl-new')?.addEventListener('click', () => {
    resetForm();
  });
  document.getElementById('engine-pl-clear')?.addEventListener('click', () => {
    steps = [];
    renderSteps();
  });
  document.getElementById('engine-pl-save')?.addEventListener('click', savePipeline);
  document.querySelectorAll('[data-prof-kind]').forEach((button) => {
    button.addEventListener('click', () => {
      const kind = button.getAttribute('data-prof-kind');
      if (kind) loadProfiles(kind);
    });
  });
}

wireEvents();
resetForm();
loadPipelines();
