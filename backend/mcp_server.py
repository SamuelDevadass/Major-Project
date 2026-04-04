import os, re, json, io, asyncio, time, requests
import numpy as np
import faiss
import feedparser
import spacy
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from newspaper import Article
from datetime import datetime
from huggingface_hub import login
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from docling.document_converter import DocumentConverter

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

app = FastAPI(title="ESG Intelligence MCP Server")

print("[MCP SERVER] : Loading BERT & NLP models to RAM ....")
EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
print("[MCP SERVER] : Initializing Docling Document Converter ....")
DOC_CONVERTER = DocumentConverter()

try:
    NLP = spacy.load("en_core_web_sm")
except OSError:
    print("[MCP SERVER] : spacy model not found. INSTALLING ....")
    os.system("python -m spacy download en_core_web_sm")
    NLP = spacy.load("en_core_web_sm")

# HF Login for BERT
HF_TOKEN = os.getenv("HFT_TOKEN")
if HF_TOKEN:
    login(token=HF_TOKEN)
    print("[MCP SERVER] : BERT Authenticated via HuggingFace")
    print("[MCP SERVER] : Embedding model configured successfully")

# Groq Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_CLIENT = None
if GROQ_API_KEY:
    GROQ_CLIENT = Groq(api_key=GROQ_API_KEY)
    print("[MCP SERVER] : Groq LLM Configured successfully")
else:
    print("[MCP SERVER] : WARNING: GROQ_API_KEY missing. LLM not configured!")

CHUNK_TOKENS = 300
CHUNK_OVERLAP = 50
MAX_ARTICLES = 5

REFERENCES_LIST={}

# --- SCHEMAS ---
class NewsRequest(BaseModel):
    ticker: str
    company_name: str
class LLMRequest(BaseModel):
    prompt: str
    ticker: Optional[str] = "Synthesis"
    model: Optional[str] = "meta-llama/llama-4-scout-17b-16e-instruct"
class AuditRequest(BaseModel):
    ticker: str
    company_name: str  # Add this line!
    pdf_url: Optional[str] = None # Make this optional since you're searching now

def chunk_text(text: str):
    words = text.split()
    chunks = []
    for i in range(0, len(words), CHUNK_TOKENS - CHUNK_OVERLAP):
        chunk = " ".join(words[i : i + CHUNK_TOKENS])
        if chunk.strip():
            chunks.append(chunk)
    return chunks

