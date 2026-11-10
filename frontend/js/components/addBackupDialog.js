/** Add a backup folder path. */

import { h } from "../util/dom.js";
import { openModal } from "./modal.js";

export function openAddBackupDialog({ onSubmit, onBrowse }) {
  const input = h("input", {
    type: "text",
    name: "path",
    placeholder: "C:\\Users\\You\\Apple\\MobileSync\\Backup\\DEMO-UDID-…",
    "aria-label": "Backup folder path",
  });
  const error = h("p", { class: "field-error", role: "alert" });
  const cancel = h("button", { class: "btn", type: "button", text: "Cancel" });
  const browse = h("button", { class: "btn", type: "button", text: "Browse…" });
  const add = h("button", { class: "btn primary", type: "submit", text: "Add backup" });

  const form = h(
    "form",
    { novalidate: true },
    h("h2", { text: "Add backup folder" }),
    h("p", {
      class: "modal-sub",
      text: "Choose the device folder that contains Info.plist and Manifest.plist.",
    }),
    h(
      "div",
      { class: "field" },
      h("label", { for: "backup-path", text: "Folder path" }),
      h("div", { class: "field-row" }, input, browse),
    ),
    error,
    h("div", { class: "dialog-actions" }, cancel, add),
  );
  input.id = "backup-path";
  const modal = openModal(form, { label: "Add backup folder" });
  cancel.addEventListener("click", () => modal.close());

  browse.addEventListener("click", async () => {
    try {
      const result = await onBrowse?.();
      if (result) input.value = result;
    } catch (err) {
      error.textContent = err?.message || "Could not open the folder picker.";
    }
  });

  let busy = false;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    const path = input.value.trim();
    if (!path) {
      error.textContent = "Enter a folder path.";
      input.focus();
      return;
    }
    busy = true;
    add.disabled = true;
    add.textContent = "Adding…";
    error.textContent = "";
    try {
      await onSubmit(path);
      modal.close();
    } catch (err) {
      error.textContent = err?.message || "That folder is not a valid iOS backup.";
    } finally {
      busy = false;
      add.disabled = false;
      add.textContent = "Add backup";
    }
  });
  return modal;
}
