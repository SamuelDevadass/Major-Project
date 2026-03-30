import requests
import os
from pathlib import Path
from dotenv import load_dotenv

# Load env just for API keys/URLs if needed
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)

class NewsRAGAgent:
    """
    Agent 2 — The MCP Client.
    Delegates all heavy scraping and RAG work to the MCP Server.
    """
    def __init__(self):
        # The URL where your mcp_server.py is running
        self.mcp_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001/tools/fetch_esg_news")

    def run(self, companies: list[str], agent1_result: dict) -> dict:
        """
        Input: list of tickers and the metadata from Agent 1.
        Output: Aggregated RAG results from the MCP Server.
        """
        print(f"📡 [AGENT 2] Initializing MCP Request for {len(companies)} companies...")
        
        final_results = {}

        for ticker in companies:
            # 1. Extract the best company name from Agent 1's Kaggle metadata
            a1_data = agent1_result.get(ticker, {})
            meta = a1_data.get("kaggle_meta", {})
            company_name = meta.get("company_name", ticker)

            print(f"🔍 [AGENT 2] Requesting Tool: fetch_esg_news for {ticker}")

            try:
                # 2. THE ACTUAL MCP HANDSHAKE (HTTP Transport)
                response = requests.post(
                    self.mcp_url,
                    json={
                        "ticker": ticker,
                        "company_name": company_name
                    },
                    timeout=90  # High timeout because scraping takes time
                )

                if response.status_code == 200:
                    # Server returns {news_available, rag_chunks, bert_sentiment, source_count}
                    data = response.json()
                    final_results[ticker] = data
                    print(f"✅ [AGENT 2] Received {data.get('source_count', 0)} articles for {ticker}")
                else:
                    print(f"❌ [AGENT 2] MCP Server Error ({response.status_code}) for {ticker}")
                    final_results[ticker] = self._get_fallback_state()

            except Exception as e:
                print(f"⚠️ [AGENT 2] Connection to MCP Server failed: {e}")
                final_results[ticker] = self._get_fallback_state()

        return final_results

    def _get_fallback_state(self):
        """Standardized error state so the pipeline doesn't break."""
        return {
            "news_available": False,
            "rag_chunks": [],
            "bert_sentiment": 0.5,
            "error": "MCP Tool Offline",
            "missing_2025": True
        }