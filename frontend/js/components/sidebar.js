/** Sidebar: categories, albums, moments (project-docs/UI_SPEC.md §4). */

import { h, formatCount } from "../util/dom.js";
import { categoryIcons, icon } from "../util/icons.js";

function scopeEquals(a, b) {
  if (!a || !b) return false;
  if (a.kind !== b.kind) return false;
  if (a.kind === "category") return a.key === b.key;
  return a.id === b.id;
}

export function createSidebar(root, data, { selected, onSelect } = {}) {
  root.innerHTML = "";
  root.className = "sidebar";
  root.setAttribute("role", "listbox");
  root.setAttribute("aria-label", "Photo categories, albums and places");

  const rows = [];
  let current = selected || { kind: "category", key: "all", label: "All" };

  function makeRow({ scope, label, count, iconName, moment = false }) {
    const iconSpan = iconName
      ? h("span", { class: "row-icon", html: icon(iconName, 18) })
      : null;
    const pill =
      count > 0 ? h("span", { class: "count-pill", text: formatCount(count) }) : null;
    const row = h(
      "div",
      {
        class: `sidebar-row${moment ? " moment-row" : ""}`,
        role: "option",
        tabindex: "-1",
        "aria-selected": "false",
        dataset: { scopeKind: scope.kind },
        onclick: () => choose(scope),
      },
      iconSpan,
      h("span", { class: "row-label", text: label }),
      pill,
    );
    row._scope = scope;
    rows.push(row);
    return row;
  }

  function choose(scope) {
    current = scope;
    setSelected(scope);
    onSelect?.(scope);
  }

  function setSelected(scope) {
    for (const row of rows) {
      const active = scopeEquals(row._scope, scope);
      row.setAttribute("aria-selected", String(active));
      row.tabIndex = active ? 0 : -1;
      if (active) row.scrollIntoView({ block: "nearest" });
    }
  }

  const list = h("div", { class: "sidebar-list" });
  for (const category of data.categories || []) {
    list.append(
      makeRow({
        scope: { kind: "category", key: category.key, label: category.label },
        label: category.label,
        count: category.count,
        iconName: categoryIcons[category.key] || "photo",
      }),
    );
  }

  if ((data.albums || []).length) {
    list.append(h("div", { class: "sidebar-heading", role: "presentation", text: "Albums" }));
    for (const album of data.albums) {
      list.append(
        makeRow({
          scope: { kind: "album", id: album.id, title: album.title },
          label: album.title,
          count: album.count,
          iconName: "album",
        }),
      );
    }
  }

  if ((data.moments || []).length) {
    list.append(h("div", { class: "sidebar-heading", role: "presentation", text: "Moments" }));
    for (const moment of data.moments) {
      list.append(
        makeRow({
          scope: { kind: "moment", id: moment.id, title: moment.title },
          label: moment.title,
          count: 0, // moments render without a count pill (UI spec)
          moment: true,
        }),
      );
    }
  }

  root.append(list);
  setSelected(current);

  root.addEventListener("keydown", (event) => {
    const index = rows.indexOf(document.activeElement);
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const direction = event.key === "ArrowDown" ? 1 : -1;
      const next = rows[Math.min(rows.length - 1, Math.max(0, (index < 0 ? 0 : index) + direction))];
      next?.focus();
    } else if (event.key === "Home" || event.key === "End") {
      event.preventDefault();
      (event.key === "Home" ? rows[0] : rows[rows.length - 1])?.focus();
    } else if ((event.key === "Enter" || event.key === " ") && index >= 0) {
      event.preventDefault();
      choose(rows[index]._scope);
    }
  });

  return {
    setSelected,
    getSelected: () => current,
  };
}
