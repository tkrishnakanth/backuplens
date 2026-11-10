"""Raw-file export job (preserves domain/relative paths)."""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

from backend.backup import Session
from backend.export.paths import prepare_destination, resolve_conflict, safe_join, sanitize_component


def _relative_for(record) -> Path:
    parts = [sanitize_component(part) for part in Path(record.relative_path).parts if part not in ("", ".", "..")]
    return Path(sanitize_component(record.domain)) / Path(*parts)


def run_raw_export(job, file_ids: list[str], destination: Path, session: Session, on_conflict: str = "rename") -> None:
    exported = skipped = failed = 0
    errors: list[str] = []
    for index, file_id in enumerate(file_ids):
        if job.cancelled:
            break
        job.current_file = file_id
        part = None
        try:
            record = session.file_record(file_id)
            final = safe_join(destination, _relative_for(record))
            final.parent.mkdir(parents=True, exist_ok=True)
            resolved = resolve_conflict(final, on_conflict)
            if resolved is None:
                skipped += 1
            else:
                part = Path(str(resolved) + ".part")
                session.extract_file(record.file_id, part)
                os.replace(part, resolved)
                if record.mtime:
                    os.utime(resolved, times=(record.mtime, record.mtime))
                exported += 1
                job.bytes_done += max(0, int(record.size or 0))
        except Exception as exc:  # noqa: BLE001 - collect and continue
            failed += 1
            errors.append(f"{file_id}: {type(exc).__name__}: {exc}"[:500])
            if part is not None:
                part.unlink(missing_ok=True)
        job.done = index + 1
        job.errors = errors
    job.current_file = None
    job.errors = errors
    lines = [
        "BackupLens raw file export",
        f"Date: {dt.datetime.now().isoformat(timespec='seconds')}",
        f"Destination: {destination}",
        f"Requested: {len(file_ids)}",
        f"Exported: {exported}",
        f"Skipped: {skipped}",
        f"Failed: {failed}",
        f"Cancelled: {'yes' if job.cancelled else 'no'}",
    ]
    if errors:
        lines.extend(["", "Errors:", *[f"- {error}" for error in errors[:500]]])
    try:
        report_part = destination / "raw-export-report.part"
        report_part.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(report_part, destination / "raw-export-report.txt")
    except OSError:
        pass
    job.message = f"{exported} exported, {skipped} skipped, {failed} failed"


__all__ = ["prepare_destination", "run_raw_export"]
