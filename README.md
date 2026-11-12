# FinAlly — AI Trading Workstation

A Bloomberg-style trading terminal with live streaming prices, a simulated $10,000 portfolio, and an LLM assistant that can analyze positions and place trades from natural language. Built entirely by coding agents as an agentic-AI course capstone.

## Features

- Live watchlist with price flashes and sparklines (SSE)
- Market-order trading: instant fill, no fees
- Portfolio heatmap, P&L chart, positions table
- AI chat that trades and manages the watchlist

## Stack

Single Docker container on port 8000:

- **Backend:** FastAPI + `uv`, SQLite
- **Frontend:** Next.js (static export) + Tailwind + Recharts
- **Market data:** built-in GBM simulator, or Massive API if a key is set
- **LLM:** LiteLLM → OpenRouter (`gpt-oss-120b` on Cerebras), structured outputs

## Configuration

Create `.env` in the project root:

```bash
OPENROUTER_API_KEY=   # required for AI chat only
MASSIVE_API_KEY=      # optional; empty uses the simulator
LLM_MOCK=false        # true for deterministic mock LLM (tests)
SIM_SEED=             # optional; reproducible simulator prices
```

## Run

```bash
docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally
```

Open <http://localhost:8000>. (Dockerfile and start/stop scripts are not built yet.)

## Status

- Done: market data component (`backend/`, see `planning/MARKET_DATA_SUMMARY.md`)
- To do: portfolio/watchlist/chat APIs, frontend, Docker, E2E tests

Full spec: [`planning/PLAN.md`](planning/PLAN.md)

## License

See [LICENSE](LICENSE).
