// Minimal helper to fetch and drop an example into a target <textarea>
export async function loadExample(selectEl, textareaSelector) {
  const path = selectEl.value;
  if (!path) return;
  try {
    const res = await fetch(path, { cache: "no-cache" });
    const txt = await res.text();
    const ta = document.querySelector(textareaSelector);
    if (ta) ta.value = txt.trim();
  } catch (e) {
    console.error("Failed to load example:", e);
    alert("Could not load example. See console for details.");
  }
}
