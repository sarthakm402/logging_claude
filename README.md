# logging_claude

A self-hosted analytics dashboard for **Claude Code usage**. Claude Code emits OpenTelemetry (OTLP) logs and metrics; this project collects them, stores them in PostgreSQL, and shows tokens, cost, models, users, latency and prompt/response history in a React dashboard. Sessions can be grouped into **projects** so you can see usage per project.

## How it works

```
Claude Code ──OTLP (4317 gRPC / 4318 HTTP)──▶ OpenTelemetry Collector
                                                │  ├─ debug (stdout)
                                                │  ├─ file → otel-logs/logs.json, metrics.json
                                                │  └─ OTLP/HTTP → FastAPI backend (:8000)
                                                ▼
                                        FastAPI  /v1/logs, /v1/metrics
                                                │
                                                ▼
                                          PostgreSQL
                                                │
                                   /api/dashboard/*, /api/projects/*
                                                ▼
                                    React + Vite dashboard (:5173)
```

The backend decodes OTLP protobuf (gzip supported) and handles these Claude Code events:

- `claude_code.user_prompt` → `prompts`
- `claude_code.api_request` → `api_requests` (model, token counts, cost, duration, time-to-first-token)
- `claude_code.assistant_response` → `responses`

Metrics (sum and gauge types) are received on `/v1/metrics`.

## Tech stack

- **Backend:** Python, FastAPI, Uvicorn, psycopg 3, `opentelemetry-proto`
- **Database:** PostgreSQL
- **Collector:** OpenTelemetry Collector (contrib)
- **Frontend:** React 19, Vite, Recharts

## Project structure

```
.
├── app.py                      # FastAPI app: OTLP ingestion + dashboard/project APIs
├── db.py                       # DB connection + schema creation (init_db)
├── docker-compose.yml          # postgres, otel-collector, backend, frontend
├── otel-collector-config.yaml  # collector pipelines (logs & metrics)
├── otel-logs/                  # raw logs/metrics written by the collector
├── requirements.txt
└── frontend/                   # React dashboard
    └── src/
        ├── api/dashboard.js    # API client
        ├── pages/Dashboard.jsx
        └── components/         # MetricCard, TokenChart, CostChart, ModelTable,
                                # UserTable, ActivityTable, Performance, ProjectManager
```

## Database schema

`users`, `projects`, `sessions`, `prompts`, `api_requests`, `responses` — created automatically by `db.py` (`CREATE TABLE IF NOT EXISTS`), with indexes on request/prompt timestamps and session id.

## Getting started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker (for PostgreSQL and the collector)

### 1. Start PostgreSQL and the collector

```bash
docker compose up -d postgres otel-collector
```

> `docker-compose.yml` also defines `backend` and `frontend` services that use `build:`, which expects a `Dockerfile` in the repo root and in `frontend/`. If those aren't present yet, run the backend and frontend locally as shown below.

### 2. Configure the backend

Create a `.env` file in the project root:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=claude_usage
POSTGRES_USER=claude
POSTGRES_PASSWORD=<your-password>
```

Use the same values as in `docker-compose.yml`, and change the default password for anything beyond local use.

### 3. Run the backend

```bash
pip install -r requirements.txt
python db.py                      # create tables
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API docs: http://localhost:8000/docs

### 4. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The API URL defaults to `http://localhost:8000`; override it with `VITE_API_URL`.

### 5. Point Claude Code at the collector

Set these environment variables before launching Claude Code:

```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_LOGS_EXPORTER=otlp
export OTEL_METRICS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
# Needed to capture prompt/response text:
export OTEL_LOG_USER_PROMPTS=1
```

Use Claude Code as usual and data will start appearing on the dashboard.

## API overview

**Ingestion**

| Method | Path | Description |
| --- | --- | --- |
| POST | `/v1/logs` | OTLP logs receiver |
| POST | `/v1/metrics` | OTLP metrics receiver |

**Dashboard (global)** — all `GET`

`/api/dashboard/summary`, `/tokens`, `/cost`, `/models`, `/users`, `/activity`, `/sessions`, `/performance`, `/prompts/{prompt_id}`

**Projects**

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/projects` | Create a project |
| GET | `/api/projects` | List projects |
| GET | `/api/projects/{id}` | Project details |
| DELETE | `/api/projects/{id}` | Delete a project |
| POST | `/api/sessions/{session_id}/project` | Assign a session to a project |
| DELETE | `/api/sessions/{session_id}/project` | Remove a session from its project |

**Per-project dashboard** — `GET /api/dashboard/projects/{id}/` followed by `summary`, `sessions`, `tokens`, `cost`, `models`, `users`, `activity`, or `performance`.

## Notes

- CORS currently allows only `http://localhost:5173`; edit `app.py` if you serve the frontend elsewhere.
- The collector's `otlp_http` exporters target `host.docker.internal:8000`, so the backend should run on the host (or adjust the endpoint when running it inside Compose).
- Don't commit real credentials; keep secrets in `.env` (already git-ignored).

## License

See [LICENSE](LICENSE).
