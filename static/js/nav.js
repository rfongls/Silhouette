(function(){
  const STORAGE_KEY = 'silhouette.theme';
  const rootPath = () => (document.body && document.body.dataset && document.body.dataset.root) || window.ROOT || '';
  const rootUrl = (path) => {
    if (!path) return rootPath();
    if (/^https?:\/\//i.test(path)) return path;
    return `${rootPath()}${path}`;
  };

  function markActive(){
    const path = location.pathname;
    const map = [
      {sel:'[data-nav="reports"]', match:/^\/ui\/home\/?$/},
      {sel:'[data-nav="skills"]', match:/^\/ui\/skills\/?/},
    ];
    map.forEach((m) => {
      const a = document.querySelector(m.sel);
      if (!a) return;
      if (m.match.test(path)) a.classList.add('active');
    });
  }

  let menuButton;
  let drawer;
  let backdrop;
  let closeButton;
  let themeSelect;
  let menuOpen = false;
  let focusRestore = null;

  function setMenuState(open){
    if (!drawer) return;
    if (open) {
      if (menuOpen) return;
      menuOpen = true;
      focusRestore = document.activeElement;
      menuButton && menuButton.setAttribute('aria-expanded', 'true');
      backdrop && backdrop.removeAttribute('hidden');
      drawer.removeAttribute('hidden');
      requestAnimationFrame(() => drawer.classList.add('open'));
      document.body.classList.add('menu-open');
      const focusTarget = themeSelect || drawer;
      setTimeout(() => {
        if (focusTarget && typeof focusTarget.focus === 'function') {
          focusTarget.focus({ preventScroll: true });
        }
      }, 120);
      document.addEventListener('keydown', onKeyDown);
    } else {
      if (!menuOpen) return;
      menuOpen = false;
      menuButton && menuButton.setAttribute('aria-expanded', 'false');
      document.body.classList.remove('menu-open');
      const finish = () => {
        drawer && drawer.setAttribute('hidden', '');
        backdrop && backdrop.setAttribute('hidden', '');
      };
      if (drawer.classList.contains('open')) {
        drawer.classList.remove('open');
        drawer.addEventListener('transitionend', finish, { once: true });
        setTimeout(() => finish(), 260);
      } else {
        finish();
      }
      document.removeEventListener('keydown', onKeyDown);
      if (focusRestore && typeof focusRestore.focus === 'function') {
        focusRestore.focus({ preventScroll: true });
      } else if (menuButton) {
        menuButton.focus();
      }
      focusRestore = null;
    }
  }

  function onKeyDown(event){
    if (event.key === 'Escape') {
      event.preventDefault();
      setMenuState(false);
    }
  }

  function setupMenu(){
    menuButton = document.getElementById('menu-toggle');
    drawer = document.getElementById('app-drawer');
    backdrop = document.getElementById('app-menu-backdrop');
    closeButton = document.getElementById('menu-close');
    themeSelect = document.getElementById('theme-select');

    if (menuButton) menuButton.addEventListener('click', () => setMenuState(!menuOpen));
    if (closeButton) closeButton.addEventListener('click', () => setMenuState(false));
    if (backdrop) backdrop.addEventListener('click', () => setMenuState(false));

    document.addEventListener('keyup', (event) => {
      if (event.key === 'm' && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        setMenuState(!menuOpen);
      }
    });

    if (themeSelect) {
      themeSelect.addEventListener('change', (event) => {
        applyTheme(event.target && event.target.value);
      });
    }
  }

  function renderSkills(skills){
    const list = document.getElementById('menu-skills');
    if (!list) return;
    list.innerHTML = '';
    const items = Array.isArray(skills) ? skills : [];
    if (!items.length) {
      const li = document.createElement('li');
      li.className = 'menu-empty muted';
      li.textContent = 'No additional skills available';
      list.appendChild(li);
      return;
    }
    items.forEach((skill) => {
      if (!skill) return;
      const li = document.createElement('li');
      li.className = 'menu-skill';
      const link = document.createElement('a');
      const name = skill.name || skill.id || 'Skill';
      link.href = rootUrl(skill.dashboard || '#');
      link.textContent = name;
      if (skill.desc) {
        const small = document.createElement('small');
        small.textContent = skill.desc;
        link.appendChild(small);
      }
      link.addEventListener('click', () => setMenuState(false));
      li.appendChild(link);
      list.appendChild(li);
    });
  }

  async function loadSkills(){
    const list = document.getElementById('menu-skills');
    if (!list) return;
    try {
      const response = await fetch(rootUrl('/api/ui/skills'));
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      renderSkills(data);
    } catch (err) {
      const li = document.createElement('li');
      li.className = 'menu-empty muted';
      li.textContent = 'Unable to load skills';
      list.innerHTML = '';
      list.appendChild(li);
      console.warn('Failed to load skills', err);
    }
  }

  function getStoredTheme(){
    try {
      return localStorage.getItem(STORAGE_KEY) || '';
    } catch (err) {
      return '';
    }
  }

  function applyTheme(theme, persist = true){
    const root = document.documentElement;
    const normalized = theme === 'dark' || theme === 'light' ? theme : 'system';
    if (normalized === 'system') {
      root.removeAttribute('data-theme');
      root.style.colorScheme = '';
      if (persist) {
        try { localStorage.removeItem(STORAGE_KEY); } catch (err) { /* ignore */ }
      }
    } else {
      root.setAttribute('data-theme', normalized);
      root.style.colorScheme = normalized;
      if (persist) {
        try { localStorage.setItem(STORAGE_KEY, normalized); } catch (err) { /* ignore */ }
      }
    }
    if (themeSelect && themeSelect.value !== normalized) {
      themeSelect.value = normalized;
    }
  }

  function initTheme(){
    const stored = getStoredTheme();
    const theme = stored === 'dark' || stored === 'light' ? stored : 'system';
    applyTheme(theme, false);
    if (themeSelect) themeSelect.value = theme;

    const media = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
    if (media) {
      const update = () => {
        if (!getStoredTheme()) {
          applyTheme('system', false);
        }
      };
      if (typeof media.addEventListener === 'function') media.addEventListener('change', update);
      else if (typeof media.addListener === 'function') media.addListener(update);
    }
  }

  function onReady(fn){
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn);
    else fn();
  }

  onReady(() => {
    markActive();
    setupMenu();
    initTheme();
    loadSkills();
  });
})();
