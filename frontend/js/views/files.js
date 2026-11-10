/** Raw file explorer (browse + LIKE search + export). Read-only by design. */

import { api } from "../api.js";
import { openModal } from "../components/modal.js";
import { showToast } from "../components/toast.js";
import { formatBytes } from "../util/dates.js";
import { formatCount, h } from "../util/dom.js";
import { icon } from "../util/icons.js";

function formatMtime(value) {
  if (!value) return "—";
  return new Date(Number(value) * 1000).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function openRawExportDialog({ count, onStart }) {
  const destination = h("input", {
    type: "text",
    placeholder: "D:\\BackupLens\\Raw export",
    "aria-label": "Destination folder",
  });
  const browse = h("button", { class: "btn", type: "button", text: "Browse…" });
  const conflict = h(
    "select",
    { "aria-label": "If a file exists" },
    h("option", { value: "rename", text: "Rename new files" }),
    h("option", { value: "skip", text: "Skip existing files" }),
    h("option", { value: "overwrite", text: "Overwrite existing files" }),
  );
  const error = h("p", { class: "field-error", role: "alert" });
  const stage = h("p", { class: "progress-stage", text: "" });
  const fill = h("div", { class: "progress-fill" });
  const progress = h("div", { class: "export-progress", hidden: true }, stage, h("div", { class: "progress-track" }, fill));
  const cancel = h("button", { class: "btn", type: "button", text: "Cancel" });
  const start = h("button", { class: "btn primary", type: "submit", text: "Export" });

  const form = h(
    "form",
    { novalidate: true },
    h("h2", { text: "Export raw files" }),
    h("p", { class: "modal-sub", text: `${formatCount(count)} file(s) · relative paths preserved under the destination` }),
    h(
      "div",
      { class: "field" },
      h("label", { text: "Destination folder" }),
      h("div", { class: "field-row" }, destination, browse),
    ),
    h("div", { class: "field" }, h("label", { text: "If a file exists" }), conflict),
    error,
    progress,
    h("div", { class: "dialog-actions" }, cancel, start),
  );
  const modal = openModal(form, { label: "Export raw files" });
  let jobId = null;
  let timer = 0;
  let running = false;

  browse.addEventListener("click", async () => {
    try {
      const picked = await api.pickFolder();
      if (picked) destination.value = picked;
    } catch (err) {
      error.textContent = err?.message || "Folder picker unavailable; type a path instead.";
    }
  });

  cancel.addEventListener("click", async () => {
    if (running && jobId) {
      await api.cancelJob(jobId).catch(() => {});
      stage.textContent = "Cancelling…";
      return;
    }
    modal.close();
  });

  function poll() {
    api
      .jobStatus(jobId)
      .then((job) => {
        progress.hidden = false;
        const total = Math.max(1, job.total || count);
        const done = job.done || 0;
        fill.style.width = `${Math.min(100, Math.round((done / total) * 100))}%`;
        stage.textContent =
          job.state === "done"
            ? "Export complete"
            : job.state === "cancelled"
              ? "Export cancelled"
              : job.state === "failed"
                ? "Export failed"
                : `Exporting ${formatCount(done)} / ${formatCount(total)}`;
        if (job.errors?.length) error.textContent = `${job.errors.length} file(s) failed: ${job.errors[0]}`;
        if (job.state !== "running" && job.state !== "queued") {
          running = false;
          window.clearInterval(timer);
          start.disabled = false;
          cancel.textContent = "Close";
          if (job.state === "done") showToast(`Raw export finished: ${formatCount(job.done)} files.`, "success");
        }
      })
      .catch((err) => {
        window.clearInterval(timer);
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
      return;
    }
    start.disabled = true;
    start.textContent = "Starting…";
    progress.hidden = false;
    try {
      jobId = await onStart(folder, conflict.value);
      running = true;
      cancel.textContent = "Cancel export";
      start.textContent = "Exporting…";
      timer = window.setInterval(poll, 500);
      poll();
    } catch (err) {
      start.disabled = false;
      start.textContent = "Export";
      progress.hidden = true;
      error.textContent = err?.message || "Could not start the raw export.";
    }
  });
  return modal;
}

export function showFiles(ctx) {
  if (!ctx.session?.open) {
    showToast("Open a backup first.");
    return;
  }
  ctx.destroyBrowser?.();
  ctx.destroyBrowser = null;
  ctx.browser = null;
  ctx.header.setMode("files");
  ctx.header.setDevice(ctx.session.backup);
  ctx.sidebar.hidden = true;
  ctx.main.innerHTML = "";
  ctx.main.scrollTop = 0;
  ctx.status.setStatus("Loading file domains…", "working");

  const state = {
    domains: [],
    domain: "",
    path: "",
    mode: "browse",
    entries: [],
    results: [],
    total: 0,
    sort: "path",
    dir: "asc",
    searchDomain: "%",
    searchPath: "%",
    selected: new Set(),
  };

  const domainSelect = h("select", { "aria-label": "Domain" });
  const breadcrumb = h("span", { class: "files-breadcrumb" });
  const upBtn = h("button", { class: "btn", type: "button", text: "Up" });
  const photosBtn = h(
    "button",
    { class: "btn", type: "button" },
    h("span", { html: icon("photo", 16) }),
    "Back to photos",
  );
  const searchDomain = h("input", {
    type: "text",
    value: "%",
    "aria-label": "Domain pattern",
    placeholder: "%whatsapp%",
  });
  const searchPath = h("input", {
    type: "text",
    value: "%",
    "aria-label": "Path pattern",
    placeholder: "Media/DCIM/%",
  });
  const searchBtn = h("button", { class: "btn primary", type: "button", text: "Search" });
  const browseBtn = h("button", { class: "btn", type: "button", text: "Browse" });
  const presetRow = h("div", { class: "files-presets" });
  const tableWrap = h("div", { class: "files-table-wrap" });
  const footerText = h("span", { class: "files-footer-text" });
  const footer = h("div", { class: "files-footer" }, footerText);
  const exportBtn = h("button", { class: "btn", type: "button", text: "Export matching…" });

  const toolbar = h(
    "div",
    { class: "files-toolbar" },
    photosBtn,
    h("label", { class: "files-label" }, "Domain", domainSelect),
    upBtn,
    breadcrumb,
  );
  const searchBar = h(
    "div",
    { class: "files-searchbar" },
    h("label", { class: "files-label" }, "Domain", searchDomain),
    h("label", { class: "files-label wide" }, "Path LIKE", searchPath),
    searchBtn,
    browseBtn,
  );
  const presets = [
    ["Camera Roll videos", "CameraRollDomain", "%.mov"],
    ["DCIM", "CameraRollDomain", "Media/DCIM/%"],
    ["SQLite databases", "%", "%.sqlite"],
    ["WhatsApp", "%whatsapp%", "%"],
  ];
  for (const [label, domain, path] of presets) {
    presetRow.append(
      h("button", {
        class: "files-preset",
        type: "button",
        text: label,
        onclick: () => {
          searchDomain.value = domain;
          searchPath.value = path;
          runSearch();
        },
      }),
    );
  }

  ctx.main.append(h("div", { class: "files-view" }, toolbar, searchBar, presetRow, tableWrap, footer));

  function updateBreadcrumb() {
    breadcrumb.textContent = state.path ? `${state.domain} / ${state.path}` : state.domain;
    upBtn.disabled = !state.path;
  }

  function sortHeader(label, key) {
    return h(
      "button",
      {
        class: `files-sort${state.sort === key ? " is-active" : ""}`,
        type: "button",
        text: label + (state.sort === key ? (state.dir === "asc" ? " ▲" : " ▼") : ""),
        onclick: () => {
          if (state.sort === key) state.dir = state.dir === "asc" ? "desc" : "asc";
          else {
            state.sort = key;
            state.dir = "asc";
          }
          runSearch();
        },
      },
    );
  }

  function renderTable() {
    tableWrap.innerHTML = "";
    state.selected.clear();
    if (state.mode === "browse") {
      const table = h("table", { class: "files-table" });
      table.append(
        h(
          "thead",
          {},
          h("tr", {}, h("th", { text: "Name" }), h("th", { text: "Type" }), h("th", { text: "Size" }), h("th", { text: "Modified" }), h("th", { text: "" })),
        ),
      );
      const body = h("tbody");
      for (const entry of state.entries) {
        const isDir = entry.type === "dir";
        body.append(
          h(
            "tr",
            {},
            h(
              "td",
              {},
              isDir
                ? h("button", {
                    class: "files-link",
                    type: "button",
                    text: entry.name,
                    onclick: () => {
                      state.path = entry.path;
                      loadTree();
                    },
                  })
                : h("span", { text: entry.name }),
            ),
            h("td", { text: entry.type }),
            h("td", { text: isDir ? `${entry.count || 0} entries` : formatBytes(entry.size) }),
            h("td", { text: isDir ? "—" : formatMtime(entry.mtime) }),
            h(
              "td",
              {},
              isDir
                ? h("button", {
                    class: "btn small",
                    type: "button",
                    text: "Open",
                    onclick: () => {
                      state.path = entry.path;
                      loadTree();
                    },
                  })
                : h("a", {
                    class: "btn small",
                    href: api.fileDownloadUrl(entry.fileId),
                    download: entry.name,
                    text: "Download",
                  }),
            ),
          ),
        );
      }
      table.append(body);
      tableWrap.append(table);
      if (!state.entries.length) tableWrap.append(h("p", { class: "empty-home", text: "This folder is empty." }));
      footerText.textContent = `${state.entries.length} entries`;
      exportBtn.textContent = "Export listed files…";
    } else {
      const table = h("table", { class: "files-table" });
      table.append(
        h(
          "thead",
          {},
          h(
            "tr",
            {},
            h("th", {}, h("input", { type: "checkbox", "aria-label": "Select all results", onchange: (event) => toggleAll(event.target.checked) })),
            h("th", {}, sortHeader("Domain", "domain")),
            h("th", {}, sortHeader("Path", "path")),
            h("th", {}, sortHeader("Size", "size")),
            h("th", {}, sortHeader("Modified", "date")),
            h("th", { text: "" }),
          ),
        ),
      );
      const body = h("tbody");
      for (const item of state.results) {
        const checkbox = h("input", {
          type: "checkbox",
          "aria-label": `Select ${item.name}`,
          onchange: (event) => {
            if (event.target.checked) state.selected.add(item.fileId);
            else state.selected.delete(item.fileId);
          },
        });
        checkbox.dataset.fileId = item.fileId;
        body.append(
          h(
            "tr",
            {},
            h("td", {}, checkbox),
            h("td", { text: item.domain }),
            h("td", { title: item.path, text: item.path }),
            h("td", { text: formatBytes(item.size) }),
            h("td", { text: formatMtime(item.mtime) }),
            h("td", {}, h("a", { class: "btn small", href: api.fileDownloadUrl(item.fileId), download: item.name, text: "Download" })),
          ),
        );
      }
      table.append(body);
      tableWrap.append(table);
      if (!state.results.length) tableWrap.append(h("p", { class: "empty-home", text: "No files match this query." }));
      footerText.textContent = `${formatCount(state.total)} matching · showing ${state.results.length}`;
      exportBtn.textContent = "Export selected / matching…";
    }
    footer.append(exportBtn);
  }

  function toggleAll(checked) {
    for (const checkbox of tableWrap.querySelectorAll('input[type="checkbox"][data-file-id]')) {
      checkbox.checked = checked;
      if (checked) state.selected.add(checkbox.dataset.fileId);
      else state.selected.delete(checkbox.dataset.fileId);
    }
  }

  async function loadDomains() {
    try {
      const payload = await api.fileDomains();
      state.domains = payload.domains || [];
    } catch (error) {
      state.domains = [];
      showToast(error?.message || "Could not list domains", "error");
    }
    domainSelect.innerHTML = "";
    if (!state.domains.length) {
      tableWrap.innerHTML = "";
      tableWrap.append(
        h("p", {
          class: "empty-home",
          text: "No raw files are available in this demo session. Open a real backup to browse its Manifest.",
        }),
      );
      footerText.textContent = "";
      return;
    }
    for (const entry of state.domains) {
      domainSelect.append(h("option", { value: entry.domain, text: `${entry.domain} (${formatCount(entry.count)})` }));
    }
    const preferred = state.domains.find((entry) => entry.domain === "CameraRollDomain") || state.domains[0];
    state.domain = preferred.domain;
    domainSelect.value = state.domain;
    state.path = "";
    await loadTree();
  }

  async function loadTree() {
    state.mode = "browse";
    updateBreadcrumb();
    ctx.status.setStatus(`Reading ${state.domain} / ${state.path || ""}…`, "working");
    try {
      const payload = await api.fileTree(state.domain, state.path);
      state.entries = payload.entries || [];
      renderTable();
      ctx.status.setStatus(`${state.entries.length} entries · ${state.domain}`);
    } catch (error) {
      state.entries = [];
      renderTable();
      showToast(error?.message || "Could not read this folder", "error");
    }
  }

  async function runSearch() {
    state.mode = "search";
    state.searchDomain = searchDomain.value.trim() || "%";
    state.searchPath = searchPath.value.trim() || "%";
    state.selected.clear();
    ctx.status.setStatus("Searching files…", "working");
    try {
      const payload = await api.fileSearch({
        domain: state.searchDomain,
        path: state.searchPath,
        sort: state.sort,
        dir: state.dir,
        limit: 200,
        offset: 0,
      });
      state.results = payload.items || [];
      state.total = payload.total || 0;
      renderTable();
      ctx.status.setStatus(`${formatCount(state.total)} files match`);
    } catch (error) {
      state.results = [];
      state.total = 0;
      renderTable();
      showToast(error?.message || "Search failed", "error");
    }
  }

  domainSelect.addEventListener("change", () => {
    state.domain = domainSelect.value;
    state.path = "";
    loadTree();
  });
  upBtn.addEventListener("click", () => {
    const parts = state.path.split("/").filter(Boolean);
    parts.pop();
    state.path = parts.join("/");
    loadTree();
  });
  photosBtn.addEventListener("click", () => {
    ctx.showBrowser(ctx.session);
  });
  searchBtn.addEventListener("click", () => runSearch());
  browseBtn.addEventListener("click", () => loadTree());
  searchPath.addEventListener("keydown", (event) => {
    if (event.key === "Enter") runSearch();
  });
  exportBtn.addEventListener("click", () => {
    let ids = null;
    let count = 0;
    if (state.selected.size) {
      ids = Array.from(state.selected);
      count = ids.length;
    } else if (state.mode === "search") {
      count = state.total;
    } else {
      count = state.entries.filter((entry) => entry.type !== "dir").length;
      ids = state.entries.filter((entry) => entry.type !== "dir").map((entry) => entry.fileId);
    }
    if (!count) {
      showToast("Nothing to export in this view.");
      return;
    }
    openRawExportDialog({
      count,
      onStart: async (destination, onConflict) => {
        const payload = ids?.length ? { ids, destination, onConflict } : { domain: state.searchDomain, path: state.searchPath, destination, onConflict };
        const result = await api.startFileExport(payload);
        return result.jobId;
      },
    });
  });

  loadDomains();
}
