/** Bootstrapping and view routing. */

import { api, isMock } from "./api.js";
import { openAboutDialog } from "./components/about.js";
import { createHeader } from "./components/header.js";
import { openProgressOverlay } from "./components/progressOverlay.js";
import { openSettingsDialog } from "./components/settingsDialog.js";
import { createStatusBar } from "./components/statusBar.js";
import { showToast } from "./components/toast.js";
import { store } from "./state.js";
import { delay } from "./util/dom.js";
import { createBrowser } from "./views/browser.js";
import { showFiles } from "./views/files.js";
import { showHome } from "./views/home.js";

const DEFAULT_SETTINGS = {
  theme: "system",
  dateGroupingZone: "capture",
  thumbnailSize: 320,
};

function applyTheme(theme) {
  const resolved =
    theme === "system"
      ? window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"
      : theme;
  document.documentElement.dataset.theme = resolved || "light";
}

const ctx = {
  store,
  backups: [],
  session: null,
  browser: null,
  settings: { ...DEFAULT_SETTINGS },
  destroyBrowser: null,
  main: document.getElementById("main"),
  sidebar: document.getElementById("sidebar"),
  header: null,
  status: null,
};

ctx.applySettings = async (settings, { notify = false } = {}) => {
  ctx.settings = { ...ctx.settings, ...settings };
  applyTheme(ctx.settings.theme);
  if (ctx.browser) {
    await ctx.browser.applySettings(ctx.settings);
  }
  if (notify) showToast("Settings saved.", "success");
};

async function followIndex(overlay, state) {
  let current = state;
  overlay.update(current);
  while (current.indexState === "building") {
    await delay(280);
    current = await api.sessionState();
    overlay.update(current);
  }
  if (current.indexState === "failed") {
    throw new Error(current.progress?.message || "The photo library could not be read.");
  }
  return current;
}

ctx.openBackupFlow = async (backup, password) => {
  const overlay = openProgressOverlay(`Opening “${backup.deviceName || "backup"}”`);
  let opened = false;
  try {
    let state = await api.openSession(backup.id, password);
    opened = true;
    state = await followIndex(overlay, state);
    overlay.close();
    ctx.session = state;
    await ctx.showBrowser(state);
  } catch (error) {
    overlay.close();
    if (opened) await api.closeSession().catch(() => {});
    throw error;
  }
};

ctx.showBrowser = async (state) => {
  ctx.destroyBrowser?.();
  ctx.destroyBrowser = null;
  ctx.session = state;
  if (!ctx.backups?.length) {
    try {
      const payload = await api.listBackups();
      ctx.backups = payload.backups || [];
    } catch {
      ctx.backups = [];
    }
  }
  ctx.header.setBackupsCount(ctx.backups.length);
  ctx.status.setBackupsCount(ctx.backups.length);
  ctx.header.setMode("browser");
  ctx.header.setDevice(state.backup);
  ctx.sidebar.hidden = false;
  store.set({ view: "browser", session: state });
  const browser = createBrowser(ctx, state);
  ctx.browser = browser;
  ctx.destroyBrowser = () => {
    browser.destroy();
    ctx.browser = null;
    ctx.destroyBrowser = null;
  };
  await browser.load();
};

ctx.showHome = async () => {
  ctx.destroyBrowser?.();
  ctx.destroyBrowser = null;
  ctx.browser = null;
  store.set({ view: "home" });
  await showHome(ctx);
};

