/** Preload and lightbox preview (project-docs/UI_SPEC.md §8). */

import { api } from "../api.js";
import { formatBytes, isoToLocal, timeLabel } from "../util/dates.js";
import { h } from "../util/dom.js";
import { icon } from "../util/icons.js";
import { showToast } from "./toast.js";

function infoRow(label, value) {
  return [h("dt", { text: label }), h("dd", { text: value ?? "—" })];
}

export function openLightbox({ assets, index = 0, onExport }) {
  if (!assets?.length) return { close() {} };
  const previousFocus = document.activeElement;
  let current = Math.max(0, Math.min(index, assets.length - 1));
  let detail = null;
  let scale = 1;
  let videoMode = "preview";

  const title = h("div", { class: "lightbox-title", text: "" });
  const infoBtn = h(
    "button",
    { class: "icon-btn", type: "button", "aria-label": "Toggle info", title: "Info (I)" },
    h("span", { html: icon("info", 20) }),
  );
  const zoomOutBtn = h(
    "button",
    { class: "icon-btn", type: "button", "aria-label": "Zoom out", title: "Zoom out (-)" },
    h("span", { html: icon("zoomOut", 20) }),
  );
  const zoomInBtn = h(
    "button",
    { class: "icon-btn", type: "button", "aria-label": "Zoom in", title: "Zoom in (+)" },
    h("span", { html: icon("zoomIn", 20) }),
  );
  const download = h("a", {
    class: "icon-btn",
    "aria-label": "Download original",
    title: "Download original",
    download: "",
  });
  download.innerHTML = icon("download", 20);
  const exportBtn = h(
    "button",
    { class: "icon-btn", type: "button", "aria-label": "Export", title: "Export…" },
    h("span", { html: icon("export", 20) }),
  );
  const closeBtn = h(
    "button",
    { class: "icon-btn", type: "button", "aria-label": "Close preview", title: "Close (Esc)" },
    h("span", { html: icon("close", 22) }),
  );
  const toolbar = h(
    "div",
    { class: "lightbox-toolbar" },
    title,
    infoBtn,
    zoomOutBtn,
    zoomInBtn,
    download,
    exportBtn,
    closeBtn,
  );

  const stage = h("div", { class: "lightbox-stage" });
  const prev = h(
    "button",
    { class: "lightbox-nav prev", type: "button", "aria-label": "Previous item" },
    h("span", { html: icon("chevronLeft", 30) }),
  );
  const next = h(
    "button",
    { class: "lightbox-nav next", type: "button", "aria-label": "Next item" },
    h("span", { html: icon("chevronRight", 30) }),
  );
  const liveBtn = h("button", { class: "lightbox-live", type: "button", hidden: true, text: "Live" });
  stage.append(prev, next, liveBtn);

  const infoPanel = h("aside", { class: "lightbox-info", hidden: true });
  const body = h("div", { class: "lightbox-body" }, stage, infoPanel);
  const overlay = h("div", { class: "lightbox", role: "dialog", "aria-modal": "true", "aria-label": "Preview" }, toolbar, body);
  document.body.append(overlay);
  closeBtn.focus();

  function renderMedia() {
    for (const node of Array.from(stage.querySelectorAll("img, video, .lightbox-hint"))) node.remove();
    if (!detail) return;
    if (detail.kind === "video" || videoMode === "live") {
      const url = videoMode === "live" ? api.liveUrl(detail.id) : api.originalUrl(detail.id);
      if (!url) {
        stage.append(
          h("div", { class: "lightbox-hint", text: "This video is not available in demo mode." }),
        );
        return;
      }
      const video = h("video", { controls: true, playsinline: true, preload: "metadata" });
      video.src = url;
      video.style.transform = `scale(${scale})`;
      video.addEventListener("error", () => {
        video.remove();
        stage.append(
          h("div", {
            class: "lightbox-hint",
            text: "Your browser cannot play this format. Use “Download original” and open it in a media player.",
          }),
        );
      });
      stage.append(video);
    } else {
      const img = h("img", { alt: detail.filename || "", draggable: "false" });
      img.src = api.previewUrl(detail.id);
      img.style.transform = `scale(${scale})`;
      img.addEventListener("error", () => {
        img.remove();
        stage.append(h("div", { class: "lightbox-hint", text: "Preview not available for this file." }));
      });
      stage.append(img);
    }
  }

  function renderInfo() {
    infoPanel.innerHTML = "";
    if (!detail) return;
    infoPanel.append(h("h3", { text: detail.filename || "Item" }));
    const dl = h("dl");
    dl.append(
      ...infoRow("Captured", isoToLocal(detail.takenAtIso)),
      ...infoRow("Type", detail.kind === "video" ? "Video" : "Photo"),
      ...infoRow("Dimensions", `${detail.width || "?"} × ${detail.height || "?"}`),
      ...infoRow("Size", formatBytes(detail.size)),
    );
    if (detail.duration) dl.append(...infoRow("Duration", timeLabel(detail.duration)));
    if (detail.latitude != null) {
      dl.append(...infoRow("Location", `${detail.latitude.toFixed(4)}, ${detail.longitude.toFixed(4)}`));
    }
    if (detail.moment) dl.append(...infoRow("Moment", detail.moment));
    if (detail.albums?.length) dl.append(...infoRow("Albums", detail.albums.join(", ")));
    if (detail.relPath) dl.append(...infoRow("Backup path", detail.relPath));
    if (detail.fileId) dl.append(...infoRow("File ID", detail.fileId));
    if (detail.favorite) dl.append(...infoRow("Favorite", "Yes"));
    infoPanel.append(dl);
  }

  function updateChrome() {
    const asset = assets[current];
    title.textContent = `${asset.name} · ${current + 1} / ${assets.length}`;
    liveBtn.hidden = !detail?.isLive;
    liveBtn.textContent = videoMode === "live" ? "Still" : "Live";
    if (detail) {
      const url = api.originalUrl(detail.id);
      if (url) {
        download.href = url;
        download.download = detail.filename || "original";
        download.hidden = false;
      } else {
        download.hidden = true;
      }
    }
    prev.disabled = assets.length <= 1;
    next.disabled = assets.length <= 1;
    renderMedia();
    renderInfo();
  }

  async function load(indexToLoad) {
    current = (indexToLoad + assets.length) % assets.length;
    videoMode = "preview";
    scale = 1;
    detail = null;
    updateChrome();
    try {
      detail = await api.asset(assets[current].id);
      updateChrome();
      preload(current + 1);
      preload(current - 1);
    } catch (error) {
      title.textContent = "Could not load item";
      showToast(error?.message || "Could not load asset details", "error");
    }
  }

  function preload(offset) {
    const target = assets[(offset + assets.length) % assets.length];
    if (!target) return;
    const image = new Image();
    image.src = api.previewUrl(target.id);
  }

  function move(delta) {
    load(current + delta);
  }

  function close() {
    document.removeEventListener("keydown", onKey);
    overlay.remove();
    if (previousFocus instanceof HTMLElement) previousFocus.focus();
  }

  function onKey(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      close();
    } else if (event.key === "ArrowLeft") {
      move(-1);
    } else if (event.key === "ArrowRight") {
      move(1);
    } else if (event.key === "+" || event.key === "=") {
      scale = Math.min(4, scale + 0.25);
      renderMedia();
    } else if (event.key === "-") {
      scale = Math.max(1, scale - 0.25);
      renderMedia();
    } else if (event.key === "i" || event.key === "I") {
      infoPanel.hidden = !infoPanel.hidden;
    }
  }

  prev.addEventListener("click", () => move(-1));
  next.addEventListener("click", () => move(1));
  closeBtn.addEventListener("click", close);
  infoBtn.addEventListener("click", () => {
    infoPanel.hidden = !infoPanel.hidden;
  });
  zoomInBtn.addEventListener("click", () => {
    scale = Math.min(4, scale + 0.25);
    renderMedia();
  });
  zoomOutBtn.addEventListener("click", () => {
    scale = Math.max(1, scale - 0.25);
    renderMedia();
  });
  liveBtn.addEventListener("click", () => {
    videoMode = videoMode === "live" ? "preview" : "live";
    updateChrome();
  });
  exportBtn.addEventListener("click", () => {
    if (detail) {
      close();
      onExport?.([detail.id]);
    }
  });
  document.addEventListener("keydown", onKey);
  overlay.addEventListener("mousedown", (event) => {
    if (event.target === overlay) close();
  });

  load(current);
  return { close };
}
