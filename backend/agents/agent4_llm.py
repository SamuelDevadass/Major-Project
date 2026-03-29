# backend/agents/agent4_llm.py
# Agent 4 — Three-Stage LLM Credibility Pipeline
# NOTE: CRISIL scores are 0-100, HIGHER = BETTER ESG performance

import json
import os
import time
import re
from groq import Groq
from config.thresholds import CONFIDENCE_COMMENDATORY, CONFIDENCE_BALANCED
from config.prompts import (NEWS_INTELLIGENCE_PROMPT,CREDIBILITY_VALIDATION_PROMPT,
                            NARRATIVE_COMMENDATORY_PROMPT,NARRATIVE_BALANCED_PROMPT,
                            NARRATIVE_CAUTIONARY_PROMPT,SYNTHESIS_VERDICT_PROMPT)
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent.parent/".env"
load_dotenv(env_path)

MODEL      = "llama-3.3-70b-versatile"
TEMP       = 0.3
MAX_TOKENS = 1000
RATE_LIMIT_SLEEP_THRESHOLD = 28


class LLMAgent:
    """
    Agent 4 — 3-stage LLM credibility pipeline per company + synthesis verdict.

    Input:
        companies    : list of ticker strings
        agent1_result: output from Agent 1
        agent2_result: output from Agent 2
        agent3_result: output from Agent 3

    Output dict keyed by ticker + "verdict" key.
    """

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        print("\n" + "="*70)
        print("AGENT 4: LLM PIPELINE INITIALIZATION")
        print("="*70)
        
        if not api_key:
            print("❌ ERROR: GROQ_API_KEY not found in environment variables")
            print("\nTroubleshooting steps:")
            print("1. Create a .env file in your project root directory")
            print("2. Add this line: GROQ_API_KEY=your_actual_groq_api_key")
            print("3. Get your API key from: https://console.groq.com/keys")
            print(f"4. Expected .env location: {env_path}")
            print("="*70 + "\n")
            raise ValueError("GROQ_API_KEY missing - add it to .env file")
        
        print(f"✅ GROQ_API_KEY loaded successfully!")
        print(f"✅ Using model: {MODEL}")
        self._client     = Groq(api_key=api_key)
        self._call_count = 0

    def run(self, companies, agent1_result, agent2_result, agent3_result):
        result = {}
        
        print("\n" + "="*70)
        print(f"AGENT 4: Processing {len(companies)} companies")
        print("="*70)

        for ticker in companies:
            print(f"\n{'─'*70}")
            print(f"Processing: {ticker}")
            print(f"{'─'*70}")
            
            a1 = agent1_result.get(ticker, {})
            a2 = agent2_result.get(ticker, {})
            a3 = agent3_result.get(ticker, {})

            if not a1.get("found", False):
                print(f"⚠️  {ticker}: No data found in Agent 1, using fallback")
                result[ticker] = self._fallback_company(ticker, "not_found")
                continue

            result[ticker] = self._run_company_pipeline(ticker, a1, a2, a3)

        print(f"\n{'='*70}")
        print("SYNTHESIS: Generating final verdict")
        print(f"{'='*70}")
        result["verdict"] = self._run_synthesis(companies, result, agent1_result)
        
        print(f"\n{'='*70}")
        print("AGENT 4: Pipeline Complete")
        print(f"{'='*70}\n")
        
        return result


    def _run_company_pipeline(self, ticker, a1, a2, a3):
        meta         = a1.get("kaggle_meta", {})
        yearly       = a1.get("yearly_scores", {})
        trend        = a3.get("trend", {})
        val_tbl      = a3.get("validation_table", [])
        rag          = a2.get("rag_chunks", [])
        latest_year  = max(yearly.keys()) if yearly else None
        latest_scores = yearly.get(latest_year, {}) if latest_year else {}

        print(f"Company: {meta.get('company_name', ticker)}")
        print(f"News chunks available: {len(rag)}")
        print(f"Latest ESG score: {latest_scores.get('Total', 'N/A')}")

        print(f"\n  → Call 1: News Intelligence Analysis")
        call1_prompt = NEWS_INTELLIGENCE_PROMPT.format(
            company_name=meta.get("company_name", ticker),
            ticker=ticker,
            industry=meta.get("sector", "Unknown"),
            rag_chunks="\n\n---\n\n".join(rag) if rag else "No news articles available.",
            e_score=latest_scores.get("E", "N/A"),
            s_score=latest_scores.get("S", "N/A"),
            g_score=latest_scores.get("G", "N/A"),
            total_score=latest_scores.get("Total", "N/A"),
        )
        call1_result, fallback1 = self._call_llm_json(call1_prompt, ticker, "call1")
        if not call1_result:
            print(f"  ❌ Call 1 failed, using fallback")
            return self._fallback_company(ticker, "call1_failed")
        print(f"  ✅ Call 1 successful: {call1_result.get('overall_news_sentiment', 'N/A')} sentiment")

        print(f"  → Call 2: Credibility Validation")
        call2_prompt = CREDIBILITY_VALIDATION_PROMPT.format(
            company_name=meta.get("company_name", ticker),
            ticker=ticker,
            yearly_scores=self._format_yearly_scores(yearly),
            regression_summary=self._format_regression(trend),
            validation_table=self._format_validation_table(val_tbl),
            crisil_rating=self._format_crisil_rating(meta),
            positive_findings=call1_result.get("positive_findings", []),
            negative_findings=call1_result.get("negative_findings", []),
            governance_flags=call1_result.get("governance_flags", []),
            overall_news_sentiment=call1_result.get("overall_news_sentiment", "insufficient_data"),
        )
        call2_result, fallback2 = self._call_llm_json(call2_prompt, ticker, "call2")
        if not call2_result:
            print(f"  ❌ Call 2 failed, using fallback")
            return self._fallback_company(ticker, "call2_failed", call1_result)

        confidence = call2_result.get("confidence_score", 50)
        print(f"  ✅ Call 2 successful: Confidence={confidence}, Verdict={call2_result.get('credibility_verdict', 'N/A')}")

        investor_signal    = self._derive_signal(confidence, trend)
        narrative_template = self._select_narrative_template(confidence)
        
        template_name = {
            NARRATIVE_COMMENDATORY_PROMPT: "Commendatory",
            NARRATIVE_BALANCED_PROMPT: "Balanced",
            NARRATIVE_CAUTIONARY_PROMPT: "Cautionary"
        }.get(narrative_template, "Unknown")
        
        print(f"  → Call 3: {template_name} Narrative (confidence={confidence}, signal={investor_signal})")

        call3_prompt = narrative_template.format(
            company_name=meta.get("company_name", ticker),
            ticker=ticker,
            confidence_score=confidence,
            esg_summary=self._format_esg_summary(yearly, trend),
            trend_classification=trend.get("trend_classification", "Unknown"),
            positive_findings=call1_result.get("positive_findings", []),
            negative_findings=call1_result.get("negative_findings", []),
            governance_flags=call1_result.get("governance_flags", []),
            washing_risk=call2_result.get("washing_risk", "medium"),
            investor_signal=investor_signal,
        )
        call3_result, fallback3 = self._call_llm_json(call3_prompt, ticker, "call3")
        if not call3_result:
            print(f"  ❌ Call 3 failed, using fallback")
            return self._fallback_company(ticker, "call3_failed", call1_result, call2_result)
        print(f"  ✅ Call 3 successful: Narrative generated ({len(call3_result.get('narrative', ''))} chars)")

        return {
            "news_findings":   call1_result,
            "credibility":     call2_result,
            "narrative":       call3_result.get("narrative", ""),
            "key_highlights":  call3_result.get("key_highlights", []),
            "investor_signal": call3_result.get("investor_signal", investor_signal),
            "llm_fallback":    any([fallback1, fallback2, fallback3]),
        }


    def _run_synthesis(self, companies, result, agent1_result):
        summaries = []
        for ticker in companies:
            r      = result.get(ticker, {})
            a1     = agent1_result.get(ticker, {})
            yearly = a1.get("yearly_scores", {})
            latest_year  = max(yearly.keys()) if yearly else None
            total_score  = yearly.get(latest_year, {}).get("Total", "N/A") if latest_year else "N/A"
            trend        = a1.get("trend", {})
            meta         = a1.get("kaggle_meta", {})

            summaries.append(
                f"Ticker: {ticker}\n"
                f"Company: {meta.get('company_name', ticker)}\n"
                f"Sector: {meta.get('sector', 'Unknown')}\n"
                f"CRISIL ESG Score (latest, 0-100 higher=better): {total_score}\n"
                f"CRISIL Rating: {meta.get('esg_rating', 'N/A')} | Category: {meta.get('category', 'N/A')}\n"
                f"Confidence Score: {r.get('credibility', {}).get('confidence_score', 'N/A')}\n"
                f"Investor Signal: {r.get('investor_signal', 'HOLD')}\n"
                f"Trend: {r.get('credibility', {}).get('credibility_verdict', 'Unknown')}\n"
            )

        prompt = SYNTHESIS_VERDICT_PROMPT.format(
            num_companies=len(companies),
            company_summaries="\n\n".join(summaries),
        )

        print(f"  → Generating comparative verdict for {len(companies)} companies")
        verdict_result, _ = self._call_llm_json(prompt, "synthesis", "verdict")

        if not verdict_result:
            print(f"  ❌ Synthesis failed, using fallback verdict")
            return {
                "winner":        companies[0],
                "winner_name":   companies[0],
                "rankings":      companies,
                "verdict_text":  "Verdict could not be generated — LLM call failed.",
                "most_improved": companies[0],
                "biggest_risk":  companies[-1],
            }
        
        print(f"  ✅ Synthesis successful: Winner={verdict_result.get('winner', 'N/A')}")
        return verdict_result


    def _call_llm_json(self, prompt, ticker, call_label):
        """
        Call Groq LLM API and return parsed JSON response.
        
        Returns:
            tuple: (parsed_json_dict, fallback_used_bool)
        """
        self._rate_limit_check()

        for attempt in range(2):
            try:
                # Make API call
                response = self._client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=TEMP,
                    max_tokens=MAX_TOKENS,
                )
                self._call_count += 1
                text = response.choices[0].message.content.strip()

                # Strip markdown fences if present
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                text = text.strip()
                text = re.sub(r'[\x00-\x1F]+', ' ', text)
                parsed = json.loads(text)
                return parsed, False

            except json.JSONDecodeError as e:
                print(f"    ⚠️  JSON parsing error on attempt {attempt + 1}/2")
                print(f"    Error: {str(e)[:100]}")
                
                if attempt == 0:
                    # Retry with clearer instructions
                    prompt = (
                        "Your previous response was not valid JSON. "
                        "Return ONLY a valid JSON object with no preamble, "
                        f"no markdown, no explanation.\n\n{prompt}"
                    )
                    print(f"    → Retrying with stricter prompt...")
                    continue
                else:
                    print(f"    ❌ Failed to parse JSON after 2 attempts")
                    return None, True

            except Exception as e:
                print(f"    ❌ LLM API call failed on attempt {attempt + 1}/2")
                print(f"    Error type: {type(e).__name__}")
                print(f"    Error message: {str(e)[:200]}")
                
                # Don't retry on API errors (rate limits, auth failures, etc.)
                if attempt == 1 or "rate" in str(e).lower() or "auth" in str(e).lower():
                    return None, True
                
                # Wait before retry
                time.sleep(2)
                continue

        return None, True

    def _rate_limit_check(self):
        """Pause execution if approaching rate limits."""
        if self._call_count >= RATE_LIMIT_SLEEP_THRESHOLD:
            print(f"\n  ⏸️  Rate limit threshold reached ({RATE_LIMIT_SLEEP_THRESHOLD} calls), sleeping 60s...")
            time.sleep(60)
            self._call_count = 0
            print(f"  ▶️  Resuming...\n")


    def _derive_signal(self, confidence, trend):
        """
        CRISIL: higher score = better, positive slope = improving.
        
        Returns: "BUY", "HOLD", "CAUTION", or "AVOID"
        """
        direction = trend.get("Total", {}).get("direction", "worsening")
        if confidence >= CONFIDENCE_COMMENDATORY and direction == "improving":
            return "BUY"
        elif confidence >= CONFIDENCE_BALANCED:
            return "HOLD"
        elif confidence >= 25:
            return "CAUTION"
        else:
            return "AVOID"

    def _select_narrative_template(self, confidence):
        """Select narrative template based on confidence score."""
        if confidence >= CONFIDENCE_COMMENDATORY:
            return NARRATIVE_COMMENDATORY_PROMPT
        elif confidence >= CONFIDENCE_BALANCED:
            return NARRATIVE_BALANCED_PROMPT
        return NARRATIVE_CAUTIONARY_PROMPT


    def _format_yearly_scores(self, yearly):
        lines = []
        for yr in sorted(yearly.keys()):
            s = yearly[yr]
            lines.append(
                f"  {yr}: E={s.get('E','N/A')} S={s.get('S','N/A')} "
                f"G={s.get('G','N/A')} Total={s.get('Total','N/A')}"
            )
        return "\n".join(lines) if lines else "No yearly scores available"

    def _format_regression(self, trend):
        lines = []
        for key in ["E", "S", "G", "Total"]:
            t = trend.get(key, {})
            lines.append(
                f"  {key}: slope={t.get('slope','N/A')} "
                f"r2={t.get('r2','N/A')} direction={t.get('direction','N/A')}"
            )
        return "\n".join(lines) if lines else "No trend data available"

    def _format_validation_table(self, table):
        if not table:
            return "No validation data available."
        lines = []
        for row in table:
            lines.append(
                f"  {row['year']}: status={row['status']} "
                f"direction={row['direction']} "
                f"delta_Total={row.get('delta', {}).get('Total', 'N/A')}"
            )
        return "\n".join(lines)

    def _format_crisil_rating(self, meta):
        """Format CRISIL-specific rating and category."""
        return (
            f"CRISIL ESG Rating: {meta.get('esg_rating', 'N/A')} | "
            f"Category: {meta.get('category', 'N/A')} | "
            f"Sector: {meta.get('sector', 'N/A')}"
        )

    def _format_esg_summary(self, yearly, trend):
        latest = max(yearly.keys()) if yearly else None
        scores = yearly.get(latest, {}) if latest else {}
        return (
            f"Latest year ({latest}): "
            f"E={scores.get('E','N/A')} S={scores.get('S','N/A')} "
            f"G={scores.get('G','N/A')} Total={scores.get('Total','N/A')} "
            f"(CRISIL scale 0-100, higher=better) | "
            f"Trend: {trend.get('trend_classification','Unknown')}"
        )


    def _fallback_company(self, ticker, reason, call1=None, call2=None):
        """Generate fallback response when LLM calls fail."""
        return {
            "news_findings": call1 or {
                "positive_findings":      [],
                "negative_findings":      [],
                "governance_flags":       [],
                "overall_news_sentiment": "insufficient_data",
            },
            "credibility": call2 or {
                "confidence_score":       50,
                "credibility_verdict":    "stable",
                "supporting_evidence":    [],
                "contradicting_evidence": [],
                "washing_risk":           "medium",
            },
            "narrative":       f"[Fallback] LLM pipeline could not complete for {ticker} ({reason}).",
            "key_highlights":  ["Data unavailable", "Analysis incomplete", "Manual review recommended"],
            "investor_signal": "HOLD",
            "llm_fallback":    True,
        }