# Agent 2 — Live News RAG via RSS + Direct Source Scraping
# Fetches news from:
# 1. Google News RSS (aggregated sources)
# 2. Direct Indian ESG news sources (Economic Times, ESG Times, Business Standard)
# Chunks articles, builds per-company FAISS index.
# Runs 3 targeted RAG queries per company.

import json
import os
from pathlib import Path
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import requests
from bs4 import BeautifulSoup
import spacy
import feedparser
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from dotenv import load_dotenv
from newspaper import Article
import time

env_path = Path(__file__).resolve().parents[2]/".env"
load_dotenv(env_path)

_nlp_model: spacy.Language | None = None

def _get_nlp_model() -> spacy.Language:
    global _nlp_model
    if _nlp_model is None:
        try:
            _nlp_model = spacy.load("en_core_web_sm")
        except OSError:
            raise RuntimeError("Spacy models missing. Run python -m spacy download en_core_web_sm to install required models")
    return _nlp_model

BASE_DIR = Path(__file__).parent.parent

_EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
_embed_model: SentenceTransformer | None = None

CHUNK_TOKENS    = 300
CHUNK_OVERLAP   = 50
TOP_K           = 7
REQUEST_TIMEOUT = 5    
MAX_ARTICLES    = 7
MIN_ARTICLE_LENGTH = 100  

RAG_QUERIES = [
    "company earnings results revenue profit expansion acquisition merger business strategy",
    "sustainability ESG climate renewable carbon CSR initiative green energy emissions",
    "fraud investigation penalty fine SEBI violation lawsuit protest accident controversy",
    "stock performance outlook analyst rating guidance share price upgrade downgrade",
    "new project partnership contract expansion launch investment capacity production",
]
DIRECT_SOURCES = [
    {
        "name": "Economic Times",
        "url": "https://economictimes.indiatimes.com/searchresult.cms?query={query}",
        "article_selector": "div.eachStory",
        "title_selector": "h3 a, h4 a",
        "link_selector": "h3 a, h4 a",
    },
    {
        "name": "ESG Times India",
        "url": "https://www.esgtimes.in/?s={query}",
        "article_selector": "article, div.post",
        "title_selector": "h2 a, h3 a",
        "link_selector": "h2 a, h3 a",
    },
    {
        "name": "Business Standard",
        "url": "https://www.business-standard.com/search?q={query}",
        "article_selector": "div.listing-txt, div.cardlist",
        "title_selector": "h2 a, h3 a",
        "link_selector": "h2 a, h3 a",
    },
    {
    "name": "Moneycontrol",
    "url": "https://www.moneycontrol.com/news/tags/{query}.html",
    "article_selector": "li.clearfix, div.newslist",
    "title_selector": "h2 a, a",
    "link_selector": "h2 a, a",
    }
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
}


def _get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(_EMBED_MODEL_NAME)
    return _embed_model


