/** Non-blocking toasts (aria-live container lives in index.html). */

let root = null;

function ensureRoot() {
  if (!root) root = document.getElementById("toasts");
  return root;
}

export function showToast(message, type = "info", timeout = 4200) {
  const container = ensureRoot();
  if (!container) return;
  const node = document.createElement("div");
  node.className = `toast ${type === "error" ? "error" : type === "success" ? "success" : ""}`.trim();
  node.setAttribute("role", type === "error" ? "alert" : "status");
  node.textContent = String(message);
  container.appendChild(node);
  window.setTimeout(() => {
    node.style.opacity = "0";
    node.style.transition = "opacity .18s ease";
    window.setTimeout(() => node.remove(), 220);
  }, timeout);
}
