import os
import time
import asyncio
import numpy as np
import faiss
import requests
import feedparser
import spacy
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from newspaper import Article
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from huggingface_hub import login
from pathlib import Path
from dotenv import load_dotenv
import uvicorn
env_path=Path(__file__).resolve().parent.parent/".env"
load_dotenv(env_path)
load_dotenv()

app = FastAPI(title="ESG Intelligence MCP Server")

# --- INITIALIZE HEAVY MODELS (Stored in RAM) ---
print("⏳ Loading BERT and NLP Models...")
EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
try:
    NLP = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading spacy model...")
    os.system("python -m spacy download en_core_web_sm")
    NLP = spacy.load("en_core_web_sm")

# HF Login for BERT
HF_TOKEN = os.getenv("HFT_TOKEN")
if HF_TOKEN:
    login(token=HF_TOKEN)
    print("✅ BERT Authenticated via MCP")

# --- CONSTANTS ---
CHUNK_TOKENS = 300
CHUNK_OVERLAP = 50
TOP_K = 7
MAX_ARTICLES = 7

# --- SCHEMAS ---
class NewsRequest(BaseModel):
    ticker: str
    company_name: str

# --- TOOL 1: NEWS FETCHING & RAG ---
def chunk_text(text: str):
    words = text.split()
    chunks = []
    for i in range(0, len(words), CHUNK_TOKENS - CHUNK_OVERLAP):
        chunk = " ".join(words[i : i + CHUNK_TOKENS])
        if chunk.strip():
            chunks.append(chunk)
    return chunks

@app.post("/tools/fetch_esg_news")
async def tool_fetch_news(req: NewsRequest):
    print(f"🔌 [MCP] Fetching News for: {req.company_name}")
    
    # 1. RSS Fetching (Simplified version of your logic)
    query = requests.utils.quote(f"{req.company_name} ESG sustainability")
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(rss_url)
    
    articles = []
    for entry in feed.entries[:MAX_ARTICLES]:
        try:
            # Quick scrape of content
            art = Article(entry.link)
            art.download()
            art.parse()
            if len(art.text) > 100:
                articles.append(art.text)
        except:
            articles.append(entry.title) # Fallback to title

    if not articles:
        return {"news_available": False, "rag_chunks": [], "sentiment": 0.5}

    # 2. Chunking & FAISS
    all_chunks = []
    for text in articles:
        all_chunks.extend(chunk_text(text))
    
    embeddings = EMBED_MODEL.encode(all_chunks, convert_to_numpy=True)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings.astype('float32'))

    # 3. RAG Query
    q_emb = EMBED_MODEL.encode(["ESG sustainability controversy carbon emissions"])
    _, indices = index.search(q_emb.astype('float32'), k=5)
    
    retrieved = [all_chunks[i] for i in indices[0] if i < len(all_chunks)]

    # 4. BERT Sentiment (Mock/Simple)
    # In reality, you'd run a classifier here
    sentiment_score = 0.75 # Placeholder for BERT result

    return {
        "news_available": True,
        "rag_chunks": retrieved,
        "source_count": len(articles),
        "bert_sentiment": sentiment_score,
        "timestamp": datetime.now().isoformat()
    }

# --- TOOL 2: LLM SYNTHESIS (For Agent 4) ---
class SynthesisRequest(BaseModel):
    data: dict

@app.post("/tools/generate_synthesis")
async def tool_synthesis(req: SynthesisRequest):
    print("🔌 [MCP] Generating Final ESG Report...")
    # This is where your Groq/OpenAI logic from Agent 4 moves to
    # For now, we return a signal that Agent 4 can use
    return {"status": "ready_for_llm", "context_length": len(str(req.data))}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)