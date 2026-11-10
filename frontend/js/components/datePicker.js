/** Calendar popover for jumping to a date group (UI spec §3/§11.3). */

import { clear, h } from "../util/dom.js";
import {
  addMonths,
  dayFromDate,
  dayKeyToDate,
  monthGrid,
  monthLabel,
  startOfMonth,
} from "../util/dates.js";
import { icon } from "../util/icons.js";

export function openDatePicker({ anchor, days, onPick }) {
  const dayCounts = new Map(days.map((day) => [day.date, day.count]));
  let month = startOfMonth(days.length ? dayKeyToDate(days[0].date) : new Date());

  const popover = h("div", { class: "date-popover", role: "dialog", "aria-label": "Jump to date" });
  const head = h("div", { class: "date-popover-head" });
  const prev = h("button", { class: "icon-btn", type: "button", "aria-label": "Previous month" }, h("span", { html: icon("chevronLeft", 18) }));
  const next = h("button", { class: "icon-btn", type: "button", "aria-label": "Next month" }, h("span", { html: icon("chevronRight", 18) }));
  const label = h("span");
  head.append(prev, label, next);
  const grid = h("div", { class: "date-grid" });
  popover.append(head, grid);

  function render() {
    clear(grid);
    label.textContent = monthLabel(month);
    const dow = ["M", "T", "W", "T", "F", "S", "S"];
    for (const name of dow) grid.append(h("div", { class: "date-dow", text: name }));
    for (const date of monthGrid(month)) {
      const day = dayFromDate(date);
      const inMonth = date.getUTCMonth() === month.getUTCMonth();
      const count = dayCounts.get(day) || 0;
      const cell = h("button", {
        class: `date-cell${count ? " has-items" : ""}${inMonth ? "" : " is-empty"}`,
        type: "button",
        text: inMonth ? String(date.getUTCDate()) : "",
        "aria-label": count ? `${day}, ${count} items` : day,
        disabled: !inMonth || count === 0,
        onclick: () => {
          onPick?.(day);
          close();
        },
      });
      if (count) cell.title = `${count} item${count === 1 ? "" : "s"}`;
      grid.append(cell);
    }
  }

  prev.addEventListener("click", () => {
    month = addMonths(month, -1);
    render();
  });
  next.addEventListener("click", () => {
    month = addMonths(month, 1);
    render();
  });

  const rect = anchor.getBoundingClientRect();
  popover.style.position = "fixed";
  popover.style.top = `${Math.min(window.innerHeight - 360, rect.bottom + 6)}px`;
  popover.style.left = `${Math.max(8, Math.min(window.innerWidth - 308, rect.right - 292))}px`;
  document.body.append(popover);
  render();

  function close() {
    popover.remove();
    document.removeEventListener("mousedown", outside);
    document.removeEventListener("keydown", onKey);
  }
  function outside(event) {
    if (!popover.contains(event.target) && !anchor.contains(event.target)) close();
  }
  function onKey(event) {
    if (event.key === "Escape") close();
  }
  document.addEventListener("mousedown", outside);
  document.addEventListener("keydown", onKey);
  return { close };
}
