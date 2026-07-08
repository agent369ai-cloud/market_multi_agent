# Ichiba Merchant Support Assistant (IMSA)

A prototype multi-agent merchant support assistant built with FastAPI and a LangGraph-based agent workflow. It accepts merchant queries and routes them across agents for planning, RAG, SQL/API retrieval, synthesis, and guardrail review.

## Features

- FastAPI backend with `/ask` support endpoint
- Pydantic request/response validation
- Modular agent graph pipeline defined in `graph_flow.py`
- Includes router, planner, memory, RAG, SQL, API, synthesizer, critic, and guardrail agents
- Synthesizer uses a real LLM call (Groq, OpenAI-compatible client)
- RAG uses real semantic search (Cohere embeddings + Pinecone)
- SQL uses a real Postgres database (via Docker Compose)
- Memory persists real conversation turns per session in Postgres
- Listing-status API is a real standalone FastAPI microservice (`listing_api_service/`), called over HTTP
- React (Vite) frontend in `frontend/`

## Requirements

- Python 3.11+
- Node.js 18+ (for the frontend)
- Docker (for the local Postgres database)
- `venv` or other virtual environment
- API keys: Groq, Cohere, Pinecone

## Setup

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate   # .venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in real values for `GROQ_API_KEY`, `COHERE_API_KEY`, `PINECONE_API_KEY`, `PINECONE_ENV`:

```bash
cp .env.example .env
```

3. Start the local Postgres database:

```bash
docker compose up -d
```

This creates the `merchant_listings`, `campaign_records`, and `conversation_turns` tables and seeds the first two from `db/init.sql` on first run.

4. Create and seed the Pinecone index (one-time, or whenever you update the doc corpus):

```bash
python scripts/seed_pinecone.py
```

5. (Optional) Install and run the frontend:

```bash
cd frontend
npm install
npm run dev
```

## Configuration

The app uses `config.py` for the following settings (all read from `.env`):

- `GROQ_API_KEY`, `GROQ_API_BASE`, `MODEL_NAME` — LLM used by the synthesizer agent
- `COHERE_API_KEY`, `COHERE_EMBED_MODEL` — embeddings for RAG
- `PINECONE_API_KEY`, `PINECONE_ENV`, `PINECONE_INDEX_NAME` — vector search for RAG
- `DATABASE_URL` — Postgres connection string for the SQL and memory agents (defaults to the `docker-compose.yml` credentials)
- `LISTING_API_BASE_URL` — base URL of the listing-status microservice (defaults to `http://127.0.0.1:8100`)
- `ENV` — environment mode

## Run

Three processes, each in its own terminal:

```bash
# 1. main app
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# 2. listing-status microservice (used by the API agent)
uvicorn listing_api_service.main:app --reload --host 0.0.0.0 --port 8100

# 3. frontend (optional)
cd frontend && npm run dev
```

Then open:

- Health check: `http://127.0.0.1:8000/`
- Support endpoint: `http://127.0.0.1:8000/ask`
- Interactive API docs: `http://127.0.0.1:8000/docs`
- Listing-status microservice: `http://127.0.0.1:8100/`
- Frontend (if running): `http://127.0.0.1:5173`

## Testing the agents

`scripts/test_agents.py` drives the full LangGraph pipeline directly (no server needed) across all four routes, plus unit-style checks on the critic and guardrail agents:

```bash
python scripts/test_agents.py
```

## API

### POST /ask

Request body:

```json
{
  "merchant_id": "merchant-123",
  "language": "en",
  "query": "How can I resolve a billing issue?",
  "session_id": "session-abc"
}
```

Response body:

```json
{
  "merchant_id": "merchant-123",
  "query": "How can I resolve a billing issue?",
  "route": "...",
  "plan": ["..."],
  "evidence": [
    {
      "source": "...",
      "source_type": "...",
      "confidence": 0.9,
      "content": "...",
      "metadata": {}
    }
  ],
  "final_answer": "...",
  "status": "success"
}
```

## Project structure

- `app.py` — FastAPI app entrypoint
- `config.py` — application settings
- `models.py` — request/response and evidence models
- `graph_flow.py` — agent workflow graph definition
- `agents.py` — agent implementations (router, planner, memory, RAG, SQL, API, synthesizer, critic, guardrail, memory_writer)
- `tools.py` — data-source integrations used by the agents (Pinecone/Cohere RAG, Postgres SQL, Postgres-backed memory, HTTP call to the listing microservice)
- `listing_api_service/` — standalone FastAPI microservice mocking an external listing-status API, backed by the same Postgres data
- `requirements.txt` — Python dependencies
- `docker-compose.yml`, `db/init.sql` — local Postgres database for the SQL and memory agents
- `scripts/seed_pinecone.py` — creates and seeds the Pinecone index used for RAG
- `scripts/test_agents.py` — drives the full agent pipeline across all routes for testing
- `frontend/` — React (Vite) chat UI
- `SampleRequest01.JSON`, `SampleRequest02.JSON` — sample requests

## Notes

This is a proof-of-concept repository. You should secure API keys and validate external agent integrations before production use.

## Contributing

Contributions are welcome. Please see `CONTRIBUTING.md` for guidelines on reporting issues, submitting pull requests, and preparing code changes.

