# FinAlly — AI Trading Workstation

## Project Specification

## 1. Vision

FinAlly (Finance Ally) is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot.

This is the capstone project for an agentic AI coding course. It is built entirely by Coding Agents demonstrating how orchestrated AI agents can produce a production-quality full-stack application. Agents interact through files in `planning/`.

## 2. User Experience

### First Launch

The user runs a single Docker command (or a provided start script). A browser opens to `http://localhost:8000`. No login, no signup. They immediately see:

- A watchlist of 10 default tickers with live-updating prices in a grid
- $10,000 in virtual cash
- A dark, data-rich trading terminal aesthetic
- An AI chat panel ready to assist

### What the User Can Do

- **Watch prices stream** — prices flash green (uptick) or red (downtick) with subtle CSS animations that fade
- **View sparkline mini-charts** — price action beside each ticker in the watchlist, accumulated on the frontend from the SSE stream since page load (sparklines fill in progressively)
- **Click a ticker** to see a larger detailed chart in the main chart area
- **Buy and sell shares** — market orders only, instant fill at current price, no fees, no confirmation dialog
- **Monitor their portfolio** — a heatmap (treemap) showing positions sized by weight and colored by P&L, plus a P&L chart tracking total portfolio value over time
- **View a positions table** — ticker, quantity, average cost, current price, unrealized P&L, % change
- **Chat with the AI assistant** — ask about their portfolio, get analysis, and have the AI execute trades and manage the watchlist through natural language
- **Manage the watchlist** — add/remove tickers manually or via the AI chat

### Visual Design

- **Dark theme**: backgrounds around `#0d1117` or `#1a1a2e`, muted gray borders, no pure black
- **Price flash animations**: brief green/red background highlight on price change, fading over ~500ms via CSS transitions
- **Connection status indicator**: a small colored dot (green = connected, yellow = reconnecting, red = disconnected) visible in the header
- **Professional, data-dense layout**: inspired by Bloomberg/trading terminals — every pixel earns its place
- **Responsive but desktop-first**: optimized for wide screens, functional on tablet

