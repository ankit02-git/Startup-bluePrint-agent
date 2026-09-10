# Startup Blueprint Generator Agent

> **Problem Statement #20** - An AI-powered RAG agent that transforms raw startup ideas into complete, actionable business blueprints using **IBM Granite** (watsonx.ai) and Retrieval-Augmented Generation (RAG).

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)
![React](https://img.shields.io/badge/React-18-blue?logo=react)
![IBM Granite](https://img.shields.io/badge/IBM%20Granite-4--h--small-blue?logo=ibm)
![License](https://img.shields.io/badge/License-MIT-green)

---

## What It Does

Describe your startup idea in plain English. The agent:

1. **Retrieves** relevant knowledge from its vector database (market data, funding, legal, GTM strategies, startup ecosystem)
2. **Augments** the prompt with retrieved context (RAG)
3. **Generates** a complete, structured blueprint using **IBM Granite 4** via watsonx.ai
4. **Delivers** a 10-section blueprint covering every aspect of launching a startup

### Blueprint Sections Generated

| Section | Description |
|---------|-------------|
| Executive Summary | Problem, solution, market opportunity |
| Business Model Canvas | All 9 BMC components with specifics |
| Market Analysis | TAM/SAM/SOM, competitors, trends |
| Revenue Model | Pricing strategy, Year 1/2/3 projections |
| Estimated Budget | Startup costs, team plan, funding needs |
| Go-To-Market Strategy | ICP, channels, launch plan, first 100 customers |
| Funding Roadmap | Investors, government schemes, accelerators |
| Legal & Compliance | Entity structure, IP, regulations |
| Technology Stack | IBM Cloud/watsonx integration + tech architecture |
| 90-Day Action Plan | Week-by-week milestones |

---

## Architecture

```
+-------------------------------------------------------------+
|                    React Frontend (Port 3000)               |
|       Idea Input > Section Tabs > Download Blueprint        |
+---------------------------+---------------------------------+
                            | REST API
+---------------------------v---------------------------------+
|                   FastAPI Backend (Port 8000)               |
|   /api/blueprint   /api/blueprint/section   /api/health     |
+----------+-----------------------------+--------------------+
           |                             |
+----------v--------------+  +----------v------------------+
|   RAG Engine            |  |   IBM Granite Client        |
|   Pure-Python vector    |  |   ibm-watsonx-ai SDK 1.7.1  |
|   store (cosine sim)    |  |   ibm/granite-4-h-small     |
|   sentence-transformers |  |   IBM Cloud Lite (Free)     |
+----------+--------------+  +-----------------------------+
           |
+----------v---------------------------------------------+
|         Knowledge Base (6 Documents)                   |
|  startup_funding        market_research                |
|  revenue_models         legal_requirements             |
|  gtm_strategy           startup_ecosystem              |
+--------------------------------------------------------+
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **LLM** | IBM Granite 4 Hybrid Small (ibm/granite-4-h-small) |
| **Cloud** | IBM Cloud Lite (Free Tier - no credit card needed) |
| **Vector Store** | Pure-Python cosine similarity (no native build deps) |
| **Embeddings** | sentence-transformers - all-MiniLM-L6-v2 |
| **Backend** | Python 3.10+ / FastAPI / Uvicorn |
| **Frontend** | React 18 / Axios / Custom Markdown Renderer |

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- IBM Cloud Lite account (free) with watsonx.ai

### Step 1 - Clone the repo

```bash
git clone https://github.com/ankit02-git/Startup-bluePrint-agent.git
cd Startup-bluePrint-agent
```

### Step 2 - IBM Cloud Setup (Free, 10 minutes)

1. Register at https://cloud.ibm.com/registration
2. Go to https://dataplatform.cloud.ibm.com and create a new project
3. Copy the **Project ID** from Manage > General
4. Generate an **API Key** at https://cloud.ibm.com/iam/apikeys

### Step 3 - Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env and fill in WATSONX_API_KEY and WATSONX_PROJECT_ID

# Start the server
uvicorn main:app --reload --port 8000
```

### Step 4 - Frontend Setup

```bash
cd frontend
npm install --legacy-peer-deps
npm start
```

Open http://localhost:3000

---

## Configuration

Edit `backend/.env` (copy from `.env.example`):

```env
WATSONX_API_KEY=your_ibm_cloud_api_key
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_PROJECT_ID=your_watsonx_project_id
GRANITE_MODEL_ID=ibm/granite-4-h-small
```

> **Important:** `backend/.env` is git-ignored. Never commit real credentials.
> Use `.env.example` as the template - it is safe to commit.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/health | Health check + IBM config status |
| POST | /api/blueprint | Generate complete 10-section blueprint |
| POST | /api/blueprint/section | Generate a single section |
| GET | /api/rag/search?query=... | Debug RAG retrieval |
| POST | /api/rag/ingest | Re-ingest knowledge base |
| GET | /docs | Interactive Swagger UI |

### Example Request

```bash
curl -X POST http://localhost:8000/api/blueprint \
  -H "Content-Type: application/json" \
  -d '{
    "idea": "An AI app for Indian farmers to detect crop diseases by photo, with government subsidy recommendations.",
    "industry": "AgriTech",
    "target_market": "India"
  }'
```

---

## Knowledge Base

Six domain-expert documents are pre-seeded. Add your own `.txt` files to `backend/knowledge_base/` and call `POST /api/rag/ingest` to re-index.

| File | Content |
|------|---------|
| startup_funding.txt | Pre-seed to Series C, VCs, SISFS, SBIR, YC, angels |
| market_research.txt | TAM/SAM/SOM, industry sizes, Porter's 5 Forces |
| revenue_models.txt | 10 revenue models, BMC guide, unit economics |
| legal_requirements.txt | Entity types, DPIIT, patents, SAFE notes, GDPR |
| gtm_strategy.txt | ICP, PLG/SLG, PIRATE metrics, launch playbooks |
| startup_ecosystem.txt | India/global hubs, IBM programs, grants |

---

## Project Structure

```
startup-blueprint-agent/
+-- .gitignore
+-- README.md
+-- backend/
|   +-- main.py                    # FastAPI application and all routes
|   +-- requirements.txt           # Python dependencies
|   +-- .env.example               # Credentials template (safe to commit)
|   +-- setup_and_run.sh           # Linux/macOS one-command setup
|   +-- setup_and_run.ps1          # Windows PowerShell setup
|   +-- knowledge_base/
|   |   +-- startup_funding.txt
|   |   +-- market_research.txt
|   |   +-- revenue_models.txt
|   |   +-- legal_requirements.txt
|   |   +-- gtm_strategy.txt
|   |   +-- startup_ecosystem.txt
|   +-- rag/
|   |   +-- rag_engine.py          # Pure-Python vector store + retrieval
|   |   +-- granite_client.py      # IBM Granite (watsonx.ai) client
|   +-- agents/
|       +-- blueprint_agent.py     # Main orchestration agent
+-- frontend/
    +-- package.json
    +-- public/index.html
    +-- src/
        +-- index.js
        +-- index.css              # Dark-theme design system
        +-- App.js                 # Full SPA with custom markdown renderer
```

---

## Extending the Project

- **Add domain knowledge**: Drop `.txt` files into `backend/knowledge_base/` then call `POST /api/rag/ingest`
- **New blueprint sections**: Add entries to `SECTION_PROMPTS` in `agents/blueprint_agent.py`
- **Change IBM model**: Update `GRANITE_MODEL_ID` in `.env`

---

## License

MIT License - Built for IBM Startup Blueprint Generator Challenge - Problem Statement #20