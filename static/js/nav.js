// Settings pop-up + Theme switcher + "single hamburger" guard
(() => {
  'use strict';
  const DOC = document;

  const THEME_KEY = 'app.theme';
  const VALID_THEMES = new Set(['default', 'dark']);

  const qs = (selector, root = DOC) => root.querySelector(selector);
  const qsa = (selector, root = DOC) => Array.from(root.querySelectorAll(selector));
  let primaryTrigger = null;

  function currentTheme() {
    const stored = (() => {
      try {
        return localStorage.getItem(THEME_KEY);
      } catch (err) {
        return null;
      }
    })();
    return stored && VALID_THEMES.has(stored) ? stored : 'default';
  }

  function applyTheme(theme) {
    const next = VALID_THEMES.has(theme) ? theme : 'default';
    DOC.documentElement.setAttribute('data-theme', next);
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch (err) {
      // ignore persistence issues (private mode, etc.)
    }
    qsa('[data-theme-choice]').forEach((btn) => {
      const checked = btn.dataset.themeChoice === next;
      btn.setAttribute('aria-checked', String(checked));
    });
  }

  function ensureSingleHamburger() {
    const triggers = qsa('#app-hamburger, #hamburger-btn, .hamburger-btn, [data-role="hamburger"]');
    if (triggers.length > 1) {
      triggers.slice(1).forEach((el) => {
        el.style.display = 'none';
        el.setAttribute('data-hidden-duplicate', 'true');
      });
    }
    return triggers[0] || null;
  }

  function buildMenu() {
    let menu = qs('#app-menu');
    if (!menu) {
      menu = DOC.createElement('div');
      menu.id = 'app-menu';
      menu.className = 'app-menu';
      menu.setAttribute('role', 'menu');
      menu.setAttribute('hidden', '');
      menu.setAttribute('aria-hidden', 'true');
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
    }

    let backdrop = qs('#menu-backdrop');
    if (!backdrop) {
      backdrop = DOC.createElement('div');
      backdrop.id = 'menu-backdrop';
      backdrop.setAttribute('hidden', '');
      DOC.body.appendChild(backdrop);
    }

    menu.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-theme-choice]');
      if (!btn) {
        return;
      }
      applyTheme(btn.dataset.themeChoice);
      hideMenu();
    });

    backdrop.addEventListener('click', hideMenu);
    DOC.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        hideMenu();
      }
    });

    return menu;
  }

  function showMenu() {
    const menu = qs('#app-menu');
    const backdrop = qs('#menu-backdrop');
    if (menu) {
      menu.removeAttribute('hidden');
      menu.classList.add('open');
      menu.setAttribute('aria-hidden', 'false');
      const firstItem = menu.querySelector('[data-theme-choice]');
      if (firstItem && typeof firstItem.focus === 'function') {
        firstItem.focus();
      }
    }
    if (backdrop) {
      backdrop.removeAttribute('hidden');
    }
    if (primaryTrigger) {
      primaryTrigger.setAttribute('aria-expanded', 'true');
    }
  }

  function hideMenu() {
    const menu = qs('#app-menu');
    const backdrop = qs('#menu-backdrop');
    const wasOpen = menu && !menu.hasAttribute('hidden');
    if (menu) {
      menu.classList.remove('open');
      menu.setAttribute('hidden', '');
      menu.setAttribute('aria-hidden', 'true');
    }
    if (backdrop) {
      backdrop.setAttribute('hidden', '');
    }
    if (primaryTrigger && wasOpen) {
      primaryTrigger.setAttribute('aria-expanded', 'false');
      if (typeof primaryTrigger.focus === 'function') {
        primaryTrigger.focus();
      }
    }
  }

  function toggleMenu() {
    const menu = qs('#app-menu');
    if (!menu || menu.hasAttribute('hidden')) {
      showMenu();
    } else {
      hideMenu();
    }
  }

  DOC.addEventListener('DOMContentLoaded', () => {
    primaryTrigger = ensureSingleHamburger();
    buildMenu();
    applyTheme(currentTheme());
    if (primaryTrigger) {
      primaryTrigger.setAttribute('aria-expanded', 'false');
      primaryTrigger.addEventListener('click', (event) => {
        event.preventDefault();
        toggleMenu();
      });
    }
  });
})();
