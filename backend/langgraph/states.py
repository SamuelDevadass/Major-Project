# backend/langgraph/states.py
from typing import Optional, Dict, Any
from services.job_store import create_job, update_job, complete_job, fail_job
from services.company_service import get_valid_tickers, get_companies_list

class PipelineState:
    """
    Central state object for LangGraph pipeline.
    Tracks job progress, intermediate agent results, and final outputs.
    """
    def __init__(self, job_id: str, input_tickers: list[str], year_range: list[int]):
        self.job_id = job_id
        self.year_range = year_range

        # Validate tickers
        valid = get_valid_tickers()
        self.companies = [t for t in input_tickers if t in valid]
        self.companies_list = get_companies_list()

        # Intermediate results per agent
        self.agent_results: Dict[str, Any] = {
            "agent1": {},
            "agent2": {},
            "agent3": {},
            "agent4": {},
            "agent5": {},
        }

        # Job store initialization
        create_job(job_id)

    # ── Job store helpers ──────────────────────────────
    def update_job(self, step: int, progress_pct: int, log: str, status: str = "running"):
        update_job(self.job_id, step, progress_pct, log, status)

    def complete_job(self, results: dict, file1: Optional[str], file2: Optional[str]):
        complete_job(self.job_id, results, file1, file2)

    def fail_job(self, error_msg: str):
        fail_job(self.job_id, error_msg)