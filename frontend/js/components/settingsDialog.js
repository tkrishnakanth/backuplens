/** Settings dialog (theme, grouping, thumbnail size, cache). */

import { h } from "../util/dom.js";
import { openModal } from "./modal.js";

const MB = 1024 * 1024;

function select(name, options, value, label) {
  const element = h("select", { name, "aria-label": label });
  for (const [optionValue, text] of options) {
    const option = h("option", { value: optionValue, text });
    if (String(optionValue) === String(value)) option.selected = true;
    element.append(option);
  }
  return element;
}

export function openSettingsDialog({ settings, onBrowse, onSave }) {
  const theme = select(
    "theme",
    [
      ["system", "Follow system"],
      ["light", "Light"],
      ["dark", "Dark"],
    ],
    settings.theme || "system",
    "Theme",
  );
  const zone = select(
    "dateGroupingZone",
    [
      ["capture", "Capture timezone (from the backup)"],
      ["machine", "This computer's timezone"],
    ],
    settings.dateGroupingZone || "capture",
    "Date grouping timezone",
  );
  const thumbs = select(
    "thumbnailSize",
    [
      ["160", "Small (160 px)"],
      ["240", "Medium (240 px)"],
      ["320", "Default (320 px)"],
      ["480", "Large (480 px)"],
    ],
    settings.thumbnailSize || 320,
    "Thumbnail size",
  );
  const cacheLocation = h("input", {
    type: "text",
    value: settings.cacheLocation || "",
    "aria-label": "Cache folder",
  });
  const browse = h("button", { class: "btn", type: "button", text: "Browse…" });
  const cacheLimit = h("input", {
    type: "number",
    min: "16",
    step: "16",
    value: String(Math.round((settings.cacheLimitBytes || 0) / MB) || 2048),
    "aria-label": "Cache limit in megabytes",
  });
  const error = h("p", { class: "field-error", role: "alert" });
  const cancel = h("button", { class: "btn", type: "button", text: "Cancel" });
  const save = h("button", { class: "btn primary", type: "submit", text: "Save settings" });

  const form = h(
    "form",
    { novalidate: true },
    h("h2", { text: "Settings" }),
    h("p", { class: "modal-sub", text: "Stored locally in %LOCALAPPDATA%\\BackupLens\\config.json." }),
    h("div", { class: "field" }, h("label", { text: "Theme" }), theme),
    h("div", { class: "field" }, h("label", { text: "Date grouping" }), zone),
    h("div", { class: "field" }, h("label", { text: "Thumbnail size" }), thumbs),
    h(
      "div",
      { class: "field" },
      h("label", { text: "Cache folder" }),
      h("div", { class: "field-row" }, cacheLocation, browse),
    ),
    h(
      "div",
      { class: "field" },
      h("label", { text: "Cache limit (MB)" }),
      cacheLimit,
    ),
    h("p", {
      class: "dialog-note",
      text: "The cache stores thumbnails, previews and decrypted originals while the app runs. It is cleared on exit unless persistence is enabled with CACHE_PERSIST.",
    }),
    error,
    h("div", { class: "dialog-actions" }, cancel, save),
  );

  const modal = openModal(form, { label: "Settings" });
  cancel.addEventListener("click", () => modal.close());
  browse.addEventListener("click", async () => {
    try {
      const picked = await onBrowse?.();
      if (picked) cacheLocation.value = picked;
    } catch (err) {
      error.textContent = err?.message || "Folder picker unavailable; type a path.";
    }
  });

  let busy = false;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    const limitMb = Number(cacheLimit.value);
    if (!Number.isFinite(limitMb) || limitMb < 16) {
      error.textContent = "Cache limit must be at least 16 MB.";
      return;
    }
    busy = true;
    save.disabled = true;
    save.textContent = "Saving…";
    error.textContent = "";
    try {
      await onSave?.({
        theme: theme.value,
        dateGroupingZone: zone.value,
        thumbnailSize: Number(thumbs.value),
        cacheLocation: cacheLocation.value.trim(),
        cacheLimitBytes: Math.round(limitMb * MB),
      });
      modal.close();
    } catch (err) {
      error.textContent = err?.message || "Could not save settings.";
    } finally {
      busy = false;
      save.disabled = false;
      save.textContent = "Save settings";
    }
  });
  return modal;
}
