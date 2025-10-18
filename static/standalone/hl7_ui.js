// Verbatim behavior hook for Generate → Next Steps (matches working build semantics).
window.InteropUI = window.InteropUI || {};
window.InteropUI.onGenerateComplete = function () {
  const msg = document.querySelector('#gen-output')?.textContent || '';
  const di = document.querySelector('#deid-message-from-gen');
  const vi = document.querySelector('#val-message-from-gen');
  if (di) di.value = msg;
  if (vi) vi.value = msg;
  document.querySelector('#deid-panel')?.classList.remove('collapsed');
  document.querySelector('#validate-panel')?.classList.remove('collapsed');
};
HTMLElement.prototype.openPanel = function () { this.classList.remove('collapsed'); };

// (Safe minimal shims; your legacy file includes more helpers. This keeps behavior intact.)
window.InteropUI.setOutput = function (id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text || '';
};

// If your repo already serves a richer /static/js/interop_ui.js, you can remove these shims.
