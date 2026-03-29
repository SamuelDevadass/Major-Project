import uuid
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from services.company_service import get_valid_tickers
from services.job_store import create_job
#from services.pipeline import run_pipeline
from langgraph.orchestrator import run_pipeline

router = APIRouter(tags=["Analysis"])

# CRISIL data: 2022, 2023, 2024, 2025 — only one valid 3-year training window
VALID_YEAR_RANGES = [
    [2022, 2023, 2024],
]


class AnalyzeRequest(BaseModel):
    companies:  list[str]
    year_range: list[int]

    @field_validator("companies")
    @classmethod
    def validate_companies(cls, v):
        if not v:
            raise ValueError("At least one company is required.")
        if len(v) > 5:
            raise ValueError("Maximum 5 companies per analysis run.")
        tickers_upper = [t.upper().strip() for t in v]
        unknown = [t for t in tickers_upper if t not in get_valid_tickers()]
        if unknown:
            raise ValueError(f"Unknown tickers: {unknown}")
        return tickers_upper

    @field_validator("year_range")
    @classmethod
    def validate_year_range(cls, v):
        if v not in VALID_YEAR_RANGES:
            raise ValueError(f"Invalid year range. Must be: {VALID_YEAR_RANGES}")
        return v


@router.post("/analyze", summary="Start an ESG analysis job")
async def start_analysis(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Accepts ticker strings (uppercase_with_underscores) and year range.
    Frontend sends ticker, not company_name.
    """
    job_id = str(uuid.uuid4())
    create_job(job_id)
    background_tasks.add_task(run_pipeline, job_id, request.companies, request.year_range)
    return JSONResponse(content={"job_id": job_id, "status": "started"})