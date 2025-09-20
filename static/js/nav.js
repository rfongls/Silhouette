export {};

(function () {
  const html = document.documentElement;
  const drawer = document.getElementById('app-drawer');
  const hamburger = document.getElementById('app-hamburger');
  const backdrop = document.getElementById('drawer-backdrop');
  if (!drawer || !hamburger || !backdrop) {
    return;
  }

  function setOpen(open) {
    drawer.classList.toggle('open', !!open);
    drawer.setAttribute('aria-hidden', open ? 'false' : 'true');
    hamburger.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) {
      const first = drawer.querySelector('a,button');
      if (first && typeof first.focus === 'function') {
        first.focus();
      }
    } else if (typeof hamburger.focus === 'function') {
      hamburger.focus();
    }
  }

  hamburger.addEventListener('click', () => {
    setOpen(!drawer.classList.contains('open'));
  });

  backdrop.addEventListener('click', () => setOpen(false));

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      setOpen(false);
    }
  });

  const savedTheme = (() => {
    try {
      return localStorage.getItem('silhouette.theme') || 'default';
    } catch (err) {
      return 'default';
    }
  })();
  if (savedTheme) {
    html.setAttribute('data-theme', savedTheme);
  }

  document.querySelectorAll('[data-theme-choice]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const next = btn.getAttribute('data-theme-choice') || 'default';
      html.setAttribute('data-theme', next);
      try {
        localStorage.setItem('silhouette.theme', next);
      } catch (err) {
        /* ignore persistence errors */
      }
    });
  });
})();
