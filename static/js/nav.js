// static/js/nav.js
// Settings pop-up + Theme switcher + "single hamburger" guard
(() => {
  'use strict';
  const DOC = document;

  const THEME_KEY = 'app.theme';
  const VALID_THEMES = new Set(['default', 'dark']);

  const qs  = (s, root = DOC) => root.querySelector(s);
  const qsa = (s, root = DOC) => Array.from(root.querySelectorAll(s));

  function currentTheme() {
    const t = localStorage.getItem(THEME_KEY);
    return VALID_THEMES.has(t) ? t : 'default';
  }

  function applyTheme(theme) {
    if (!VALID_THEMES.has(theme)) theme = 'default';
    DOC.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
    // reflect in menu
    qsa('[data-theme-choice]').forEach(btn => {
      const checked = btn.dataset.themeChoice === theme;
      btn.setAttribute('aria-checked', String(checked));
    });
  }

  function ensureSingleHamburger() {
    // Support multiple possible IDs/classes; keep the first, hide the rest.
    const triggers = qsa('#app-hamburger, #hamburger-btn, .hamburger-btn, [data-role="hamburger"]');
    if (triggers.length > 1) {
      triggers.slice(1).forEach(el => {
        el.style.display = 'none';
        el.setAttribute('data-hidden-duplicate', 'true');
      });
    }
    return triggers[0] || null;
  }

  function buildMenu() {
    if (qs('#app-menu')) return qs('#app-menu');

    const menu = DOC.createElement('div');
    menu.id = 'app-menu';
    menu.className = 'app-menu';
    menu.setAttribute('role', 'menu');
    menu.setAttribute('hidden', '');

    menu.innerHTML = `
      <div class="menu-heading">Settings</div>
      <div class="menu-divider"></div>
      <div class="menu-heading">Theme</div>
      <div class="menu-row">
        <button type="button" class="menu-item" role="menuitemradio"
                data-theme-choice="default" aria-checked="false">Default</button>
        <button type="button" class="menu-item" role="menuitemradio"
                data-theme-choice="dark" aria-checked="false">Dark</button>
      </div>
    `;

    DOC.body.appendChild(menu);

    let backdrop = qs('#menu-backdrop');
    if (!backdrop) {
      backdrop = DOC.createElement('div');
      backdrop.id = 'menu-backdrop';
      backdrop.setAttribute('hidden', '');
      DOC.body.appendChild(backdrop);
    }

    // Theme selection
    menu.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-theme-choice]');
      if (!btn) return;
      applyTheme(btn.dataset.themeChoice);
      hideMenu();
    });

    // Dismiss
    backdrop.addEventListener('click', hideMenu);
    DOC.addEventListener('keydown', (e) => { if (e.key === 'Escape') hideMenu(); });

    return menu;
  }

  function showMenu() {
    const menu = qs('#app-menu');
    const backdrop = qs('#menu-backdrop');
    if (menu) {
      menu.removeAttribute('hidden');
      menu.classList.add('open');
    }
    if (backdrop) backdrop.removeAttribute('hidden');
  }

  function hideMenu() {
    const menu = qs('#app-menu');
    const backdrop = qs('#menu-backdrop');
    if (menu) {
      menu.classList.remove('open');
      menu.setAttribute('hidden', '');
    }
    if (backdrop) backdrop.setAttribute('hidden', '');
  }

  function toggleMenu() {
    const menu = qs('#app-menu');
    if (!menu) return showMenu();
    menu.hasAttribute('hidden') ? showMenu() : hideMenu();
  }

  DOC.addEventListener('DOMContentLoaded', () => {
    const trigger = ensureSingleHamburger();
    buildMenu();
    applyTheme(currentTheme());
    if (trigger) trigger.addEventListener('click', (e) => {
      e.preventDefault();
      toggleMenu();
    });
  });
})();
