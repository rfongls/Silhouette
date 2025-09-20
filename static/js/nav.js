// Global navigation + theme handling
(function () {
  const THEME_KEY = "silhouette.theme";

  function applyTheme(name) {
    const theme = name === "dark" ? "dark" : "default";
    const root = document.documentElement;
    if (root) {
      root.setAttribute("data-theme", theme);
      root.dataset.theme = theme;
    }
    if (document.body) {
      document.body.setAttribute("data-theme", theme);
    }
  }

  // Apply saved theme as early as possible
  try {
    const saved = localStorage.getItem(THEME_KEY) || "default";
    applyTheme(saved);
  } catch (_) {
    applyTheme("default");
  }

  function reflectThemeControls(theme) {
    const dark = document.getElementById("theme-dark");
    const def = document.getElementById("theme-default");
    if (dark) dark.checked = theme === "dark";
    if (def) def.checked = theme !== "dark";
  }

  function setTheme(name) {
    const theme = name === "dark" ? "dark" : "default";
    applyTheme(theme);
    reflectThemeControls(theme);
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch (_) {
      /* ignore */
    }
  }

  function closeMenu(btn, panel, backdrop) {
    if (panel) {
      panel.classList.remove("open");
      panel.hidden = true;
    }
    if (btn) {
      btn.setAttribute("aria-expanded", "false");
    }
    if (backdrop) {
      backdrop.hidden = true;
    }
    document.body && document.body.classList.remove("menu-open");
  }

  function openMenu(btn, panel, backdrop) {
    if (panel) {
      panel.hidden = false;
      requestAnimationFrame(() => panel.classList.add("open"));
    }
    if (btn) {
      btn.setAttribute("aria-expanded", "true");
    }
    if (backdrop) {
      backdrop.hidden = false;
    }
    document.body && document.body.classList.add("menu-open");
  }

  document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("menu-button");
    const panel = document.getElementById("menu-panel");
    const backdrop = document.getElementById("menu-backdrop");

    const saved = (() => {
      try {
        return localStorage.getItem(THEME_KEY) || "default";
      } catch (_) {
        return "default";
      }
    })();
    reflectThemeControls(saved);

    if (btn && panel) {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const isOpen = btn.getAttribute("aria-expanded") === "true";
        if (isOpen) {
          closeMenu(btn, panel, backdrop);
        } else {
          openMenu(btn, panel, backdrop);
        }
      });
    }

    if (backdrop) {
      backdrop.addEventListener("click", () => closeMenu(btn, panel, backdrop));
    }

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeMenu(btn, panel, backdrop);
      }
    });

    if (panel) {
      panel.addEventListener("click", (event) => {
        const link = event.target.closest("a.menu-link");
        if (link) {
          closeMenu(btn, panel, backdrop);
          return;
        }
        const themeRadio = event.target.closest('input[name="theme"]');
        if (themeRadio) {
          setTheme(themeRadio.value);
        }
      });

      panel.addEventListener("change", (event) => {
        const themeRadio = event.target.closest('input[name="theme"]');
        if (themeRadio) {
          setTheme(themeRadio.value);
        }
      });
    }
  });
})();
