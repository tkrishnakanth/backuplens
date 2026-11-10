"""Read-only raw file explorer over Manifest.db."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from backend.backup import Session
from backend.media.cache import MediaCache
from backend.media.pipeline import mimetype_for


class FileBrowseError(ValueError):
    pass


@dataclass(slots=True)
class RawFile:
    path: Path
    filename: str
    mimetype: str


def escape_like(value: str) -> str:
    """Escape LIKE metacharacters for an exact-prefix query."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_domains(session: Session) -> list[dict[str, object]]:
    rows = session.manifest_query(
        "SELECT domain, count(*) AS n FROM Files WHERE flags=1 GROUP BY domain ORDER BY lower(domain)"
    )
    return [{"domain": str(row["domain"]), "count": int(row["n"])} for row in rows]


def _parse_file_rows(session: Session, file_ids: list[str]) -> dict[str, tuple[int, float | None, str | None]]:
    from iphone_backup_decrypt.utils import FilePlist

    parsed: dict[str, tuple[int, float | None, str | None]] = {}
    for start in range(0, len(file_ids), 400):
        chunk = file_ids[start : start + 400]
        placeholders = ",".join("?" for _ in chunk)
        rows = session.manifest_query(
            f"SELECT fileID, file FROM Files WHERE fileID IN ({placeholders})", chunk
        )
        for row in rows:
            blob = row.get("file")
            if not blob:
                continue
            try:
                info = FilePlist(blob)
                parsed[str(row["fileID"])] = (int(info.filesize), info.mtime, info.target)
            except Exception:  # noqa: BLE001 - one malformed row must not break the browser
                continue
    return parsed


def tree(session: Session, domain: str, path: str = "") -> dict[str, object]:
    if not domain:
        raise FileBrowseError("domain is required")
    prefix = str(path or "").strip("/")
    if ".." in Path(prefix).parts:
        raise FileBrowseError("Unsafe path")
    prefix_search = f"{prefix}/" if prefix else ""
    rows = session.manifest_query(
        "SELECT fileID, relativePath, flags FROM Files "
        "WHERE domain=? AND relativePath LIKE ? ESCAPE '\\' AND flags IN (1,2,4) "
        "ORDER BY relativePath",
        (domain, escape_like(prefix_search) + "%"),
    )
    entries: dict[str, dict[str, object]] = {}
    for row in rows:
        relative = str(row["relativePath"])
        if prefix_search and not relative.startswith(prefix_search):
            continue
        rest = relative[len(prefix_search) :]
        if not rest:
            continue
        name, separator, _tail = rest.partition("/")
        flags = int(row["flags"])
        is_dir = bool(separator) or flags == 2
        entry = entries.get(name)
        if is_dir:
            if entry is None or entry.get("type") != "dir":
                entry = {"name": name, "path": f"{prefix_search}{name}", "type": "dir", "count": 0}
                entries[name] = entry
            if separator:
                current = entry.get("count")
                entry["count"] = (int(current) if isinstance(current, int) else 0) + 1
        else:
            entry = {
                "name": name,
                "path": relative,
                "type": "symlink" if flags == 4 else "file",
                "fileId": str(row["fileID"]),
                "size": 0,
                "mtime": None,
                "target": None,
            }
            entries[name] = entry

    file_entries = [entry for entry in entries.values() if entry["type"] != "dir"]
    parsed = _parse_file_rows(session, [str(entry["fileId"]) for entry in file_entries])
    for entry in file_entries:
        size, mtime, target = parsed.get(str(entry["fileId"]), (0, None, None))
        entry["size"] = size
        entry["mtime"] = mtime
        if target:
            entry["target"] = target

    ordered = sorted(
        entries.values(),
        key=lambda entry: (0 if entry["type"] == "dir" else 1, str(entry["name"]).casefold()),
    )
    return {"domain": domain, "path": prefix, "entries": ordered}


