/** Date-grouped, virtualised thumbnail grid (project-docs/UI_SPEC.md §5). */

import { clear, h, on } from "../util/dom.js";
import { dayLabel, localDay, timeLabel } from "../util/dates.js";
import { icon } from "../util/icons.js";

const GAP = 5;
const HEADER_H = 28;
const GROUP_GAP_X = 15;
const GROUP_GAP_Y = 65;
const PAD = 15;
const SCREENS_BEFORE = 2;
const SCREENS_AFTER = 3;

function tileSize() {
  const value = getComputedStyle(document.documentElement).getPropertyValue("--tile");
  return parseFloat(value) || 294;
}

function decodeFlags(flags) {
  return {
    favorite: Boolean(flags & 1),
    hidden: Boolean(flags & 2),
    trashed: Boolean(flags & 4),
    live: Boolean(flags & 8),
    portrait: Boolean(flags & 16),
    panorama: Boolean(flags & 32),
    timelapse: Boolean(flags & 64),
    slomo: Boolean(flags & 128),
    screenshot: Boolean(flags & 256),
  };
}

function groupAssets(assets) {
  const groups = new Map();
  for (const asset of assets) {
    const day = localDay(asset.takenAt, asset.tzOffset);
    if (!groups.has(day)) groups.set(day, { day, label: dayLabel(day), items: [] });
    groups.get(day).items.push(asset);
  }
  return Array.from(groups.values());
}

