// Minimal, framework-agnostic menu + theme switcher
// Works on every page where layout.html includes #hamburger-btn and #app-menu

(() => {
  const STORAGE_KEY = "silhouette.theme";

  const $id = (id) => document.getElementById(id);

  function getSavedTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY) || "default";
    } catch (_) {
      return "default";
    }
  }

  function applyTheme(theme) {
    const value = theme === "dark" ? "dark" : "default";
    const root = document.documentElement;
    const body = document.body;
    if (root) {
      root.setAttribute("data-theme", value);
    }
    if (body) {
      body.setAttribute("data-theme", value);
    }
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch (_) {
      /* ignore write errors */
    }
    const btn = $id("hamburger-btn");
    if (btn) {
      btn.setAttribute("data-theme-applied", value);
    }
  }

  function ensureInitialTheme() {
    applyTheme(getSavedTheme());
  }

  function openMenu() {
    const btn = $id("hamburger-btn");
    const menu = $id("app-menu");
    const backdrop = $id("menu-backdrop");
    if (!btn || !menu || !backdrop) return;
    menu.hidden = false;
    backdrop.hidden = false;
    menu.classList.add("open");
    btn.setAttribute("aria-expanded", "true");
    menu.setAttribute("aria-hidden", "false");
    const first = menu.querySelector("a,button");
    if (first) {
      first.focus();
    }
  }

  function closeMenu(restoreFocus = true) {
    const btn = $id("hamburger-btn");
    const menu = $id("app-menu");
    const backdrop = $id("menu-backdrop");
    if (!btn || !menu || !backdrop) return;
    menu.classList.remove("open");
    btn.setAttribute("aria-expanded", "false");
    menu.setAttribute("aria-hidden", "true");
    backdrop.hidden = true;
    window.setTimeout(() => {
      menu.hidden = true;
    }, 120);
    if (restoreFocus) {
      btn.focus();
    }
  }

  function isMenuOpen() {
    const menu = $id("app-menu");
    return !!(menu && menu.classList.contains("open"));
  }

  function toggleMenu() {
    if (isMenuOpen()) {
      closeMenu();
    } else {
      openMenu();
    }
  }

  function onDocumentKeydown(event) {
    if (event.key === "Escape" && isMenuOpen()) {
      event.preventDefault();
      closeMenu();
    }
  }

  function handleMenuClick(event) {
    const target = event.target;
    const themeBtn = target.closest("[data-theme-choice]");
    if (themeBtn) {
      const choice = themeBtn.getAttribute("data-theme-choice") || "default";
      applyTheme(choice === "dark" ? "dark" : "default");
      closeMenu();
      return;
    }
    if (target.closest("a")) {
      closeMenu();
    }
  }

  function wireHandlers() {
    const btn = $id("hamburger-btn");
    const backdrop = $id("menu-backdrop");
    const menu = $id("app-menu");
    applyTheme(getSavedTheme());
    if (!btn || !backdrop || !menu) {
      return;
    }
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      toggleMenu();
    });
    backdrop.addEventListener("click", (event) => {
      event.preventDefault();
      if (isMenuOpen()) {
        closeMenu();
      }
    });
    menu.addEventListener("click", handleMenuClick);
    document.addEventListener("keydown", onDocumentKeydown);
  }

  ensureInitialTheme();

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      wireHandlers();
    });
  } else {
    wireHandlers();
  }
})();
