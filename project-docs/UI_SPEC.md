# UI_SPEC — match the reference screenshot

Reference image: `project-docs/local/ibackup-viewer-photos.png` (the screenshot of the iBackup Viewer
photo browser, 1917 × ~980 px). Put the file there (see the privacy note in `SETUP.md`: the image
contains personal data, so crop/blur it or keep it out of a public repo).

**Scope of imitation:** layout, proportions, spacing, colour feel and behaviour. **Not** copied:
logos, the app name, the Photos flower icon artwork, or any proprietary asset. Use own inline SVG
icons (simple line/solid glyphs) and the neutral system font stack.

Items marked **[seen]** are visible in the screenshot. Items marked **[inferred]** are reasonable
behaviour that is not visible and are design decisions for the implementer.

---

## 1. Overall layout [seen]

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ HEADER (≈118 px)                                                             │
│  Title + badge | app icon | Unique ID                          [menu ≡]      │
│                                  toolbar → [📅] [Current Folder] [All ▾] [☑]  │
├───────────────┬──────────────────────────────────────────────────────────────┤
│ SIDEBAR       │ MAIN SCROLL AREA                                             │
│ ≈365 px wide  │  date-grouped thumbnail grid                                 │
│ own scrollbar │                                                              │
│               │                                                              │
├───────────────┴──────────────────────────────────────────────────────────────┤
│ STATUS BAR (≈40 px):  ● [version]                                [Devices 0] │
└──────────────────────────────────────────────────────────────────────────────┘
```

- Light theme, white background. Thin 1 px light-grey separators between header/sidebar/main/status bar.
- Sidebar and main area **scroll independently**; the header and status bar are fixed.
- Reference viewport is 1920 × 1080; the layout must scale gracefully from 1280 px upward.
  Sidebar width: `clamp(260px, 19vw, 365px)`.

## 2. Design tokens (approximate, sampled by eye from the screenshot)

| Token | Value | Use |
|---|---|---|
| `--bg` | `#ffffff` | page, header, sidebar, grid |
| `--text` | `#1f2328` | primary text |
| `--text-muted` | `#5f6b7a` | secondary text, counts |
| `--accent` | `#17619f` (deep blue) | selected sidebar row |
| `--accent-text` | `#ffffff` | text on accent |
| `--btn-bg` | `#eceef1` | toolbar buttons |
| `--btn-bg-hover` | `#e0e3e8` | hover |
| `--pill-bg` | `#e8eef6` | count pill background |
| `--pill-border` | `#c9d3e0` | count pill border |
| `--pill-text` | `#4a5b73` | count pill text |
| `--divider` | `#d9dde3` | separators |
| `--status-bg` | `#f6f6f6` | bottom bar |
| Font | `system-ui, "Segoe UI", Roboto, Helvetica, Arial, sans-serif` | everywhere |

Provide a dark theme as a stretch goal using the same tokens (`prefers-color-scheme`), but the
light theme must be pixel-faithful first.

## 3. Header [seen]

Row 1 (height ≈ 60 px):
- **Title** "Local Backups" at left, large and light weight (≈ 36 px, weight 300). Immediately right of
  it a small **rounded grey badge** with the count of discovered backups (e.g. `2`).
- Right of the title, a **device icon** in a white rounded square card with a soft shadow, hanging
  from the top edge (≈ 50 × 50 px). In our app this shows a generic photo/phone glyph (not the Apple
  Photos artwork).
- Next to it: `Unique ID :` (regular) followed by the UDID in **bold** (≈ 18 px).
- Far right: **hamburger menu** icon (≡). Menu items: Backups, Settings, Clear cache, About, Close backup.

