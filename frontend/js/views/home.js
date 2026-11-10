/** Home view: discovered backups and the add-folder card (UI spec §7). */

import { api } from "../api.js";
import { formatBytes, isoToLocal } from "../util/dates.js";
import { h } from "../util/dom.js";
import { icon } from "../util/icons.js";
import { openAddBackupDialog } from "../components/addBackupDialog.js";
import { openPasswordDialog } from "../components/passwordDialog.js";
import { showToast } from "../components/toast.js";

function metaRow(label, value) {
  return [h("dt", { text: label }), h("dd", { text: value ?? "—" })];
}

function backupCard(backup, { current, onClick }) {
  return h(
    "button",
    { class: "backup-card", type: "button", onclick: onClick },
    h(
      "div",
      { class: "backup-card-head" },
      h("span", { class: "backup-glyph", html: icon("phone", 26) }),
      h(
        "span",
        {},
        h("div", { class: "backup-name", text: backup.deviceName || backup.id }),
        h("div", {
          class: "backup-model",
          text: `${backup.productType || "iOS device"} · iOS ${backup.iosVersion || "?"}`,
        }),
      ),
      backup.encrypted
        ? h("span", { class: "lock-pill" }, h("span", { html: icon("lock", 15) }), "Encrypted")
        : null,
    ),
    h(
      "dl",
      { class: "backup-meta" },
      ...metaRow("Last backup", isoToLocal(backup.lastBackup)),
      ...metaRow("Size", formatBytes(backup.sizeBytes)),
      ...metaRow("Unique ID", backup.udid || backup.id),
    ),
    current ? h("span", { class: "open-badge", text: "Currently open" }) : null,
  );
}

export async function showHome(ctx) {
  ctx.destroyBrowser?.();
  ctx.header.setMode("home");
  ctx.header.setDevice(null);
  ctx.sidebar.hidden = true;
  ctx.main.innerHTML = "";
  ctx.main.scrollTop = 0;
  ctx.status.setStatus("Looking for backups…", "working");
  ctx.main.append(h("div", { class: "home" }, h("h2", { text: "Local Backups" }), h("p", { class: "empty-home", text: "Scanning default backup folders…" })));

  let backups = [];
  let error = null;
  try {
    const payload = await api.listBackups();
    backups = payload.backups || [];
  } catch (err) {
    error = err;
  }
  ctx.backups = backups;
  ctx.header.setBackupsCount(backups.length);
  ctx.status.setBackupsCount(backups.length);
  ctx.store.set({ view: "home", backups });

  const container = h("div", { class: "home" });
  container.append(h("h2", { text: "Local Backups" }));
  if (error) {
    container.append(
      h("p", { class: "empty-home", text: error.message || "Could not list backups." }),
    );
    ctx.status.setStatus(error.message || "Could not list backups", "error");
  } else {
    container.append(
      h("p", {
        class: "empty-home",
        text: backups.length
          ? "Pick a backup to browse its photos. Backups are only read, never changed."
          : "No backups found in the default folders. Add the device folder manually.",
      }),
    );
  }

  const grid = h("div", { class: "backup-grid" });
  for (const backup of backups) {
    const current = Boolean(ctx.session?.open && ctx.session.backup?.id === backup.id);
    grid.append(
      backupCard(backup, {
        current,
        onClick: async () => {
          if (current) {
            await ctx.showBrowser(ctx.session);
            return;
          }
          if (ctx.session?.open) {
            showToast("Close the current backup first (menu → Close backup).", "error");
            return;
          }
          if (backup.encrypted) {
            openPasswordDialog({
              deviceName: backup.deviceName,
              onSubmit: (password) => ctx.openBackupFlow(backup, password),
            });
          } else {
            ctx.openBackupFlow(backup, null).catch((err) => {
              showToast(err?.message || "Could not open the backup", "error");
            });
          }
        },
      }),
    );
  }

  grid.append(
    h(
      "button",
      {
        class: "backup-card add-card",
        type: "button",
        onclick: () => {
          openAddBackupDialog({
            onSubmit: async (path) => {
              await api.addBackup(path);
              showToast("Backup folder added.", "success");
              await showHome(ctx);
            },
            onBrowse: async () => {
              const picked = await api.pickFolder();
              return picked || null;
            },
          });
        },
      },
      h("span", { html: icon("folder", 28) }),
      "Add backup folder…",
    ),
  );
  container.append(grid);
  ctx.main.replaceChildren(container);

  if (!error && backups.length) {
    ctx.status.setStatus(`${backups.length} backup${backups.length === 1 ? "" : "s"} found`);
  }
}
