module.exports = {
  content: ["./templates/**/*.html", "./static/**/*.js"],
  // Keep legacy-UI-only classes from being purged in production builds
  safelist: [
    "legacy-compat",
    "legacy-interop-skin",
    "fullbleed",
    "standalone-pipeline",
    "cards-stack",
    "action-tray",
    "visible",
    "codepane",
    "limit10",
    "summary-title",
    "summary-meta",
    "minimax",
  ],
  theme: { extend: {} },
  plugins: [],
};
