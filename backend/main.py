from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from services.company_service import load_companies
from routers import companies, analyze, status, results, download


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load company names from cleaned Excel."""
    load_companies()  # raises RuntimeError if Excel missing
    yield


app = FastAPI(
    title="ESG Intelligence Platform",
    description="Multi-Source Agentic AI System for Corporate Sustainability Analysis",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies.router)
app.include_router(analyze.router)
app.include_router(status.router)
app.include_router(results.router)
app.include_router(download.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)