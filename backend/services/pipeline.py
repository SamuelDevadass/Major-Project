# Pipeline orchestrator — calls Agents 1-5 sequentially.
# Uses company_name strings as keys throughout (not tickers).
# Updates job_store after each step for frontend polling.

import asyncio
from services.job_store import update_job, complete_job, fail_job

STEP_PROGRESS = {
    1: 10,
    2: 25,
    3: 45,
    4: 62,
    5: 80,
    6: 93,
}


async def run_pipeline(job_id: str, companies: list[str], year_range: list[int]) -> None:
    """
    Main pipeline entry point — called as FastAPI background task.
    companies: list of company_name strings (uppercase with _)
    year_range: [2022, 2023, 2024]
    """
    try:
        ## STEP 1: Init 
        update_job(job_id, 1, STEP_PROGRESS[1], "[MCP] Orchestrator initialized — session started")
        await asyncio.sleep(0)
        print("="*75)
        print("INITIALIZING ALL AGENTS")

        ## STEP 2: Agent 1 — Data Retrieval 
        update_job(job_id, 2, STEP_PROGRESS[2],
                   f"[AGENT 1] Loading CRISIL ESG data for {len(companies)} companies")
        await asyncio.sleep(0)
        print("="*75)
        print("INITIALIZING AGENT 1: DATA RETRIEVAL AGENT")

        from agents.agent1_data_retrieval import DataRetrievalAgent
        agent1_result = await asyncio.to_thread(
            DataRetrievalAgent().run, companies, year_range
        )
        print("="*75)
        print(f"AGENT 1 EXECUTION COMPLETED\nDATA FETCHED FOR {len(companies)} COMPANIES SUCCESSFULLY")

        #  STEP 3: Agent 2 — Live News RAG 
        update_job(job_id, 3, STEP_PROGRESS[3],
                   f"[AGT2] Fetching live news + building FAISS index — {len(companies)} companies")
        await asyncio.sleep(0)
        print("="*75)
        print(f"INITIALIZING AGENT 2: NEWS RAG AGENT")

        from agents.agent2_news_rag import NewsRAGAgent
        agent2_result = await asyncio.to_thread(
            NewsRAGAgent().run, companies, agent1_result)
        print("="*75)
        print(f"AGENT 2 EXECUTION COMPLETED SUCCESSLY")

        # ── STEP 4: Agent 3 — LOWESS + Validation ────────────────────────────
        update_job(job_id, 4, STEP_PROGRESS[4],
                   "[AGT3] LOWESS smoothing + adaptive forward validation")
        await asyncio.sleep(0)

        from agents.agent3_validation import ValidationAgent
        agent3_result = await asyncio.to_thread(
            ValidationAgent().run, agent1_result)

        # ── STEP 5: Agent 4 — LLM Analysis ───────────────────────────────────
        update_job(job_id, 5, STEP_PROGRESS[5],
                   f"[AGT4] Groq LLaMA3-70B — {len(companies) * 3 + 1} calls")
        await asyncio.sleep(0)

        from agents.agent4_llm import LLMAgent
        agent4_result = await asyncio.to_thread(
            LLMAgent().run, companies, agent1_result, agent2_result, agent3_result)

        # ── STEP 6: Agent 5 — Excel + Charts ─────────────────────────────────
        update_job(job_id, 6, STEP_PROGRESS[6],
                   "[AGT5] Generating Excel workbooks + matplotlib charts")
        await asyncio.sleep(0)

        from agents.agent5_excel import ExcelAgent
        agent5_result = await asyncio.to_thread(
            ExcelAgent().run, job_id, agent1_result, agent3_result, agent4_result
        )

        # ── ASSEMBLE FINAL RESULTS ────────────────────────────────────────────
        results = _build_results(
            job_id, companies, year_range,
            agent1_result, agent2_result, agent3_result, agent4_result, agent5_result
        )

        complete_job(
            job_id,
            results=results,
            file1=agent5_result.get("file1"),
            file2=agent5_result.get("file2"),
        )

    except Exception as e:
        fail_job(job_id, str(e))
        raise


def _build_results(
    job_id: str,
    companies: list[str],
    year_range: list[int],
    agent1: dict,
    agent2: dict,
    agent3: dict,
    agent4: dict,
    agent5: dict,
) -> dict:
    """Assembles the complete GET /results payload."""
    per_company = {}
    charts      = agent5.get("charts_base64", {})

    for company in companies:
        a1 = agent1.get(company, {})
        a2 = agent2.get(company, {})
        a3 = agent3.get(company, {})
        a4 = agent4.get(company, {})

        per_company[company] = {
            "yearly_scores":    a1.get("yearly_scores",      {}),
            "trend":            a3.get("trend",               {}),
            "validation_table": a3.get("validation_table",   []),
            "news_findings":    a2.get("news_findings",       {}),
            "credibility":      a4.get("credibility",         {}),
            "narrative":        a4.get("narrative",           ""),
            "key_highlights":   a4.get("key_highlights",      []),
            "investor_signal":  a4.get("investor_signal",     "HOLD"),
            "chart_base64":     charts.get(company),          # from agent5
            "kaggle_meta":      a1.get("kaggle_meta",         {}),
            "data_quality":     a1.get("data_quality_flags",  {}),
        }

    return {
        "job_id":      job_id,
        "companies":   companies,
        "year_range":  year_range,
        "per_company": per_company,
        "verdict":     agent4.get("verdict", {}),
        "file_paths": {
            "file1": agent5.get("file1"),
            "file2": agent5.get("file2"),
        },
    }