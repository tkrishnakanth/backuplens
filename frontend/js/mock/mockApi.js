/** Deterministic demo API used by ?mock=1. No network, no external assets. */

const DAY = 86400;
const TOTAL = 3860;
const TRASHED = 520;
const BASE_DAY = Date.UTC(2023, 0, 1, 12) / 1000;
const TZ_OFFSET = 3600;

const CATEGORY_LABELS = [
  ["all", "All"],
  ["camera_roll", "Camera Roll"],
  ["photos", "Photos"],
  ["videos", "Videos"],
  ["favorites", "Favorites"],
  ["live", "Live Photos"],
  ["portrait", "Portrait"],
  ["panoramas", "Panoramas"],
  ["timelapse", "Time-lapse"],
  ["slomo", "Slo-mo"],
  ["screenshots", "Screenshots"],
  ["hidden", "Hidden"],
  ["trashed", "Trashed"],
];

const ALBUM_NAMES = Array.from({ length: 20 }, (_, index) => `Album ${String(index + 1).padStart(2, "0")}`);

const MOMENT_NAMES = Array.from({ length: 20 }, (_, index) => `Place ${String(index + 1).padStart(2, "0")}`);

function hash(value) {
  let x = (Math.imul(value + 1, 2654435761) ^ 0x9e3779b9) >>> 0;
  x ^= x >>> 13;
  x = Math.imul(x, 0x85ebca6b) >>> 0;
  x ^= x >>> 16;
  return (x >>> 0) / 4294967296;
}

function makeAssets() {
  const assets = [];
  for (let i = 0; i < TOTAL; i += 1) {
    const trashed = i >= TOTAL - TRASHED;
    const kind = !trashed && i % 12 === 0 ? "video" : "photo";
    const favorite = i % 300 === 0;
    const hidden = false;
    const live = !trashed && kind === "photo" && i % 123 === 0;
    const portrait = !trashed && i % 14 === 0;
    const panorama = !trashed && (i === 1002 || i === 2003);
    const timelapse = false;
    const slomo = !trashed && kind === "video" && i % 270 === 0;
    const screenshot = !trashed && i % 39 === 0;
    const hasAdjustments = i % 20 === 0;
    const ext = kind === "video" ? "MOV" : screenshot ? "PNG" : "HEIC";
    const number = String(TOTAL - i).padStart(4, "0");
    let album = null;
    if (i < 640) album = ALBUM_NAMES[0];
    else if (i < 644) album = ALBUM_NAMES[1];
    else if (i % 4 === 0) album = ALBUM_NAMES[2 + (Math.floor(i / 4) % (ALBUM_NAMES.length - 2))];
    const moment = MOMENT_NAMES[Math.floor(hash(i + 11) * MOMENT_NAMES.length)];
    const takenAt = BASE_DAY - Math.floor(i / 3) * DAY + Math.floor(hash(i) * 36000);
    const flags =
      (favorite ? 1 : 0) |
      (hidden ? 2 : 0) |
      (trashed ? 4 : 0) |
      (live ? 8 : 0) |
      (portrait ? 16 : 0) |
      (panorama ? 32 : 0) |
      (timelapse ? 64 : 0) |
      (slomo ? 128 : 0) |
      (screenshot ? 256 : 0);
    assets.push({
      id: `a${i + 1}`,
      name: `TEST_${number}.${ext}`,
      originalName: `TEST_${number}.${ext}`,
      takenAt,
      kind: kind === "video" ? "v" : "p",
      width: kind === "video" ? 1920 : 4032,
      height: kind === "video" ? 1080 : 3024,
      flags,
      duration: kind === "video" ? 3 + hash(i + 3) * 120 : 0,
      size: 400000 + Math.floor(hash(i + 5) * 9000000),
      tzOffset: TZ_OFFSET,
      album,
      moment,
      trashed,
      favorite,
      hidden,
      live,
      portrait,
      panorama,
      timelapse,
      slomo,
      screenshot,
      hasAdjustments,
      fileId: `${(i + 1).toString(16).padStart(8, "0")}`.repeat(5).slice(0, 40),
    });
  }
  return assets;
}

