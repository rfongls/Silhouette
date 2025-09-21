// static/js/nav.js
// Single hamburger + robust fallback + theme persistence (light/dark/hc/pro)
(() => {
  'use strict';
  const D = document;

  const THEME_KEY = 'theme';
  const THEMES = new Set(['light','dark','high-contrast','professional']);

  const $  = (s, r=D) => r.querySelector(s);
  const $$ = (s, r=D) => Array.from(r.querySelectorAll(s));

  function getTheme() {
    const t = localStorage.getItem(THEME_KEY);
    return THEMES.has(t) ? t : 'light';
  }
  function applyTheme(t) {
    if (!THEMES.has(t)) t = 'light';
    D.documentElement.setAttribute('data-theme', t);
    D.body && D.body.setAttribute('data-theme', t);
    localStorage.setItem(THEME_KEY, t);
    $$('input[name="theme"][type="radio"]').forEach(r => r.checked = (r.value === t));
  }

  function ensureSingleHamburger() {
    const triggers = $$('#hamburger-toggle, #app-hamburger, .hamburger-btn, [data-role="hamburger"]');
    if (triggers.length > 1) triggers.slice(1).forEach(el => el.style.display='none');
    return triggers[0] || null;
  }

  function ensureDrawerDom() {
    if (!$('#hamburger-menu')) {
      const menu = D.createElement('div');
      menu.id = 'hamburger-menu';
      menu.className = 'hamburger-menu';
      menu.innerHTML = `
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
      D.body.appendChild(menu);
    }
    if (!$('#overlay')) {
      const ov = D.createElement('div');
      ov.id = 'overlay';
      ov.className = 'overlay';
      D.body.appendChild(ov);
    }
  }

  function bind() {
    ensureDrawerDom();
    applyTheme(getTheme());

    const toggle  = ensureSingleHamburger();
    const menu    = $('#hamburger-menu');
    const close   = $('#close-hamburger');
    const overlay = $('#overlay');

    const open = () => { menu.classList.add('open'); overlay.classList.add('active'); D.body.style.overflow='hidden'; };
    const closeFn = () => { menu.classList.remove('open'); overlay.classList.remove('active'); D.body.style.overflow=''; };
    const toggleFn = () => (menu.classList.contains('open') ? closeFn() : open());

    // expose fallback for inline onclick
    window.SilhouetteMenuToggle = toggleFn;

    toggle && toggle.addEventListener('click', e => { e.preventDefault(); toggleFn(); });
    close  && close.addEventListener('click', closeFn);
    overlay&& overlay.addEventListener('click', closeFn);
    D.addEventListener('keydown', e => { if (e.key === 'Escape') closeFn(); });

    $$('input[name="theme"][type="radio"]').forEach(r =>
      r.addEventListener('change', e => { if (e.target.checked) applyTheme(e.target.value); })
    );
  }

  // Early theme & reliable init
  applyTheme(getTheme());
  (D.readyState === 'loading') ? D.addEventListener('DOMContentLoaded', bind) : bind();
})();
