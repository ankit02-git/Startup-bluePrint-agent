#!/bin/bash
# Setup and run script for the Startup Blueprint Generator Agent Backend

echo "======================================"
echo " Startup Blueprint Generator Agent"
echo " Backend Setup (FastAPI + IBM Granite)"
echo "======================================"
echo ""

# Create virtual environment
echo "[1/5] Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "[2/5] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Setup .env file
if [ ! -f .env ]; then
    echo "[3/5] Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  ACTION REQUIRED: Edit .env and fill in your IBM Cloud credentials:"
    echo "   WATSONX_API_KEY=your_key_here"
    echo "   WATSONX_PROJECT_ID=your_project_id_here"
    echo ""
    echo "   Get free credentials at: https://cloud.ibm.com/registration"
    echo "   Then create a watsonx.ai project at: https://dataplatform.cloud.ibm.com"
    echo ""
else
    echo "[3/5] .env file already exists. Skipping."
fi

# Ingest knowledge base
echo "[4/5] Ingesting knowledge base into ChromaDB..."
python3 -c "
import sys
sys.path.insert(0, '.')
from rag.rag_engine import get_rag_engine
engine = get_rag_engine()
count = engine.ingest_knowledge_base(force_reingest=True)
print(f'  ✅ Ingested {count} chunks into vector store.')
"

# Start server
echo "[5/5] Starting FastAPI server..."
echo ""
echo "  🚀 Server: http://localhost:8000"
echo "  📚 API Docs: http://localhost:8000/docs"
echo "  🏥 Health Check: http://localhost:8000/api/health"
echo ""
uvicorn main:app --reload --host 0.0.0.0 --port 8000