const assets = makeAssets();
const byId = new Map(assets.map((asset) => [asset.id, asset]));
const albumIndex = new Map(ALBUM_NAMES.map((title, index) => [`al${index + 1}`, title]));
const momentIndex = new Map(MOMENT_NAMES.map((title, index) => [`mo${index + 1}`, title]));

const mockBackups = [
  {
    id: "DEMO-UDID-00000001",
    path: "C:\\Backups\\DEMO-UDID-00000001",
    deviceName: "iPhone",
    displayName: "iPhone",
    productType: "iPhone13,3",
    iosVersion: "17.0",
    buildVersion: "TESTBUILD",
    serialNumber: "TESTSERIAL0001",
    imei: "000000000000000",
    udid: "DEMO-UDID-00000001",
    lastBackup: "2020-01-01T00:00:00Z",
    encrypted: true,
    manifestVersion: "10.0",
    sizeBytes: 136501070876,
  },
  {
    id: "00008030-0000000000000002",
    path: "C:\\Backups\\00008030-0000000000000002",
    deviceName: "iPad",
    displayName: "iPad",
    productType: "iPad13,4",
    iosVersion: "16.0",
    buildVersion: "TESTBUILD2",
    serialNumber: "DEMOIPAD0001",
    imei: null,
    udid: "00008030-0000000000000002",
    lastBackup: "2020-02-02T00:00:00Z",
    encrypted: false,
    manifestVersion: "10.0",
    sizeBytes: 42949672960,
  },
];

let extraBackups = [];
let currentSession = { open: false, backup: null, indexState: "idle", progress: null };
let unlockTimer = null;

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function allBackups() {
  return [...mockBackups, ...extraBackups];
}

function fail(code, message, status) {
  const error = new Error(message);
  error.code = code;
  error.status = status || 400;
  return error;
}

function matchesScope(asset, query) {
  if (query.album) {
    const title = albumIndex.get(query.album);
    if (!title) throw fail("album_not_found", "Unknown album", 404);
    if (asset.album !== title || asset.trashed) return false;
  } else if (query.moment) {
    const title = momentIndex.get(query.moment);
    if (!title) throw fail("moment_not_found", "Unknown moment", 404);
    if (asset.moment !== title || asset.trashed) return false;
  } else {
    const scope = query.scope || "all";
    const checks = {
      all: () => !asset.trashed,
      camera_roll: () => !asset.trashed,
      photos: () => !asset.trashed && asset.kind === "p",
      videos: () => !asset.trashed && asset.kind === "v",
      favorites: () => !asset.trashed && asset.favorite,
      live: () => !asset.trashed && asset.live,
      portrait: () => !asset.trashed && asset.portrait,
      panoramas: () => !asset.trashed && asset.panorama,
      timelapse: () => !asset.trashed && asset.timelapse,
      slomo: () => !asset.trashed && asset.slomo,
      screenshots: () => !asset.trashed && asset.screenshot,
      hidden: () => asset.hidden,
      trashed: () => asset.trashed,
    };
    const check = checks[scope];
    if (!check) throw fail("scope_not_found", "Unknown scope", 404);
    if (!check()) return false;
  }
  return true;
}

function filterAssets(query = {}) {
  const matchesTime = (asset) => {
    if (query.from && asset.takenAt < Number(query.from)) return false;
    if (query.to && asset.takenAt > Number(query.to)) return false;
    return true;
  };
  const needle = query.q ? String(query.q).toLowerCase() : null;
  return assets.filter((asset) => {
    if (!matchesScope(asset, query)) return false;
    if (query.type === "photo" && asset.kind !== "p") return false;
    if (query.type === "video" && asset.kind !== "v") return false;
    if (!matchesTime(asset)) return false;
    if (needle && !asset.name.toLowerCase().includes(needle)) return false;
    return true;
  });
}

function countCategory(key) {
  if (key === "all") return assets.length; // sidebar count includes trashed
  return filterAssets({ scope: key }).length;
}

function toCompact(asset) {
  return [asset.id, asset.name, asset.takenAt, asset.kind, asset.width, asset.height, asset.flags, Number(asset.duration.toFixed(3)), asset.size, asset.tzOffset];
}

