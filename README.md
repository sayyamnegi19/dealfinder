# Deal Finder — AI price comparison across Amazon.in & Flipkart

Search once. An AI agent queries live marketplace data through **MCP servers**, groups
identical products, compares prices, and recommends the best deal — streaming its progress
to the browser.

```
┌──────────────────────────────┐
│ React 19 + TS + Tailwind     │  search bar → POST /api/search
│ (Vite dev server :5173)      │  EventSource → /api/search/{id}/stream  (SSE)
└──────────────┬───────────────┘
               │ /api proxy
┌──────────────▼───────────────┐
│ Django 6 (ASGI, uvicorn :8000)│
│  ┌─────────────────────────┐ │
│  │ Pydantic AI agent        │ │  FallbackModel chain:
│  │  tool: search_marketplaces│ │  google:gemini-3.5-flash-lite → groq:openai/gpt-oss-120b
│  ├─────────────────────────┤ │
│  │ MCP pool (failover)      │ │  stdio MCP servers, priority order
│  └───────┬─────────────────┘ │
└──────────┼───────────────────┘
   stdio   ├─ india-retail-intelligence   (Amazon.in + Flipkart scraper, live)
           └─ demo-fallback                (deterministic sample data, clearly labelled)
                     │
              ┌──────▼──────┐
              │ PostgreSQL  │  searches · product groups · offers · agent events
              └─────────────┘
```

## Features

- **Live marketplace data** via MCP servers (Amazon.in + Flipkart), fetched on demand.
- **MCP failover pool** — servers are tried in priority order; if one is blocked/down the next
  one is used, ending with clearly-labelled demo data so the app never dead-ends.
- **AI agent** (Pydantic AI) with a free-model fallback chain and a strict structured output
  contract — the model groups listings and picks the best deal, but prices/URLs always come
  from real fetched data (no hallucinated prices).
- **Streaming UX** — every agent step (server attempts, listings found, comparison) is streamed
  to the browser over SSE and persisted for replay.
- **Postgres persistence** — searches, product groups, offers, agent runs and events.

## Stack

| Layer    | Choice |
|----------|--------|
| Frontend | React 19, TypeScript, Vite 8, Tailwind CSS v4 |
| Backend  | Django 6, Django REST Framework, uvicorn (ASGI) |
| Agent    | Pydantic AI 2.x, `FallbackModel` (Gemini → Groq, both free tiers) |
| Data     | PostgreSQL 18 |
| Market pages | MCP servers over stdio (FastMCP 4) |

## Repository layout

```
New_Project/
├── backend/
│   ├── config/                  Django settings/urls/asgi
│   ├── apps/deals/              models, serializers, API views, SSE, runner bridge
│   ├── agent/                   Pydantic AI agent: llm.py, schemas.py, tools.py, finder.py, run.py
│   ├── mcp_layer/               MCP pool: config, adapters, pool, types, check CLI
│   ├── mcp_servers/             vendored amazon/flipkart MCP server (see attribution below)
│   └── fallback_mcp/            demo fallback MCP server + sample data
├── frontend/                    React app (Vite)
├── mcp_servers.json             MCP pool configuration (priority order, tools, timeouts)
├── .env / .env.example          secrets & configuration
└── README.md
```

## Setup (local dev, no Docker)

Prerequisites: **Python 3.12+**, **Node 20+**, **PostgreSQL 16+** running locally.

### 1. Database

```bash
createdb dealfinder        # or: psql -U postgres -c "CREATE DATABASE dealfinder;"
```

### 2. Environment

```bash
cp .env.example .env
# edit .env:
#   GEMINI_API_KEY=...   (free: https://aistudio.google.com)
#   GROQ_API_KEY=...     (free: https://console.groq.com)
#   DB_PASSWORD=...      (your local postgres password)
```

### 3. Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium     # browsers for the Amazon scraping fallback
.venv/bin/python manage.py migrate
.venv/bin/uvicorn config.asgi:application --reload --port 8000
```

### 4. Frontend (second terminal)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api to :8000)
```

## CLI tools (no server needed)

```bash
# 1) Probe the MCP pool directly (verifies live scraping + failover)
.venv/bin/python -m mcp_layer.check "sony wh-1000xm5"
.venv/bin/python -m mcp_layer.check "iphone 15" --force-fallback

# 2) Run the full agent from the terminal
.venv/bin/python -m agent.run "sony wh-1000xm5 headphones"
.venv/bin/python -m agent.run "boat rockerz 450" --force-fallback --json

# 3) Headless end-to-end UI test (drives the real page, saves screenshots)
.venv/bin/python scripts/ui_check.py /tmp/dealfinder-ui
```

