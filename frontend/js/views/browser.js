/** Browser view: sidebar + virtualised grid + selection + lightbox. */

import { api } from "../api.js";
import { openContextMenu } from "../components/contextMenu.js";
import { openDatePicker } from "../components/datePicker.js";
import { openDateRangeDialog } from "../components/dateRangeDialog.js";
import { openExportDialog } from "../components/exportDialog.js";
import { createGrid } from "../components/grid.js";
import { openLightbox } from "../components/lightbox.js";
import { createSidebar } from "../components/sidebar.js";
import { showToast } from "../components/toast.js";
import { localDay } from "../util/dates.js";
import { formatCount, isTypingTarget } from "../util/dom.js";

function decodeRow(row) {
  const [id, name, takenAt, kind, width, height, flags, duration, size, tzOffset] = row;
  return { id, name, takenAt, kind, width, height, flags, duration, size, tzOffset };
}

function scopeLabel(scope) {
  return scope.kind === "category" ? scope.label : scope.title;
}

function scopeQuery(scope) {
  if (scope.kind === "album") return { album: scope.id };
  if (scope.kind === "moment") return { moment: scope.id };
  return { scope: scope.key };
}

function scopeForExport(scope, type) {
  if (scope.kind === "album") return { kind: "album", id: scope.id, type };
  if (scope.kind === "moment") return { kind: "moment", id: scope.id, type };
  return { kind: "category", key: scope.key, type };
}

function resolveScope(saved, sidebarData) {
  const categories = sidebarData.categories || [];
  if (saved?.kind === "category") {
    const found = categories.find((item) => item.key === saved.key);
    if (found) return { kind: "category", key: found.key, label: found.label };
  }
  if (saved?.kind === "album") {
    const found = (sidebarData.albums || []).find((item) => item.id === saved.id);
    if (found) return { kind: "album", id: found.id, title: found.title };
  }
  if (saved?.kind === "moment") {
    const found = (sidebarData.moments || []).find((item) => item.id === saved.id);
    if (found) return { kind: "moment", id: found.id, title: found.title };
  }
  const all = categories.find((item) => item.key === "all") || { key: "all", label: "All" };
  return { kind: "category", key: all.key, label: all.label };
}

export function createBrowser(ctx, sessionState) {
  const backup = sessionState.backup;
  const storageScope = `bl.scope.${backup?.id || "default"}`;
  const storageType = `bl.type.${backup?.id || "default"}`;
  let sidebarData = null;
  let sidebar = null;
  let grid = null;
  let allAssets = [];
  let visibleAssets = [];
  let scope = { kind: "category", key: "all", label: "All" };
  let typeFilter = "all";
  let searchQuery = "";
  let dateFrom = null;
  let dateTo = null;
  let searchTimer = 0;
  let settings = ctx.settings || {};
  let activeLightbox = null;
  let destroyed = false;

  ctx.sidebar.hidden = false;
  ctx.main.innerHTML = "";
  ctx.main.scrollTop = 0;

  function updateStatus() {
    const selected = grid?.getSelection().length || 0;
    if (selected > 0) {
      ctx.status.setSelection(visibleAssets.length, selected);
    } else {
      ctx.status.setStatus(
        `${formatCount(visibleAssets.length)} items Â· ${scopeLabel(scope)}${
          typeFilter === "all" ? "" : ` Â· ${typeFilter === "photo" ? "Photos" : "Videos"}`
        }`,
      );
    }
    ctx.store.set({
      visibleCount: visibleAssets.length,
      selectionCount: selected,
      typeFilter,
      scope,
    });
  }

  function applyFilters() {
    const wanted = typeFilter === "photo" ? "p" : typeFilter === "video" ? "v" : null;
    const needle = searchQuery ? searchQuery.toLowerCase() : null;
    visibleAssets = allAssets.filter((asset) => {
      if (wanted && asset.kind !== wanted) return false;
      if (needle) {
        const haystack = `${asset.name}\n${asset.originalName || ""}`.toLowerCase();
        if (!haystack.includes(needle)) return false;
      }
      if (dateFrom || dateTo) {
        const day = localDay(asset.takenAt, asset.tzOffset);
        if (day === "unknown") return false;
        if (dateFrom && day < dateFrom) return false;
        if (dateTo && day > dateTo) return false;
      }
      return true;
    });
    grid?.setAssets(visibleAssets);
    updateStatus();
  }

  function applyTypeFilter() {
    applyFilters();
  }

  function openPreview(asset, index) {
    activeLightbox = openLightbox({
      assets: visibleAssets,
      index,
      onExport: (ids) => exportIds(ids),
    });
  }

  function exportIds(ids) {
    if (!ids?.length) {
      showToast("Select at least one item first.");
      return;
    }
    openExportDialog({
      summary: "Selected items",
      count: ids.length,
      ids,
      onDone: (job) => {
        if (job.state === "done") showToast(`Export finished: ${formatCount(job.done)} files.`, "success");
        else if (job.state === "cancelled") showToast("Export cancelled.");
        else if (job.state === "failed") showToast("Export failed â€” see the dialog for details.", "error");
      },
    });
  }

  function exportCurrent() {
    if (!visibleAssets.length) {
      showToast("There are no items in this view.");
      return;
    }
    openExportDialog({
      summary: `${scopeLabel(scope)}${typeFilter === "all" ? "" : ` Â· ${typeFilter === "photo" ? "Photos" : "Videos"}`}`,
      count: visibleAssets.length,
      scope: scopeForExport(scope, typeFilter),
      onDone: (job) => {
        if (job.state === "done") showToast(`Export finished: ${formatCount(job.done)} files.`, "success");
      },
    });
  }

  async function loadScope(nextScope, { initial = false } = {}) {
    scope = nextScope;
    sessionStorage.setItem(storageScope, JSON.stringify(scope));
    ctx.header.setFilterLabel(
      typeFilter === "all" ? "All" : typeFilter === "photo" ? "Photos" : "Videos",
    );
    ctx.main.scrollTop = 0;
    if (!initial) {
      grid?.setLoading();
      ctx.status.setStatus(`Loading ${scopeLabel(scope)}â€¦`, "working");
    }
    try {
      const payload = await api.assets(scopeQuery(scope));
      allAssets = (payload.items || []).map(decodeRow);
      if (settings.dateGroupingZone === "machine") {
        for (const asset of allAssets) asset.tzOffset = undefined;
      }
      applyFilters();
      ctx.status.setStatus(
        `${formatCount(visibleAssets.length)} items Â· ${scopeLabel(scope)}`,
      );
    } catch (error) {
      allAssets = [];
      visibleAssets = [];
      grid?.setAssets([]);
      ctx.status.setStatus(error?.message || "Could not load this view", "error");
      showToast(error?.message || "Could not load this view", "error");
    }
  }

  function setTypeFilter(value) {
    typeFilter = value;
    sessionStorage.setItem(storageType, value);
    ctx.header.setFilterLabel(value === "all" ? "All" : value === "photo" ? "Photos" : "Videos");
    applyTypeFilter();
  }

  function onKeyDown(event) {
    if (destroyed) return;
    if (document.querySelector(".lightbox, .modal-overlay")) return;
    if (isTypingTarget(event.target)) return;
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "a") {
      event.preventDefault();
      grid?.selectAllVisible();
    } else if (event.key === "Escape") {
      if ((grid?.getSelection().length || 0) > 0) {
        grid.clearSelection();
      }
      ctx.header.setSelectionMode(false);
      grid?.setSelectionMode(false);
    } else if (event.key === "Home") {
      event.preventDefault();
      ctx.main.scrollTop = 0;
    } else if (event.key === "End") {
      event.preventDefault();
      ctx.main.scrollTop = ctx.main.scrollHeight;
    } else if (event.key === "Delete") {
      event.preventDefault(); // read-only app
    }
  }

  async function load() {
    ctx.header.setMode("browser");
    ctx.header.setDevice(backup);
    ctx.header.setSearchValue("");
    searchQuery = "";
    dateFrom = null;
    dateTo = null;
    ctx.status.setBackupsCount(ctx.backups?.length || 1);
    ctx.status.setStatus("Reading photo libraryâ€¦", "working");
    try {
      sidebarData = await api.sidebar();
    } catch (error) {
      ctx.status.setStatus(error?.message || "Could not read the library", "error");
      showToast(error?.message || "Could not read the library", "error");
      return;
    }

    const saved = (() => {
      try {
        return JSON.parse(sessionStorage.getItem(storageScope) || "null");
      } catch {
        return null;
      }
    })();
    scope = resolveScope(saved, sidebarData);
    typeFilter = sessionStorage.getItem(storageType) || "all";

    sidebar = createSidebar(ctx.sidebar, sidebarData, {
      selected: scope,
      onSelect: (next) => {
        grid?.clearSelection();
        loadScope(next).catch((error) => showToast(error?.message || "Could not load view", "error"));
      },
    });

    ctx.main.innerHTML = "";
    grid = createGrid(ctx.main, {
      thumbUrl: (id, size) => api.thumbUrl(id, settings.thumbnailSize || size),
      onOpen: (asset, index) => openPreview(asset, index),
      onSelectionChange: () => updateStatus(),
      onContextMenu: (asset, event) => {
        const index = visibleAssets.findIndex((item) => item.id === asset.id);
        openContextMenu({
          x: event.clientX,
          y: event.clientY,
          items: [
            { label: "Open preview", action: () => openPreview(asset, index) },
            { label: "Export selectedâ€¦", action: () => exportIds([asset.id]) },
            {
              label: "Copy filename",
              action: async () => {
                try {
                  await navigator.clipboard.writeText(asset.name);
                  showToast("Filename copied.");
                } catch {
                  showToast(asset.name);
                }
              },
            },
            { separator: true },
            { label: "Show info", action: () => openPreview(asset, index) },
          ],
        });
      },
    });
    grid.setLoading();
    document.addEventListener("keydown", onKeyDown);
    await loadScope(scope, { initial: true });
  }

  return {
    load,
    async applySettings(nextSettings) {
      settings = nextSettings || settings;
      await loadScope(scope);
    },
    async handleToolbar(action, payload = {}) {
      if (action === "calendar") {
        openDatePicker({
          anchor: payload.event?.currentTarget,
          days: grid?.days() || [],
          onPick: (day) => grid?.scrollToDay(day),
        });
      } else if (action === "current-folder") {
        exportCurrent();
      } else if (action === "filter") {
        setTypeFilter(payload.value || "all");
      } else if (action === "search") {
        window.clearTimeout(searchTimer);
        const value = payload.value || "";
        searchTimer = window.setTimeout(() => {
          searchQuery = value.trim();
          applyFilters();
        }, 180);
      } else if (action === "date-range") {
        openDateRangeDialog({
          from: dateFrom || "",
          to: dateTo || "",
          onApply: ({ from, to }) => {
            dateFrom = from;
            dateTo = to;
            applyFilters();
          },
        });
      } else if (action === "toggle-selection-mode") {
        const enabled = Boolean(payload.enabled);
        grid?.setSelectionMode(enabled);
        ctx.header.setSelectionMode(enabled);
      } else if (action === "selection") {
        if (payload.action === "select-all") grid?.selectAllVisible();
        else if (payload.action === "clear") grid?.clearSelection();
        else if (payload.action === "export") exportIds(grid?.getSelection() || []);
      }
    },
    destroy() {
      destroyed = true;
      window.clearTimeout(searchTimer);
      document.removeEventListener("keydown", onKeyDown);
      activeLightbox?.close();
      grid?.destroy();
      grid = null;
      ctx.main.innerHTML = "";
    },
  };
}