function svgThumb(id, size) {
  const asset = byId.get(id);
  const index = asset ? Number(asset.id.slice(1)) : 1;
  const hue = Math.floor(hash(index) * 360);
  const hue2 = (hue + 48) % 360;
  const label = (asset?.name || "BackupLens").slice(0, 18);
  const radius = 40 + Math.floor(hash(index + 2) * 100);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 320 320"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="hsl(${hue} 52% 62%)"/><stop offset="1" stop-color="hsl(${hue2} 44% 34%)"/></linearGradient></defs><rect width="320" height="320" fill="url(#g)"/><circle cx="${70 + (index % 180)}" cy="${60 + (index % 120)}" r="${radius}" fill="#fff" opacity="0.14"/><circle cx="${240 - (index % 90)}" cy="${210 - (index % 80)}" r="${radius * 0.65}" fill="#000" opacity="0.10"/><text x="16" y="300" font-family="Segoe UI, Arial, sans-serif" font-size="17" fill="#fff" opacity="0.92">${label}</text></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

function detailFor(asset) {
  return {
    id: asset.id,
    fileId: asset.fileId,
    thumbFileId: asset.fileId,
    liveVideoFileId: asset.live ? asset.fileId : null,
    editedFileId: asset.hasAdjustments ? asset.fileId : null,
    filename: asset.name,
    originalName: asset.originalName,
    kind: asset.kind === "v" ? "video" : "photo",
    takenAt: asset.takenAt,
    takenAtIso: new Date(asset.takenAt * 1000).toISOString(),
    timezoneOffset: asset.tzOffset,
    width: asset.width,
    height: asset.height,
    duration: asset.duration,
    size: asset.size,
    favorite: asset.favorite,
    hidden: asset.hidden,
    trashed: asset.trashed,
    isLive: asset.live,
    isPortrait: asset.portrait,
    isPanorama: asset.panorama,
    isTimelapse: asset.timelapse,
    isSlomo: asset.slomo,
    isScreenshot: asset.screenshot,
    inCameraRoll: asset.album !== null,
    hasAdjustments: asset.hasAdjustments,
    latitude: 16.3,
    longitude: 80.4,
    relPath: `Media/DCIM/${100 + (Number(asset.id.slice(1)) % 5)}APPLE/${asset.name}`,
    moment: asset.moment,
    albums: asset.album ? [asset.album] : [],
  };
}

/* ------------------------------------------------------------------ API */

export async function version() {
  return { name: "BackupLens", version: "0.1.0-demo" };
}

export async function listBackups() {
  return { backups: clone(allBackups()) };
}

export async function addBackup(path) {
  if (!path || !String(path).trim()) throw fail("bad_request", "A folder path is required", 400);
  const name = String(path).split(/[\\/]/).filter(Boolean).pop() || "Added backup";
  const backup = {
    ...mockBackups[1],
    id: name,
    path: String(path),
    deviceName: "Added backup",
    displayName: "Added backup",
    encrypted: true,
    udid: name,
    lastBackup: "2024-01-01T00:00:00Z",
  };
  extraBackups = [...extraBackups, backup];
  return { backup: clone(backup) };
}

export async function sessionState() {
  return clone(currentSession);
}

export async function openSession(backupId, password) {
  if (currentSession.open) throw fail("already_open", "Close the current backup first", 409);
  const backup = allBackups().find((item) => item.id === backupId || item.path === backupId);
  if (!backup) throw fail("backup_not_found", "Unknown backup id", 404);
  if (backup.encrypted && !password) throw fail("wrong_password", "Incorrect backup password", 401);
  if (backup.encrypted && String(password).toLowerCase() === "wrong") {
    throw fail("wrong_password", "Incorrect backup password", 401);
  }
  currentSession = {
    open: true,
    backup: clone(backup),
    indexState: "building",
    progress: { stage: "starting", done: 0, total: 0 },
  };
  window.clearTimeout(unlockTimer);
  unlockTimer = window.setTimeout(() => {
    currentSession = { ...currentSession, indexState: "ready", progress: null };
  }, 850);
  return clone(currentSession);
}

export async function closeSession() {
  window.clearTimeout(unlockTimer);
  currentSession = { open: false, backup: null, indexState: "idle", progress: null };
  return clone(currentSession);
}

export async function sidebar() {
  const albums = ALBUM_NAMES.map((title, index) => ({
    id: `al${index + 1}`,
    title,
    count: assets.filter((asset) => asset.album === title && !asset.trashed).length,
  }));
  const moments = MOMENT_NAMES.map((title, index) => ({
    id: `mo${index + 1}`,
    title,
    count: assets.filter((asset) => asset.moment === title && !asset.trashed).length,
  })).sort((a, b) => a.title.localeCompare(b.title));
  return {
    categories: CATEGORY_LABELS.map(([key, label]) => ({ key, label, count: countCategory(key) })),
    albums,
    moments,
    assetCount: assets.length,
  };
}

export async function assetsApi(query = {}) {
  const matched = filterAssets(query);
  const limit = query.limit ? Number(query.limit) : matched.length;
  const selected = matched.slice(0, limit);
  return { v: 1, count: selected.length, items: selected.map(toCompact) };
}

export { assetsApi as assets };

export async function asset(id) {
  const found = byId.get(id);
  if (!found) throw fail("asset_not_found", "Unknown asset id", 404);
  return detailFor(found);
}

export function thumbUrl(id, size = 320) {
  return svgThumb(id, size);
}

export function previewUrl(id) {
  return svgThumb(id, 1400);
}

export function originalUrl(id) {
  const asset = byId.get(id);
  if (!asset || asset.kind === "v") return null;
  return svgThumb(id, 1600);
}

export function liveUrl(id) {
  return null;
}

const jobs = new Map();

function countForExport(payload) {
  if (Array.isArray(payload.ids) && payload.ids.length) return payload.ids.length;
  if (payload.count) return Number(payload.count);
  const scope = payload.scope;
  if (scope && typeof scope === "object") {
    if (scope.kind === "album") return filterAssets({ album: scope.id, type: payload.type }).length;
    if (scope.kind === "moment") return filterAssets({ moment: scope.id, type: payload.type }).length;
    return filterAssets({ scope: scope.key || "all", type: payload.type }).length;
  }
  return filterAssets(scope || {}).length;
}

export async function startExport(payload) {
  const total = Math.max(1, countForExport(payload));
  const id = `mock-job-${Date.now()}`;
  const job = {
    jobId: id,
    kind: "export",
    state: "running",
    done: 0,
    total,
    bytes: 0,
    currentFile: null,
    message: null,
    errors: [],
    createdAt: Date.now() / 1000,
  };
  jobs.set(id, job);
  const timer = window.setInterval(() => {
    const current = jobs.get(id);
    if (!current || current.state !== "running") {
      window.clearInterval(timer);
      return;
    }
    current.done = Math.min(current.total, current.done + Math.max(1, Math.ceil(current.total / 20)));
    current.bytes += 1_500_000;
    current.currentFile = `IMG_${String(current.done).padStart(4, "0")}.HEIC`;
    if (current.done >= current.total) {
      current.state = "done";
      current.currentFile = null;
      window.clearInterval(timer);
    }
  }, 220);
  return { jobId: id };
}

export async function jobStatus(id) {
  const job = jobs.get(id);
  if (!job) throw fail("job_not_found", "Unknown job id", 404);
  return clone(job);
}

export async function cancelJob(id) {
  const job = jobs.get(id);
  if (!job) throw fail("job_not_found", "Unknown job id", 404);
  job.state = "cancelled";
  return clone(job);
}

export async function exportZip(payload) {
  return new Blob([`mock zip for ${countForExport(payload)} assets`], { type: "application/zip" });
}

export async function pickFolder() {
  return "C:\\Users\\Public\\Pictures\\BackupLens Export";
}

export async function clearCache() {
  return { cleared: true };
}

let mockSettings = {
  cacheLimitBytes: 2 * 1024 * 1024 * 1024,
  cacheLocation: "C:\\Users\\Public\\BackupLens\\cache",
  theme: "system",
  dateGroupingZone: "capture",
  thumbnailSize: 320,
};

export async function getSettings() {
  return { ...mockSettings };
}

export async function updateSettings(patch) {
  mockSettings = { ...mockSettings, ...patch };
  return { ...mockSettings };
}

export async function fileDomains() {
  return { domains: [] };
}

export async function fileTree() {
  return { domain: "", path: "", entries: [] };
}

export async function fileSearch() {
  return { items: [], total: 0, limit: 200, offset: 0 };
}

export function fileDownloadUrl() {
  return null;
}

export async function startFileExport() {
  throw fail("demo_unavailable", "Raw file export needs a real backup session", 501);
}