Row 2 (toolbar, right-aligned, height ≈ 55 px, buttons ≈ 38 px high, 4 px radius, bold 18 px label):
1. **Calendar icon button** — opens a date-jump popover (month/year picker; picking a day scrolls
   the grid to that date's group). [seen icon, behaviour inferred]
2. **"Current Folder"** with an export icon — exports every asset in the currently selected sidebar
   entry (respecting the type filter). Opens the Export dialog (§9). [seen label, behaviour inferred
   from the name]
3. **"All ▾"** with an image icon and dropdown caret — media type filter: *All / Photos / Videos*.
   [seen label, options inferred]
4. **Checklist icon button** — toggles **selection mode** (and offers *Select all in view*,
   *Clear selection*, *Export selected*). [seen icon, behaviour inferred]

## 4. Sidebar [seen]

Row height ≈ 31 px, left padding ≈ 14 px, icon (≈ 18 px) + 6 px gap + label, count pill right-aligned
with ≈ 12 px right padding. Font ≈ 18 px (scale with root font size).

**Order and labels (exact):**

| Group | Rows |
|---|---|
| *(no heading)* | All · Camera Roll · Photos · Videos · Favorites · Live Photos · Portrait · Panoramas · Time-lapse · Slo-mo · Screenshots · Hidden · Trashed |
| **Albums** (plain text heading, no count, no icon) | one row per user album, album icon, count pill |
| **Moments** (plain heading) | one row per place/moment, alphabetical, **no icon, no count** (indented to the label column ≈ 44 px) |

Rules:
- **Count pill:** rounded (≈ 10 px radius), `--pill-*` colours, ≈ 12 px font, min-width ≈ 52 px, text
  centred. Rows with **zero** count show **no pill** (e.g. Time-lapse, Hidden in the screenshot).
- **Selected row:** full-width `--accent` background, white text and icon; its pill becomes a
  translucent/white-ish variant with white text.
- Hover: very light grey background. Keyboard: ↑/↓ to move, Enter to select. Focus ring visible.
- The sidebar has a slim custom scrollbar (≈ 8 px, grey thumb) at its right edge.
- Headings "Albums" and "Moments" use slightly different weight/colour than rows and ≈ 8 px extra
  top margin.
- Icons (inline SVG, 18 px): stack (All), camera (Camera Roll), photo (Photos), video camera
  (Videos), heart outline (Favorites), concentric circles (Live Photos), person-in-square (Portrait),
  panorama frame (Panoramas), circle (Time-lapse), dotted circle (Slo-mo), dashed square
  (Screenshots), eye-slashed (Hidden), trash can (Trashed), photo-stack (album rows).

## 5. Main grid [seen]

- **Background white**, padding ≈ 15 px left/top.
- **Date groups are inline blocks that flow left→right and wrap.** Each group = a **bold date header**
  (≈ 18 px, e.g. `Tue, Sep 10, 2024`) immediately above its tiles. Several small groups sit **side by
  side on the same row** (e.g. 1-photo + 1-photo + 2-photo groups share a row). A group is **never
  split across rows** unless it is wider than the whole row; then it wraps internally and the header
  stays above the first tile only.
- **Tile:** square, ≈ 294 × 294 px at 1920 px wide (use CSS `--tile` size, adjustable by a zoom
  control, default as measured). **`object-fit: cover`**, no border, no radius, no shadow.
- **Gap between tiles:** ≈ 5 px horizontally. **Gap between group rows:** ≈ 65 px vertical (header +
  breathing space).
- Tiles in the same group touch the header's left edge; the header is left-aligned over the first tile.
- A **selection circle** (≈ 26 px, white ring, semi-transparent fill) appears at the **top-left** of a
  tile on hover and in selection mode; filled blue with a white check when selected. [seen empty
  circle on one tile; behaviour inferred]
- Videos: small duration badge bottom-right (`0:23`) and a play glyph; Live Photos: small concentric
  circle glyph top-left of the tile area when not in selection mode. [inferred]
- Vertical scrollbar at the far right (≈ 10 px) of the main area.
- **Virtualisation is mandatory:** render only groups near the viewport (± 2 screens). Total DOM
  tiles ≤ 300. Use `IntersectionObserver` for image loading with `loading="lazy"`/`decoding="async"`
  and abort requests for tiles that leave the viewport.
- Empty state: centred muted text "No items in this view". Loading state: skeleton tiles (light grey).

## 6. Status bar [seen]

Height ≈ 40 px, `--status-bg`, top border `--divider`.
- Left: a small **grey circular status dot** (≈ 18 px; grey = idle, blue pulse = working, red = error)
  then a bordered box showing the **app version** (e.g. `0.1.0`).
- Next to the dot, a long empty bordered area used for **status text** (e.g. "Indexing 1,024 /
  2,048", "Exported 120 files"). [inferred]
- Right: **"Devices"** button with a phone icon and a count pill. In BackupLens this is relabelled
  **"Backups"** and the pill shows the number of open/known backups. [seen "Devices 0"]

## 7. Home screen: "Local Backups" [seen title, content inferred]

Before a backup is opened, the main area shows a list/grid of discovered backups as cards:
device name, model (from `ProductType`), iOS version, last backup date, size, **lock icon if
encrypted**, UDID. Click → password dialog (if encrypted) → progress overlay ("Unlocking…",
"Reading photo library…") → photo browser. An **Add backup folder…** card lets the user pick a
non-default location. The title badge shows the number of backups.

## 8. Preview / lightbox [inferred]

- Opens on tile click (or Space). Dark translucent overlay, image centred, `object-fit: contain`.
- ←/→ move through the current view; Esc closes; `+`/`-` zoom; `I` toggles an info panel
  (filename, date, dimensions, size, location, backup path, fileID).
- Videos use the native `<video controls>` pointed at the Range-enabled `/original` URL; Live Photos
  show a "Live" button that plays the paired clip.
- Toolbar: Download original, Export… (opens dialog with this item), Favorite status (read-only).
- Preloads the next/previous preview.

## 9. Export dialog [inferred, driven by `project-docs/FEATURES.md` F-EXP-*]

Modal. Fields: **Scope summary** ("1,243 items"), **Destination folder** (text input + Browse button
calling `/api/fs/pick-folder`), **Folder layout** (flat / by date / by album / original path),
checkboxes (*Convert HEIC to JPEG*, *Include Live Photo videos*, *Include edited versions*, *Set file
dates to capture date*), **If file exists** (skip / rename / overwrite).
Buttons: *Export*, *Cancel*. After start: progress bar, current file, counts, **Cancel**, then a
summary with *Open folder* and any errors.
A secondary action **Download ZIP** is offered only when the selection is small (default ≤ 500
items / 2 GB).

## 10. Context menu and keyboard [inferred]

- Right-click on a tile: *Open preview · Export… · Copy filename · Show info*.
- `Ctrl+A` select all in view, `Shift+click` range select, `Ctrl+click` toggle, `Esc` clear selection,
  `Home/End` jump to newest/oldest, `PageUp/PageDown` scroll, `Delete` is **disabled** (read-only app).

## 11. Behavioural details

1. Selecting a sidebar row reloads the grid for that scope and resets scroll to top; the selected
   row persists across reloads of the same backup (remember in `sessionStorage`).
2. Changing the **All ▾** filter re-filters the current scope client-side (no reload) and updates the
   visible count in the status bar.
3. The calendar button highlights days that have items; picking a day smooth-scrolls to its group.
4. Window resize reflows groups without losing the scroll anchor (anchor on the first visible group).
5. All network errors surface as a non-blocking toast; fatal errors as a dialog with a **Copy
   diagnostics** button (never includes the password).
6. Keyboard accessibility: every control reachable by Tab, ARIA labels on icon buttons, `role=listbox`
   semantics for the sidebar, `aria-live` region for status messages.

## 12. Manual QA checklist (UI Agent + QA Agent sign-off)

- [x] At 1920×1080 the header (118 px), sidebar width (`clamp(260px, 19vw, 365px)` → 365 px), tile size
      (293.76 px) and gaps (5 px) match the reference within ~4 px. Measured from CSS and a 1920×1080
      headless-Chrome screenshot (`docs/screenshots/mock-browser.png`).
- [x] Small date groups share a row exactly as in the reference (groups flow left→right and wrap; a
      group wider than the row wraps internally). Verified with the mock library: 3-tile + 1-tile groups
      share the first row.
- [x] Selected sidebar row is solid blue with white text; zero-count rows show no pill.
- [x] Sidebar order and labels match §4 exactly, then Albums, then Moments (alphabetical).
- [x] Scrolling the synthetic mock keeps the DOM at ~25–26 tiles and ~9 date groups at 1920×1080
      (≤300 required); scrolling to the bottom still shows ~26 tiles.
- [x] Thumbnails load only for tiles near the viewport (11 of 25 rendered tiles had `src` on first paint;
      the rest stayed `data-src`), and off-screen pending loads are dropped.
- [x] Selection circle appears on hover/selection mode; click selects; Ctrl-click toggles; Shift-click
      selects a range; the status bar counter updates (verified Ctrl-click + Ctrl+A selects all in view).
- [x] Current Folder → export dialog shows the exact count of the current view.
- [x] All ▾ filter works without a reload and updates the view immediately.
- [x] Lightbox: arrows, Esc, video playback with seeking, info panel. Photo preview, Esc, zoom, info
      verified; videos use the Range-capable `/original` endpoint (206 verified). HEVC/MOV may still be
      undecodable in a given browser, in which case the documented download hint appears.
- [x] Wrong password shows a clear inline error and allows retry without restarting the app.
- [x] No request leaves `127.0.0.1`; no external fonts/scripts (mock thumbnails are `data:` SVGs).
- [ ] Works in latest Chrome, Edge and Firefox. **Chrome (headless 1920×1080) verified; Edge is the same
      Chromium engine but not smoke-tested; Firefox is untested.**

Sign-off: UI agent 2026-10-28; QA agent to re-run the two open items in Phase 8.

## 13. Screenshots produced during development

Synthetic mock data only, no personal photos:

- `docs/screenshots/mock-home.png` — Home / backups list
- `docs/screenshots/mock-browser.png` — browser shell, sidebar and virtualised grid
- `docs/screenshots/mock-lightbox.png` — preview lightbox
- `docs/screenshots/mock-export.png` — export dialog with progress

## 13. Frontend file structure (suggested, no build step)

```
frontend/
├─ index.html
├─ css/  tokens.css  layout.css  sidebar.css  grid.css  dialogs.css
└─ js/
   ├─ main.js          bootstrapping, routing between Home and Browser views
   ├─ api.js           fetch wrapper (token cookie, error mapping)
   ├─ state.js         tiny observable store
   ├─ views/home.js    backups list, password dialog
   ├─ views/browser.js layout shell
   ├─ components/sidebar.js  grid.js  lightbox.js  exportDialog.js  datePicker.js  toast.js
   └─ util/dates.js  dom.js  icons.js (inline SVG strings)
```
Vendored libraries: none required. If one is truly needed (e.g. a tiny virtual scroller), vendor it under
`frontend/vendor/` with its license.
