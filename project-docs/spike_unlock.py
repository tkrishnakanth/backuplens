"""Phase 0 spike: prove the real backup unlocks and record Photos.sqlite facts.

Reads BACKUP_PATH and BACKUP_PASSWORD from the environment, falling back to a
tiny parser for the local, git-ignored ``.env`` file. The password is never
printed, logged or written anywhere.

Usage:  .venv\\Scripts\\python.exe project-docs\\spike_unlock.py
"""

from __future__ import annotations

import os
import plistlib
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from iphone_backup_decrypt import EncryptedBackup
from iphone_backup_decrypt.exceptions import IncorrectPassphraseError

PHOTO_DB = "Media/PhotoData/Photos.sqlite"


def load_dotenv(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE lines; ignore blanks/comments; strip optional quotes."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def env(name: str, dotenv: dict[str, str]) -> str | None:
    return os.environ.get(name) or dotenv.get(name) or None


def print_heading(title: str) -> None:
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [r[0] for r in rows]


def columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')]


def describe_table(conn: sqlite3.Connection, table: str) -> None:
    print(f"\n-- PRAGMA table_info({table}) --")
    for cid, name, ctype, notnull, default, pk in conn.execute(f'PRAGMA table_info("{table}")'):
        print(f"  {cid:>3} {name:<32} {ctype:<12} notnull={notnull} pk={pk} default={default!r}")


def fmt(value: object) -> str:
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    return str(value)


def main() -> int:
    dotenv = load_dotenv(ROOT / ".env")
    backup_path = env("BACKUP_PATH", dotenv)
    password = env("BACKUP_PASSWORD", dotenv)
    if not backup_path or not password:
        print("BACKUP_PATH and BACKUP_PASSWORD must be set (env or .env).")
        return 2
    backup_dir = Path(backup_path)
    if not backup_dir.is_dir():
        print("BACKUP_PATH does not point to an existing folder.")
        return 2

    print_heading("1. DEVICE INFO (Info.plist / Manifest.plist)")
    info = plistlib.loads((backup_dir / "Info.plist").read_bytes())
    manifest_plist = plistlib.loads((backup_dir / "Manifest.plist").read_bytes())
    for key in (
        "Device Name",
        "Display Name",
        "Product Type",
        "Product Version",
        "Build Version",
        "Serial Number",
        "Unique Identifier",
        "Last Backup Date",
        "IMEI",
        "Target Identifier",
    ):
        if key in info:
            print(f"  {key:<22}: {info[key]}")
    print(f"  {'IsEncrypted':<22}: {manifest_plist.get('IsEncrypted')}")
    print(f"  {'Manifest version':<22}: {manifest_plist.get('Version')}")
    print(f"  {'Backup folder':<22}: {backup_dir}")

    started = time.perf_counter()
    manifest_dir = Path(tempfile.mkdtemp(prefix="backuplens-spike-"))
    manifest_path = manifest_dir / "Manifest.db"
    try:
        backup = EncryptedBackup(backup_directory=str(backup_dir), passphrase=password)
        backup.test_decryption()
        elapsed = time.perf_counter() - started
        print(f"\n  unlock + Manifest.db decrypt: OK in {elapsed:.1f}s")
        backup.save_manifest_file(str(manifest_path))
    except IncorrectPassphraseError:
        print("\n  UNLOCK FAILED: the password is incorrect (typed value not shown).")
        return 3

    conn = sqlite3.connect(f"file:{manifest_path.as_posix()}?mode=ro", uri=True)
    try:
        total = conn.execute("SELECT count(*) FROM Files").fetchone()[0]
        files_only = conn.execute("SELECT count(*) FROM Files WHERE flags=1").fetchone()[0]
        print(f"\n  Manifest rows: {total} (regular files: {files_only})")

        print_heading("2. FILES PER DOMAIN (top 15, regular files)")
        for domain, count in conn.execute(
            "SELECT domain, count(*) FROM Files WHERE flags=1 GROUP BY domain ORDER BY 2 DESC LIMIT 15"
        ):
            print(f"  {count:>7}  {domain}")
        domains_total = conn.execute("SELECT count(DISTINCT domain) FROM Files").fetchone()[0]
        print(f"  distinct domains: {domains_total}")

        print_heading("3. CameraRollDomain / Media/PhotoData/")
        rows = conn.execute(
            "SELECT relativePath, file FROM Files WHERE domain='CameraRollDomain' "
            "AND relativePath LIKE 'Media/PhotoData/%' AND flags=1 ORDER BY relativePath"
        ).fetchall()
        print(f"  files under Media/PhotoData/: {len(rows)}")
        thumb_like = [r[0] for r in rows if "humb" in r[0] or "THUMB" in r[0]]
        print(f"  rows whose path mentions thumb: {len(thumb_like)}")
        for path in thumb_like[:8]:
            print(f"    {path}")
        print("  first 25 paths:")
        for path, _blob in rows[:25]:
            print(f"    {path}")
        for probe in (PHOTO_DB, PHOTO_DB + "-wal", PHOTO_DB + "-shm"):
            hit = conn.execute(
                "SELECT fileID FROM Files WHERE domain='CameraRollDomain' AND relativePath=? AND flags=1",
                (probe,),
            ).fetchone()
            print(f"  present {probe:<36} {bool(hit)}")

        print_heading("4. EXTRACT Photos.sqlite (+ -wal/-shm if present)")
        photo_dir = manifest_dir / "photos"
        photo_dir.mkdir()
        extracted: list[Path] = []
        for suffix in ("", "-wal", "-shm"):
            rel = PHOTO_DB + suffix
            hit = conn.execute(
                "SELECT 1 FROM Files WHERE domain='CameraRollDomain' AND relativePath=? AND flags=1",
                (rel,),
            ).fetchone()
            if not hit:
                continue
            out = photo_dir / f"Photos.sqlite{suffix}"
            backup.extract_file(relative_path=rel, domain_like="CameraRollDomain", output_filename=str(out))
            extracted.append(out)
            print(f"  extracted {rel} -> {out.name} ({out.stat().st_size:,} bytes)")
    finally:
        conn.close()

    db_path = photo_dir / "Photos.sqlite"
    photos = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        names = table_names(photos)
        print(f"\n  Photos.sqlite tables: {len(names)}")
        for name in names:
            print(f"    {name}")

        asset_table = "ZASSET" if "ZASSET" in names else "ZGENERICASSET" if "ZGENERICASSET" in names else None
        if asset_table is None:
            print("  NO ASSET TABLE FOUND")
            return 4
        print(f"\n  detected asset table: {asset_table}")
        asset_cols = columns(photos, asset_table)
        print(f"  asset columns ({len(asset_cols)}): {', '.join(asset_cols)}")

        print_heading("4b. PRAGMA table_info for key tables")
        describe_table(photos, asset_table)
        for candidate in ("ZADDITIONALASSETATTRIBUTES", "ZGENERICALBUM", "ZMOMENT"):
            if candidate in names:
                describe_table(photos, candidate)

        join_tables = []
        for name in names:
            if not name.upper().startswith("Z_"):
                continue
            jt_cols = [c.upper() for c in columns(photos, name)]
            if any("ALBUM" in c for c in jt_cols) and any("ASSET" in c for c in jt_cols):
                join_tables.append(name)
        print(f"\n  album<->asset join candidates: {join_tables}")
        for jt in join_tables:
            describe_table(photos, jt)

        print_heading("5. SAMPLE ASSET ROWS")
        wanted = [
            "Z_PK",
            "ZDIRECTORY",
            "ZFILENAME",
            "ZKIND",
            "ZKINDSUBTYPE",
            "ZDATECREATED",
            "ZFAVORITE",
            "ZHIDDEN",
            "ZTRASHEDSTATE",
            "ZPLAYBACKSTYLE",
            "ZSAVEDASSETTYPE",
            "ZDEPTHTYPE",
            "ZISDETECTEDSCREENSHOT",
            "ZWIDTH",
            "ZHEIGHT",
            "ZDURATION",
            "ZLATITUDE",
            "ZLONGITUDE",
        ]
        select_cols = [c for c in wanted if c in asset_cols]
        rows = photos.execute(f"SELECT {', '.join(select_cols)} FROM {asset_table} LIMIT 5").fetchall()
        print("  columns: " + ", ".join(select_cols))
        for row in rows:
            print("  " + " | ".join(f"{c}={fmt(v)}" for c, v in zip(select_cols, row, strict=False)))

        print_heading("6. DISTINCT VALUE COUNTS")
        for col in (
            "ZKIND",
            "ZKINDSUBTYPE",
            "ZPLAYBACKSTYLE",
            "ZSAVEDASSETTYPE",
            "ZDEPTHTYPE",
            "ZTRASHEDSTATE",
            "ZHIDDEN",
            "ZFAVORITE",
            "ZISDETECTEDSCREENSHOT",
        ):
            if col not in asset_cols:
                print(f"  {col}: MISSING")
                continue
            values = photos.execute(
                f"SELECT {col}, count(*) FROM {asset_table} GROUP BY {col} ORDER BY 2 DESC"
            ).fetchall()
            shown = ", ".join(f"{fmt(v)}={n}" for v, n in values[:20])
            print(f"  {col}: {shown}")

        print_heading("7. CANDIDATE CATEGORY COUNTS")
        total = photos.execute(f"SELECT count(*) FROM {asset_table}").fetchone()[0]
        print(f"  total {asset_table} rows: {total}")

        def scalar(where: str) -> int:
            return photos.execute(f"SELECT count(*) FROM {asset_table} WHERE {where}").fetchone()[0]

        def cond(parts: list[str]) -> str:
            return " AND ".join(parts) if parts else "1=1"

        not_trashed = ["(ZTRASHEDSTATE IS NULL OR ZTRASHEDSTATE=0)"]
        untrashed = cond(not_trashed)
        photo_cond = ["ZKIND=0"]
        video_cond = ["ZKIND=1"]
        print(f"  All (every row)                    : {total}")
        print(f"  All excluding trashed              : {scalar(untrashed)}")
        print(f"  Photos (ZKIND=0, excl trashed)      : {scalar(cond(photo_cond + not_trashed))}")
        print(f"  Videos (ZKIND=1, excl trashed)      : {scalar(cond(video_cond + not_trashed))}")
        print(f"  Photos (ZKIND=0, all)              : {scalar(cond(photo_cond))}")
        print(f"  Videos (ZKIND=1, all)              : {scalar(cond(video_cond))}")
        dcim = ["ZDIRECTORY LIKE 'DCIM%'"]
        print(f"  DCIM directory, excl trashed       : {scalar(cond(dcim + not_trashed))}")
        print(f"  DCIM directory, all                : {scalar(cond(dcim))}")
        if "ZSAVEDASSETTYPE" in asset_cols:
            print(f"  ZSAVEDASSETTYPE=0, excl trashed    : {scalar(cond(['ZSAVEDASSETTYPE=0'] + not_trashed))}")
        if "ZCLOUDLOCALSTATE" in asset_cols:
            print(f"  ZCLOUDLOCALSTATE=0, excl trashed   : {scalar(cond(['ZCLOUDLOCALSTATE=0'] + not_trashed))}")
        if "ZTRASHEDDATE" in asset_cols:
            print(f"  has ZTRASHEDDATE, excl trashed     : {scalar(cond(['ZTRASHEDDATE IS NOT NULL'] + not_trashed))}")

        subtype_map = {
            "Favorites": "ZFAVORITE=1",
            "Live (KINDSUBTYPE=2)": "ZKINDSUBTYPE=2",
            "Live (PLAYBACKSTYLE=1)": "ZPLAYBACKSTYLE=1",
            "Portrait (KINDSUBTYPE=3)": "ZKINDSUBTYPE=3",
            "Portrait (DEPTHTYPE=2)": "ZDEPTHTYPE=2",
            "Panorama (KINDSUBTYPE=1)": "ZKINDSUBTYPE=1",
            "Slo-mo (KINDSUBTYPE=101)": "ZKINDSUBTYPE=101",
            "Time-lapse (KINDSUBTYPE=102)": "ZKINDSUBTYPE=102",
            "Timelapse (KINDSUBTYPE=100)": "ZKINDSUBTYPE=100",
            "Screenshot (ISDETECTEDSCREENSHOT=1)": "ZISDETECTEDSCREENSHOT=1",
            "Screenshot (KINDSUBTYPE=10)": "ZKINDSUBTYPE=10",
            "Hidden=1": "ZHIDDEN=1",
            "Trashed state>0": "ZTRASHEDSTATE>0",
        }
        for label, where in subtype_map.items():
            for mode, extra in (("all", []), ("excl trashed", not_trashed)):
                try:
                    value = scalar(cond([where] + extra))
                except sqlite3.Error:
                    value = "MISSING"
                print(f"  {label:<42} [{mode:<11}] : {value}")

        print_heading("7b. ALBUMS")
        album_table = "ZGENERICALBUM" if "ZGENERICALBUM" in names else None
        if album_table:
            album_cols = columns(photos, album_table)
            title_col = "ZTITLE" if "ZTITLE" in album_cols else None
            kind_col = "ZKIND" if "ZKIND" in album_cols else None
            select = ["Z_PK"] + ([title_col] if title_col else []) + ([kind_col] if kind_col else [])
            join_pair = None
            for jt in join_tables:
                jt_cols = columns(photos, jt)
                album_fk = next((c for c in jt_cols if "ALBUM" in c.upper()), None)
                asset_fk = next((c for c in jt_cols if "ASSET" in c.upper()), None)
                if album_fk and asset_fk:
                    join_pair = (jt, album_fk, asset_fk)
                    break
            print(f"  join table: {join_pair}")
            for pk, title, kind in photos.execute(
                f"SELECT {', '.join(select)} FROM {album_table} WHERE {kind_col}=2 "
                f"ORDER BY {title_col or 'Z_PK'}"
            ).fetchall():
                count = None
                if join_pair:
                    jt, album_fk, asset_fk = join_pair
                    count = photos.execute(
                        f'SELECT count(*) FROM "{jt}" j JOIN {asset_table} a ON a.Z_PK=j."{asset_fk}" '
                        f'WHERE j."{album_fk}"=? AND a.ZTRASHEDSTATE=0',
                        (pk,),
                    ).fetchone()[0]
                print(f"  pk={pk:<5} title={title!r:<28} kind={kind!r:<6} count={count}")
        else:
            print("  ZGENERICALBUM missing")

        print_heading("7e. THUMBNAIL AND PAIRING COVERAGE")
        manifest_conn = sqlite3.connect(f"file:{manifest_path.as_posix()}?mode=ro", uri=True)
        try:
            cam_files = {
                r[0]: r[1]
                for r in manifest_conn.execute(
                    "SELECT relativePath, fileID FROM Files "
                    "WHERE domain='CameraRollDomain' AND flags=1"
                )
            }
        finally:
            manifest_conn.close()
        assets = photos.execute(f"SELECT Z_PK, ZDIRECTORY, ZFILENAME, ZKINDSUBTYPE, ZHASADJUSTMENTS FROM {asset_table}").fetchall()
        resolved = sum(1 for _pk, d, f, _ks, _ha in assets if f"Media/{d}/{f}" in cam_files)
        thumbed = sum(
            1 for _pk, d, f, _ks, _ha in assets if f"Media/PhotoData/Thumbnails/V2/{d}/{f}/5005.JPG" in cam_files
        )
        live_paired = 0
        for _pk, d, f, ks, _ha in assets:
            if ks != 2:
                continue
            base = f.rsplit(".", 1)[0]
            if f"Media/{d}/{base}.MOV" in cam_files:
                live_paired += 1
        adjusted = [f for _pk, _d, f, _ks, ha in assets if ha]
        aae = sum(1 for _pk, d, f, _ks, ha in assets if ha and f"Media/{d}/{f.rsplit('.', 1)[0]}.AAE" in cam_files)
        print(f"  assets with a manifest original : {resolved}/{len(assets)}")
        print(f"  assets with a V2 5005.JPG thumb  : {thumbed}/{len(assets)}")
        print(f"  live stills with same-name .MOV   : {live_paired}/{sum(1 for a in assets if a[3] == 2)}")
        print(f"  adjusted assets                   : {len(adjusted)} (with .AAE sidecar: {aae})")

        print_heading("7c. ZMOMENT")
        if "ZMOMENT" in names:
            moment_cols = columns(photos, "ZMOMENT")
            interesting = [c for c in ("Z_PK", "ZTITLE", "ZSUBTITLE", "ZSTARTDATE", "ZENDDATE") if c in moment_cols]
            print(f"  columns: {', '.join(moment_cols[:40])}")
            print(f"  rows: {photos.execute('SELECT count(*) FROM ZMOMENT').fetchone()[0]}")
            for row in photos.execute(
                f"SELECT {', '.join(interesting)} FROM ZMOMENT LIMIT 10"
            ):
                print("   " + " | ".join(fmt(v) for v in row))
        else:
            print("  ZMOMENT missing")

        print_heading("7d. SCHEMA VERSION")
        for key in ("schema_version",):
            try:
                print(f"  PRAGMA {key}: {photos.execute(f'PRAGMA {key}').fetchone()}")
            except sqlite3.Error as exc:
                print(f"  PRAGMA {key}: {exc}")
        if "Z_METADATA" in names:
            for row in photos.execute("SELECT Z_VERSION, Z_UUID FROM Z_METADATA"):
                print(f"  CoreData metadata: version={row[0]} uuid={row[1]}")
    finally:
        photos.close()

    print_heading("DONE")
    print(f"  temporary artefacts left in: {manifest_dir}")
    print("  (delete this folder yourself; it contains decrypted data)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