### Color Scheme
- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991` (submit buttons)

## 3. Architecture Overview

### Single Container, Single Port

```
┌─────────────────────────────────────────────────┐
│  Docker Container (port 8000)                   │
│                                                 │
│  FastAPI (Python/uv)                            │
│  ├── /api/*          REST endpoints             │
│  ├── /api/stream/*   SSE streaming              │
│  └── /*              Static file serving         │
│                      (Next.js export)            │
│                                                 │
│  SQLite database (volume-mounted)               │
│  Background task: market data polling/sim        │
└─────────────────────────────────────────────────┘
```

- **Frontend**: Next.js with TypeScript, built as a static export (`output: 'export'`), served by FastAPI as static files
- **Backend**: FastAPI (Python), managed as a `uv` project
- **Database**: SQLite, single file at `db/finally.db`, volume-mounted for persistence
- **Real-time data**: Server-Sent Events (SSE) — simpler than WebSockets, one-way server→client push, works everywhere
- **AI integration**: LiteLLM → OpenRouter (Cerebras for fast inference), with structured outputs for trade execution
- **Market data**: Environment-variable driven — simulator by default, real data via Massive API if key provided

### Why These Choices

| Decision | Rationale |
|---|---|
| SSE over WebSockets | One-way push is all we need; simpler, no bidirectional complexity, universal browser support |
| Static Next.js export | Single origin, no CORS issues, one port, one container, simple deployment |
| SQLite over Postgres | No auth = no multi-user = no need for a database server; self-contained, zero config |
| Single Docker container | Students run one command; no docker-compose for production, no service orchestration |
| uv for Python | Fast, modern Python project management; reproducible lockfile; what students should learn |
| Market orders only | Eliminates order book, limit order logic, partial fills — dramatically simpler portfolio math |

---

## 4. Directory Structure

```
finally/
├── frontend/                 # Next.js TypeScript project (static export)
├── backend/                  # FastAPI uv project (Python)
│   └── db/                   # Schema definitions, seed data, migration logic
├── planning/                 # Project-wide documentation for agents
│   ├── PLAN.md               # This document
│   └── ...                   # Additional agent reference docs
├── scripts/
│   ├── start_mac.sh          # Launch Docker container (macOS/Linux)
│   ├── stop_mac.sh           # Stop Docker container (macOS/Linux)
│   ├── start_windows.ps1     # Launch Docker container (Windows PowerShell)
│   └── stop_windows.ps1      # Stop Docker container (Windows PowerShell)
├── test/                     # Playwright E2E tests + docker-compose.test.yml
├── db/                       # Volume mount target (SQLite file lives here at runtime)
│   └── .gitkeep              # Directory exists in repo; finally.db is gitignored
├── Dockerfile                # Multi-stage build (Node → Python)
├── docker-compose.yml        # Optional convenience wrapper
├── .env                      # Environment variables (gitignored, .env.example committed)
└── .gitignore
```

### Key Boundaries

- **`frontend/`** is a self-contained Next.js project. It knows nothing about Python. It talks to the backend via `/api/*` endpoints and `/api/stream/*` SSE endpoints. Internal structure is up to the Frontend Engineer agent.
- **`backend/`** is a self-contained uv project with its own `pyproject.toml`. It owns all server logic including database initialization, schema, seed data, API routes, SSE streaming, market data, and LLM integration. Internal structure is up to the Backend/Market Data agents.
- **`backend/db/`** contains schema SQL definitions and seed logic. The backend lazily initializes the database on first request — creating tables and seeding default data if the SQLite file doesn't exist or is empty.
- **`db/`** at the top level is the runtime volume mount point. The SQLite file (`db/finally.db`) is created here by the backend and persists across container restarts via Docker volume.
- **`planning/`** contains project-wide documentation, including this plan. All agents reference files here as the shared contract.
- **`test/`** contains Playwright E2E tests and supporting infrastructure (e.g., `docker-compose.test.yml`). Unit tests live within `frontend/` and `backend/` respectively, following each framework's conventions.
- **`scripts/`** contains start/stop scripts that wrap Docker commands.

---

## 5. Environment Variables

```bash
# Required for LLM chat (the rest of the app works without it; chat returns a clear "no API key configured" message)
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional: Massive (Polygon.io) API key for real market data
# If not set, the built-in market simulator is used (recommended for most users)
MASSIVE_API_KEY=

# Optional: Set to "true" for deterministic mock LLM responses (testing)
LLM_MOCK=false

# Optional: integer seed for the market simulator, making price paths reproducible (E2E tests)
SIM_SEED=
```

### Behavior

- If `MASSIVE_API_KEY` is set and non-empty → backend uses Massive REST API for market data
- If `MASSIVE_API_KEY` is absent or empty → backend uses the built-in market simulator
- If `LLM_MOCK=true` → backend returns deterministic mock LLM responses (for E2E tests)
- In Docker, environment variables are supplied only via `--env-file .env` (there is no `.env` inside the container). For local non-Docker development the backend loads `.env` from the project root.
- If `OPENROUTER_API_KEY` is missing the app still starts normally; only `/api/chat` is affected (returns a friendly error message).
- If `SIM_SEED` is set, the simulator uses it for its random generator (deterministic paths).

---

## 6. Market Data

### Two Implementations, One Interface

Both the simulator and the Massive client implement the same abstract interface. The backend selects which to use based on the environment variable. All downstream code (SSE streaming, price cache, frontend) is agnostic to the source.

### Simulator (Default)

- Generates prices using geometric Brownian motion (GBM) with configurable drift and volatility per ticker
- Updates at ~500ms intervals
- Correlated moves across tickers (e.g., tech stocks move together)
- Occasional random "events" — sudden 2-5% moves on a ticker for drama
- Starts from realistic seed prices (e.g., AAPL ~$190, GOOGL ~$175, etc.)
- Tickers not in the seed list (e.g., a user-added `PYPL`) get a random seed price between $50 and $300 with default drift/volatility
- Ignores market hours — prices move 24/7
- The seed price is the session reference price used for daily change % (see below)
- Runs as an in-process background task — no external dependencies

### Massive API (Optional)

- REST API polling (not WebSocket) — simpler, works on all tiers
- Polls for the union of all watched tickers on a configurable interval
- Free tier (5 calls/min): poll every 15 seconds
- Paid tiers: poll every 2-15 seconds depending on tier
- Parses REST response into the same format as the simulator
- The previous day's close is the reference price for daily change %
- Prices are static outside trading hours (flat sparklines, no flashes) — this is acceptable
- Invalid tickers are detected when adding to the watchlist (the add is rejected with 404 `unknown_ticker`)
- Massive-specific data must never be required by a feature; everything downstream uses the common price format

### Shared Price Cache

- A single background task (simulator or Massive poller) writes to an in-memory price cache
- The cache holds the latest price, previous price, session reference price, and timestamp for each ticker
- Daily change % = (price − reference price) / reference price, computed by the backend and sent in each SSE event
- The set of tickers tracked (simulated or polled) is the union of the watchlist and tickers with open positions, so held positions keep live prices even after removal from the watchlist
- Ticker normalization/validation (all entry points: REST, chat): trimmed, uppercased, must match `^[A-Z][A-Z.]{0,4}$`; watchlist max 50 tickers
- SSE streams read from this cache and push updates to connected clients
- This architecture supports future multi-user scenarios without changes to the data layer

### SSE Streaming

- Endpoint: `GET /api/stream/prices`
- Long-lived SSE connection; client uses native `EventSource` API
- Server pushes price updates for all tickers known to the system at a regular cadence (~500ms) — in the single-user model this is equivalent to the user's watchlist
- Each SSE event contains ticker, price, previous price, reference price, daily change %, timestamp, and change direction (`up`/`down`/`flat`)
- Client handles reconnection automatically (EventSource has built-in retry)

---

## 7. Database

### SQLite with Lazy Initialization

The backend checks for the SQLite database on startup (or first request). If the file doesn't exist or tables are missing, it creates the schema and seeds default data. This means:

- No separate migration step
- No manual database setup
- Fresh Docker volumes start with a clean, seeded database automatically

### Schema

All tables include a `user_id` column defaulting to `"default"`. This is hardcoded for now (single-user) but enables future multi-user support without schema migration.

**users_profile** — User state (cash balance)
- `id` TEXT PRIMARY KEY (default: `"default"`)
- `cash_balance` REAL (default: `10000.0`)
- `created_at` TEXT (ISO timestamp)

**watchlist** — Tickers the user is watching
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `added_at` TEXT (ISO timestamp)
- PRIMARY KEY `(user_id, ticker)` (no separate UUID id)

**positions** — Current holdings (one row per ticker per user)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `quantity` REAL (fractional shares supported; always > 0 — a row is deleted when fully sold)
- `avg_cost` REAL (unchanged by sells; recomputed as a weighted average on buys)
- `updated_at` TEXT (ISO timestamp)
- PRIMARY KEY `(user_id, ticker)` (no separate UUID id)

**trades** — Trade history (append-only log)
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `side` TEXT (`"buy"` or `"sell"`)
- `quantity` REAL (fractional shares supported)
- `price` REAL
- `executed_at` TEXT (ISO timestamp)

**portfolio_snapshots** — Portfolio value over time (for P&L chart). Recorded every 30 seconds by a background task, and immediately after each trade execution. An initial snapshot at $10,000 is seeded with the default data so the chart is never empty. `/api/portfolio/history` returns at most the latest 1000 snapshots, oldest first.
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `user_id` TEXT (default: `"default"`)
- `total_value` REAL
- `recorded_at` TEXT (ISO timestamp)

**chat_messages** — Conversation history with LLM
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `user_id` TEXT (default: `"default"`)
- `role` TEXT (`"user"` or `"assistant"`)
- `content` TEXT
- `actions` TEXT (JSON — trades executed, watchlist changes made; null for user messages)
- `created_at` TEXT (ISO timestamp)

### Default Seed Data

- One user profile: `id="default"`, `cash_balance=10000.0`
- Ten watchlist entries: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX

---

## 8. API Endpoints

### Market Data
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stream/prices` | SSE stream of live price updates |

### Portfolio
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/portfolio` | Current positions, cash balance, total value, unrealized P&L |
| POST | `/api/portfolio/trade` | Execute a trade: `{ticker, quantity, side}` |
| GET | `/api/portfolio/history` | Portfolio value snapshots over time (for P&L chart) |

### Trading Rules
- Market orders only, filled instantly at the current cached price; no fees
- No short selling, no margin: a buy requires `quantity × price ≤ cash`; a sell requires `quantity ≤ shares held`
- Quantity must be > 0. Fractional shares are allowed; quantities are rounded to the nearest tenth of a share (0.1) *(provisional — see open questions)*
- Selling the entire position deletes the position row. Partial sells leave `avg_cost` unchanged; buys recompute it as a weighted average
- All trade execution (manual or LLM-initiated) goes through one function guarded by a single asyncio lock and a SQLite transaction, so concurrent trades cannot race
- After every successful trade a portfolio snapshot is recorded

### Watchlist
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/watchlist` | Current watchlist tickers with last cached price (for initial render; live updates come from SSE) |
| POST | `/api/watchlist` | Add a ticker: `{ticker}` |
| DELETE | `/api/watchlist/{ticker}` | Remove a ticker |

### Chat
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Send a message, receive complete JSON response (message + executed actions) |

### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check (for Docker/deployment) |

### Response Shapes

Errors always use a non-2xx status and the body `{"error": "<code>", "message": "<human readable>"}`. Codes: `validation_error` (400), `unknown_ticker` (404), `insufficient_cash` (400), `insufficient_shares` (400), `no_api_key` / `llm_error` (chat only, 200 with an explanatory `message`, not an HTTP error).

`GET /api/portfolio`:
```json
{
  "cash_balance": 8100.50,
  "total_value": 10250.75,
  "total_pnl": 250.75,
  "total_pnl_pct": 2.51,
  "positions": [
    {"ticker": "AAPL", "quantity": 10.0, "avg_cost": 190.00, "current_price": 195.25,
     "market_value": 1952.50, "unrealized_pnl": 52.50, "unrealized_pnl_pct": 2.76}
  ]
}
```
`total_pnl` is measured against the $10,000 starting balance.

`POST /api/portfolio/trade` request `{"ticker": "AAPL", "quantity": 10, "side": "buy"}`; success returns `{"trade": {"ticker","side","quantity","price","executed_at"}, "portfolio": <same shape as GET /api/portfolio>}`.

`GET /api/portfolio/history`: `{"snapshots": [{"total_value": 10000.0, "recorded_at": "<ISO>"}, ...]}`

`GET /api/watchlist`: `{"watchlist": [{"ticker": "AAPL", "price": 190.12, "previous_price": 190.05, "reference_price": 189.00, "change_pct": 0.59}, ...]}`

`POST /api/watchlist` `{"ticker"}` returns the new watchlist entry; `DELETE /api/watchlist/{ticker}` returns `{"removed": "AAPL"}`.

`POST /api/chat` request `{"message": "..."}`; response:
```json
{
  "message": "Bought 10 AAPL. (Note: could not buy 5 TSLA — insufficient cash.)",
  "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10, "status": "executed", "price": 190.12},
             {"ticker": "TSLA", "side": "buy", "quantity": 5, "status": "failed", "error": "insufficient_cash"}],
  "watchlist_changes": [{"ticker": "PYPL", "action": "add", "status": "executed"}]
}
```

SSE event (`/api/stream/prices`), one event per ticker update, JSON `data`:
`{"ticker": "AAPL", "price": 190.12, "previous_price": 190.05, "reference_price": 189.00, "change_pct": 0.59, "direction": "up", "timestamp": "<ISO>"}`

---

## 9. LLM Integration

When writing code to make calls to LLMs, use cerebras-inference skill to use LiteLLM via OpenRouter to the `openrouter/openai/gpt-oss-120b` model with Cerebras as the inference provider. Structured Outputs should be used to interpret the results.

There is an OPENROUTER_API_KEY in the .env file in the project root.

### How It Works

When the user sends a chat message, the backend:

1. Loads the user's current portfolio context (cash, positions with P&L, watchlist with live prices, total portfolio value)
2. Loads the most recent 20 messages from the `chat_messages` table (bounds prompt size)
3. Constructs a prompt with a system message, portfolio context, conversation history, and the user's new message
4. Calls the LLM via LiteLLM → OpenRouter, requesting structured output, using the cerebras-inference skill
5. Parses the complete structured JSON response
6. Auto-executes any trades or watchlist changes specified in the response
7. Stores the message and executed actions in `chat_messages`
8. Returns the complete JSON response to the frontend (no token-by-token streaming — Cerebras inference is fast enough that a loading indicator is sufficient)

### Structured Output Schema

The LLM is instructed to respond with JSON matching this schema:

```json
{
  "message": "Your conversational response to the user",
  "trades": [
    {"ticker": "AAPL", "side": "buy", "quantity": 10}
  ],
  "watchlist_changes": [
    {"ticker": "PYPL", "action": "add"}
  ]
}
```

- `message` (required): The conversational text shown to the user
- `trades` (optional): Array of trades to auto-execute. Each trade goes through the same validation as manual trades (sufficient cash for buys, sufficient shares for sells)
- `watchlist_changes` (optional): Array of watchlist modifications. Adds go through the same ticker validation as manual adds (an unpriceable/unknown ticker fails with `unknown_ticker`)
- At most 10 actions (trades + watchlist changes combined) are executed per response; the rest are ignored and reported as skipped
- Before implementation, verify with the cerebras-inference skill that JSON-schema `response_format` works for this model/provider route
- If the LLM output is malformed or fails schema validation, nothing is executed and the user gets a generic "I couldn't process that response, please try again" message (stored in history like any other reply)

### Auto-Execution

Trades specified by the LLM execute automatically — no confirmation dialog. This is a deliberate design choice:
- It's a simulated environment with fake money, so the stakes are zero
- It creates an impressive, fluid demo experience
- It demonstrates agentic AI capabilities — the core theme of the course

Actions execute independently, in the order given: if one fails validation (e.g., insufficient cash) the others still run. There is no second LLM call — the backend records each action's result (`executed` / `failed` with an error code) in the response's `trades` / `watchlist_changes` arrays and appends a short plain-text note about any failures to `message`, so the user always sees what actually happened.

### System Prompt Guidance

The LLM should be prompted as "FinAlly, an AI trading assistant" with instructions to:
- Analyze portfolio composition, risk concentration, and P&L
- Suggest trades with reasoning
- Execute trades when the user asks or agrees
- Manage the watchlist proactively
- Be concise and data-driven in responses
- Always respond with valid structured JSON

### LLM Mock Mode

When `LLM_MOCK=true`, the backend returns deterministic mock responses instead of calling OpenRouter. This enables:
- Fast, free, reproducible E2E tests
- Development without an API key
- CI/CD pipelines

Mock rules (first match wins, case-insensitive):
- message contains `buy` → buys 1 share of `AAPL` (or of the first ticker-looking word in the message, if any), reply "Mock: bought 1 AAPL."
- message contains `sell` → sells 1 share of `AAPL`
- message contains `add <TICKER>` → adds that ticker to the watchlist
- anything else → reply "Mock: I'm FinAlly, your AI trading assistant." with no actions

The mock goes through the same execution path as the real LLM, so trade validation and failure reporting are exercised.

---

## 10. Frontend Design

### Layout

The frontend is a single-page application with a dense, terminal-inspired layout. The specific component architecture and layout system is up to the Frontend Engineer, but the UI should include these elements:

- **Watchlist panel** — grid/table of watched tickers with: ticker symbol, current price (flashing green/red on change), daily change %, and a sparkline mini-chart (accumulated from SSE since page load)
- **Main chart area** — larger chart for the currently selected ticker, with at minimum price over time. Clicking a ticker in the watchlist selects it here.
- **Portfolio heatmap** — treemap visualization where each rectangle is a position, sized by portfolio weight, colored by P&L (green = profit, red = loss)
- **P&L chart** — line chart showing total portfolio value over time, using data from `portfolio_snapshots`
- **Positions table** — tabular view of all positions: ticker, quantity, avg cost, current price, unrealized P&L, % change
- **Trade bar** — simple input area: ticker field, quantity field, buy button, sell button. Market orders, instant fill.
- **AI chat panel** — docked/collapsible sidebar. Message input, scrolling conversation history, loading indicator while waiting for LLM response. Trade executions and watchlist changes shown inline as confirmations.
- **Header** — portfolio total value (updating live), total P&L vs. the $10,000 starting balance (amount and %), connection status indicator, cash balance

### Technical Notes

- Use `EventSource` for SSE connection to `/api/stream/prices`
- Use **Recharts** for all charts (sparklines, main price chart, P&L line chart, and the portfolio treemap) — a single charting library
- The main chart and sparklines accumulate data from the SSE stream since page load, so they start empty after a refresh; this is accepted
- Single-page app, no dynamic routes: the selected ticker lives in client state. UI state (selected ticker, chat collapsed) is not persisted across reloads
- Development: run the backend on `:8000` (`uv run uvicorn ...`) and the frontend with `next dev`, with `rewrites` in `next.config` proxying `/api/*` to `http://localhost:8000` (rewrites apply only in dev; the static export is served by FastAPI in production)
- Price flash effect: on receiving a new price, briefly apply a CSS class with background color transition, then remove it
- All API calls go to the same origin (`/api/*`) — no CORS configuration needed
- Tailwind CSS for styling with a custom dark theme

---

## 11. Docker & Deployment

### Multi-Stage Dockerfile

```
Stage 1: Node 20 slim
  - Copy frontend/
  - npm install && npm run build (produces static export)

Stage 2: Python 3.12 slim
  - Install uv
  - Copy backend/
  - uv sync (install Python dependencies from lockfile)
  - Copy frontend build output into a static/ directory
  - Expose port 8000
  - CMD: uvicorn serving FastAPI app
```

FastAPI serves the static frontend files and all API routes on port 8000.

### Docker Volume

The SQLite database persists via a named Docker volume:

```bash
docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally
```

The container always uses the named volume above; the backend writes `finally.db` to `/app/db`. The `db/` directory in the project root (with its `.gitkeep`) is used only when running the backend locally outside Docker.

The image builds for both `amd64` and `arm64` (base images are multi-arch). Add a `.gitattributes` with `*.sh text eol=lf` so shell scripts keep LF line endings when checked out on Windows.

### Start/Stop Scripts

**`scripts/start_mac.sh`** (macOS/Linux):
- Builds the Docker image if not already built (or if `--build` flag passed)
- Runs the container with the volume mount, port mapping, and `.env` file
- Waits for `GET /api/health` to succeed before continuing
- Prints the URL to access the app
- Opens the browser by default; pass `--no-open` (`-NoOpen` in PowerShell) to skip

**`scripts/stop_mac.sh`** (macOS/Linux):
- Stops and removes the running container
- Does NOT remove the volume (data persists)

**`scripts/start_windows.ps1`** / **`scripts/stop_windows.ps1`**: PowerShell equivalents for Windows.

All scripts should be idempotent — safe to run multiple times.

### Optional Cloud Deployment

The container is designed to deploy to AWS App Runner, Render, or any container platform. A Terraform configuration for App Runner may be provided in a `deploy/` directory as a stretch goal, but is not part of the core build.

---

## 12. Testing Strategy

### Unit Tests (within `frontend/` and `backend/`)

**Backend (pytest)**:
- Market data: simulator generates valid prices, GBM math is correct, Massive API response parsing works, both implementations conform to the abstract interface
- Portfolio: trade execution logic, P&L calculations, edge cases (selling more than owned, buying with insufficient cash, selling at a loss)
- LLM: structured output parsing handles all valid schemas, graceful handling of malformed responses, trade validation within chat flow
- API routes: correct status codes, response shapes, error handling

**Frontend (React Testing Library or similar)**:
- Component rendering with mock data
- Price flash animation triggers correctly on price changes
- Watchlist CRUD operations
- Portfolio display calculations
- Chat message rendering and loading state

### E2E Tests (in `test/`)

**Infrastructure**: Playwright runs from the host (`npx playwright test` in `test/`) against the app on `localhost:8000`. `test/docker-compose.test.yml` only starts the app container, with an ephemeral (tmpfs / throwaway) volume so every run starts from a fresh seeded database. This keeps browser dependencies out of the production image without a second container.

**Environment**: Tests run with `LLM_MOCK=true` and a fixed `SIM_SEED` by default for speed and determinism. Because prices are still random, tests assert on structure and direction (e.g. prices change, cash decreases after a buy), not exact values.

**Key Scenarios**:
- Fresh start: default watchlist appears, $10k balance shown, prices are streaming
- Add and remove a ticker from the watchlist
- Buy shares: cash decreases, position appears, portfolio updates
- Sell shares: cash increases, position updates or disappears
- Portfolio visualization: heatmap renders with correct colors, P&L chart has data points
- AI chat (mocked): send a message, receive a response, trade execution appears inline
- SSE resilience: disconnect and verify reconnection


---

## 13. Open Questions

Review feedback has been incorporated into the sections above. Remaining open items:

1. **Quantity/money rounding (Section 8, Trading Rules)** — "round to the nearest tenth" is currently interpreted as share quantities rounded to 0.1 share. Confirm: is that intended, or did you mean something else (e.g. prices/cash shown to the nearest cent)? Note a 0.1-share granularity means `buy 0.05` would round to 0.1 (or 0 → rejected).