class NewsRAGAgent:
    """
    Agent 2 — fetches live news for each company at runtime,
    builds a FAISS vector index, and runs targeted RAG queries.

    Input:
        companies    : list of ticker strings
        agent1_result: output from Agent 1 (used for company names)

    Output dict:
        {
            "TICKER": {
                "news_available": True,
                "rag_chunks":     ["chunk text 1", ...],
                "scores_2025":    None,
                "missing_2025":   True,
            },
            ...
        }
    """
    def _extract_org_name(self, company_name: str) -> str:
        nlp = _get_nlp_model()
        doc = nlp(company_name)
        
        org_names = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
        
        if org_names:
            return max(org_names, key=len)
        
        cleaned = company_name
        for suffix in [" Limited", " Ltd", " Ltd.", " Private", " Pvt", " Inc", " Corporation", " Corp"]:
            cleaned = cleaned.replace(suffix, "")
        
        return cleaned.strip()

    def run(self, companies: list[str], agent1_result: dict) -> dict:
        model  = _get_embed_model()
        result = {}

        for ticker in companies:
            a1   = agent1_result.get(ticker, {})
            meta = a1.get("kaggle_meta", {})
            company_name = meta.get("company_name", ticker)

            result[ticker] = self._process_ticker(ticker, company_name, model)

        return result

    def _process_ticker(self, ticker: str, company_name: str, model: SentenceTransformer) -> dict:
        """Fetch live news, build FAISS index, run RAG queries."""

        articles = self._fetch_news(company_name, ticker)

        if not articles:
            return {
                "news_available": False,
                "rag_chunks":     [],
                "scores_2025":    None,
                "missing_2025":   True,
            }

        chunks = []
        for article in articles:
            content = article.get("content", "").strip()
            if content:
                chunks.extend(self._chunk_text(content))

        if not chunks:
            return {
                "news_available": True,
                "rag_chunks":     [],
                "scores_2025":    None,
                "missing_2025":   True,
            }

        ##  BUILD FAISS INDEX 
        embeddings = model.encode(chunks, convert_to_numpy=True, normalize_embeddings=True)
        dim        = embeddings.shape[1]
        index      = faiss.IndexFlatIP(dim)
        index.add(embeddings.astype(np.float32))

        ##  RUN 3 RAG QUERIES 
        retrieved_chunks = []
        seen_indices     = set()

        for query in RAG_QUERIES:
            q_emb = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
            _, indices = index.search(q_emb.astype(np.float32), TOP_K)
            for idx in indices[0]:
                if idx != -1 and idx not in seen_indices:
                    retrieved_chunks.append(chunks[idx])
                    seen_indices.add(idx)

        return {
            "news_available": True,
            "rag_chunks":     retrieved_chunks,
            "scores_2025":    None,
            "missing_2025":   True,
        }

    def _fetch_news(self, company_name: str, ticker: str) -> list[dict]:
        """
        Fetch news from BOTH Google News RSS AND direct Indian sources.
        Combines all results and deduplicates.
        """
        
        search_query = self._extract_org_name(company_name)
        
        print(f"\n{'='*70}")
        print(f"FETCHING NEWS FOR: {company_name}")
        print(f"Cleaned search query: {search_query}")
        print(f"{'='*70}")
        
        all_articles = []
        
        ## PART 1: GOOGLE NEWS RSS (aggregated sources)        
        print(f"\nPART 1: GOOGLE NEWS RSS")
        print(f"{'─'*70}")
        
        # Attempt 1: ESG-specific
        esg_keywords = "ESG sustainability environment social governance"
        SEARCH_VARIANTS = [ f"{search_query}",  # general (MOST IMPORTANT)
                            f"{search_query} news India",
                            f"{search_query} earnings results",
                            f"{search_query} ESG sustainability",
                            f"{search_query} controversy OR fine OR SEBI OR fraud"]
        
        for esg_query in SEARCH_VARIANTS:
            print(f"Attempt 1: ESG-focused search")
            print(f"Query: {esg_query}")
            rss_articles = self._fetch_rss(esg_query, "ESG-focused")
            all_articles.extend(rss_articles)
        
        # Attempt 2: Controversy
        if len(rss_articles) < 3:
            print(f"Only {len(rss_articles)} ESG articles, trying controversy...")
            controversy_keywords = "pollution accident fine protest SEBI violation fraud"
            controversy_query = f"{search_query} {controversy_keywords}"
            
            print(f"Attempt 2: Controversy search")
            print(f"Query: {controversy_query}")
            
            controversy_articles = self._fetch_rss(controversy_query, "Controversy")
            all_articles.extend(controversy_articles)
        
        # Attempt 3: General
        if len(rss_articles) < 3:
            print(f"Only {len(rss_articles)} articles, trying general news...")
            
            print(f"Attempt 3: General company news")
            print(f"Query: {search_query}")
            
            general_articles = self._fetch_rss(search_query, "General")
            all_articles.extend(general_articles)
        
        print(f"Google News RSS: {len(all_articles)} articles collected\n")
        
        # PART 2: DIRECT INDIAN ARTICLES SCRAPING        
        print(f"PART 2: DIRECT INDIAN SOURCES")
        print(f"{'─'*70}")
        
        direct_articles = self._fetch_direct_sources(search_query)
        all_articles.extend(direct_articles)
        
        print(f"Direct sources: {len(direct_articles)} articles collected\n")
        
        # DEDUPLICATE & RETURN
        seen_titles = set()
        unique_articles = []
        for article in all_articles:
            title_lower = article["title"].lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_articles.append(article)
        
        print(f"{'='*70}")
        print(f"FINAL RESULT: {len(unique_articles)} unique articles (from both sources)")
        print(f"{'='*70}\n")
        #return unique_articles[:MAX_ARTICLES * 3]
        return unique_articles  

    def _fetch_direct_sources(self, search_query: str) -> list[dict]:
        
        articles = []
        six_months_ago = datetime.now() - timedelta(days=180)
        
        for source in DIRECT_SOURCES:
            try:
                print(f"\nScraping: {source['name']}")
                
                # Build search URL
                url = source["url"].format(query=requests.utils.quote(search_query + " ESG"))
                print(f"URL: {url[:70]}...")
                
                # Fetch search results page
                session = requests.Session()
                session.headers.update(HEADERS)
                resp = session.get(url, timeout=REQUEST_TIMEOUT)
                
                if resp.status_code != 200:
                    print(f"Failed: HTTP {resp.status_code}")
                    continue
                
                soup = BeautifulSoup(resp.text, "html.parser")
                
                # Find article containers
                article_containers = soup.select(source["article_selector"])
                print(f"Found {len(article_containers)} result containers")
                
                # Extract articles
                for idx, container in enumerate(article_containers[:MAX_ARTICLES], 1):
                    # Extract title and link
                    title_el = container.select_one(source["title_selector"])
                    if not title_el:
                        continue
                    
                    title = title_el.get_text(strip=True)
                    link = title_el.get("href", "")
                    
                    # Fix relative URLs
                    if link.startswith("/"):
                        base_url = "/".join(url.split("/")[:3])
                        link = base_url + link
                    
                    if not link or not title:
                        continue
                    
                    print(f"{idx}. {title[:50]}...")
                    
                    # Fetch full article content
                    time.sleep(2.5)
                    content = self._fetch_article_cascading(link, None)
                    
                    if content:
                        print(f"Content: {len(content)} chars")
                    else:
                        print(f"Using title only")
                    
                    articles.append({
                        "title": title,
                        "source": source["name"],
                        "date": f"Date not available. System scraped article on {datetime.now().isoformat()}",  
                        "content": content or title,
                        "type": "Direct-Source",
                    })
                
                print(f"Collected {len(articles)} articles from {source['name']}")
                
                
            except Exception as e:
                print(f"Error scraping {source['name']}: {str(e)[:100]}")
                continue
        
        return articles

    def _fetch_rss(self, query: str, search_type: str) -> list[dict]:
        
        url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
        
        # Calculate 6-month cutoff
        six_months_ago = datetime.now() - timedelta(days=180)
        
        articles = []
        
        try:
            feed = feedparser.parse(url)
            
            print(f"RSS Status: {feed.get('status', 'Unknown')}")
            print(f"Found {len(feed.entries)} total entries")
            
            if not feed.entries:
                return []
            
            print(f"   Filtering articles (last 6 months only):")
            
            for idx, entry in enumerate(feed.entries[:MAX_ARTICLES * 3], 1):
                title = entry.get("title", "").strip()
                if not title:
                    continue
                
                # Get published date
                pub_date_str = entry.get("published", "Date not available")
                
                # Filter by date
                if pub_date_str:
                    try:
                        pub_date = parsedate_to_datetime(pub_date_str)
                        if pub_date < six_months_ago:
                            continue
                    except Exception:
                        pass
                
                source = "Google News"
                if hasattr(entry, 'source') and hasattr(entry.source, 'title'):
                    source = entry.source.title
                
                link = entry.get("link", "")
                
                print(f"{len(articles)+1}. {title[:55]}...")
                print(f"Source: {source} | Date: {pub_date_str[:10] if pub_date_str else 'N/A'}")
                
                content = self._fetch_article_cascading(link, entry)
                
                if content:
                    print(f"Final content: {len(content)} chars")
                else:
                    print(f"No content, using title only")
                
                articles.append({
                    "title": title,
                    "source": source,
                    "date": pub_date_str,
                    "content": content or title,
                    "type": search_type,
                })
                
                if len(articles) >= MAX_ARTICLES:
                    break
            
            print(f"Collected {len(articles)} articles from {search_type} search\n")
            
        except Exception as e:
            print(f"RSS fetch error: {e}\n")
            return []
        
        return articles

    def _fetch_article_cascading(self, url: str, entry) -> str:
        """
        Fetch article with cascading fallbacks:
        1. newspaper3k (best for full text)
        2. BeautifulSoup with selectors (manual scraping)
        3. RSS summary (from feed entry, if available)
        """
        
        # METHOD 1: newspaper3k
        content = self._fetch_with_newspaper(url)
        if len(content) >= MIN_ARTICLE_LENGTH:
            return content
        
        # METHOD 2: BeautifulSoup
        content = self._fetch_with_beautifulsoup(url)
        if len(content) >= MIN_ARTICLE_LENGTH:
            return content
        
        # METHOD 3: RSS summary (if entry provided)
        if entry and hasattr(entry, 'summary'):
            content = entry.summary.strip()
            if content:
                return content
        
        return ""

    def _fetch_with_newspaper(self, url: str) -> str:
        """Method 1: newspaper3k - automatic article extraction"""
        if not url or not url.startswith("http"):
            return ""
        
        try:
            article = Article(url, language='en')
            article.download()
            article.parse()
            text = article.text.strip()
            return text[:3000] if text else ""
        except Exception:
            return ""

    def _fetch_with_beautifulsoup(self, url: str) -> str:
        """Method 2: BeautifulSoup - manual scraping with selectors"""
        if not url or not url.startswith("http"):
            return ""
        
        try:
            session = requests.Session()
            session.headers.update(HEADERS)
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            
            if resp.status_code != 200:
                return ""
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Remove junk
            for tag in soup(["nav", "footer", "script", "style", "aside", "header"]):
                tag.decompose()
            
            # Try common article selectors
            for selector in ["article", "div.article-body", "div.story-body",
                              "div.entry-content", "div.post-content", "main"]:
                el = soup.select_one(selector)
                if el:
                    text = el.get_text(separator=" ", strip=True)
                    if len(text) > MIN_ARTICLE_LENGTH:
                        return text[:3000]
            
            # Fallback: get all body text
            text = soup.get_text(separator=" ", strip=True)
            return text[:2000] if len(text) > MIN_ARTICLE_LENGTH else ""
            
        except Exception:
            return ""

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into word-based chunks with overlap."""
        words  = text.split()
        chunks = []
        start  = 0
        while start < len(words):
            end   = min(start + CHUNK_TOKENS, len(words))
            chunk = " ".join(words[start:end])
            if chunk.strip():
                chunks.append(chunk)
            if end >= len(words):
                break
            start = end - CHUNK_OVERLAP
        return chunks