export function createGrid(container, { thumbUrl, onOpen, onSelectionChange, onContextMenu } = {}) {
  clear(container);
  const canvas = h("div", { class: "grid-canvas" });
  const skeleton = h("div", { class: "grid-skeleton" });
  for (let index = 0; index < 12; index += 1) skeleton.append(h("div", { class: "skeleton-tile" }));
  const status = h("div", { class: "grid-status", hidden: true, text: "No items in this view" });
  canvas.append(skeleton, status);
  container.append(canvas);

  let assets = [];
  let groups = [];
  let selection = new Set();
  let selectionMode = false;
  let lastClickedIndex = null;
  let observer = null;
  let destroyed = false;
  let width = 0;
  let signature = "";
  let raf = 0;
  let anchorDay = null;
  const elements = new Map();

  function notifySelection() {
    onSelectionChange?.(selection.size, assets.length);
  }

  function buildLayout() {
    const tile = tileSize();
    width = Math.max(200, container.clientWidth);
    const inner = Math.max(tile + GAP, width - PAD * 2);
    let x = 0;
    let y = PAD;
    let lineHeight = 0;

    for (const group of groups) {
      const count = group.items.length;
      const natural = count * tile + Math.max(0, count - 1) * GAP;
      const groupWidth = Math.min(natural, inner);
      const capacity = natural <= inner ? count : Math.max(1, Math.floor((inner + GAP) / (tile + GAP)));
      const rows = [];
      for (let index = 0; index < count; index += capacity) {
        rows.push(group.items.slice(index, index + capacity));
      }
      const height = HEADER_H + rows.length * tile + Math.max(0, rows.length - 1) * GAP;
      if (x > 0 && x + groupWidth > inner) {
        x = 0;
        y += lineHeight + GROUP_GAP_Y;
        lineHeight = 0;
      }
      group.x = PAD + x;
      group.y = y;
      group.width = groupWidth;
      group.height = height;
      group.rows = rows;
      group.tile = tile;
      x += groupWidth + GROUP_GAP_X;
      lineHeight = Math.max(lineHeight, height);
      if (x >= inner) {
        x = 0;
        y += lineHeight + GROUP_GAP_Y;
        lineHeight = 0;
      }
    }
    canvas.style.height = `${Math.max(y + lineHeight + PAD, container.clientHeight)}px`;
  }

  function makeTile(asset, index) {
    const flags = decodeFlags(asset.flags);
    const tile = h("div", {
      class: `tile${flags.live ? " live" : ""}${asset.kind === "v" ? " video" : ""}`,
      tabindex: "0",
      role: "button",
      "aria-label": `${asset.name}, ${asset.kind === "v" ? "video" : "photo"}`,
      onclick: (event) => handleTileClick(asset, index, event),
      oncontextmenu: (event) => {
        event.preventDefault();
        onContextMenu?.(asset, event);
      },
      onkeydown: (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          handleTileClick(asset, index, event);
        }
      },
    });
    const placeholder = h("div", { class: "thumb-placeholder", html: icon("photo", 34) });
    const img = h("img", {
      alt: "",
      loading: "lazy",
      decoding: "async",
      draggable: "false",
    });
    img.dataset.src = thumbUrl(asset.id, 320);
    img.addEventListener("load", () => {
      img.classList.add("loaded");
      placeholder.style.display = "none";
    });
    img.addEventListener("error", () => {
      img.style.display = "none";
    });
    img._assetId = asset.id;
    tile.append(placeholder, img);

    if (asset.kind === "v") {
      tile.append(
        h("span", { class: "badge duration-badge", text: timeLabel(asset.duration) }),
        h("span", { class: "play-glyph", html: icon("play", 16) }),
      );
    }
    if (flags.live) tile.append(h("span", { class: "live-glyph", html: icon("live", 14) }));

    const circle = h("button", {
      class: "selection-circle",
      type: "button",
      "aria-label": "Select item",
      "aria-pressed": String(selection.has(asset.id)),
      onclick: (event) => {
        event.stopPropagation();
        toggleSelection(asset, index, event.shiftKey);
      },
    });
    tile.append(circle);
    if (selection.has(asset.id)) {
      tile.classList.add("selected");
      circle.innerHTML = checkMark();
    }
    elements.set(asset.id, { tile, circle });
    observer?.observe(img);
    return tile;
  }

  function checkMark() {
    return `<svg class="icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12.5 4.2 4.2L19 7"/></svg>`;
  }

  function render(force = false) {
    if (!assets.length) {
      canvas.querySelectorAll(".date-group").forEach((node) => node.remove());
      elements.clear();
      status.hidden = false;
      skeleton.hidden = true;
      return;
    }
    status.hidden = true;
    skeleton.hidden = true;

    const viewportHeight = container.clientHeight || window.innerHeight;
    const scrollTop = container.scrollTop;
    const top = scrollTop - SCREENS_BEFORE * viewportHeight;
    const bottom = scrollTop + SCREENS_AFTER * viewportHeight;
    const visible = [];
    const ranges = [];
    groups.forEach((group, groupIndex) => {
      if (group.y + group.height < top || group.y > bottom) return;
      const firstRow = Math.max(
        0,
        Math.floor((top - group.y - HEADER_H) / (group.tile + GAP)),
      );
      const lastRow = Math.min(
        group.rows.length - 1,
        Math.floor((bottom - group.y - HEADER_H) / (group.tile + GAP)),
      );
      visible.push({ group, groupIndex, firstRow, lastRow });
      ranges.push(`${groupIndex}:${firstRow}-${lastRow}`);
    });
    const nextSignature = ranges.join("|");
    if (!force && nextSignature === signature) {
      refreshSelection(true);
      return;
    }
    signature = nextSignature;

    canvas.querySelectorAll(".date-group").forEach((node) => node.remove());
    elements.clear();

    for (const { group, firstRow, lastRow } of visible) {
      const node = h(
        "div",
        {
          class: "date-group",
          dataset: { day: group.day },
        },
        h("div", { class: "date-header", text: group.label }),
      );
      node.style.left = `${group.x}px`;
      node.style.top = `${group.y}px`;
      node.style.width = `${group.width}px`;
      node.style.height = `${group.height}px`;

      for (let rowIndex = Math.max(0, firstRow); rowIndex <= lastRow; rowIndex += 1) {
        const row = h("div", { class: "tile-row" });
        row.style.top = `${HEADER_H + rowIndex * (group.tile + GAP)}px`;
        const offset = rowIndex * group.rows[0].length;
        for (let itemIndex = 0; itemIndex < group.rows[rowIndex].length; itemIndex += 1) {
          const asset = group.rows[rowIndex][itemIndex];
          const globalIndex = assets.indexOf(asset);
          row.append(makeTile(asset, globalIndex >= 0 ? globalIndex : offset + itemIndex));
        }
        node.append(row);
      }
      canvas.append(node);
    }
    refreshSelection(true);
    loadVisibleImages();
  }

  function scheduleRender(force = false) {
    if (raf) return;
    raf = requestAnimationFrame(() => {
      raf = 0;
      if (!destroyed) {
        loadVisibleImages();
        render(force);
      }
    });
  }

  function loadVisibleImages() {
    const viewport = container.clientHeight || window.innerHeight;
    const top = -220;
    const bottom = viewport + 220;
    for (const img of canvas.querySelectorAll("img[data-src]")) {
      const rect = img.getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();
      const localTop = rect.top - containerRect.top;
      const localBottom = rect.bottom - containerRect.top;
      if (localBottom > top && localTop < bottom) {
        const source = img.dataset.src;
        if (source && !img.getAttribute("src")) img.src = source;
      }
    }
  }

  function refreshSelection(onlyRendered = false) {
    for (const [id, entry] of elements) {
      const selected = selection.has(id);
      entry.tile.classList.toggle("selected", selected);
      entry.circle.setAttribute("aria-pressed", String(selected));
      entry.circle.innerHTML = selected ? checkMark() : "";
    }
    if (!onlyRendered) notifySelection();
  }

  function toggleSelection(asset, index, shiftKey) {
    if (shiftKey && lastClickedIndex !== null) {
      const start = Math.min(lastClickedIndex, index);
      const end = Math.max(lastClickedIndex, index);
      for (let cursor = start; cursor <= end; cursor += 1) {
        if (assets[cursor]) selection.add(assets[cursor].id);
      }
    } else if (selection.has(asset.id)) {
      selection.delete(asset.id);
    } else {
      selection.add(asset.id);
    }
    lastClickedIndex = index;
    refreshSelection();
  }

  function handleTileClick(asset, index, event) {
    if (selectionMode || event.ctrlKey || event.metaKey || event.shiftKey) {
      event.preventDefault();
      toggleSelection(asset, index, event.shiftKey);
      return;
    }
    onOpen?.(asset, index);
  }

  const scrollHandler = () => scheduleRender();
  const offScroll = on(container, "scroll", scrollHandler, { passive: true });

  const resizeObserver = new ResizeObserver(() => {
    if (destroyed) return;
    const newWidth = container.clientWidth;
    if (newWidth === width) return;
    const anchor =
      anchorDay ?? groups.find((group) => group.y + group.height > container.scrollTop)?.day ?? null;
    const offset = anchor
      ? container.scrollTop - (groups.find((group) => group.day === anchor)?.y ?? 0)
      : 0;
    width = newWidth;
    buildLayout();
    const anchorGroup = groups.find((group) => group.day === anchor);
    if (anchorGroup) container.scrollTop = Math.max(0, anchorGroup.y + offset);
    signature = "";
    render(true);
  });
  resizeObserver.observe(container);

  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        const img = entry.target;
        if (entry.isIntersecting) {
          if (!img.src && img.dataset.src) img.src = img.dataset.src;
        } else if (!img.complete) {
          img.removeAttribute("src");
        }
      }
    },
    { root: container, rootMargin: "250px 0px" },
  );

  return {
    setAssets(nextAssets) {
      assets = nextAssets;
      groups = groupAssets(assets);
      selection = new Set([...selection].filter((id) => assets.some((asset) => asset.id === id)));
      signature = "";
      lastClickedIndex = null;
      buildLayout();
      render(true);
      notifySelection();
    },
    setLoading() {
      skeleton.hidden = false;
      status.hidden = true;
    },
    setSelectionMode(enabled) {
      selectionMode = Boolean(enabled);
      container.classList.toggle("selection-mode", selectionMode);
    },
    getSelection() {
      return Array.from(selection);
    },
    clearSelection() {
      selection.clear();
      lastClickedIndex = null;
      refreshSelection();
    },
    selectAllVisible() {
      for (const asset of assets) selection.add(asset.id);
      refreshSelection();
    },
    scrollToDay(day) {
      const group = groups.find((item) => item.day === day);
      if (group) {
        container.scrollTop = Math.max(0, group.y - PAD);
        scheduleRender(true);
      }
    },
    days() {
      return groups.map((group) => ({ date: group.day, label: group.label, count: group.items.length }));
    },
    refresh() {
      buildLayout();
      signature = "";
      render(true);
    },
    destroy() {
      destroyed = true;
      offScroll();
      resizeObserver.disconnect();
      observer?.disconnect();
      clear(container);
    },
  };
}