# TOOL — Google News RSS Fetch Only
@app.post("/tools/fetch_esg_news")
async def tool_fetch_news(req: NewsRequest):
    print(f"[MCP SERVER] : TOOL-1 : RSS NEWS FETCH | Target: {req.company_name}")

    import feedparser
    import requests
    from datetime import datetime, timedelta
    from email.utils import parsedate_to_datetime

    # Clean company name
    doc = NLP(req.company_name)
    org_names = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
    cleaned = org_names[0] if org_names else req.company_name

    suffixes = [" Limited", " Ltd", " Ltd.", " Private Limited", " Private",
                " Pvt Ltd", " Pvt", " Pvt.", " Inc", " Corporation",
                " Corp", " LLC", " LLP", " PLC"]

    for suffix in suffixes:
        cleaned = cleaned.replace(suffix, "")

    cleaned = cleaned.strip()
    print(f"[MCP] Cleaned Company: {cleaned}")

    # Google News RSS search variants (NO OR queries)
    SEARCH_VARIANTS = [
        f"{cleaned}",
        f"{cleaned} news",
        f"{cleaned} earnings",
        f"{cleaned} ESG",
        f"{cleaned} sustainability",
        f"{cleaned} SEBI",
        f"{cleaned} fraud",
        f"{cleaned} fine",
    ]

    articles = []
    references = []

    six_months_ago = datetime.now() - timedelta(days=180)

    for query in SEARCH_VARIANTS:
        try:
            # Add time filter
            query_time = f"{query} when:180d"
            rss_url = f"https://news.google.com/rss/search?q={requests.utils.quote(query_time)}&hl=en-IN&gl=IN&ceid=IN:en"

            print(f"[RSS] Query: {query_time}")
            print(f"[RSS] URL: {rss_url}")

            feed = feedparser.parse(rss_url)

            print(f"[RSS] Found {len(feed.entries)} entries")

            if not feed.entries:
                continue

            for entry in feed.entries[:MAX_ARTICLES]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "")
                link = entry.get("link", "")
                pub_date_str = entry.get("published", "")

                # Date filter
                if pub_date_str:
                    try:
                        pub_date = parsedate_to_datetime(pub_date_str)
                        if pub_date < six_months_ago:
                            continue
                    except Exception:
                        pass

                text = f"{title} {summary}"

                if len(text) > 50:
                    articles.append(text)
                    references.append(link)

        except Exception as e:
            print("[RSS ERROR]:", e)
            continue

    if not articles:
        print("[MCP] No RSS articles found")
        return {
            "news_available": False,
            "rag_chunks": [],
            "sentiment": 0.5
        }

    # Save references
    if req.ticker not in REFERENCES_LIST:
        REFERENCES_LIST[req.ticker] = {}

    for i, ref in enumerate(references):
        REFERENCES_LIST[req.ticker][i] = ref

    with open("references_list.json", "w", encoding="utf-8") as f:
        json.dump(REFERENCES_LIST, f, indent=3)

    # Chunk text
    all_chunks = []
    for text in articles:
        all_chunks.extend(chunk_text(text))

    return {
        "news_available": True,
        "rag_chunks": all_chunks[:20],
        "source_count": len(articles),
        "bert_sentiment": 0.75,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/tools/llm_processor")
async def tool_llm_processor(req: LLMRequest):
    if not GROQ_CLIENT:
        raise HTTPException(status_code=500, detail="Groq Client not initialized. Check API Key.")

    print(f"[MCP SERVER] : TOOL-3 : GROQ-LLM Running .... | Context: {req.ticker}")
    
    try:
        response = GROQ_CLIENT.chat.completions.create(
            model=req.model,
            messages=[{"role": "user", "content": req.prompt}],
            temperature=0.3,
            response_format={"type": "json_object"} 
        )
        # Parse the string content into a JSON object to return as a proper API response
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"[MCP SERVER] : LLM Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/tools/deep_esg_audit")
async def tool_deep_audit(req: AuditRequest):
    print(f"[MCP SERVER] : TOOL - 2 : OFFICIAL ESG REPORT PARSER | Target: {req.company_name}")
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-http2", "--disable-blink-features=AutomationControlled"]
            )

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080}
            )

            page = await context.new_page()

            await page.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            })

            # Apply stealth
            stealth = Stealth()
            await stealth.apply_stealth_async(page)

            # Go to NSE page
            target_url = "https://www.nseindia.com/companies-listing/corporate-filings-bussiness-sustainabilitiy-reports"
            await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)

            print("[MCP] NSE page loaded")

            # Wait for search box
            search_selector = "#companyInput"
            await page.wait_for_selector(search_selector, timeout=15000)

            # Type slowly (important for NSE autocomplete)
            await page.click(search_selector)
            await page.fill(search_selector, "")
            await page.type(search_selector, req.company_name, delay=100)

            await asyncio.sleep(2)

            # Press Enter
            await page.keyboard.press("Enter")
            await asyncio.sleep(3)

            print("[MCP] Searching company...")

            # Wait for table rows
            await page.wait_for_selector("table#bussinessSustainabilitiyReportsTable tbody tr", timeout=15000)

            # Extract PDF link
            pdf_link_selector = "table#bussinessSustainabilitiyReportsTable a[href$='.pdf']"
            pdf_element = await page.query_selector(pdf_link_selector)

            if not pdf_element:
                await browser.close()
                return {"status": "error", "message": f"No BRSR PDF found for {req.company_name} on NSE."}

            relative_url = await pdf_element.get_attribute("href")

            if relative_url.startswith("/"):
                pdf_url = f"https://www.nseindia.com{relative_url}"
            else:
                pdf_url = relative_url

            print(f"[MCP] PDF URL Found: {pdf_url}")

            await browser.close()

            # --- DOWNLOAD PDF USING REQUESTS (MORE RELIABLE) ---
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.nseindia.com/"
            }

            pdf_bytes = requests.get(pdf_url, headers=headers).content

            # --- DOC PARSING ---
            print(f"[MCP SERVER] : Docling parsing started for {req.ticker}...")
            loop = asyncio.get_event_loop()

            result = await loop.run_in_executor(
                None,
                lambda: DOC_CONVERTER.convert(io.BytesIO(pdf_bytes))
            )

            markdown_content = result.document.export_to_markdown()

            # --- SAVE REFERENCE ---
            current_refs = {}
            if os.path.exists("references_list.json"):
                try:
                    with open("references_list.json", "r", encoding="utf-8") as f:
                        current_refs = json.load(f)
                except:
                    current_refs = {}

            if req.ticker not in current_refs:
                current_refs[req.ticker] = {}

            current_refs[req.ticker]["brsr_report"] = pdf_url

            with open("references_list.json", "w", encoding="utf-8") as f:
                json.dump(current_refs, f, indent=3)

            return {
                "status": "success",
                "ticker": req.ticker,
                "company_name": req.company_name,
                "report_url": pdf_url,
                "markdown": markdown_content,
                "length": len(markdown_content),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            print(f"[MCP SERVER] : Deep Audit Error: {str(e)}")
            return {"status": "error", "message": f"Critical Failure: {str(e)}"}
# --- MAIN ---
if __name__ == "__main__":
    print("\n🚀 Starting ESG Intelligence MCP Server on Port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)