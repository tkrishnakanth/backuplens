/** Bottom status bar (project-docs/UI_SPEC.md §6). */

import { h, formatCount } from "../util/dom.js";
import { icon } from "../util/icons.js";

export function createStatusBar(root, { onBackups } = {}) {
  root.className = "status-bar";
  root.innerHTML = "";
  const dot = h("span", { class: "status-dot", "aria-hidden": "true" });
  const version = h("span", { class: "version-box", text: "0.1.0" });
  const text = h("span", { class: "status-text", "aria-live": "polite", text: "Ready" });
  const count = h("span", { class: "count-pill", text: "0" });
  const backups = h(
    "button",
    {
      class: "backups-btn",
      type: "button",
      title: "Back to backups",
      onclick: () => onBackups?.(),
    },
    h("span", { html: icon("phone", 16) }),
    "Backups",
    count,
  );
  root.append(dot, version, text, h("span", { class: "header-spacer" }), backups);

  let currentMode = "idle";
  return {
    setVersion(value) {
      version.textContent = `v${value}`;
    },
    setBackupsCount(value) {
      count.textContent = String(value);
    },
    setStatus(message, mode = "idle") {
      text.textContent = message;
      if (mode !== currentMode) {
        dot.className = "status-dot";
        if (mode === "working") dot.classList.add("working");
        if (mode === "error") dot.classList.add("error");
        currentMode = mode;
      }
    },
    setSelection(countVisible, countSelected) {
      if (countSelected > 0) {
        text.textContent = `${formatCount(countSelected)} selected · ${formatCount(countVisible)} items in view`;
      } else {
        text.textContent = `${formatCount(countVisible)} items in view`;
      }
    },
  };
}
