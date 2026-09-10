"""
FastAPI application — Vercel serverless compatible version.
Differences from local main.py:
  - No lifespan pre-warming (serverless functions are stateless per request)
  - RAG engine and Granite client use lazy singleton init
  - Knowledge base .txt files are read from api/knowledge_base/
  - vector_store.json is written to /tmp (only writable dir in Vercel)
  - CORS allows all origins (Vercel preview URLs are dynamic)
"""
import logging
import os
import time
from typing import Optional
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Load .env if present locally (no-op on Vercel — env vars are set in dashboard)
_ENV_PATH = Path(__file__).parent.parent / "backend" / ".env"
if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH, override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Startup Blueprint Generator Agent",
    description=(
        "AI-powered startup blueprint generation using RAG + IBM Granite. "
        "Transforms raw startup ideas into complete, actionable business blueprints."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────

class BlueprintRequest(BaseModel):
    idea: str = Field(..., min_length=20, max_length=2000)
    industry: Optional[str] = None
    target_market: Optional[str] = None


class SectionRequest(BaseModel):
    idea: str = Field(..., min_length=20, max_length=2000)
    section: str


class HealthResponse(BaseModel):
    status: str
    ibm_granite_configured: bool
    knowledge_base_chunks: int
    model_id: str
    version: str


class BlueprintResponse(BaseModel):
    idea: str
    sections: dict
    raw_blueprint: str
    generation_time_seconds: float
    model_used: str


class SectionResponse(BaseModel):
    section: str
    content: str
    generation_time_seconds: float
    model_used: str


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Startup Blueprint Generator Agent API",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    from rag_engine import get_rag_engine
    from granite_client import get_granite_client, GRANITE_MODEL_ID

    engine = get_rag_engine()
    client = get_granite_client()

    try:
        kb_count = engine.count()
    except Exception:
        kb_count = 0

    return HealthResponse(
        status="healthy",
        ibm_granite_configured=client.is_configured(),
        knowledge_base_chunks=kb_count,
        model_id=GRANITE_MODEL_ID,
        version="1.0.0",
    )


@app.post("/api/blueprint", response_model=BlueprintResponse, tags=["Blueprint"])
async def generate_blueprint(request: BlueprintRequest):
    from blueprint_agent import get_blueprint_agent
    from granite_client import GRANITE_MODEL_ID

    enriched_idea = request.idea
    if request.industry:
        enriched_idea += f" (Industry: {request.industry})"
    if request.target_market:
        enriched_idea += f" (Target Market: {request.target_market})"

    agent = get_blueprint_agent()

    if not agent.llm.is_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "IBM watsonx.ai is not configured. "
                "Set WATSONX_API_KEY and WATSONX_PROJECT_ID in Vercel environment variables."
            ),
        )

    start = time.time()
    try:
        result = agent.generate_full_blueprint(enriched_idea)
    except Exception as e:
        logger.error("Blueprint generation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    return BlueprintResponse(
        idea=request.idea,
        sections=result["sections"],
        raw_blueprint=result["raw_blueprint"],
        generation_time_seconds=round(time.time() - start, 2),
        model_used=GRANITE_MODEL_ID,
    )


@app.post("/api/blueprint/section", response_model=SectionResponse, tags=["Blueprint"])
async def generate_section(request: SectionRequest):
    from blueprint_agent import get_blueprint_agent, SECTION_PROMPTS
    from granite_client import GRANITE_MODEL_ID

    if request.section not in SECTION_PROMPTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section '{request.section}'. Valid: {list(SECTION_PROMPTS.keys())}",
        )

    agent = get_blueprint_agent()

    if not agent.llm.is_configured():
        raise HTTPException(status_code=503, detail="IBM watsonx.ai not configured.")

    start = time.time()
    try:
        content = agent.generate_section(request.idea, request.section)
    except Exception as e:
        logger.error("Section generation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    return SectionResponse(
        section=request.section,
        content=content,
        generation_time_seconds=round(time.time() - start, 2),
        model_used=GRANITE_MODEL_ID,
    )


@app.post("/api/rag/ingest", tags=["RAG"])
async def reingest_knowledge_base(background_tasks: BackgroundTasks):
    from rag_engine import get_rag_engine

    def _reingest():
        engine = get_rag_engine()
        count = engine.ingest_knowledge_base(force_reingest=True)
        logger.info("Re-ingestion complete: %d chunks.", count)

    background_tasks.add_task(_reingest)
    return {"message": "Knowledge base re-ingestion started."}


@app.get("/api/rag/search", tags=["RAG"])
async def search_knowledge_base(query: str, n_results: int = 5):
    from rag_engine import get_rag_engine
    engine = get_rag_engine()
    results = engine.retrieve(query, n_results=n_results)
    return {
        "query": query,
        "results": [
            {"document": doc[:300] + "...", "source": source, "score": score}
            for doc, source, score in results
        ],
    }


@app.get("/api/sections", tags=["Blueprint"])
async def list_sections():
    from blueprint_agent import SECTION_PROMPTS
    return {"sections": list(SECTION_PROMPTS.keys())}
