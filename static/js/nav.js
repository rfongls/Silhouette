// static/js/nav.js
// Single hamburger + settings drawer + theme persistence (light/dark/hc/professional)
(() => {
  'use strict';

  const DOC = document;
  const THEME_KEY = 'theme';
  const THEMES = new Set(['light', 'dark', 'high-contrast', 'professional']);

  const qs  = (s, r = DOC) => r.querySelector(s);
  const qsa = (s, r = DOC) => Array.from(r.querySelectorAll(s));

  function getTheme() {
    const t = localStorage.getItem(THEME_KEY);
    return THEMES.has(t) ? t : 'light';
  }
  function applyTheme(theme) {
    if (!THEMES.has(theme)) theme = 'light';
    // Apply to <html> and <body> so CSS like [data-theme="..."] wins everywhere
    DOC.documentElement.setAttribute('data-theme', theme);
    if (DOC.body) DOC.body.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
    // reflect radio state if present
    qsa('input[name="theme"][type="radio"]').forEach(r => { r.checked = (r.value === theme); });
  }

  // If the drawer HTML isn't present, inject a minimal version
  function ensureDrawerDom() {
    let menu = qs('#hamburger-menu');
    if (!menu) {
      menu = DOC.createElement('div');
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
              <label class="theme-option"><input type="radio" name="theme" value="light"><span class="theme-label">Light</span></label>
              <label class="theme-option"><input type="radio" name="theme" value="dark"><span class="theme-label">Dark</span></label>
              <label class="theme-option"><input type="radio" name="theme" value="high-contrast"><span class="theme-label">High Contrast</span></label>
              <label class="theme-option"><input type="radio" name="theme" value="professional"><span class="theme-label">Professional</span></label>
            </div>
          </div>
        </div>`;
      DOC.body.appendChild(menu);
    }
    let overlay = qs('#overlay');
    if (!overlay) {
      overlay = DOC.createElement('div');
      overlay.id = 'overlay';
      overlay.className = 'overlay';
      DOC.body.appendChild(overlay);
    }
  }

  function ensureSingleHamburger() {
    // Support multiple possible selectors; show the first, hide the rest
    const triggers = qsa('#hamburger-toggle, #app-hamburger, .hamburger-btn, [data-role="hamburger"]');
    if (triggers.length > 1) {
      triggers.slice(1).forEach(el => { el.style.display = 'none'; el.dataset.hiddenDuplicate = 'true'; });
    }
    return triggers[0] || null;
  }

  function bind() {
    ensureDrawerDom();
    applyTheme(getTheme());

    const toggle = ensureSingleHamburger();
    const menu   = qs('#hamburger-menu');
    const close  = qs('#close-hamburger');
    const overlay= qs('#overlay');

    function open()  { menu.classList.add('open'); overlay.classList.add('active'); DOC.body.style.overflow = 'hidden'; if (toggle) toggle.setAttribute('aria-expanded', 'true'); menu.setAttribute('aria-hidden', 'false'); }
    function closeFn(){ menu.classList.remove('open'); overlay.classList.remove('active'); DOC.body.style.overflow = ''; if (toggle) toggle.setAttribute('aria-expanded', 'false'); menu.setAttribute('aria-hidden', 'true'); }
    function toggleFn(){ menu.classList.contains('open') ? closeFn() : open(); }

    if (toggle) toggle.addEventListener('click', (e) => { e.preventDefault(); toggleFn(); });
    if (close)  close.addEventListener('click', closeFn);
    if (overlay) overlay.addEventListener('click', closeFn);
    DOC.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeFn(); });

    // Theme radios
    qsa('input[name="theme"][type="radio"]').forEach(r => {
      r.addEventListener('change', (e) => { if (e.target.checked) applyTheme(e.target.value); });
    });
  }

  // Early theme to avoid FOUC
  try {
    applyTheme(getTheme());
  } catch (_) {}
  if (DOC.readyState === 'loading') {
    DOC.addEventListener('DOMContentLoaded', bind);
  } else {
    bind();
  }
})();
