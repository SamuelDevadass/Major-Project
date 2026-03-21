# backend/routers/results.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from services.job_store import get_job, job_exists

router = APIRouter(tags=["Results"])


@router.get("/results/{job_id}", summary="Get full analysis results")
def get_results(job_id: str):
    """
    Returns the complete analysis results JSON once the job is done.
    - 404 if job not found
    - 202 if still running
    - 500 if job errored
    - 200 with full results payload if done

    Response: Full payload including per_company data, verdict, chart base64.
    """
    if not job_exists(job_id):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    job = get_job(job_id)

    if job["status"] == "error":
        raise HTTPException(status_code=500, detail=job.get("error_msg", "Pipeline failed."))

    if job["status"] == "running":
        return JSONResponse(status_code=202, content={"status": "running", "job_id": job_id})

    if job["results"] is None:
        raise HTTPException(status_code=500, detail="Job marked done but results are missing.")

    return JSONResponse(content=job["results"])
