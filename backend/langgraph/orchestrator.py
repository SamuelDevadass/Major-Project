# backend/langgraph/orchestrator.py
import asyncio
from langgraph.states import PipelineState

STEP_PROGRESS = {
    1: 10,
    2: 25,
    3: 45,
    4: 62,
    5: 80,
    6: 93,
}

async def run_pipeline(job_id: str, input_tickers: list[str], year_range: list[int]):
    """
    LangGraph-ready orchestrator. Sequential execution of all agents.
    """
    state = PipelineState(job_id, input_tickers, year_range)
    
    try:
        # ── STEP 1: Initialize ──────────────────────
        state.update_job(1, STEP_PROGRESS[1], "[MCP] Orchestrator initialized — session started")
        await asyncio.sleep(0)

        # ── STEP 2: Agent 1 ─────────────────────────
        from agents.agent1_data_retrieval import DataRetrievalAgent
        state.update_job(2, STEP_PROGRESS[2],
                         f"[AGENT 1] Loading CRISIL ESG data for {len(state.companies)} companies")
        agent1_result = await asyncio.to_thread(DataRetrievalAgent().run, state.companies, state.year_range)
        state.agent_results["agent1"] = agent1_result

        # ── STEP 3: Agent 2 ─────────────────────────
        from agents.agent2_news_rag import NewsRAGAgent
        state.update_job(3, STEP_PROGRESS[3],
                         f"[AGENT 2] Fetching live news + building FAISS index for {len(state.companies)} companies")
        agent2_result = await asyncio.to_thread(NewsRAGAgent().run, state.companies, agent1_result)
        state.agent_results["agent2"] = agent2_result

        # ── STEP 4: Agent 3 ─────────────────────────
        from agents.agent3_validation import ValidationAgent
        state.update_job(4, STEP_PROGRESS[4], "[AGENT 3] LOWESS smoothing + validation")
        agent3_result = await asyncio.to_thread(ValidationAgent().run, agent1_result)
        state.agent_results["agent3"] = agent3_result

        # ── STEP 5: Agent 4 ─────────────────────────
        from agents.agent4_llm import LLMAgent
        state.update_job(5, STEP_PROGRESS[5], f"[AGENT 4] LLM Analysis for {len(state.companies)*3+1} calls")
        agent4_result = await asyncio.to_thread(LLMAgent().run, state.companies, agent1_result, agent2_result, agent3_result)
        state.agent_results["agent4"] = agent4_result

        # ── STEP 6: Agent 5 ─────────────────────────
        from agents.agent5_excel import ExcelAgent
        state.update_job(6, STEP_PROGRESS[6], "[AGENT 5] Generating Excel workbooks + charts")
        agent5_result = await asyncio.to_thread(ExcelAgent().run, job_id, agent1_result, agent3_result, agent4_result)
        state.agent_results["agent5"] = agent5_result

        # ── Assemble final results ──────────────────
        results = _build_results(state)
        state.complete_job(results, agent5_result.get("file1"), agent5_result.get("file2"))

    except Exception as e:
        state.fail_job(str(e))
        raise

def _build_results(state: PipelineState) -> dict:
    """Assembles the complete GET /results payload."""
    companies = state.companies
    agent1 = state.agent_results["agent1"]
    agent2 = state.agent_results["agent2"]
    agent3 = state.agent_results["agent3"]
    agent4 = state.agent_results["agent4"]
    agent5 = state.agent_results["agent5"]
    charts = agent5.get("charts_base64", {})

    per_company = {}
    for company in companies:
        per_company[company] = {
            "yearly_scores":    agent1.get(company, {}).get("yearly_scores", {}),
            "trend":            agent3.get(company, {}).get("trend", {}),
            "validation_table": agent3.get(company, {}).get("validation_table", []),
            "news_findings":    agent2.get(company, {}).get("news_findings", {}),
            "credibility":      agent4.get(company, {}).get("credibility", {}),
            "narrative":        agent4.get(company, {}).get("narrative", ""),
            "key_highlights":   agent4.get(company, {}).get("key_highlights", []),
            "investor_signal":  agent4.get(company, {}).get("investor_signal", "HOLD"),
            "chart_base64":     charts.get(company),
            "kaggle_meta":      agent1.get(company, {}).get("kaggle_meta", {}),
            "data_quality":     agent1.get(company, {}).get("data_quality_flags", {}),
        }

    return {
        "job_id":      state.job_id,
        "companies":   companies,
        "year_range":  state.year_range,
        "per_company": per_company,
        "verdict":     agent4.get("verdict", {}),
        "file_paths": {
            "file1": agent5.get("file1"),
            "file2": agent5.get("file2"),
        },
    }