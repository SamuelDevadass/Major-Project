import os
import json
import time
import asyncio
import numpy as np
import faiss
import requests
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

# --- CONFIG & ENV ---
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

app = FastAPI(title="ESG Intelligence MCP Server")

# --- INITIALIZE HEAVY MODELS (Stored in RAM) ---
print("⏳ [MCP] Loading BERT and NLP Models into RAM...")
EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")

try:
    NLP = spacy.load("en_core_web_sm")
except OSError:
    print("📥 Downloading spacy model...")
    os.system("python -m spacy download en_core_web_sm")
    NLP = spacy.load("en_core_web_sm")

# HF Login for BERT
HF_TOKEN = os.getenv("HFT_TOKEN")
if HF_TOKEN:
    login(token=HF_TOKEN)
    print("✅ BERT Authenticated via HuggingFace")

# Groq Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_CLIENT = None
if GROQ_API_KEY:
    GROQ_CLIENT = Groq(api_key=GROQ_API_KEY)
    print("✅ Groq LLM Configured Successfully")
else:
    print("⚠️ WARNING: GROQ_API_KEY missing. LLM tools will fail.")

# --- CONSTANTS ---
CHUNK_TOKENS = 300
CHUNK_OVERLAP = 50
MAX_ARTICLES = 7

# --- SCHEMAS ---
class NewsRequest(BaseModel):
    ticker: str
    company_name: str

class LLMRequest(BaseModel):
    prompt: str
    ticker: Optional[str] = "Synthesis"
    model: Optional[str] = "meta-llama/llama-4-scout-17b-16e-instruct"

# --- HELPER FUNCTIONS ---
def chunk_text(text: str):
    words = text.split()
    chunks = []
    for i in range(0, len(words), CHUNK_TOKENS - CHUNK_OVERLAP):
        chunk = " ".join(words[i : i + CHUNK_TOKENS])
        if chunk.strip():
            chunks.append(chunk)
    return chunks

# --- TOOL 1: NEWS FETCHING & RAG ---
@app.post("/tools/fetch_esg_news")
async def tool_fetch_news(req: NewsRequest):
    print(f"🔌 [MCP] Tool: fetch_esg_news | Target: {req.company_name}")
    
    # 1. RSS Fetching
    query = requests.utils.quote(f"{req.company_name} ESG sustainability")
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(rss_url)
    
    articles = []
    for entry in feed.entries[:MAX_ARTICLES]:
        try:
            art = Article(entry.link)
            art.download()
            art.parse()
            if len(art.text) > 100:
                articles.append(art.text)
        except:
            articles.append(entry.title)

    if not articles:
        return {"news_available": False, "rag_chunks": [], "sentiment": 0.5}

    # 2. Vectorization & FAISS
    all_chunks = []
    for text in articles:
        all_chunks.extend(chunk_text(text))
    
    embeddings = EMBED_MODEL.encode(all_chunks, convert_to_numpy=True)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings.astype('float32'))

    # 3. Targeted RAG Query
    q_emb = EMBED_MODEL.encode(["ESG sustainability controversy carbon emissions"])
    _, indices = index.search(q_emb.astype('float32'), k=5)
    retrieved = [all_chunks[i] for i in indices[0] if i < len(all_chunks)]

    return {
        "news_available": True,
        "rag_chunks": retrieved,
        "source_count": len(articles),
        "bert_sentiment": 0.75, # Placeholder for BERT inference logic
        "timestamp": datetime.now().isoformat()
    }

# --- TOOL 2: LLM PROCESSOR (For Agent 4) ---
@app.post("/tools/llm_processor")
async def tool_llm_processor(req: LLMRequest):
    if not GROQ_CLIENT:
        raise HTTPException(status_code=500, detail="Groq Client not initialized. Check API Key.")

    print(f"🔌 [MCP] Tool: llm_processor | Context: {req.ticker}")
    
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
        print(f"❌ [MCP] LLM Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- MAIN ---
if __name__ == "__main__":
    print("\n🚀 Starting ESG Intelligence MCP Server on Port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)