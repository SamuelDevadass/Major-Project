import requests
import os
import json
from pathlib import Path
from dotenv import load_dotenv

class NewsRAGAgent:
    def __init__(self):
        self.base_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001")
        self.news_url = f"{self.base_url}/tools/fetch_esg_news"
        self.audit_url = f"{self.base_url}/tools/deep_esg_audit"
        self.llm_url = f"{self.base_url}/tools/llm_processor"

    def run(self, companies: list[str], agent1_result: dict) -> dict:
        print(f"📡 [AGENT 2] Starting Qualitative & Official Audit...")
        final_results = {}

        for ticker in companies:
            source_map = {}
            a1_data = agent1_result.get(ticker, {})
            # Ensure we get a clean company name for the search tools
            company_name = a1_data.get("kaggle_meta", {}).get("company_name", ticker)
            
            # --- PHASE A: FETCH NEWS (TOOL 1) ---
            # Passes both ticker and company_name as required by NewsRequest schema
            news_payload = {"ticker": ticker, "company_name": company_name}
            news_data = self._call_mcp(self.news_url, news_payload)
            
            news_text_with_ids = ""
            if news_data.get("news_available"):
                # Note: Ensure your MCP Tool 1 returns 'articles' or 'rag_chunks'
                for i, chunk in enumerate(news_data.get("rag_chunks", []), 1):
                    id_tag = f"[N{i}]"
                    news_text_with_ids += f"{id_tag} {chunk}\n"
                    source_map[id_tag] = "News Article" 

            # --- PHASE B: DEEP AUDIT / BRSR (TOOL 2) ---
            # FIX: We no longer send a 'pdf_url' because the tool searches NSE using company_name
            audit_payload = {
                "ticker": ticker, 
                "company_name": company_name
            }
            print(f"🔍 [AGENT 2] Hunting for BRSR Report for: {company_name}")
            audit_data = self._call_mcp(self.audit_url, audit_payload)
            
            brsr_summary = "No official report found."
            
            if audit_data.get("status") == "success":
                # The tool now returns the actual URL it found on NSE
                actual_report_url = audit_data.get("report_url", "NSE Official Filing")
                source_map["[B1]"] = actual_report_url
                
                # --- PHASE C: LOCAL LLM SUMMARIZATION (TOOL 3) ---
                # We send the Markdown to the LLM to get the facts
                markdown_text = audit_data.get('markdown', '')[:15000] # Increased limit for better context
                
                extraction_prompt = f"""
                Using the context provided in [B1], extract a summary of:
                1. Scope 1 and Scope 2 emissions.
                2. Renewable energy consumption percentage.
                3. Gender diversity (Female employee %).
                
                Use the tag [B1] for every data point extracted.
                
                REPORT CONTENT:
                [B1] {markdown_text}
                """
                
                llm_response = self._call_mcp(self.llm_url, {
                    "prompt": extraction_prompt, 
                    "ticker": ticker
                })
                
                # Handle the case where LLM tool returns a dict or error message
                if isinstance(llm_response, dict):
                    brsr_summary = llm_response.get("response", "Processing failed.")
                else:
                    brsr_summary = llm_response

            # --- AGGREGATE ---
            final_results[ticker] = {
                "news_summary": news_text_with_ids,
                "official_fact_sheet": brsr_summary,
                "sentiment": news_data.get("sentiment", 0.5), # Matches Tool 1 output
                "references": source_map 
            }
            
            print(f"✅ [AGENT 2] Audit Complete for {ticker}. References Mapped: {list(source_map.keys())}")

        return final_results

    def _call_mcp(self, url, payload):
        try:
            # Critical: Use json=payload to ensure correct Content-Type header
            response = requests.post(url, json=payload, timeout=180) 
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ [AGENT 2] Error {response.status_code} from {url}: {response.text}")
                return {}
        except Exception as e:
            print(f"⚠️ [AGENT 2] MCP Call Failed ({url}): {e}")
            return {}