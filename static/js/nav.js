// static/js/nav.js
// Settings side-drawer (single hamburger) + Theme manager
(() => {
  'use strict';
  const DOC = document;

  const THEME_KEY = 'theme';
  const VALID = new Set(['default', 'dark', 'high-contrast', 'professional']);

  const qs = (sel, root = DOC) => root.querySelector(sel);
  const qsa = (sel, root = DOC) => Array.from(root.querySelectorAll(sel));

  function getTheme() {
    const stored = localStorage.getItem(THEME_KEY);
    return VALID.has(stored) ? stored : 'default';
  }

  function applyTheme(theme) {
    const value = VALID.has(theme) ? theme : 'default';
    DOC.documentElement.setAttribute('data-theme', value);
    localStorage.setItem(THEME_KEY, value);
    qsa('input[name="theme"][type="radio"]').forEach((radio) => {
      radio.checked = radio.value === value;
    });
  }

  function ensureSingleHamburger() {
    const triggers = qsa('#hamburger-toggle, #app-hamburger, .hamburger-btn, [data-role="hamburger"]');
    if (triggers.length > 1) {
      triggers.slice(1).forEach((el) => {
        el.style.display = 'none';
        el.dataset.hiddenDuplicate = 'true';
      });
    }
    return triggers[0] || null;
  }

  function bindDrawer() {
    const drawer = qs('#hamburger-menu');
    const overlay = qs('#overlay');
    const trigger = ensureSingleHamburger();
    const closeBtn = qs('#close-hamburger');

    function openDrawer() {
      if (drawer) {
        drawer.classList.add('open');
        drawer.setAttribute('aria-hidden', 'false');
      }
      if (overlay) overlay.classList.add('active');
      DOC.body.style.overflow = 'hidden';
      if (trigger) trigger.setAttribute('aria-expanded', 'true');
    }

    function closeDrawer() {
      if (drawer) {
        drawer.classList.remove('open');
        drawer.setAttribute('aria-hidden', 'true');
      }
      if (overlay) overlay.classList.remove('active');
      DOC.body.style.overflow = '';
      if (trigger) trigger.setAttribute('aria-expanded', 'false');
    }

    function toggleDrawer() {
      if (!drawer) return;
      if (drawer.classList.contains('open')) {
        closeDrawer();
      } else {
        openDrawer();
      }
    }

    if (trigger) {
      trigger.addEventListener('click', (event) => {
        event.preventDefault();
        toggleDrawer();
      });
    }
    if (closeBtn) {
      closeBtn.addEventListener('click', (event) => {
        event.preventDefault();
        closeDrawer();
      });
    }
    if (overlay) {
      overlay.addEventListener('click', closeDrawer);
    }
    DOC.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeDrawer();
      }
    });

    qsa('input[name="theme"][type="radio"]').forEach((radio) => {
      radio.addEventListener('change', (event) => {
        if (event.target.checked) {
          applyTheme(event.target.value);
        }
      });
    });
  }

  // Apply theme as early as possible
  try {
    applyTheme(getTheme());
  } catch (_) {
    /* ignore */
  }

  DOC.addEventListener('DOMContentLoaded', () => {
    bindDrawer();
    // Ensure drawer radios reflect stored theme
    applyTheme(getTheme());
  });
})();
