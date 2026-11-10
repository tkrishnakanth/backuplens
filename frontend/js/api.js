/** HTTP client. In ?mock=1 mode every call is served by js/mock/mockApi.js. */

import * as mockApi from "./mock/mockApi.js";

const params = new URLSearchParams(window.location.search);
export const isMock = params.get("mock") === "1";

export class ApiError extends Error {
  constructor(code, message, status) {
    super(message || code || "Request failed");
    this.name = "ApiError";
    this.code = code || "error";
    this.status = status || 0;
  }
}

async function request(path, { method = "GET", body, headers = {}, raw = false } = {}) {
  const options = {
    method,
    credentials: "same-origin",
    cache: "no-store",
    headers: { ...headers },
  };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(path, options);
  } catch (error) {
    throw new ApiError("network", "Could not reach the local BackupLens server", 0);
  }
  if (!response.ok) {
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    const error = payload?.error || {};
    throw new ApiError(
      error.code || `http_${response.status}`,
      error.message || `Request failed (${response.status})`,
      response.status,
    );
  }
  if (raw) return response;
  if (response.status === 204) return null;
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

const real = {
  version: () => fetch("/version", { credentials: "same-origin" }).then((r) => r.json()),
  listBackups: () => request("/api/backups"),
  addBackup: (path) => request("/api/backups/add", { method: "POST", body: { path } }),
  sessionState: () => request("/api/session"),
  openSession: (backupId, password) =>
    request("/api/session/open", { method: "POST", body: { backupId, password } }),
  closeSession: (purgeCache = false) =>
    request("/api/session/close", { method: "POST", body: { purgeCache } }),
  sidebar: () => request("/api/library/sidebar"),
  assets: (query) => request(`/api/library/assets?${new URLSearchParams(query).toString()}`),
  asset: (id) => request(`/api/library/assets/${encodeURIComponent(id)}`),
  thumbUrl: (id, size = 320) =>
    `/api/media/${encodeURIComponent(id)}/thumb?size=${encodeURIComponent(size)}`,
  previewUrl: (id) => `/api/media/${encodeURIComponent(id)}/preview`,
  originalUrl: (id) => `/api/media/${encodeURIComponent(id)}/original`,
  liveUrl: (id) => `/api/media/${encodeURIComponent(id)}/live`,
  startExport: (payload) => request("/api/export", { method: "POST", body: payload }),
  jobStatus: (id) => request(`/api/jobs/${encodeURIComponent(id)}`),
  cancelJob: (id) => request(`/api/jobs/${encodeURIComponent(id)}/cancel`, { method: "POST" }),
  exportZip: async (payload) => {
    const response = await request("/api/export/zip", { method: "POST", body: payload, raw: true });
    return response.blob();
  },
  pickFolder: async () => {
    const result = await request("/api/fs/pick-folder", { method: "POST", body: {} });
    return typeof result === "string" ? result : result?.path;
  },
  clearCache: () => request("/api/cache/clear", { method: "POST", body: {} }),
  getSettings: () => request("/api/settings"),
  updateSettings: (patch) => request("/api/settings", { method: "POST", body: patch }),
  fileDomains: () => request("/api/files/domains"),
  fileTree: (domain, path = "") =>
    request(`/api/files/tree?${new URLSearchParams({ domain, path }).toString()}`),
  fileSearch: (query) => request(`/api/files/search?${new URLSearchParams(query).toString()}`),
  fileDownloadUrl: (fileId) => `/api/files/${encodeURIComponent(fileId)}/download`,
  startFileExport: (payload) =>
    request("/api/files/export", { method: "POST", body: payload }),
};

export const api = isMock ? mockApi : real;
