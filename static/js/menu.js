// Global hamburger menu + theme switcher
// - Neutral control anchored top-right
// - Auto-injects markup if layout omitted it
(() => {
  const STORAGE_KEY = "silhouette.theme";
  const doc = typeof document !== "undefined" ? document : null;
  if (!doc) return;

  const byId = (id) => doc.getElementById(id);

  function getRootPath() {
    const meta =
      doc.querySelector('meta[name="app-root"]') ||
      doc.querySelector('meta[name="root-path"]');
    if (meta) {
      return meta.getAttribute("content") || "";
    }
    const body = doc.body;
    if (body) {
      return body.getAttribute("data-root") || body.dataset?.root || "";
    }
    return "";
  }

  function ensureButton() {
    let btn = byId("hamburger-btn");
    if (!btn) {
      btn = doc.createElement("button");
      btn.id = "hamburger-btn";
      doc.body.appendChild(btn);
    }
    btn.type = "button";
    btn.setAttribute("aria-label", "Open menu");
    btn.setAttribute("aria-controls", "app-menu");
    btn.setAttribute("aria-expanded", "false");
    if (!btn.querySelector(".hamburger-icon")) {
      btn.innerHTML = '<span class="hamburger-icon" aria-hidden="true"></span>';
    }
    // Remove legacy .btn class if present so neutral styles apply.
    btn.classList.remove("btn");
    return btn;
  }

  function ensureBackdrop() {
    let backdrop = byId("menu-backdrop");
    if (!backdrop) {
      backdrop = doc.createElement("div");
      backdrop.id = "menu-backdrop";
      doc.body.appendChild(backdrop);
    }
    backdrop.hidden = true;
    return backdrop;
  }

  function ensureMenu(root) {
    let menu = byId("app-menu");
    if (!menu) {
      menu = doc.createElement("nav");
      menu.id = "app-menu";
      doc.body.appendChild(menu);
    }
    menu.classList.add("app-menu");
    menu.setAttribute("aria-hidden", "true");
    menu.hidden = true;
    if (!menu.innerHTML.trim()) {
      menu.innerHTML = `
        <ul>
          <li><a class="menu-item" href="${root}/ui/home">Skills</a></li>
          <li><a class="menu-item" href="${root}/ui/security/dashboard">Cybersecurity Skill</a></li>
          <li><a class="menu-item" href="${root}/ui/interop/skills">Interoperability Skill</a></li>
          <li class="menu-divider"></li>
          <li class="menu-heading">Theme</li>
          <li><button class="menu-item" type="button" data-theme-choice="light">Default</button></li>
          <li><button class="menu-item" type="button" data-theme-choice="dark">Dark</button></li>
        </ul>`;
    } else {
      // Ensure theme buttons advertise supported values even if markup existed.
      menu.querySelectorAll("[data-theme-choice]").forEach((el) => {
        const choice = el.getAttribute("data-theme-choice");
        if (choice && choice !== "dark") {
          el.setAttribute("data-theme-choice", "light");
        }
        if (el.tagName === "BUTTON" && !el.getAttribute("type")) {
          el.setAttribute("type", "button");
        }
      });
    }
    return menu;
  }

  function ensureMarkup() {
    if (!doc.body) return;
    const root = getRootPath();
    const btn = ensureButton();
    const backdrop = ensureBackdrop();
    const menu = ensureMenu(root);
    return { btn, backdrop, menu };
  }

  function getSavedTheme() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored === "dark" ? "dark" : "light";
    } catch (_) {
      return "light";
    }
  }

  function applyTheme(theme) {
    const value = theme === "dark" ? "dark" : "light";
    const root = doc.documentElement;
    const body = doc.body;
    if (root) {
      root.setAttribute("data-theme", value);
    }
    if (body) {
      body.setAttribute("data-theme", value);
    }
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch (_) {
      /* ignore storage write failures */
    }
    const btn = byId("hamburger-btn");
    if (btn) {
      btn.setAttribute("data-theme-applied", value);
    }
  }

  function ensureInitialTheme() {
    applyTheme(getSavedTheme());
  }

  function openMenu() {
    const btn = byId("hamburger-btn");
    const menu = byId("app-menu");
    const backdrop = byId("menu-backdrop");
    if (!btn || !menu || !backdrop) return;
    menu.hidden = false;
    backdrop.hidden = false;
    requestAnimationFrame(() => menu.classList.add("open"));
    btn.setAttribute("aria-expanded", "true");
    menu.setAttribute("aria-hidden", "false");
    const first = menu.querySelector("a,button.menu-item");
    if (first) {
      first.focus();
    }
  }

  function closeMenu(restoreFocus = true) {
    const btn = byId("hamburger-btn");
    const menu = byId("app-menu");
    const backdrop = byId("menu-backdrop");
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
    const menu = byId("app-menu");
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
    const themeBtn = event.target.closest("[data-theme-choice]");
    if (themeBtn) {
      const choice = themeBtn.getAttribute("data-theme-choice") || "light";
      applyTheme(choice === "dark" ? "dark" : "light");
      closeMenu();
      return;
    }
    if (event.target.closest("a")) {
      closeMenu();
    }
  }

  function wireHandlers() {
    const btn = byId("hamburger-btn");
    const backdrop = byId("menu-backdrop");
    const menu = byId("app-menu");
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
    doc.addEventListener("keydown", onDocumentKeydown);
  }

  function boot() {
    ensureMarkup();
    ensureInitialTheme();
    wireHandlers();
  }

  if (doc.readyState === "loading") {
    doc.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
