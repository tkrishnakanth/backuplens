/** Export dialog (wired to /api/export from Phase 6). */

import { api } from "../api.js";
import { formatBytes } from "../util/dates.js";
import { formatCount, h } from "../util/dom.js";
import { openModal } from "./modal.js";
import { showToast } from "./toast.js";

function checkbox(label, name, checked = false) {
  return h(
    "label",
    { class: "field-check" },
    h("input", { type: "checkbox", name, checked }),
    label,
  );
}

export function openExportDialog({
  summary,
  count,
  ids = null,
  scope = null,
  onDone,
}) {
  const destination = h("input", {
    type: "text",
    name: "destination",
    placeholder: "D:\\Exports\\Photos",
    "aria-label": "Destination folder",
  });
  const browse = h("button", { class: "btn", type: "button", text: "Browse…" });
  const layout = h(
    "select",
    { name: "layout", "aria-label": "Folder layout" },
    h("option", { value: "flat", text: "Flat (all files together)" }),
    h("option", { value: "by-date", text: "By date (YYYY/YYYY-MM-DD)" }),
    h("option", { value: "by-album", text: "By album" }),
    h("option", { value: "original-path", text: "Original backup path" }),
  );
  const conflict = h(
    "select",
    { name: "onConflict", "aria-label": "If a file exists" },
    h("option", { value: "skip", text: "Skip existing files" }),
    h("option", { value: "rename", text: "Rename new files" }),
    h("option", { value: "overwrite", text: "Overwrite existing files" }),
  );
  const convert = checkbox("Convert HEIC to JPEG", "convertHeicToJpeg");
  const live = checkbox("Include Live Photo videos", "includeLiveVideo", true);
  const edited = checkbox("Include edited versions (.AAE)", "includeEdited");
  const dates = checkbox("Set file dates to capture date", "setFileDates", true);

  const error = h("p", { class: "field-error", role: "alert" });
  const progressWrap = h("div", { class: "export-progress", hidden: true });
  const progressStage = h("p", { class: "progress-stage", text: "" });
  const progressFill = h("div", { class: "progress-fill" });
  const progressTrack = h("div", { class: "progress-track" }, progressFill);
  const summaryText = h("p", { class: "export-summary" });
  progressWrap.append(progressStage, progressTrack, summaryText);

  const cancel = h("button", { class: "btn", type: "button", text: "Cancel" });
  const zip = h("button", {
    class: "btn",
    type: "button",
    text: "Download ZIP",
    hidden: !(ids?.length && ids.length <= 500),
  });
  const start = h("button", { class: "btn primary", type: "submit", text: "Export" });
  const actions = h("div", { class: "dialog-actions" }, zip, cancel, start);

  const form = h(
    "form",
    { novalidate: true },
    h("h2", { text: "Export photos" }),
    h("p", { class: "modal-sub", text: `${summary} · ${formatCount(count)} items` }),
    h(
      "div",
      { class: "field" },
      h("label", { for: "export-destination", text: "Destination folder" }),
      h("div", { class: "field-row" }, destination, browse),
    ),
    h(
      "div",
      { class: "field" },
      h("label", { for: "export-layout", text: "Folder layout" }),
      layout,
    ),
    h(
      "div",
      { class: "field" },
      h("label", { for: "export-conflict", text: "If a file exists" }),
      conflict,
    ),
    convert,
    live,
    edited,
    dates,
    error,
    progressWrap,
    actions,
  );
  destination.id = "export-destination";
  layout.id = "export-layout";
  conflict.id = "export-conflict";

  const modal = openModal(form, { label: "Export photos", wide: true });
  let jobId = null;
  let pollTimer = 0;
  let running = false;

  cancel.addEventListener("click", async () => {
    if (running && jobId) {
      try {
        await api.cancelJob(jobId);
        progressStage.textContent = "Cancelling…";
      } catch (err) {
        showToast(err?.message || "Could not cancel the export", "error");
      }
      return;
    }
    modal.close();
  });

  browse.addEventListener("click", async () => {
    try {
      const result = await api.pickFolder();
      if (result) destination.value = result;
    } catch (err) {
      error.textContent = err?.message || "Folder picker unavailable; type a path instead.";
    }
  });

  zip.addEventListener("click", async () => {
    if (!ids?.length) return;
    zip.disabled = true;
    try {
      const blob = await api.exportZip({ ids });
      const url = URL.createObjectURL(blob);
      const anchor = h("a", { href: url, download: "backuplens-export.zip" });
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 5000);
    } catch (err) {
      error.textContent = err?.message || "ZIP download failed.";
    } finally {
      zip.disabled = false;
    }
  });

  function updateProgress(job) {
    progressWrap.hidden = false;
    const total = Math.max(1, Number(job.total) || count);
    const done = Number(job.done) || 0;
    const percent = Math.min(100, Math.round((done / total) * 100));
    progressFill.style.width = `${percent}%`;
    progressStage.textContent =
      job.state === "done"
        ? "Export complete"
        : job.state === "cancelled"
          ? "Export cancelled"
          : job.state === "failed"
            ? "Export failed"
            : `Exporting ${formatCount(done)} / ${formatCount(total)} (${percent}%)`;
    summaryText.textContent = job.currentFile
      ? `${job.currentFile} · ${formatBytes(job.bytes)} written`
      : `${formatBytes(job.bytes)} written`;
    if (job.errors?.length) {
      error.textContent = `${job.errors.length} file(s) failed: ${job.errors.slice(0, 2).join("; ")}`;
    }
    if (job.state !== "running" && job.state !== "queued") {
      running = false;
      window.clearInterval(pollTimer);
      start.disabled = false;
      cancel.textContent = "Close";
      onDone?.(job);
    }
  }

  function poll() {
    if (!jobId) return;
    api
      .jobStatus(jobId)
      .then(updateProgress)
      .catch((err) => {
        window.clearInterval(pollTimer);
        running = false;
        start.disabled = false;
        error.textContent = err?.message || "Lost track of the export job.";
      });
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (running) return;
    const folder = destination.value.trim();
    if (!folder) {
      error.textContent = "Choose a destination folder.";
      destination.focus();
      return;
    }
    error.textContent = "";
    start.disabled = true;
    start.textContent = "Starting…";
    progressWrap.hidden = false;
    progressFill.style.width = "4%";
    progressStage.textContent = "Starting export…";
    try {
      const payload = {
        destination: folder,
        options: {
          convertHeicToJpeg: convert.querySelector("input").checked,
          includeLiveVideo: live.querySelector("input").checked,
          includeEdited: edited.querySelector("input").checked,
          layout: layout.value,
          onConflict: conflict.value,
          setFileDates: dates.querySelector("input").checked,
        },
      };
      if (ids?.length) payload.ids = ids;
      else if (scope) payload.scope = scope;
      const result = await api.startExport(payload);
      jobId = result.jobId;
      running = true;
      start.textContent = "Exporting…";
      cancel.textContent = "Cancel export";
      pollTimer = window.setInterval(poll, 500);
      poll();
    } catch (err) {
      start.disabled = false;
      start.textContent = "Export";
      progressWrap.hidden = true;
      error.textContent = err?.message || "Could not start the export.";
    }
  });

  return modal;
}
