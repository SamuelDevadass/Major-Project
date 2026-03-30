# backend/agents/agent4_llm.py
# Agent 4 — Three-Stage LLM Credibility Pipeline
# NOTE: CRISIL scores are 0-100, HIGHER = BETTER ESG performance

import json
import requests
import time
from config.thresholds import CONFIDENCE_COMMENDATORY, CONFIDENCE_BALANCED
from config.prompts import (NEWS_INTELLIGENCE_PROMPT, CREDIBILITY_VALIDATION_PROMPT,
                            NARRATIVE_COMMENDATORY_PROMPT, NARRATIVE_BALANCED_PROMPT,
                            NARRATIVE_CAUTIONARY_PROMPT, SYNTHESIS_VERDICT_PROMPT)
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)

MODEL      = "meta-llama/llama-4-scout-17b-16e-instruct"
TEMP       = 0.3
MAX_TOKENS = 1000
RATE_LIMIT_SLEEP_THRESHOLD = 28


class LLMAgent:
    def __init__(self):
        self.mcp_llm_url = "http://localhost:8001/tools/llm_processor"
        print("✅ AGENT 4: Initialized via MCP LLM Gateway")

    def _call_mcp_llm(self, prompt, ticker):
        try:
            payload = {"prompt": prompt, "ticker": ticker}
            response = requests.post(self.mcp_llm_url, json=payload, timeout=90)
            if response.status_code == 200:
                return response.json(), False
            else:
                print(f"  ⚠️ MCP LLM Error: {response.text}")
                return None, True
        except Exception as e:
            print(f"  ❌ Failed to reach MCP Server: {e}")
            return None, True

    def run(self, companies, agent1_result, agent2_result, agent3_result):
        result = {}
        print(f"\nAGENT 4: Analyzing {len(companies)} companies via MCP Pipeline")

        for ticker in companies:
            a1 = agent1_result.get(ticker, {})
            a2 = agent2_result.get(ticker, {})
            a3 = agent3_result.get(ticker, {})

            if not a1.get("found", False):
                result[ticker] = self._fallback_company(ticker, "not_found")
                continue

            result[ticker] = self._run_company_pipeline(ticker, a1, a2, a3)

        result["verdict"] = self._run_synthesis(companies, result, agent1_result)
        return result

    def _run_company_pipeline(self, ticker, a1, a2, a3):
        meta = a1.get("kaggle_meta", {})
        yearly = a1.get("yearly_scores", {})
        trend = a3.get("trend", {})
        rag = a2.get("rag_chunks", [])
        latest_year = max(yearly.keys()) if yearly else None
        latest_scores = yearly.get(latest_year, {}) if latest_year else {}

        # STAGE 1: News Intelligence
        prompt1 = NEWS_INTELLIGENCE_PROMPT.format(
            company_name=meta.get("company_name", ticker),
            ticker=ticker,
            industry=meta.get("sector", "Unknown"),
            rag_chunks="\n\n---\n\n".join(rag) if rag else "No news available.",
            e_score=latest_scores.get("E", "N/A"),
            s_score=latest_scores.get("S", "N/A"),
            g_score=latest_scores.get("G", "N/A"),
            total_score=latest_scores.get("Total", "N/A"),
        )
        call1, fall1 = self._call_mcp_llm(prompt1, ticker)
        if fall1: return self._fallback_company(ticker, "stage1_fail")

        # STAGE 2: Credibility Validation
        prompt2 = CREDIBILITY_VALIDATION_PROMPT.format(
            company_name=meta.get("company_name", ticker),
            ticker=ticker,
            yearly_scores=self._format_yearly_scores(yearly),
            regression_summary=self._format_regression(trend),
            validation_table=self._format_validation_table(a3.get("validation_table", [])),
            crisil_rating=self._format_crisil_rating(meta),
            positive_findings=call1.get("positive_findings", []),
            negative_findings=call1.get("negative_findings", []),
            governance_flags=call1.get("governance_flags", []),
            overall_news_sentiment=call1.get("overall_news_sentiment", "neutral"),
        )
        call2, fall2 = self._call_mcp_llm(prompt2, ticker)
        if fall2: return self._fallback_company(ticker, "stage2_fail", call1)

        # STAGE 3: Narrative Generation
        confidence = call2.get("confidence_score", 50)
        investor_signal = self._derive_signal(confidence, trend)
        template = self._select_narrative_template(confidence)

        prompt3 = template.format(
            company_name=meta.get("company_name", ticker),
            ticker=ticker,
            confidence_score=confidence,
            esg_summary=self._format_esg_summary(yearly, trend),
            trend_classification=trend.get("trend_classification", "Unknown"),
            positive_findings=call1.get("positive_findings", []),
            negative_findings=call1.get("negative_findings", []),
            governance_flags=call1.get("governance_flags", []),
            washing_risk=call2.get("washing_risk", "medium"),
            investor_signal=investor_signal,
        )
        call3, fall3 = self._call_mcp_llm(prompt3, ticker)
        if fall3: return self._fallback_company(ticker, "stage3_fail", call1, call2)

        return {
            "news_findings": call1,
            "credibility": call2,
            "narrative": call3.get("narrative", ""),
            "key_highlights": call3.get("key_highlights", []),
            "investor_signal": call3.get("investor_signal", investor_signal),
            "llm_fallback": False
        }

    # --- HELPERS & FORMATTERS ---
    def _run_synthesis(self, companies, result, agent1_result):
        summaries = []
        for ticker in companies:
            r = result.get(ticker, {})
            a1 = agent1_result.get(ticker, {})
            meta = a1.get("kaggle_meta", {})
            summaries.append(f"Ticker: {ticker} | Company: {meta.get('company_name')} | Signal: {r.get('investor_signal')}")
        
        prompt = SYNTHESIS_VERDICT_PROMPT.format(num_companies=len(companies), company_summaries="\n".join(summaries))
        verdict, _ = self._call_mcp_llm(prompt, "synthesis")
        return verdict if verdict else {"winner": "N/A", "verdict_text": "Synthesis failed"}

    def _derive_signal(self, confidence, trend):
        direction = trend.get("Total", {}).get("direction", "worsening")
        if confidence >= CONFIDENCE_COMMENDATORY and direction == "improving": return "BUY"
        if confidence >= CONFIDENCE_BALANCED: return "HOLD"
        return "CAUTION" if confidence >= 25 else "AVOID"

    def _select_narrative_template(self, confidence):
        if confidence >= CONFIDENCE_COMMENDATORY: return NARRATIVE_COMMENDATORY_PROMPT
        if confidence >= CONFIDENCE_BALANCED: return NARRATIVE_BALANCED_PROMPT
        return NARRATIVE_CAUTIONARY_PROMPT

    def _format_yearly_scores(self, yearly):
        return "\n".join([f"{y}: {s}" for y, s in sorted(yearly.items())])

    def _format_regression(self, trend):
        return "\n".join([f"{k}: {v}" for k, v in trend.items() if isinstance(v, dict)])

    def _format_validation_table(self, table):
        return "\n".join([str(row) for row in table])

    def _format_crisil_rating(self, meta):
        return f"Rating: {meta.get('esg_rating')} | Category: {meta.get('category')}"

    def _format_esg_summary(self, yearly, trend):
        latest = max(yearly.keys()) if yearly else "N/A"
        return f"Latest Year: {latest} | Trend: {trend.get('trend_classification', 'N/A')}"

    def _fallback_company(self, ticker, reason, c1=None, c2=None):
        return {"narrative": f"Fallback due to {reason}", "investor_signal": "HOLD", "llm_fallback": True}