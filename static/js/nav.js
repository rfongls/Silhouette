// Global navigation: hamburger drawer and theme switching
// Works under sub-path deployments (root_path) and injects a hamburger if one is missing.

(function(){
  const ROOT =
    (document.body && document.body.dataset && document.body.dataset.root) ||
    (document.querySelector('meta[name="root-path"]')?.content) ||
    '';
  const HOME_PATH = '/ui/home';
  const INTEROP_PATH = '/ui/interop/skills';
  // If your Cybersecurity UI lives elsewhere, adjust this path:
  const SECURITY_PATH = '/ui/security';

  function rootUrl(p){ return (ROOT || '') + p; }

  function ensureDrawer(){
    let dr = document.getElementById('app-drawer');
    if (dr) return dr;
    dr = document.createElement('div');
    dr.id = 'app-drawer';
    dr.setAttribute('hidden', '');
    dr.innerHTML = `
      <div class="drawer-backdrop" data-close="1"></div>
      <aside class="drawer-panel" role="dialog" aria-label="Application menu">
        <nav class="drawer-menu">
          <a class="drawer-item" href="${rootUrl(HOME_PATH)}">Skills</a>
          <a class="drawer-item" href="${rootUrl(SECURITY_PATH)}">Cybersecurity Skill</a>
          <a class="drawer-item" href="${rootUrl(INTEROP_PATH)}">Interoperability Skill</a>
          <div class="drawer-section">Themes</div>
          <label class="drawer-item"><input type="radio" name="__theme" value="default"> Default</label>
          <label class="drawer-item"><input type="radio" name="__theme" value="dark"> Dark</label>
        </nav>
      </aside>
    `;
    document.body.appendChild(dr);
    return dr;
  }

  function ensureHamburger(){
    // Try to find an existing menu button
    let btn = document.querySelector('#hamburger, .hamburger, .menu-toggle, [data-role="hamburger"]');
    if (btn) return btn;
    // Inject one into the topbar if not present
    btn = document.createElement('button');
    btn.id = 'hamburger';
    btn.className = 'menu-btn';
    btn.type = 'button';
    btn.setAttribute('aria-label', 'Open menu');
    btn.setAttribute('aria-expanded', 'false');
    btn.innerHTML = '<span class="menu-icon"></span>';
    const bar = document.querySelector('.topbar') || document.body;
    bar.insertBefore(btn, bar.firstChild);
    return btn;
  }

  function setTheme(theme){
    const t = (theme === 'dark') ? 'dark' : 'default';
    document.body.setAttribute('data-theme', t);
    try { localStorage.setItem('sil.theme', t); } catch(_) {}
    // Reflect in radios if present
    const radios = document.querySelectorAll('input[name="__theme"]');
    radios.forEach(r => { r.checked = (r.value === t); });
  }
  function initTheme(){
    let t = null;
    try { t = localStorage.getItem('sil.theme'); } catch(_) {}
    setTheme(t || 'default');
  }
  function bindThemeRadios(container){
    const radios = container.querySelectorAll('input[name="__theme"]');
    radios.forEach(r => r.addEventListener('change', () => setTheme(r.value)));
  }

  function openDrawer(){
    const dr = ensureDrawer();
    dr.removeAttribute('hidden');
    requestAnimationFrame(() => dr.classList.add('open'));
    document.body.classList.add('drawer-open');
    const hb = document.querySelector('#hamburger, .hamburger, .menu-toggle, [data-role="hamburger"]');
    if (hb) hb.setAttribute('aria-expanded','true');
  }
  function closeDrawer(){
    const dr = document.getElementById('app-drawer');
    if (!dr) return;
    const panel = dr.querySelector('.drawer-panel');
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      dr.setAttribute('hidden','');
      document.body.classList.remove('drawer-open');
    };
    dr.classList.remove('open');
    if (panel) {
      panel.addEventListener('transitionend', finish, { once: true });
      setTimeout(finish, 320);
    } else {
      finish();
    }
    const hb = document.querySelector('#hamburger, .hamburger, .menu-toggle, [data-role="hamburger"]');
    if (hb) hb.setAttribute('aria-expanded','false');
  }

  document.addEventListener('DOMContentLoaded', () => {
    const btn = ensureHamburger();
    const drawer = ensureDrawer();
    initTheme();
    bindThemeRadios(drawer);
    btn.addEventListener('click', () => {
      const isOpen = drawer && drawer.classList.contains('open');
      if (isOpen) closeDrawer(); else openDrawer();
    });
    drawer.addEventListener('click', (e) => {
      if (e.target && e.target.dataset && e.target.dataset.close === '1') {
        closeDrawer();
      }
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeDrawer();
    });
  });
})();
