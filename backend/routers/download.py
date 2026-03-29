import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(tags=["Download"])

@router.get("/outputs/{job_id}/{filename}", summary="Download Excel report")
async def download_file(job_id: str, filename: str):
    # Get the backend root (one level up from 'routers')
    # This assumes main.py and outputs/ are in the same 'backend' folder
    base_path = Path(__file__).resolve().parent.parent 
    file_path = base_path / "outputs" / job_id / filename
    
    print(f"DEBUG: Agent 5 Location Check: {file_path}")

    if not file_path.exists():
        print(f"ERROR: Agent 5 hasn't created the file yet at: {file_path}")
        raise HTTPException(
            status_code=404, 
            detail=f"File not found. Verify Agent 5 finished for Job: {job_id}"
        )

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )