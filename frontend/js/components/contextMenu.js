/** Right-click context menu. */

import { h } from "../util/dom.js";

let active = null;

export function closeContextMenu() {
  if (active) {
    active.remove();
    active = null;
  }
}

export function openContextMenu({ x, y, items }) {
  closeContextMenu();
  const menu = h("div", { class: "context-menu", role: "menu" });
  for (const item of items) {
    if (item.separator) {
      menu.append(h("div", { class: "menu-separator" }));
      continue;
    }
    menu.append(
      h(
        "button",
        {
          class: "menu-item",
          type: "button",
          role: "menuitem",
          disabled: item.disabled,
          onclick: () => {
            closeContextMenu();
            item.action?.();
          },
        },
        item.label,
      ),
    );
  }
  document.body.append(menu);
  const rect = menu.getBoundingClientRect();
  menu.style.left = `${Math.min(x, window.innerWidth - rect.width - 8)}px`;
  menu.style.top = `${Math.min(y, window.innerHeight - rect.height - 8)}px`;
  active = menu;

  const outside = (event) => {
    if (!menu.contains(event.target)) {
      closeContextMenu();
      document.removeEventListener("mousedown", outside);
    }
  };
  const onKey = (event) => {
    if (event.key === "Escape") {
      closeContextMenu();
      document.removeEventListener("keydown", onKey);
    }
  };
  document.addEventListener("mousedown", outside);
  document.addEventListener("keydown", onKey);
  return { close: closeContextMenu };
}
