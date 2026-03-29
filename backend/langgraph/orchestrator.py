import asyncio
from langgraph.graph import StateGraph, END
from langgraph.states import PipelineState, AgentState

STEP_PROGRESS = {1: 10, 2: 25, 3: 45, 4: 62, 5: 80, 6: 93}

# ── NODES: Functional Wrappers for Agents ───────────────────

async def agent1_retrieval(state: AgentState):
    from agents.agent1_data_retrieval import DataRetrievalAgent
    # We use a temp PipelineState instance just for the update_job helper
    helper = PipelineState(state["job_id"], state["input_tickers"], state["year_range"])
    helper.update_job(2, STEP_PROGRESS[2], f"[AGENT 1] Loading CRISIL data for {len(state['companies'])} companies")
    
    result = await asyncio.to_thread(DataRetrievalAgent().run, state["companies"], state["year_range"])
    return {"agent_results": {"agent1": result}}

async def agent2_news(state: AgentState):
    from agents.agent2_news_rag import NewsRAGAgent
    helper = PipelineState(state["job_id"], state["input_tickers"], state["year_range"])
    helper.update_job(3, STEP_PROGRESS[3], "[AGENT 2] Fetching live news + FAISS indexing")
    
    a1_res = state["agent_results"].get("agent1", {})
    result = await asyncio.to_thread(NewsRAGAgent().run, state["companies"], a1_res)
    return {"agent_results": {"agent2": result}}

async def agent3_validation(state: AgentState):
    from agents.agent3_validation import ValidationAgent
    helper = PipelineState(state["job_id"], state["input_tickers"], state["year_range"])
    helper.update_job(4, STEP_PROGRESS[4], "[AGENT 3] LOWESS smoothing + validation")
    
    a1_res = state["agent_results"].get("agent1", {})
    result = await asyncio.to_thread(ValidationAgent().run, a1_res)
    return {"agent_results": {"agent3": result}}

async def agent4_analysis(state: AgentState):
    from agents.agent4_llm import LLMAgent
    helper = PipelineState(state["job_id"], state["input_tickers"], state["year_range"])
    helper.update_job(5, STEP_PROGRESS[5], "[AGENT 4] Generating LLM Narratives & Synthesis")
    
    results = state["agent_results"]
    result = await asyncio.to_thread(
        LLMAgent().run, state["companies"], results.get("agent1"), results.get("agent2"), results.get("agent3")
    )
    return {"agent_results": {"agent4": result}}

async def agent5_reporting(state: AgentState):
    from agents.agent5_excel import ExcelAgent
    helper = PipelineState(state["job_id"], state["input_tickers"], state["year_range"])
    helper.update_job(6, STEP_PROGRESS[6], "[AGENT 5] Generating Excel workbooks")
    
    results = state["agent_results"]
    result = await asyncio.to_thread(
        ExcelAgent().run, state["job_id"], results.get("agent1"), results.get("agent3"), results.get("agent4")
    )
    return {"agent_results": {"agent5": result}}

# ── ORCHESTRATOR: The Main Entry Point ──────────────────────

async def run_pipeline(job_id: str, input_tickers: list[str], year_range: list[int]):
    """
    LangGraph-native orchestrator.
    This structure generates the visual DAG in LangSmith.
    """
    # 1. Initialize Helper for initial UI log
    init_helper = PipelineState(job_id, input_tickers, year_range)
    init_helper.update_job(1, STEP_PROGRESS[1], "[MCP] Orchestrator started")

    # 2. Build and Compile the Graph
    workflow = StateGraph(AgentState)
    workflow.add_node("agent1", agent1_retrieval)
    workflow.add_node("agent2", agent2_news)
    workflow.add_node("agent3", agent3_validation)
    workflow.add_node("agent4", agent4_analysis)
    workflow.add_node("agent5", agent5_reporting)

    workflow.set_entry_point("agent1")
    workflow.add_edge("agent1", "agent2")
    workflow.add_edge("agent2", "agent3")
    workflow.add_edge("agent3", "agent4")
    workflow.add_edge("agent4", "agent5")
    workflow.add_edge("agent5", END)

    app = workflow.compile()

    # 3. Execute
    initial_state = {
        "job_id": job_id,
        "input_tickers": input_tickers,
        "year_range": year_range,
        "companies": init_helper.companies,
        "agent_results": {},
        "status": "running"
    }

    try:
        final_state = await app.ainvoke(initial_state)
        
        # Assemble results using your existing logic
        results = _build_results_from_dict(final_state)
        a5 = final_state["agent_results"].get("agent5", {})
        init_helper.complete_job(results, a5.get("file1"), a5.get("file2"))
        
    except Exception as e:
        init_helper.fail_job(str(e))
        raise

# ── RESULT BUILDER (Refactored for dictionary state) ────────

def _build_results_from_dict(state: dict) -> dict:
    companies = state["companies"]
    agent1 = state["agent_results"].get("agent1", {})
    agent2 = state["agent_results"].get("agent2", {})
    agent3 = state["agent_results"].get("agent3", {})
    agent4 = state["agent_results"].get("agent4", {})
    agent5 = state["agent_results"].get("agent5", {})
    charts = agent5.get("charts_base64", {})

    per_company = {}
    for company in companies:
        a3_data = agent3.get(company, {})
        val_table = a3_data.get("validation_table", [])
        latest_val = val_table[-1] if val_table else {}
        actual_scores = latest_val.get("actual", {})
        
        if not actual_scores:
            yearly = agent1.get(company, {}).get("yearly_scores", {})
            latest_yr = max(yearly.keys()) if yearly else None
            actual_scores = yearly.get(latest_yr, {})
            
        per_company[company] = {
            "yearly_scores":    actual_scores,
            "trend":            a3_data.get("trend", {}),
            "validation_table": val_table,
            "news_findings":    agent2.get(company, {}).get("news_findings", {}),
            "credibility":      agent4.get(company, {}).get("credibility", {}),
            "narrative":        agent4.get(company, {}).get("narrative", ""),
            "verdict_label":    agent4.get(company, {}).get("credibility", {}).get("credibility_verdict", "Stable"),
            "key_highlights":   agent4.get(company, {}).get("key_highlights", []),
            "investor_signal":  agent4.get(company, {}).get("investor_signal", "HOLD"),
            "chart_base64":     charts.get(company),
            "kaggle_meta":      agent1.get(company, {}).get("kaggle_meta", {}),
            "data_quality":     agent1.get(company, {}).get("data_quality_flags", {}),
        }

    return {
        "job_id":      state["job_id"],
        "companies":   companies,
        "year_range":  state["year_range"],
        "per_company": per_company,
        "verdict":     agent4.get("verdict", {}),
        "file_paths":  {"file1": agent5.get("file1"), "file2": agent5.get("file2")},
    }