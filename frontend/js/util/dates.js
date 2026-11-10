/** Date, duration and byte formatting. */

const DAY = 86400;

export function pad2(value) {
  return String(value).padStart(2, "0");
}

/** Local calendar day key for a Unix timestamp and an iOS timezone offset (seconds). */
export function localDay(timestamp, tzOffset) {
  if (!timestamp) return "unknown";
  const offset =
    typeof tzOffset === "number" ? tzOffset : -new Date(timestamp * 1000).getTimezoneOffset() * 60;
  const date = new Date((timestamp + offset) * 1000);
  return `${date.getUTCFullYear()}-${pad2(date.getUTCMonth() + 1)}-${pad2(date.getUTCDate())}`;
}

/** "Tue, Sep 10, 2024" (matches the reference header format). */
export function dayLabel(day) {
  if (!day || day === "unknown") return "Unknown date";
  const [year, month, date] = day.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, date)).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function timeLabel(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  if (hours > 0) return `${hours}:${pad2(minutes)}:${pad2(secs)}`;
  return `${minutes}:${pad2(secs)}`;
}

export function formatDuration(seconds) {
  return timeLabel(seconds);
}

export function formatBytes(bytes) {
  const value = Number(bytes) || 0;
  if (value <= 0) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let index = 0;
  let size = value;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size >= 10 || index === 0 ? Math.round(size) : size.toFixed(1)} ${units[index]}`;
}

export function isoToLocal(iso) {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function dayKeyToDate(day) {
  const [year, month, date] = day.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, date));
}

export function addMonths(date, delta) {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + delta, 1));
}

export function monthLabel(date) {
  return date.toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function startOfMonth(date) {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), 1));
}

export function monthGrid(date) {
  const first = startOfMonth(date);
  const knock = (first.getUTCDay() + 6) % 7; // Monday-first
  const start = new Date(first.getTime() - knock * DAY * 1000);
  const cells = [];
  for (let index = 0; index < 42; index += 1) {
    cells.push(new Date(start.getTime() + index * DAY * 1000));
  }
  return cells;
}

export function dayFromDate(date) {
  return `${date.getUTCFullYear()}-${pad2(date.getUTCMonth() + 1)}-${pad2(date.getUTCDate())}`;
}
