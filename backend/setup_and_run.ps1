# Startup Blueprint Generator — Backend PowerShell Setup
Write-Host "======================================" -ForegroundColor Cyan
Write-Host " Startup Blueprint Generator Agent" -ForegroundColor Cyan
Write-Host " Backend Setup (Windows / PowerShell)" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# Create virtual environment
Write-Host "`n[1/5] Creating Python virtual environment..." -ForegroundColor Yellow
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "[2/5] Installing Python dependencies..." -ForegroundColor Yellow
pip install --upgrade pip
pip install -r requirements.txt

# Setup .env
if (-not (Test-Path ".env")) {
    Write-Host "[3/5] Creating .env from template..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host ""
    Write-Host "ACTION REQUIRED: Edit .env with your IBM Cloud credentials:" -ForegroundColor Red
    Write-Host "  WATSONX_API_KEY=your_api_key" -ForegroundColor White
    Write-Host "  WATSONX_PROJECT_ID=your_project_id" -ForegroundColor White
    Write-Host "  Get free account: https://cloud.ibm.com/registration" -ForegroundColor Cyan
} else {
    Write-Host "[3/5] .env already exists. Skipping." -ForegroundColor Green
}

# Ingest knowledge base
Write-Host "[4/5] Ingesting knowledge base into ChromaDB..." -ForegroundColor Yellow
python -c @"
import sys
sys.path.insert(0, '.')
from rag.rag_engine import get_rag_engine
engine = get_rag_engine()
count = engine.ingest_knowledge_base(force_reingest=True)
print(f'Ingested {count} chunks into vector store.')
"@

# Start server
Write-Host "`n[5/5] Starting FastAPI server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Server:      http://localhost:8000" -ForegroundColor Green
Write-Host "  API Docs:    http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  Health:      http://localhost:8000/api/health" -ForegroundColor Green
Write-Host ""
uvicorn main:app --reload --host 0.0.0.0 --port 8000
