// static/js/nav.js
(() => {
  'use strict';
  const D = document;
  const $ = (s, r = D) => r.querySelector(s);
  const $$ = (s, r = D) => Array.from(r.querySelectorAll(s));
  const THEME_KEY = 'theme';
  const THEMES = new Set(['light', 'dark', 'high-contrast', 'professional']);

  function applyTheme(theme) {
    if (!THEMES.has(theme)) theme = 'light';
    D.documentElement.setAttribute('data-theme', theme);
    if (D.body) D.body.setAttribute('data-theme', theme);
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch (err) {
      /* ignore storage errors */
    }
    $$('input[name="theme"][type="radio"]').forEach((radio) => {
      radio.checked = radio.value === theme;
    });
  }

  function getTheme() {
    try {
      const stored = localStorage.getItem(THEME_KEY);
      if (stored && THEMES.has(stored)) return stored;
    } catch (err) {
      /* ignore */
    }
    return 'light';
  }

  function ensureDrawerDom() {
    if (!$('#hamburger-menu')) {
      const el = D.createElement('div');
      el.id = 'hamburger-menu';
      el.className = 'hamburger-menu';
      el.innerHTML = `
        <div class="hamburger-content">
          <div class="hamburger-header">
            <h3>Settings</h3>
            <button class="close-hamburger" id="close-hamburger" aria-label="Close">×</button>
          </div>
          <div class="menu-section">
            <h4>Theme</h4>
            <div class="theme-selector">
              <label class="theme-option"><input type="radio" name="theme" value="light"> <span>Light</span></label>
              <label class="theme-option"><input type="radio" name="theme" value="dark"> <span>Dark</span></label>
              <label class="theme-option"><input type="radio" name="theme" value="high-contrast"> <span>High Contrast</span></label>
              <label class="theme-option"><input type="radio" name="theme" value="professional"> <span>Professional</span></label>
            </div>
          </div>
        </div>`;
      D.body.appendChild(el);
    }
    if (!$('#overlay')) {
      const overlay = D.createElement('div');
      overlay.id = 'overlay';
      overlay.className = 'overlay';
      D.body.appendChild(overlay);
    }
  }

  function ensureSingleHamburger() {
    const triggers = $$('#hamburger-toggle, #app-hamburger, .hamburger-btn, [data-role="hamburger"]');
    if (triggers.length > 1) {
      triggers.slice(1).forEach((el) => {
        el.style.display = 'none';
      });
    }
    return triggers[0] || null;
  }

  function bind() {
    ensureDrawerDom();
    applyTheme(getTheme());

    const toggle = ensureSingleHamburger();
    const menu = $('#hamburger-menu');
    const close = $('#close-hamburger');
    const overlay = $('#overlay');

    const open = () => {
      menu?.classList.add('open');
      overlay?.classList.add('active');
      if (D.body) D.body.style.overflow = 'hidden';
    };
    const closeFn = () => {
      menu?.classList.remove('open');
      overlay?.classList.remove('active');
      if (D.body) D.body.style.overflow = '';
    };
    const toggleFn = () => {
      if (menu?.classList.contains('open')) {
        closeFn();
      } else {
        open();
      }
    };

    window.SilhouetteMenuToggle = toggleFn;

    toggle?.addEventListener('click', (event) => {
      event.preventDefault();
      toggleFn();
    });
    close?.addEventListener('click', closeFn);
    overlay?.addEventListener('click', closeFn);
    D.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') closeFn();
    });

    $$('input[name="theme"][type="radio"]').forEach((radio) => {
      radio.addEventListener('change', (event) => {
        if (event.target.checked) applyTheme(event.target.value);
      });
    });
  }

  applyTheme(getTheme());
  if (D.readyState === 'loading') {
    D.addEventListener('DOMContentLoaded', bind);
  } else {
    bind();
  }
})();
