// static/js/panel_manager.js
(() => {
  'use strict';

  const D = document;
  const $$ = (selector, root = D) => Array.from(root.querySelectorAll(selector));

  const DETAILS_SELECTOR = 'details.collapsible, details.card.collapsible';

  function normalizePanelId(panelId) {
    if (!panelId) return null;
    const raw = String(panelId).trim();
    if (!raw) return null;
    return raw.endsWith('-panel') ? raw : `${raw}-panel`;
  }

  class PanelManager {
    constructor() {
      this.currentPanel = null;
      this.completedPanels = new Set();
      this.bindEvents();
      this.ensureInitialPanel();
    }

    bindEvents() {
      $$('.module-btn[data-panel]').forEach((btn) => {
        if (btn.dataset.panelManagerBound === 'true') return;
        btn.dataset.panelManagerBound = 'true';
        btn.addEventListener('click', (event) => {
          const panelId = event.currentTarget?.dataset?.panel;
          if (!panelId) return;
          event.preventDefault();
          this.showPanel(panelId);
        }, true);
      });
    }

    ensureInitialPanel() {
      const activePanel = D.querySelector('.panel.active')?.id
        || D.querySelector('.module-btn.active[data-panel]')?.dataset.panel
        || $$('.panel')[0]?.id
        || null;
      if (activePanel) {
        this.showPanel(activePanel);
      }
    }

    markPanelCompleted(panelId) {
      const normalized = normalizePanelId(panelId);
      if (!normalized) return;
      this.completedPanels.add(normalized);
      const chip = D.querySelector(`.module-btn[data-panel="${normalized}"]`);
      if (chip) {
        chip.classList.add('completed');
        chip.setAttribute('aria-current', 'step');
      }
    }

    resetPanelCompletion(panelId) {
      const normalized = normalizePanelId(panelId);
      if (!normalized) return;
      this.completedPanels.delete(normalized);
      const chip = D.querySelector(`.module-btn[data-panel="${normalized}"]`);
      if (chip) {
        chip.classList.remove('completed');
        chip.setAttribute('aria-current', chip.classList.contains('active') ? 'page' : 'false');
      }
    }

    showPanel(panelId) {
      const normalized = normalizePanelId(panelId);
      if (!normalized) return;

      if (this.currentPanel && this.currentPanel !== normalized) {
        try { window.PanelStateCache?.save(this.currentPanel); } catch (_) {}
      }

      const targetPanel = D.getElementById(normalized);
      if (!targetPanel) return;

      const parentDetails = targetPanel.closest(DETAILS_SELECTOR);
      if (parentDetails) {
        parentDetails.open = true;
        $$(DETAILS_SELECTOR).forEach((det) => {
          if (det !== parentDetails && det.open) det.open = false;
        });
      }

      $$('.panel').forEach((panel) => {
        const isActive = panel.id === normalized;
        panel.classList.toggle('active', isActive);
        if ('hidden' in panel) {
          panel.hidden = !isActive;
        }
      });

      $$('.module-btn[data-panel]').forEach((btn) => {
        const isActive = btn.dataset.panel === normalized;
        btn.classList.toggle('active', isActive);
        btn.setAttribute('aria-expanded', String(isActive));
        btn.setAttribute('aria-controls', btn.dataset.panel || '');
        if (!isActive && btn.classList.contains('completed') && !this.completedPanels.has(btn.dataset.panel)) {
          btn.classList.remove('completed');
        }
        btn.setAttribute('aria-current', isActive ? 'page' : (btn.classList.contains('completed') ? 'step' : 'false'));
      });

      $$('.action-tray').forEach((tray) => {
        tray.classList.remove('visible');
        if ('hidden' in tray) tray.hidden = true;
      });

      this.currentPanel = normalized;
      window.InteropUI = window.InteropUI || {};
      window.InteropUI.currentPanel = normalized;
      try { window.PanelStateCache?.restore(normalized); } catch (_) {}
    }

    runPipeline(targetPanel) {
      const normalized = normalizePanelId(targetPanel);
      if (!normalized) return;
      if (this.currentPanel) {
        this.markPanelCompleted(this.currentPanel);
        try { window.PanelStateCache?.save(this.currentPanel); } catch (_) {}
      }
      this.showPanel(normalized);
    }
  }

  function init() {
    if (!D.querySelector('.panel')) return;
    window.InteropUI = window.InteropUI || {};
    if (window.InteropUI.panelManager instanceof PanelManager) {
      window.InteropUI.panelManager.bindEvents();
      window.InteropUI.panelManager.ensureInitialPanel?.();
      return;
    }
    const manager = new PanelManager();
    window.InteropUI.panelManager = manager;
  }

  if (D.readyState === 'loading') {
    D.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
