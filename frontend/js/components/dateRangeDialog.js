/** Date-range filter dialog for the photo browser (F-PHO-14). */

import { h } from "../util/dom.js";
import { openModal } from "./modal.js";

export function openDateRangeDialog({ from = "", to = "", onApply }) {
  const fromInput = h("input", { type: "date", value: from, "aria-label": "From date" });
  const toInput = h("input", { type: "date", value: to, "aria-label": "To date" });
  const error = h("p", { class: "field-error", role: "alert" });
  const clear = h("button", { class: "btn", type: "button", text: "Clear range" });
  const cancel = h("button", { class: "btn", type: "button", text: "Cancel" });
  const apply = h("button", { class: "btn primary", type: "submit", text: "Apply" });

  const form = h(
    "form",
    { novalidate: true },
    h("h2", { text: "Date range" }),
    h("p", { class: "modal-sub", text: "Show photos captured between these local days." }),
    h("div", { class: "field" }, h("label", { text: "From" }), fromInput),
    h("div", { class: "field" }, h("label", { text: "To" }), toInput),
    error,
    h("div", { class: "dialog-actions" }, clear, cancel, apply),
  );
  const modal = openModal(form, { label: "Date range" });
  cancel.addEventListener("click", () => modal.close());
  clear.addEventListener("click", () => {
    onApply?.({ from: null, to: null });
    modal.close();
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (fromInput.value && toInput.value && fromInput.value > toInput.value) {
      error.textContent = "The From date must be before the To date.";
      return;
    }
    onApply?.({ from: fromInput.value || null, to: toInput.value || null });
    modal.close();
  });
  return modal;
}
