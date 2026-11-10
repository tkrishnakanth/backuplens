/** About dialog. */

import { h } from "../util/dom.js";
import { openModal } from "./modal.js";

export function openAboutDialog(version) {
  const content = h(
    "div",
    {},
    h("h2", { text: "BackupLens" }),
    h("p", { class: "modal-sub", text: `Version ${version || "0.1.0"}` }),
    h("p", {
      text: "A local-only, read-only browser for photos and videos in encrypted iOS backups. Nothing leaves this computer, and the backup folder is never modified.",
    }),
    h("p", {
      class: "dialog-note",
      text: "BackupLens is an independent project. It is not affiliated with Apple or any commercial backup viewer. Photos stored only in iCloud may not be present in a local backup.",
    }),
    h("div", { class: "dialog-actions" }, h("button", { class: "btn primary", type: "button", text: "Close", onclick: () => modal.close() })),
  );
  const modal = openModal(content, { label: "About BackupLens" });
  return modal;
}
