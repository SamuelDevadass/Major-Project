# backend/routers/status.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from services.job_store import get_job, job_exists

router = APIRouter(tags=["Status"])


@router.get("/status/{job_id}", summary="Poll pipeline progress")
def get_status(job_id: str):
    """
    Returns current step, status, progress % and latest log message.
    Frontend polls this every 2 seconds during active processing.
    Reads from in-memory store only — always responds in < 50ms.

    Response: { job_id, step, status, progress_pct, log, error_msg }
    """
    if not job_exists(job_id):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    job = get_job(job_id)
    return JSONResponse(content={
        "job_id":       job_id,
        "step":         job["step"],
        "status":       job["status"],
        "progress_pct": job["progress_pct"],
        "log":          job["log"],
        "error_msg":    job.get("error_msg"),
    })
