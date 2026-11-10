/** Password prompt for encrypted backups. */

import { h } from "../util/dom.js";
import { openModal } from "./modal.js";

export function openPasswordDialog({ deviceName, onSubmit }) {
  const input = h("input", {
    type: "password",
    name: "password",
    autocomplete: "current-password",
    "aria-label": "Backup password",
    placeholder: "Backup password",
  });
  const error = h("p", { class: "field-error", role: "alert" });
  const cancel = h("button", { class: "btn", type: "button", text: "Cancel" });
  const submit = h("button", { class: "btn primary", type: "submit", text: "Unlock" });

  const form = h(
    "form",
    { novalidate: true },
    h("h2", { text: `Unlock “${deviceName || "this backup"}”` }),
    h("p", {
      class: "modal-sub",
      text: "This backup is encrypted. The password is used only in memory and is never stored or sent anywhere.",
    }),
    h("div", { class: "field" }, h("label", { for: "backup-password", text: "Password" }), input),
    error,
    h("div", { class: "dialog-actions" }, cancel, submit),
  );
  input.id = "backup-password";

  const modal = openModal(form, { label: "Unlock backup" });
  cancel.addEventListener("click", () => modal.close());

  let busy = false;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    if (!input.value) {
      error.textContent = "Enter the backup password.";
      input.focus();
      return;
    }
    busy = true;
    submit.disabled = true;
    cancel.disabled = true;
    error.textContent = "";
    submit.textContent = "Unlocking…";
    try {
      await onSubmit(input.value);
      input.value = "";
      modal.close();
    } catch (err) {
      error.textContent =
        err?.code === "wrong_password"
          ? "Incorrect password. Check the password you set in iTunes/Finder and try again."
          : err?.message || "Could not open this backup.";
      input.select();
    } finally {
      busy = false;
      submit.disabled = false;
      cancel.disabled = false;
      submit.textContent = "Unlock";
    }
  });

  return modal;
}
