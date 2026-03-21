# backend/routers/download.py

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from services.job_store import get_job, job_exists

router = APIRouter(tags=["Download"])


@router.get("/download/{job_id}/{file_number}", summary="Download Excel report")
def download_file(job_id: str, file_number: int):
    """
    Serves the Excel workbook for the given job.
    file_number 1 → esg_cross_company.xlsx
    file_number 2 → esg_per_company.xlsx

    Security: validates job_id exists in store and file path is on disk.
    Never serves arbitrary file paths.
    """
    if not job_exists(job_id):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    if file_number not in (1, 2):
        raise HTTPException(status_code=400, detail="file_number must be 1 or 2.")

    job = get_job(job_id)

    if job["status"] != "done":
        raise HTTPException(status_code=400, detail="Analysis not yet complete.")

    key       = "file1" if file_number == 1 else "file2"
    file_path = job.get(key)

    if file_path is None:
        raise HTTPException(status_code=404, detail=f"File {file_number} not available for this job.")

    file_path = Path(file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found on disk: {file_path.name}")

    filename = "esg_cross_company.xlsx" if file_number == 1 else "esg_per_company.xlsx"

    return FileResponse(
        path=str(file_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
