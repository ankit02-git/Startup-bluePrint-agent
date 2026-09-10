"""
Startup Blueprint Generator Agent - FastAPI Backend
"""
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from pydantic import BaseModel, Field

_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")


# ─────────────────────────────────────────────
# Lifespan: pre-warm RAG engine on startup
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing RAG engine and ingesting knowledge base...")
    try:
        from rag.rag_engine import get_rag_engine
        engine = get_rag_engine()
        count = engine.ingest_knowledge_base()
        logger.info("Knowledge base ready: %d chunks indexed.", count)
    except Exception as e:
        logger.warning("RAG initialization failed (non-fatal): %s", e)
    yield
    logger.info("Shutting down Startup Blueprint Agent.")


app = FastAPI(
    title="Startup Blueprint Generator Agent",
    description=(
        "AI-powered startup blueprint generation using RAG + IBM Granite. "
        "Transforms raw startup ideas into complete, actionable business blueprints."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────

class BlueprintRequest(BaseModel):
    idea: str = Field(
        ...,
        min_length=20,
        max_length=2000,
        description="Startup idea description (20-2000 characters)",
        example="An AI-powered platform for farmers to get real-time crop disease detection using smartphone photos, with connections to local agronomists and government subsidy information.",
    )
    industry: Optional[str] = Field(
        default=None,
        description="Industry vertical (optional hint for better context retrieval)",
        example="AgriTech",
    )
    target_market: Optional[str] = Field(
        default=None,
        description="Target market geography",
        example="India",
    )


class SectionRequest(BaseModel):
    idea: str = Field(..., min_length=20, max_length=2000)
    section: str = Field(
        ...,
        description="Section name to generate",
        example="market_analysis",
    )


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
    """Check system health, IBM Granite configuration, and knowledge base status."""
    from rag.rag_engine import get_rag_engine
    from rag.granite_client import get_granite_client, GRANITE_MODEL_ID

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
    """
    Generate a complete startup blueprint from a raw startup idea.
    
    The blueprint includes:
    - Executive Summary
    - Business Model Canvas
    - Market Analysis (TAM/SAM/SOM + competitors)
    - Revenue Model with pricing strategy
    - Estimated Budget and funding needs
    - Go-To-Market Strategy
    - Funding Roadmap (investors, grants, accelerators)
    - Legal & Compliance roadmap
    - Technology Stack (including IBM Cloud/watsonx)
    - 90-Day Action Plan
    """
    from agents.blueprint_agent import get_blueprint_agent
    from rag.granite_client import GRANITE_MODEL_ID

    # Enrich the idea with optional context
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
                "Please set WATSONX_API_KEY and WATSONX_PROJECT_ID in your .env file. "
                "Get free credentials at cloud.ibm.com (IBM Cloud Lite account)."
            ),
        )

    start = time.time()
    try:
        result = agent.generate_full_blueprint(enriched_idea)
    except Exception as e:
        logger.error("Blueprint generation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    elapsed = round(time.time() - start, 2)

    return BlueprintResponse(
        idea=request.idea,
        sections=result["sections"],
        raw_blueprint=result["raw_blueprint"],
        generation_time_seconds=elapsed,
        model_used=GRANITE_MODEL_ID,
    )


@app.post("/api/blueprint/section", response_model=SectionResponse, tags=["Blueprint"])
async def generate_section(request: SectionRequest):
    """
    Generate a single section of the startup blueprint.
    
    Available sections:
    - executive_summary
    - business_model_canvas
    - market_analysis
    - revenue_model
    - estimated_budget
    - go_to_market
    - funding_roadmap
    - legal_compliance
    - tech_stack
    """
    from agents.blueprint_agent import get_blueprint_agent, SECTION_PROMPTS
    from rag.granite_client import GRANITE_MODEL_ID

    if request.section not in SECTION_PROMPTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section '{request.section}'. Valid sections: {list(SECTION_PROMPTS.keys())}",
        )

    agent = get_blueprint_agent()

    if not agent.llm.is_configured():
        raise HTTPException(
            status_code=503,
            detail="IBM watsonx.ai is not configured. Please set WATSONX_API_KEY and WATSONX_PROJECT_ID.",
        )

    start = time.time()
    try:
        content = agent.generate_section(request.idea, request.section)
    except Exception as e:
        logger.error("Section generation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    elapsed = round(time.time() - start, 2)

    return SectionResponse(
        section=request.section,
        content=content,
        generation_time_seconds=elapsed,
        model_used=GRANITE_MODEL_ID,
    )


@app.post("/api/rag/ingest", tags=["RAG"])
async def reingest_knowledge_base(background_tasks: BackgroundTasks):
    """Trigger re-ingestion of the knowledge base documents into ChromaDB."""
    from rag.rag_engine import get_rag_engine

    def _reingest():
        engine = get_rag_engine()
        count = engine.ingest_knowledge_base(force_reingest=True)
        logger.info("Re-ingestion complete: %d chunks.", count)

    background_tasks.add_task(_reingest)
    return {"message": "Knowledge base re-ingestion started in background."}


@app.get("/api/rag/search", tags=["RAG"])
async def search_knowledge_base(query: str, n_results: int = 5):
    """Search the RAG knowledge base for relevant chunks (for debugging)."""
    from rag.rag_engine import get_rag_engine

    engine = get_rag_engine()
    results = engine.retrieve(query, n_results=n_results)

    return {
        "query": query,
        "results": [
            {"document": doc[:300] + "...", "source": source, "distance": dist}
            for doc, source, dist in results
        ],
    }


@app.get("/api/sections", tags=["Blueprint"])
async def list_sections():
    """List all available blueprint sections."""
    from agents.blueprint_agent import SECTION_PROMPTS
    return {"sections": list(SECTION_PROMPTS.keys())}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )
