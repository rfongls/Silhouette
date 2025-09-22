// static/js/panel_state_cache.js
(function () {
  'use strict';
  const store = new Map();

  function keyOf(el) {
    return el.id || el.name || null;
  }

  function snapshot(panel) {
    const data = {};
    panel.querySelectorAll('input,textarea,select').forEach((el) => {
      const key = keyOf(el);
      if (!key) return;
      if (el.type === 'checkbox' || el.type === 'radio') {
        data[key] = el.checked;
      } else {
        data[key] = el.value;
      }
    });
    return data;
  }

  function hydrate(panel, data) {
    if (!data) return;
    Object.entries(data).forEach(([key, value]) => {
      let el = null;
      try {
        el = panel.querySelector(`#${CSS.escape(key)}`);
      } catch (_) {
        el = null;
      }
      if (!el) {
        try {
          el = panel.querySelector(`[name="${CSS.escape(key)}"]`);
        } catch (_) {
          el = panel.querySelector(`[name="${key}"]`);
        }
      }
      if (!el) return;
      if (el.type === 'checkbox' || el.type === 'radio') {
        el.checked = Boolean(value);
      } else {
        el.value = value;
      }
    });
  }

  window.PanelStateCache = {
    save(panelId) {
      if (!panelId) return;
      const panel = document.getElementById(panelId);
      if (!panel) return;
      store.set(panelId, snapshot(panel));
    },
    restore(panelId) {
      if (!panelId) return;
      const panel = document.getElementById(panelId);
      if (!panel) return;
      hydrate(panel, store.get(panelId));
    },
    clear(panelId) {
      if (!panelId) return;
      store.delete(panelId);
    },
    reset() {
      store.clear();
    }
  };
})();
