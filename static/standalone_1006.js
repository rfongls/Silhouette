// Standalone (legacy) UI scoped behaviors.
// - Opens Next Steps trays only after a fragment renders output (htmx:afterOnLoad)
// - Auto-handoff: Generated HL7 -> De-ID textarea (if blank), De-ID -> Validate textarea (if blank)
// - Clickable headers: [data-toggle]
// - Next-step buttons scroll to the relevant card
(function () {
  function on(event, selector, handler) {
    document.addEventListener(event, (e) => {
      const el = e.target.closest(selector);
      if (el) handler(e, el);
    });
  }

  function setIfBlank(sourceId, destId) {
    const src = document.getElementById(sourceId);
    const dst = document.getElementById(destId);
    if (!src || !dst) return;
    if (!dst.value && src.value) dst.value = src.value;
  }

  // After HTMX swaps, reveal the tray that matches the target ID
  document.addEventListener("htmx:afterOnLoad", (evt) => {
    const target = evt.detail && evt.detail.target;
    if (!target) return;
    const root = target.closest(".legacy-interop-skin");
    if (!root) return;
    const tray = root.querySelector(`[data-tray="${target.id}"]`);
    if (tray) tray.classList.add("has-output");

    // Auto-handoff chain:
    // 1) After Generate -> copy to De-ID textarea if empty
    if (target.id === "gen_output") setIfBlank("hl7_text", "deid_message");
    // 2) After De-ID -> copy to Validate textarea if empty
    if (target.id === "deid_output") setIfBlank("deid_message", "validate_message");
  });

  // Toggle card bodies by clicking a [data-toggle] control in card header
  on("click", ".legacy-interop-skin .card [data-toggle]", (_e, el) => {
    const body = el.closest(".card")?.querySelector(".card-body");
    if (body) body.toggleAttribute("hidden");
  });

  // "Next steps" tray buttons
  on("click", ".legacy-interop-skin .action-tray [data-next]", (_e, el) => {
    const step = el.getAttribute("data-next");
    const allCards = Array.from(document.querySelectorAll(".legacy-interop-skin .card"));
    function scrollToHeader(headerText) {
      const match = allCards.find(c => c.querySelector(".card-header h3")?.textContent?.toLowerCase().includes(headerText));
      if (match) match.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    if (step === "deid") return scrollToHeader("de-identify");
    if (step === "validate") return scrollToHeader("validate");
    if (step === "mllp") return scrollToHeader("mllp");
  });
})();
