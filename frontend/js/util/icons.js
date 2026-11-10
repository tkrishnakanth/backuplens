/** Own inline SVG icons (no third-party artwork). */

const paths = {
  stack: `
    <rect x="4" y="7" width="14" height="13" rx="2"/>
    <path d="M8 7V5.5A1.5 1.5 0 0 1 9.5 4H18a2 2 0 0 1 2 2v10.5a1.5 1.5 0 0 1-1.5 1.5H18"/>`,
  camera: `
    <path d="M4 8h3l1.2-2h7.6L17 8h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1Z"/>
    <circle cx="12" cy="13" r="3.4"/>`,
  photo: `
    <rect x="3.5" y="5" width="17" height="14" rx="2"/>
    <circle cx="8.5" cy="9.5" r="1.4"/>
    <path d="m5 17 4.2-4.4 3.1 3.1 2.2-2.2L19 17"/>`,
  video: `
    <rect x="3.5" y="6" width="12" height="12" rx="2"/>
    <path d="m15.5 10 4.2-2.4v8.8L15.5 14"/>`,
  heart: `
    <path d="M12 19.5S4 14.7 4 9.6A3.9 3.9 0 0 1 11.2 7L12 8l.8-1A3.9 3.9 0 0 1 20 9.6c0 5.1-8 9.9-8 9.9Z"/>`,
  live: `
    <circle cx="12" cy="12" r="8"/>
    <circle cx="12" cy="12" r="4.2"/>
    <circle cx="12" cy="12" r="1" fill="currentColor"/>`,
  portrait: `
    <rect x="4" y="3.8" width="16" height="16.4" rx="2"/>
    <circle cx="12" cy="10" r="2.4"/>
    <path d="M7.8 17.2c.7-2.3 2.3-3.5 4.2-3.5s3.5 1.2 4.2 3.5"/>`,
  panorama: `
    <path d="M3 7.5c3 1 6 1.3 9 1.3s6-.3 9-1.3v9c-3-1-6-1.3-9-1.3s-6 .3-9 1.3Z"/>
    <path d="M7 12h10"/>`,
  timelapse: `
    <circle cx="12" cy="12" r="8"/>
    <path d="M12 7.5V12l3 2"/>`,
  slomo: `
    <circle cx="12" cy="12" r="8" stroke-dasharray="2.5 3"/>
    <circle cx="12" cy="12" r="1.6" fill="currentColor"/>`,
  screenshot: `
    <rect x="4" y="4" width="16" height="16" rx="2" stroke-dasharray="3 2.5"/>
    <path d="M8 9h8M8 12h8M8 15h5"/>`,
  hidden: `
    <path d="M3 12s3.5-5.5 9-5.5 9 5.5 9 5.5-3.5 5.5-9 5.5S3 12 3 12Z"/>
    <circle cx="12" cy="12" r="2.6"/>
    <path d="m4 20 16-16"/>`,
  trash: `
    <path d="M5 7h14M10 7V5h4v2M7 7l1 12a1 1 0 0 0 1 .9h6a1 1 0 0 0 1-.9L17 7"/>
    <path d="M10 11v5M14 11v5"/>`,
  album: `
    <rect x="5" y="5" width="14" height="14" rx="2"/>
    <path d="M8 5V3.8M8 20.2V19M16 5V3.8M16 20.2V19"/>
    <path d="m7.5 16 3-3.2 2.2 2.2 1.8-1.8 2 2.4"/>`,
  menu: `<path d="M4 7h16M4 12h16M4 17h16"/>`,
  calendar: `
    <rect x="4" y="5.5" width="16" height="14" rx="2"/>
    <path d="M8 3.5v4M16 3.5v4M4 10h16"/>`,
  export: `
    <path d="M12 16V4M8 8l4-4 4 4"/>
    <path d="M5 15v4a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-4"/>`,
  image: `
    <rect x="3.5" y="5" width="17" height="14" rx="2"/>
    <circle cx="8.5" cy="9.5" r="1.4"/>
    <path d="m5 17 4.2-4.4 3.1 3.1 2.2-2.2L19 17"/>`,
  checklist: `
    <rect x="4" y="4" width="16" height="16" rx="2.5"/>
    <path d="m7.5 9.2 1.6 1.6 3-3"/>
    <path d="M13.8 9h3M7.5 15l1.6 1.6 3-3M13.8 15h3"/>`,
  chevronDown: `<path d="m7 10 5 5 5-5"/>`,
  chevronLeft: `<path d="m14 6-6 6 6 6"/>`,
  chevronRight: `<path d="m10 6 6 6-6 6"/>`,
  lock: `
    <rect x="5.5" y="10" width="13" height="9.5" rx="1.6"/>
    <path d="M8.5 10V8a3.5 3.5 0 0 1 7 0v2"/>`,
  phone: `
    <rect x="6.5" y="3" width="11" height="18" rx="2"/>
    <path d="M10.5 18.2h3"/>`,
  folder: `
    <path d="M3.5 6.5h6l1.6 2H20a.8.8 0 0 1 .8.8v8.4a1 1 0 0 1-1 1H4.2a1 1 0 0 1-1-1V7.5a1 1 0 0 1 1-1Z"/>`,
  play: `<path d="M9 6.5v11l9-5.5Z" fill="currentColor" stroke="none"/>`,
  close: `<path d="m6 6 12 12M18 6 6 18"/>`,
  info: `
    <circle cx="12" cy="12" r="8.5"/>
    <path d="M12 10.5V17M12 7.6v.4"/>`,
  download: `
    <path d="M12 4v11M8 11.5l4 4 4-4"/>
    <path d="M5 19h14"/>`,
  zoomIn: `
    <circle cx="10.5" cy="10.5" r="6"/>
    <path d="m15.2 15.2 4.3 4.3M10.5 7.8v5.4M7.8 10.5h5.4"/>`,
  zoomOut: `
    <circle cx="10.5" cy="10.5" r="6"/>
    <path d="m15.2 15.2 4.3 4.3M7.8 10.5h5.4"/>`,
  search: `
    <circle cx="10.7" cy="10.7" r="6"/>
    <path d="m15.3 15.3 4.2 4.2"/>`,
  dots: `
    <circle cx="6" cy="12" r="1.3" fill="currentColor" stroke="none"/>
    <circle cx="12" cy="12" r="1.3" fill="currentColor" stroke="none"/>
    <circle cx="18" cy="12" r="1.3" fill="currentColor" stroke="none"/>`,
  grid: `
    <rect x="4" y="4" width="6.5" height="6.5" rx="1"/>
    <rect x="13.5" y="4" width="6.5" height="6.5" rx="1"/>
    <rect x="4" y="13.5" width="6.5" height="6.5" rx="1"/>
    <rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1"/>`,
  folders: `
    <path d="M3.5 7h5l1.4 1.8h6.3a1 1 0 0 1 1 1v6.7a1 1 0 0 1-1 1H4.5a1 1 0 0 1-1-1Z"/>
    <path d="M7 5h5l1.4 1.6H18a1 1 0 0 1 1 1v1.2"/>`,
};

export function icon(name, size = 18, className = "") {
  const body = paths[name] || "";
  return `<svg class="icon ${className}" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${body}</svg>`;
}

export const categoryIcons = {
  all: "stack",
  camera_roll: "camera",
  photos: "photo",
  videos: "video",
  favorites: "heart",
  live: "live",
  portrait: "portrait",
  panoramas: "panorama",
  timelapse: "timelapse",
  slomo: "slomo",
  screenshots: "screenshot",
  hidden: "hidden",
  trashed: "trash",
};
