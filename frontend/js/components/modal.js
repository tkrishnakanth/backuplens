/** Modal helper with focus restore and Escape handling. */

import { h, qsa } from "../util/dom.js";

const root = () => document.getElementById("modal-root");

export function openModal(content, { label = "Dialog", wide = false, onClose = null } = {}) {
  const previous = document.activeElement;
  const overlay = h("div", { class: "modal-overlay", role: "presentation" });
  const card = h(
    "div",
    {
      class: `modal-card${wide ? " wide" : ""}`,
      role: "dialog",
      "aria-modal": "true",
      "aria-label": label,
    },
    content,
  );
  overlay.append(card);
  root().append(overlay);

  function close() {
    document.removeEventListener("keydown", onKey);
    overlay.remove();
    if (previous instanceof HTMLElement) previous.focus();
    onClose?.();
  }

  function onKey(event) {
    if (event.key === "Escape") {
      event.stopPropagation();
      close();
    } else if (event.key === "Tab") {
      const focusable = qsa(
        'button:not([disabled]), input:not([disabled]), select:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
        card,
      ).filter((el) => el.offsetParent !== null);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  }

  overlay.addEventListener("mousedown", (event) => {
    if (event.target === overlay) close();
  });
  document.addEventListener("keydown", onKey);

  const firstField = card.querySelector("input, select, button");
  firstField?.focus();

  return { close, card, overlay };
}
