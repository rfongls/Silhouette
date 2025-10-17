(function () {
  const doc = document;
  const win = window;
  const urls = win.STANDALONE_PIPELINE_URLS || {};
  function $(selector, root) {
    return (root || doc).querySelector(selector);
  }

  function $all(selector, root) {
    return Array.from((root || doc).querySelectorAll(selector));
  }

  function extractText(node) {
    if (!node) return "";
    if (node.tagName === "PRE") {
      return node.textContent || "";
    }
    if ("value" in node && node.value) {
      return node.value;
    }
    return node.textContent || "";
  }

  function setText(id, value, { overwrite = false } = {}) {
    const el = $(id.startsWith("#") ? id : `#${id}`);
    if (!el) return;
    if (!overwrite && "value" in el && el.value) {
      return;
    }
    if ("value" in el) {
      el.value = value;
      el.dispatchEvent(new Event("input", { bubbles: true }));
    } else {
      el.textContent = value;
    }
  }

  win.InteropUI = win.InteropUI || {};
  win.InteropUI.copyFrom = function (fromSelector, toSelector) {
    try {
      const source = $(fromSelector);
      const target = $(toSelector);
      if (!source || !target) return;
      const text = extractText(source);
      if ("value" in target) {
        target.value = text.trim();
        target.dispatchEvent(new Event("input", { bubbles: true }));
      } else {
        target.textContent = text;
      }
    } catch (_) {}
  };

  win.InteropUI.loadFileIntoTextarea = function (inputEl, targetId) {
    try {
      const fileInput = typeof inputEl === "string" ? $(inputEl) : inputEl;
      const textarea = $(targetId.startsWith("#") ? targetId : `#${targetId}`);
      const file = fileInput?.files?.[0];
      if (!file || !textarea) return;
      const reader = new FileReader();
      reader.onload = () => {
        textarea.value = reader.result || "";
        textarea.dispatchEvent(new Event("input", { bubbles: true }));
      };
      reader.readAsText(file);
    } catch (_) {}
  };

  function revealTrayFor(target) {
    if (!target || !target.id) return null;
    const selector = `#${target.id}`;
    let matched = null;
    $all(`.action-tray[data-source="${selector}"]`).forEach((tray) => {
      tray.classList.add("has-output");
      matched = tray;
    });
    return matched;
  }

  function handoffMessage(stage, text) {
    if (!text) return;
    if (stage === "gen") {
      setText("#deid-msg", text);
      setText("#validate-msg", text);
    } else if (stage === "deid") {
      setText("#validate-msg", text);
    } else if (stage === "validate") {
      setText("#mllp-msg", text, { overwrite: true });
    }
  }

  function openPanel(id) {
    const panel = $(id);
    if (!panel) return;
    if (panel.tagName === "DETAILS") {
      panel.open = true;
    }
    try {
      panel.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (_) {}
  }

  function wireActionTray(event) {
    const button = event.target.closest(".action-tray [data-action]");
    if (!button) return;
    const tray = button.closest(".action-tray");
    if (!tray) return;
    const sourceSelector = tray.getAttribute("data-source") || "";
    const action = button.getAttribute("data-action") || "";
    const source = sourceSelector ? $(sourceSelector) : null;
    const text = extractText(source);
    if (action === "deid") {
      setText("#deid-msg", text, { overwrite: true });
      openPanel("#deid-panel");
    } else if (action === "validate") {
      setText("#validate-msg", text, { overwrite: true });
      openPanel("#validate-panel");
    } else if (action === "mllp") {
      setText("#mllp-msg", text, { overwrite: true });
      openPanel("#mllp-panel");
    } else if (action === "pipeline") {
      if (urls.ui_pipeline) {
        win.open(urls.ui_pipeline, "_blank", "noopener,noreferrer");
      }
    }
  }

  async function loadSamples(version) {
    if (!urls.samples || !urls.sample) return null;
    try {
      const listResp = await fetch(`${urls.samples}?version=${encodeURIComponent(version || "hl7-v2-4")}&limit=200`, {
        headers: { Accept: "application/json" },
      });
      if (!listResp.ok) return null;
      const data = await listResp.json();
      const items = Array.isArray(data.items) ? data.items : [];
      if (items.length === 0) return null;
      const first = items[0];
      const triggerList = doc.getElementById("std-trigger-list");
      if (triggerList) {
        triggerList.innerHTML = "";
        items.forEach((item) => {
          const option = doc.createElement("option");
          option.value = item.trigger || item.filename;
          option.label = item.description || option.value;
          triggerList.appendChild(option);
        });
      }
      if (!first.relpath) return null;
      const sampleResp = await fetch(`${urls.sample}?relpath=${encodeURIComponent(first.relpath)}`, {
        headers: { Accept: "text/plain" },
      });
      if (!sampleResp.ok) return null;
      const text = await sampleResp.text();
      return { text, trigger: first.trigger || "", relpath: first.relpath };
    } catch (err) {
      console.warn("standalone.loadSamples.failed", err);
      return null;
    }
  }

  async function handleSampleLoad(event) {
    const button = event.target.closest("#std-load-sample");
    if (!button) return;
    event.preventDefault();
    const version = doc.getElementById("std-version")?.value || "hl7-v2-4";
    const payload = await loadSamples(version);
    if (payload && payload.text) {
      setText("#gen-output", payload.text, { overwrite: true });
      setText("#deid-msg", payload.text, { overwrite: true });
      setText("#validate-msg", payload.text, { overwrite: true });
      setText("#mllp-msg", payload.text, { overwrite: false });
      const trigInput = doc.getElementById("std-trigger-input");
      if (trigInput && payload.trigger) {
        trigInput.value = payload.trigger;
      }
      revealTrayFor({ id: "gen-output" });
    }
  }

  function afterSwap(evt) {
    const target = evt.detail ? evt.detail.target : null;
    if (!target) return;
    const tray = revealTrayFor(target);
    const text = extractText(target).trim();
    const stage = tray?.getAttribute("data-stage") || "";
    handoffMessage(stage, text);
    if (stage === "gen" && text) {
      setText("#mllp-msg", text, { overwrite: false });
    }
  }

  doc.addEventListener("click", wireActionTray);
  doc.addEventListener("click", handleSampleLoad);
  doc.addEventListener("htmx:afterSwap", afterSwap);
  doc.addEventListener("htmx:afterOnLoad", afterSwap);

  // Ensure trays open after initial render if content already present
  doc.addEventListener("DOMContentLoaded", () => {
    $all(".action-tray").forEach((tray) => {
      const sourceSelector = tray.getAttribute("data-source");
      const source = sourceSelector ? $(sourceSelector) : null;
      if (extractText(source).trim()) {
        tray.classList.add("has-output");
      }
    });
    // Preload triggers so the datalist is populated even before interaction.
    if (urls.samples && urls.sample) {
      loadSamples(doc.getElementById("std-version")?.value || "hl7-v2-4");
    }
  });
})();
