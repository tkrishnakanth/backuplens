"""In-memory background job manager (export/indexing jobs use it from Phase 3 onward)."""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field


@dataclass
class Job:
    id: str
    kind: str
    state: str = "queued"  # queued | running | done | failed | cancelled
    total: int = 0
    done: int = 0
    bytes_done: int = 0
    current_file: str | None = None
    message: str | None = None
    errors: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)

    @property
    def cancelled(self) -> bool:
        return self.cancel_event.is_set()

    def to_dict(self) -> dict[str, object]:
        return {
            "jobId": self.id,
            "kind": self.kind,
            "state": self.state,
            "done": self.done,
            "total": self.total,
            "bytes": self.bytes_done,
            "currentFile": self.current_file,
            "message": self.message,
            "errors": list(self.errors[:200]),
            "createdAt": self.created_at,
        }


Runner = Callable[[Job], None]


class JobManager:
    """Threads execute jobs; progress lives on the :class:`Job` and is polled by the UI."""

    def __init__(self, max_workers: int = 2) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="backuplens-job")
        self._closed = False

    def create(self, kind: str, runner: Runner, *, total: int = 0) -> Job:
        job = Job(id=uuid.uuid4().hex, kind=kind, total=total)
        with self._lock:
            self._jobs[job.id] = job
        self._executor.submit(self._run, job, runner)
        return job

    def _run(self, job: Job, runner: Runner) -> None:
        if job.cancelled:
            job.state = "cancelled"
            return
        job.state = "running"
        try:
            runner(job)
        except Exception as exc:  # noqa: BLE001 - job failures are reported, not raised
            job.state = "failed"
            job.message = f"{type(exc).__name__}: {exc}"
        else:
            job.state = "cancelled" if job.cancelled else "done"
        finally:
            job.current_file = None

    def get(self, job_id: str) -> Job:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        return job

    def cancel(self, job_id: str) -> Job:
        job = self.get(job_id)
        job.cancel_event.set()
        if job.state == "queued":
            job.state = "cancelled"
        return job

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        with self._lock:
            for job in self._jobs.values():
                if job.state in ("queued", "running"):
                    job.cancel_event.set()
        self._executor.shutdown(wait=True, cancel_futures=True)