async function handleMenu(action) {
  if (action === "backups") {
    await ctx.showHome();
  } else if (action === "files") {
    if (!ctx.session?.open) {
      showToast("Open a backup first.");
    } else {
      showFiles(ctx);
    }
  } else if (action === "settings") {
    openSettingsDialog({
      settings: ctx.settings,
      onBrowse: async () => api.pickFolder(),
      onSave: async (patch) => {
        const saved = await api.updateSettings(patch);
        await ctx.applySettings(saved, { notify: true });
      },
    });
  } else if (action === "clear-cache") {
    try {
      await api.clearCache();
      showToast("Thumbnail and preview cache cleared.", "success");
    } catch (error) {
      showToast(error?.message || "Could not clear the cache.", "error");
    }
  } else if (action === "about") {
    openAboutDialog(document.querySelector(".version-box")?.textContent?.replace(/^v/, ""));
  } else if (action === "close") {
    if (!ctx.session?.open) {
      showToast("No backup is open.");
      return;
    }
    try {
      await api.closeSession();
    } catch (error) {
      showToast(error?.message || "Could not close the backup.", "error");
      return;
    }
    ctx.session = null;
    ctx.header.setDevice(null);
    await ctx.showHome();
    showToast("Backup closed. Temporary decrypted data was removed.", "success");
  } else if (action === "quit") {
    try {
      await api.quitApp();
      showToast("BackupLens is shutting down. You can close this tab.");
      window.setTimeout(() => window.close(), 600);
    } catch (error) {
      showToast(error?.message || "Could not quit BackupLens.", "error");
    }
  }
}

function fatalMessage(message) {
  ctx.main.innerHTML = "";
  const box = document.createElement("div");
  box.className = "home";
  const title = document.createElement("h2");
  title.textContent = "BackupLens";
  const text = document.createElement("p");
  text.className = "empty-home";
  text.textContent = message;
  box.append(title, text);
  ctx.main.append(box);
  ctx.status.setStatus("Not connected", "error");
}

async function boot() {
  ctx.header = createHeader(document.getElementById("header"), {
    isMock,
    onMenuAction: handleMenu,
    onToolbarAction: (action, payload) => {
      if (ctx.browser) ctx.browser.handleToolbar(action, payload);
    },
  });
  ctx.status = createStatusBar(document.getElementById("statusbar"), {
    onBackups: () => ctx.showHome(),
  });

  try {
    const version = await api.version();
    ctx.status.setVersion(version?.version || "0.1.0");
  } catch {
    /* version is cosmetic */
  }

  try {
    const settings = await api.getSettings();
    ctx.settings = { ...DEFAULT_SETTINGS, ...settings };
  } catch {
    ctx.settings = { ...DEFAULT_SETTINGS };
  }
  applyTheme(ctx.settings.theme);
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (ctx.settings.theme === "system") applyTheme("system");
  });

  if (isMock && new URLSearchParams(window.location.search).get("open") === "1") {
    const payload = await api.listBackups();
    await ctx.openBackupFlow(payload.backups[0], "demo");
    return;
  }

  let state = null;
  try {
    state = await api.sessionState();
  } catch (error) {
    if (error?.code === "unauthorized") {
      fatalMessage(
        "Not authorised. Open the URL printed in the BackupLens console — it contains the one-time access token.",
      );
      return;
    }
    fatalMessage(error?.message || "Could not reach the local BackupLens server.");
    return;
  }

  if (state?.open && state.indexState === "ready") {
    ctx.session = state;
    await ctx.showBrowser(state);
    return;
  }
  if (state?.open && state.indexState === "building") {
    const overlay = openProgressOverlay("Resuming backup");
    try {
      state = await followIndex(overlay, state);
      overlay.close();
      ctx.session = state;
      await ctx.showBrowser(state);
    } catch (error) {
      overlay.close();
      await api.closeSession().catch(() => {});
      await ctx.showHome();
      showToast(error?.message || "The photo library could not be read.", "error");
    }
    return;
  }
  if (state?.open && state.indexState === "failed") {
    await api.closeSession().catch(() => {});
    await ctx.showHome();
    showToast("The previous library index failed; pick the backup again.", "error");
    return;
  }
  await ctx.showHome();
}

window.addEventListener("beforeunload", () => {
  ctx.destroyBrowser?.();
});

boot().catch((error) => {
  console.error(error);
  fatalMessage(error?.message || "BackupLens could not start.");
});
