/** Progress overlay used while unlocking and indexing. */

import { formatCount, h } from "../util/dom.js";
export function openProgressOverlay(title = "Opening backup") {
  const heading = h("h3", { text: title });
  const stage = h("p", { class: "progress-stage", text: "Starting…" });
  const fill = h("div", { class: "progress-fill indeterminate" });
  const hint = h("p", {
    class: "progress-hint",
    text: "Your backup is only read, never modified. Large libraries can take a few seconds.",
  });
  const card = h(
    "div",
    { class: "modal-card progress-card" },
    heading,
    stage,
    h("div", { class: "progress-track" }, fill),
    hint,
  );
  const overlay = h("div", { class: "modal-overlay", role: "presentation" }, card);
  document.getElementById("modal-root").append(overlay);

  return {
    update(state) {
      const progress = state?.progress || {};
      const labelMap = {
        starting: "Unlocking the backup…",
        unlocking: "Unlocking the backup…",
        extracting: "Reading the photo library…",
        reading: "Reading photo metadata…",
        resolving: "Linking photos, thumbnails and Live Photos…",
        ready: "Ready",
        failed: "Could not read the photo library",
      };
      const label = labelMap[progress.stage] || "Working…";
      if (progress.stage === "failed") {
        stage.textContent = progress.message || label;
        fill.classList.remove("indeterminate");
        fill.style.width = "100%";
        fill.style.background = "var(--danger)";
        return;
      }
      const hasTotal = Number(progress.total) > 0;
      if (hasTotal) {
        const percent = Math.min(100, Math.round((Number(progress.done) / Number(progress.total)) * 100));
        stage.textContent = `${label} ${formatCount(progress.done)} / ${formatCount(progress.total)} (${percent}%)`;
        fill.classList.remove("indeterminate");
        fill.style.width = `${Math.max(4, percent)}%`;
      } else {
        stage.textContent = label;
      }
    },
    close() {
      overlay.remove();
    },
  };
}
