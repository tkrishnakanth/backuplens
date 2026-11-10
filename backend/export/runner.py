"""Export job runner with progress, cooperative cancel and a text report."""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

from backend.backup import Session

from .models import ExportOptions, ExportPlan
from .writer import write_item


def _write_report(
    destination: Path,
    plan: ExportPlan,
    *,
    exported: int,
    skipped: int,
    failed: int,
    errors: list[str],
    cancelled: bool,
) -> None:
    lines = [
        "BackupLens export report",
        f"Date: {dt.datetime.now().isoformat(timespec='seconds')}",
        f"Destination: {destination}",
        f"Requested: {len(plan.items)}",
        f"Exported: {exported}",
        f"Skipped (existing): {skipped}",
        f"Failed: {failed}",
        f"Cancelled: {'yes' if cancelled else 'no'}",
    ]
    if errors:
        lines.append("")
        lines.append("Errors:")
        lines.extend(f"- {error}" for error in errors[:500])
    part = destination / "export-report.part"
    try:
        part.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(part, destination / "export-report.txt")
    except OSError:
        part.unlink(missing_ok=True)


def run_export(job, plan: ExportPlan, destination: Path, options: ExportOptions, session: Session) -> None:
    """Job body. Per-file errors are collected; the job keeps going until cancelled."""
    exported = skipped = failed = 0
    errors: list[str] = []
    for index, item in enumerate(plan.items):
        if job.cancelled:
            break
        job.current_file = item.filename
        try:
            result = write_item(session, item, destination, options)
        except Exception as exc:  # noqa: BLE001 - one bad file must not stop the export
            failed += 1
            message = f"{item.filename}: {type(exc).__name__}: {exc}"
            errors.append(message[:500])
            job.errors = errors
        else:
            if result is None:
                skipped += 1
            else:
                exported += 1
                job.bytes_done += max(0, item.size)
        job.done = index + 1
        if job.done % 25 == 0:
            job.errors = errors
    job.current_file = None
    job.errors = errors
    _write_report(
        destination,
        plan,
        exported=exported,
        skipped=skipped,
        failed=failed,
        errors=errors,
        cancelled=job.cancelled,
    )
    job.message = (
        f"{exported} exported, {skipped} skipped, {failed} failed"
        + (" (cancelled)" if job.cancelled else "")
    )
