# backend/services/job_store.py
# Shared in-memory job store.
# Imported by routers (read) and pipeline (write).

from typing import Optional
from pathlib import Path

# ── JOB STORE ─────────────────────────────────────────────────────────────────
# Dict keyed by job_id (UUID string).
# Each entry:
# {
#   "status":       "running" | "done" | "error",
#   "step":         1-6,
#   "progress_pct": 0-100,
#   "log":          str,
#   "results":      dict | None,
#   "file1":        str | None,   # absolute path to esg_cross_company.xlsx
#   "file2":        str | None,   # absolute path to esg_per_company.xlsx
#   "error_msg":    str | None,
# }
_store: dict[str, dict] = {}


def create_job(job_id: str) -> None:
    """Initialise a new job entry."""
    _store[job_id] = {
        "status":       "running",
        "step":         1,
        "progress_pct": 0,
        "log":          "[MCP] Initializing pipeline...",
        "results":      None,
        "file1":        None,
        "file2":        None,
        "error_msg":    None,
    }


def update_job(
    job_id: str,
    step: int,
    progress_pct: int,
    log: str,
    status: str = "running",
) -> None:
    """Update step, progress, log and status for a job."""
    if job_id not in _store:
        return
    _store[job_id].update({
        "step":         step,
        "progress_pct": progress_pct,
        "log":          log,
        "status":       status,
    })


def complete_job(job_id: str, results: dict, file1: Optional[str], file2: Optional[str]) -> None:
    """Mark job as done and store results + file paths."""
    if job_id not in _store:
        return
    _store[job_id].update({
        "status":       "done",
        "step":         6,
        "progress_pct": 100,
        "log":          "[DONE] Analysis complete — results ready",
        "results":      results,
        "file1":        file1,
        "file2":        file2,
    })


def fail_job(job_id: str, error_msg: str) -> None:
    """Mark job as failed with an error message."""
    if job_id not in _store:
        return
    step = _store[job_id].get("step", 1)
    pct  = _store[job_id].get("progress_pct", 0)
    _store[job_id].update({
        "status":       "error",
        "step":         step,
        "progress_pct": pct,
        "log":          f"[ERROR] {error_msg}",
        "error_msg":    error_msg,
    })


def get_job(job_id: str) -> Optional[dict]:
    """Return job dict or None if not found."""
    return _store.get(job_id)


def job_exists(job_id: str) -> bool:
    return job_id in _store