def _row_item(session: Session, row: dict, parsed: dict[str, tuple[int, float | None, str | None]]) -> dict:
    from iphone_backup_decrypt.utils import FilePlist

    file_id = str(row["fileID"])
    size, mtime = 0, None
    if file_id not in parsed:
        blob = row.get("file")
        if blob:
            try:
                info = FilePlist(blob)
                size, mtime = int(info.filesize), info.mtime
            except Exception:  # noqa: BLE001
                size, mtime = 0, None
            parsed[file_id] = (size, mtime, None)
    else:
        size, mtime, _target = parsed[file_id]
    return {
        "fileId": file_id,
        "domain": str(row["domain"]),
        "path": str(row["relativePath"]),
        "name": Path(str(row["relativePath"])).name,
        "size": size,
        "mtime": mtime,
        "flags": int(row["flags"]),
    }


def search(
    session: Session,
    *,
    domain: str = "",
    path: str = "",
    sort: str = "path",
    direction: str = "asc",
    limit: int = 200,
    offset: int = 0,
) -> dict[str, object]:
    domain_pattern = domain or "%"
    path_pattern = path or "%"
    where = (
        "flags=1 AND domain LIKE ? ESCAPE '\\' AND relativePath LIKE ? ESCAPE '\\'"
    )
    params = (domain_pattern, path_pattern)
    total = int(session.manifest_scalar(f"SELECT count(*) FROM Files WHERE {where}", params) or 0)

    sort = sort if sort in ("path", "name", "domain", "size", "date") else "path"
    direction = "DESC" if direction.lower() == "desc" else "ASC"
    limit = max(1, min(5000, int(limit)))
    offset = max(0, int(offset))

    if sort in ("path", "domain"):
        column = "relativePath" if sort == "path" else "domain"
        rows = session.manifest_query(
            f"SELECT fileID, domain, relativePath, flags, file FROM Files WHERE {where} "
            f"ORDER BY lower({column}) {direction} LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )
        parsed: dict[str, tuple[int, float | None, str | None]] = {}
        paged = [_row_item(session, row, parsed) for row in rows]
        return {"items": paged, "total": total, "limit": limit, "offset": offset}

    # name/size/date need values from the file plist (or basename); scan matches.
    scanned: list[dict] = []
    parsed = {}
    for row in session.iter_manifest(
        f"SELECT fileID, domain, relativePath, flags, file FROM Files WHERE {where}", params
    ):
        scanned.append(_row_item(session, row, parsed))
    if sort == "name":
        scanned.sort(key=lambda item: str(item["name"]).lower(), reverse=direction == "DESC")
    elif sort == "size":
        scanned.sort(key=lambda item: int(item["size"] or 0), reverse=direction == "DESC")
    else:
        scanned.sort(key=lambda item: float(item["mtime"] or 0), reverse=direction == "DESC")
    return {"items": scanned[offset : offset + limit], "total": total, "limit": limit, "offset": offset}


def raw_file(session: Session, cache: MediaCache, file_id: str) -> RawFile:
    record = session.file_record(file_id)
    suffix = Path(record.relative_path).suffix.lower()
    filename = Path(record.relative_path).name
    mimetype = mimetype_for(record.relative_path)
    if not session.is_encrypted and record.backup_path and record.backup_path.is_file():
        return RawFile(path=record.backup_path, filename=filename, mimetype=mimetype)
    if record.backup_path is None or not record.backup_path.is_file():
        from backend.backup import PayloadMissing

        raise PayloadMissing("The file is missing from the backup payload")
    namespace = session.info.udid or session.backup_dir.name
    dest = cache.path(namespace, "raw", record.file_id, suffix)
    if not dest.exists():
        session.extract_file(record.file_id, dest)
        cache.note_write()
    return RawFile(path=dest, filename=filename, mimetype=mimetype)


def ids_matching(
    session: Session,
    *,
    domain: str = "",
    path: str = "",
) -> list[str]:
    domain_pattern = domain or "%"
    path_pattern = path or "%"
    rows = session.manifest_query(
        "SELECT fileID FROM Files WHERE flags=1 "
        "AND domain LIKE ? ESCAPE '\\' AND relativePath LIKE ? ESCAPE '\\'",
        (domain_pattern, path_pattern),
    )
    return [str(row["fileID"]) for row in rows]


_FILE_ID = re.compile(r"[0-9a-fA-F]{40}")


def is_file_id(value: str) -> bool:
    return bool(_FILE_ID.fullmatch(value))