## API

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/search/` | POST | Create a search `{query, sites?, limit?}` → `{id}` |
| `/api/search/{id}/` | GET | Full result (groups, offers, summary, caveats) |
| `/api/search/{id}/stream` | GET | **SSE** stream of agent events; starts the run for a pending search |
| `/api/searches/` | GET | Recent searches |
| `/api/health/mcp/` | GET | MCP pool status (`?probe=1` actually connects to each server) |

SSE event types: `status`, `tool_started`, `search_completed`, `llm_tool_call`,
`llm_tool_result`, `result_ready`, `error`, `done` (carries the full result).

Quick test without the UI:

```bash
curl -s -X POST localhost:8000/api/search/ -H 'Content-Type: application/json' \
  -d '{"query": "sony wh-1000xm5"}'            # → {"id": "...", ...}
curl -N localhost:8000/api/search/<id>/stream   # watch events live
```

## How the MCP layer works

- `mcp_servers.json` lists servers in priority order with their tool mappings and timeouts.
  `{python}` / `{backend}` placeholders are substituted at load time.
- `MCPPool.search()` tries servers in order; the **first one that returns listings wins**.
  A server that errors (blocked, timeout, dead process) is recorded and skipped — the next
  server is tried. Only when *no live server responds successfully* is the demo fallback used
  (or always, with `MCP_FORCE_FALLBACK=1`).
- Each server's raw tool output is normalized into one `Offer` shape by the adapters in
  `mcp_layer/adapters.py`.
- Every attempt (server, ok/fail, latency, count) is streamed to the UI, so you can see exactly
  which server answered.
- Adding a server (e.g. Bright Data / Firecrawl / any HTTP MCP server) is a config change in
  `mcp_servers.json`, not a code change.

### Attribution

`backend/mcp_servers/retail_intel_server.py` is vendored from
[`balaadityaai/mcp-india-retail-intelligence`](https://github.com/balaadityaai/mcp-india-retail-intelligence)
(MIT). It was adapted only for SDK compatibility: the published package still imports
`mcp.server.fastmcp`, which MCP 2.x removed, so the server here uses `from fastmcp import FastMCP`
and takes the proxy URL through httpx's `proxy=` parameter. Scraper logic is unchanged.

## The agent

- One tool: `search_marketplaces(query)` → runs the MCP pool, stores offers, returns a **compact**
  list (`id`, `site`, `title`, `price`, `mrp`, `discount_pct`, `rating`, `url`, `is_sample`).
- The model must reference listings **by id** in its structured `DealReport` — so prices and URLs
  in the UI always come from fetched data, never from the model.
- A tool-call cap, compact payloads and a 2-4 sentence output keep token usage low (free tiers
  are token-limited). If the primary LLM hits an API error/rate limit, `FallbackModel` switches
  providers automatically.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Amazon listings missing (HTTP 503) | Amazon blocks plain HTTP scrapers; install Playwright (`playwright install chromium`) — the vendored server auto-falls back to a real browser. A proxy (`RETAIL_INTEL_PROXY`) also works. |
| `fe_sendauth: no password supplied` | `DB_PASSWORD` missing in `.env`. |
| SSE looks frozen in the UI | Check `GET /api/health/mcp/?probe=1`; run the backend with `uvicorn` (ASGI), not `runserver`, so async streaming works. |
| All results labelled **sample** | Every live server failed for that query; retry later or check the MCP probe. |
| LLM rate-limit / 429 | Reorder `LLM_CHAIN` in `.env` (e.g. put `groq:...` first), or wait for the daily quota reset. |

## Limitations (development build)

- Scraping marketplaces is best-effort and against their ToS — keep volume low, personal use.
- The agent runs inside the SSE request; there is no background worker (no Redis/Celery by
  design). A backend restart mid-search leaves that search in `running`.
- Single-process only: the "who starts the run" claim is a DB row update, fine for dev scale.

## Roadmap ideas

- Price history & drop alerts (Postgres already `offer`-ready)
- Watchlist + auth
- More marketplaces (Croma, Reliance Digital, quick-commerce) via extra MCP servers
- Paid scraping MCP (Bright Data / Firecrawl) as a higher-priority pool entry
