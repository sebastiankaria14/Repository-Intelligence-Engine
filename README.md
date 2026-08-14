# Repository Intelligence Engine (RIE)

> **An MRI for your codebase** — AI-powered software intelligence platform that analyzes GitHub repositories using knowledge graphs, vector search, and local LLMs.

![Status](https://img.shields.io/badge/status-Phase%201-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## What is RIE?

RIE clones a GitHub repository, parses its source code, and builds a connected knowledge base covering:

- **Architecture Discovery** — auto-detect MVC, layered, hexagonal, microservices patterns
- **API Discovery** — REST/GraphQL/gRPC endpoints with request lifecycle mapping
- **Database Intelligence** — ER diagrams, migration history, ORM analysis
- **Dependency Intelligence** — service dependency graphs, impact analysis
- **Git Intelligence** — ownership, hotspots, change coupling, contributor stats
- **Security Intelligence** — Semgrep, CodeQL, Joern — linked to the dependency graph
- **Performance Intelligence** — N+1 queries, circular deps, heavy endpoints
- **Technical Debt** — dead code, duplication, god classes, effort estimation
- **AI Chat** — natural-language queries grounded in the knowledge graph

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Parsing** | Tree-sitter, ts-morph, JavaParser, ANTLR |
| **Static Analysis** | Semgrep, CodeQL, Joern |
| **Git** | GitPython, pygit2, libgit2 |
| **Knowledge Graph** | Neo4j (Memgraph-compatible interface) |
| **Vector Search** | Qdrant |
| **Full-Text Search** | Meilisearch |
| **AI Models** | Ollama (DeepSeek Coder, Qwen, Llama 3) |
| **Backend** | FastAPI, Celery, Redis |
| **Database** | PostgreSQL |
| **Frontend** | React, TypeScript, Tailwind CSS, React Flow, Cytoscape.js, Recharts |
| **Deployment** | Docker Compose |

## Prerequisites

- **Docker** & **Docker Compose** (v2+)
- **≥16 GB RAM** (for all services + Ollama models)
- **≥50 GB disk** (Ollama models ~15-20 GB)
- **Git** installed locally

## Quick Start

```bash
# 1. Clone the repository
git clone <repo-url>
cd repository-intelligence-engine

# 2. Copy the environment file
cp .env.example .env

# 3. Start all services
docker compose up -d

# 4. Wait for all services to be healthy
docker compose ps

# 5. Open the dashboard
open http://localhost:3000

# 6. Or use the API directly
curl http://localhost:8000/health
```

### First-time setup notes

- The `ollama-init` service will pull 3 AI models (~15-20 GB total) on first run. This takes time.
- Neo4j takes ~30s to start. The backend waits for it automatically.
- All data is persisted in Docker volumes.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/repositories` | Submit a GitHub URL for analysis |
| `GET` | `/api/repositories/{id}/status` | Pipeline progress |
| `GET` | `/api/repositories/{id}/architecture` | Architecture analysis |
| `GET` | `/api/repositories/{id}/apis` | Discovered endpoints |
| `GET` | `/api/repositories/{id}/database` | Database schema |
| `GET` | `/api/repositories/{id}/dependencies` | Dependency graph |
| `GET` | `/api/repositories/{id}/git-insights` | Git history intelligence |
| `GET` | `/api/repositories/{id}/security` | Security findings |
| `GET` | `/api/repositories/{id}/performance` | Performance findings |
| `GET` | `/api/repositories/{id}/technical-debt` | Debt assessment |
| `GET` | `/api/repositories/{id}/graph` | Knowledge graph (Cytoscape.js) |
| `POST` | `/api/repositories/{id}/chat` | AI chat with citations |
| `WS` | `/ws/scan/{repo_id}` | Real-time scan progress |

## Development

```bash
# Backend (without Docker)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (without Docker)
cd frontend
npm install
npm run dev

# Run tests
cd backend && pytest -v
cd frontend && npm test
```

## Architecture

```
Presentation (React) → API (FastAPI) → Analysis Modules
                                        ↓
                         Knowledge Graph (Neo4j) + Vector (Qdrant) + Search (Meilisearch)
                                        ↓
                              AI Chat (Ollama / RAG)
```

## Project Structure

```
repository-intelligence-engine/
├── docker-compose.yml          # All 10 services
├── .env.example                # Environment template
├── .github/workflows/ci.yml    # CI pipeline
├── backend/
│   ├── app/
│   │   ├── api/                # FastAPI routers
│   │   ├── core/               # Config, database, security, logging
│   │   ├── models/             # SQLAlchemy + Pydantic models
│   │   ├── parsing/            # Tree-sitter / ts-morph / JavaParser
│   │   ├── analysis/           # Architecture, API, DB, deps, git, security, perf, debt
│   │   ├── graph/              # Neo4j driver (interface-based)
│   │   ├── vector/             # Qdrant client
│   │   ├── search/             # Meilisearch client
│   │   ├── ai/                 # Ollama client + RAG
│   │   └── tasks/              # Celery pipeline
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/         # Sidebar, Header
│   │   ├── views/              # All 8 dashboard views
│   │   └── lib/                # API + WebSocket clients
│   ├── Dockerfile
│   └── package.json
└── infra/
    └── postgres/init.sql
```

## License

MIT
