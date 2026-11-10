/** Header + toolbar (project-docs/UI_SPEC.md §3). */

import { h } from "../util/dom.js";
import { icon } from "../util/icons.js";

function menuButton(label, action, { selected = false, iconName = null } = {}) {
  return h(
    "button",
    {
      class: `menu-item${selected ? " is-selected" : ""}`,
      type: "button",
      role: "menuitem",
      onclick: action,
    },
    iconName ? h("span", { html: icon(iconName, 17) }) : null,
    label,
  );
}

export function createHeader(root, { onMenuAction, onToolbarAction, isMock = false } = {}) {
  root.className = "app-header";
  root.innerHTML = "";

  const badge = h("span", { class: "count-badge", text: "0" });
  const title = h(
    "div",
    { class: "title-wrap" },
    h("h1", { class: "app-title", text: "Local Backups" }),
    badge,
    isMock ? h("span", { class: "demo-badge", text: "Demo" }) : null,
  );

  const deviceCard = h("div", { class: "device-card", hidden: true }, h("span", { html: icon("photo", 34) }));
  const uniqueId = h("div", { class: "unique-id", hidden: true });
  const menuBtn = h(
    "button",
    {
      class: "icon-btn menu-btn",
      type: "button",
      "aria-label": "Main menu",
      "aria-haspopup": "menu",
      "aria-expanded": "false",
    },
    h("span", { html: icon("menu", 24) }),
  );

  const mainMenu = h("div", { class: "menu-pop align-right", role: "menu", hidden: true });
  const menuItems = [
    ["backups", "Backups"],
    ["files", "Files"],
    ["settings", "Settings"],
    ["clear-cache", "Clear cache"],
    ["about", "About"],
    ["close", "Close backup"],
    ["quit", "Quit BackupLens"],
  ];
  for (const [action, label] of menuItems) {
    mainMenu.append(
      menuButton(label, () => {
        closeMenus();
        onMenuAction?.(action);
      }),
    );
  }

  const menuWrap = h("div", { class: "dropdown-wrap" }, menuBtn, mainMenu);
  const row1 = h("div", { class: "header-row" }, title, deviceCard, uniqueId, h("span", { class: "header-spacer" }), menuWrap);

  const calendarBtn = h(
    "button",
    {
      class: "tool-btn icon-only",
      type: "button",
      title: "Jump to a date",
      "aria-label": "Jump to a date",
      onclick: (event) => onToolbarAction?.("calendar", { event }),
    },
    h("span", { html: icon("calendar", 20) }),
  );

  const searchInput = h("input", {
    type: "search",
    placeholder: "Search filename…",
    "aria-label": "Search filename",
  });
  searchInput.addEventListener("input", () =>
    onToolbarAction?.("search", { value: searchInput.value }),
  );
  const searchWrap = h(
    "label",
    { class: "toolbar-search" },
    h("span", { html: icon("search", 18) }),
    searchInput,
  );

  const rangeBtn = h(
    "button",
    {
      class: "tool-btn",
      type: "button",
      title: "Filter by date range",
      "aria-label": "Filter by date range",
      onclick: (event) => onToolbarAction?.("date-range", { event }),
    },
    h("span", { html: icon("calendar", 19) }),
    "Date range",
  );

  const currentFolderBtn = h(
    "button",
    {
      class: "tool-btn",
      type: "button",
      onclick: () => onToolbarAction?.("current-folder"),
    },
    h("span", { html: icon("export", 19) }),
    "Current Folder",
  );

  const filterLabel = h("span", { text: "All" });
  const filterBtn = h(
    "button",
    {
      class: "tool-btn",
      type: "button",
      "aria-haspopup": "menu",
      "aria-expanded": "false",
    },
    h("span", { html: icon("image", 19) }),
    filterLabel,
    h("span", { class: "caret", html: icon("chevronDown", 16) }),
  );
  const filterMenu = h(
    "div",
    { class: "menu-pop align-right", role: "menu", hidden: true },
    menuButton("All", () => chooseFilter("all", "All"), { selected: true }),
    menuButton("Photos", () => chooseFilter("photo", "Photos")),
    menuButton("Videos", () => chooseFilter("video", "Videos")),
  );
  const filterWrap = h("div", { class: "dropdown-wrap" }, filterBtn, filterMenu);

  const selectionBtn = h(
    "button",
    {
      class: "tool-btn icon-only",
      type: "button",
      title: "Selection tools",
      "aria-label": "Selection tools",
      "aria-haspopup": "menu",
      "aria-expanded": "false",
    },
    h("span", { html: icon("checklist", 20) }),
  );
  const selectionMenu = h(
    "div",
    { class: "menu-pop align-right", role: "menu", hidden: true },
    menuButton("Select all in view", () => selectionAction("select-all")),
    menuButton("Clear selection", () => selectionAction("clear")),
    h("div", { class: "menu-separator" }),
    menuButton("Export selected…", () => selectionAction("export")),
  );
  const selectionWrap = h("div", { class: "selection-wrap" }, selectionBtn, selectionMenu);

  const toolbar = h(
    "div",
    { class: "header-row toolbar-row", hidden: true },
    searchWrap,
    rangeBtn,
    calendarBtn,
    currentFolderBtn,
    filterWrap,
    selectionWrap,
  );

  root.append(row1, toolbar);

  function closeMenus() {
    for (const [button, menu] of [
      [menuBtn, mainMenu],
      [filterBtn, filterMenu],
      [selectionBtn, selectionMenu],
    ]) {
      menu.hidden = true;
      button.setAttribute("aria-expanded", "false");
    }
  }

  function toggle(button, menu) {
    const wasHidden = menu.hidden;
    closeMenus();
    menu.hidden = !wasHidden;
    button.setAttribute("aria-expanded", String(!menu.hidden));
  }

  menuBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    toggle(menuBtn, mainMenu);
  });
  filterBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    toggle(filterBtn, filterMenu);
  });
  selectionBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    selectionBtn.classList.toggle("is-active");
    toggle(selectionBtn, selectionMenu);
    onToolbarAction?.("toggle-selection-mode", { enabled: selectionBtn.classList.contains("is-active") });
  });

  function chooseFilter(value, label) {
    filterLabel.textContent = label;
    closeMenus();
    onToolbarAction?.("filter", { value, label });
  }

  function selectionAction(action) {
    closeMenus();
    onToolbarAction?.("selection", { action });
  }

  document.addEventListener("click", (event) => {
    if (!root.contains(event.target)) closeMenus();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenus();
  });

  return {
    setMode(mode) {
      const isBrowser = mode === "browser";
      const isFiles = mode === "files";
      toolbar.hidden = !isBrowser;
      deviceCard.hidden = !(isBrowser || isFiles);
      uniqueId.hidden = !(isBrowser || isFiles);
      if (!isBrowser) {
        closeMenus();
        selectionBtn.classList.remove("is-active");
      }
    },
    setBackupsCount(value) {
      badge.textContent = String(value);
    },
    setDevice(info) {
      if (!info) {
        uniqueId.hidden = true;
        deviceCard.hidden = true;
        return;
      }
      const udid = info.udid || info.id || "";
      uniqueId.innerHTML = "";
      uniqueId.append(h("span", { text: "Unique ID : " }), h("strong", { text: udid }));
      uniqueId.hidden = false;
      deviceCard.hidden = false;
      deviceCard.title = `${info.deviceName || "Device"} · ${info.productType || ""}`;
    },
    setFilterLabel(label) {
      filterLabel.textContent = label;
    },
    setSelectionMode(enabled) {
      selectionBtn.classList.toggle("is-active", Boolean(enabled));
    },
    setSearchValue(value) {
      searchInput.value = value || "";
    },
    closeMenus,
  };
}
