# Review of Uncommitted Changes

Scope: `.claude/settings.json`, `planning/PLAN.md`, new `.claude/agents/reviewer.md`, new `.claude/commands/doc-review.md`.

## Summary

The PLAN.md edits are a clear improvement. They close real gaps: trading rules, response shapes, error codes, mock-LLM rules and concurrency. The main problem is that the plan now contradicts the already-finished market data code. There are also several under-specified edge cases (below). Nothing is blocking for the tooling files.

## High priority: plan vs. existing market data code

The CLAUDE.md says market data is complete. The new PLAN.md requires things the code in `backend/app/market/` does not do (verified in `models.py`, `cache.py`, `stream.py`, `simulator.py`):

1. **No reference price or daily change %.** `PriceUpdate` has only ticker, price, previous_price, timestamp, and derived change, change_percent, direction. The plan requires `reference_price` and `change_pct` (vs. reference). Existing `change_percent` is vs. the previous tick, not the session reference, and is named differently. Needs a work item: add reference price to the cache and the sim/Massive sources (seed price / previous-day close).
2. **SSE format mismatch.** The plan says "one event per ticker update" with `{ticker, price, ..., change_pct, direction, timestamp: ISO}`. The code emits a single `data:` event containing a dict of all tickers, only when the cache version changes, with a Unix-float timestamp. Decide which is canonical and update the other. The plan's ISO timestamp vs. the code's Unix seconds also needs resolving.
3. **`SIM_SEED` unsupported.** The simulator uses the global `np.random` and `random` modules. Seeding requires a per-instance `numpy.random.Generator` and `random.Random` (and the unknown-ticker `random.uniform(50,300)` must use it too). Also note that timing-driven loops mean seeded paths are only reproducible per tick count, not per wall clock.
4. **Tracked set = watchlist + open positions.** Nothing in the plan says who calls `add_ticker`/`remove_ticker` on the source when the watchlist or positions change (e.g. selling the last share of a ticker that is not on the watchlist must stop tracking it). Define an owner (the trade/watchlist service).
5. **Cache removal.** `PriceCache.remove` exists, but the plan must say not to call it for tickers with open positions.

Recommendation: add a short "Delta vs. completed market data" subsection to PLAN.md listing these, so the backend agent knows it must modify finished code.

## Spec gaps and inconsistencies in PLAN.md

- **Rounding (Open Question 1).** Rounding quantity to 0.1 contradicts "fractional shares supported" and makes `buy 0.05` unusable. Money values are stored as REAL floats; specify rounding cash/prices to cents (or store integer cents) and round before the cash check, so `quantity x price <= cash` is not subject to float drift. Suggest resolving: quantities to 4 decimals (or 0.01), money to 2 decimals.
- **Price unavailable.** A trade or watchlist add for a valid-format ticker with no cached price yet (just added, Massive poll pending) is undefined. Add an error code (e.g. `price_unavailable`, 503) and say `GET /api/watchlist` returns `price: null` for such entries.
- **Unknown ticker semantics differ by source.** With the simulator every regex-valid ticker is "known" (random seed price), so `unknown_ticker` never fires. State that explicitly, and note E2E tests cannot test `unknown_ticker` in sim mode. With Massive, validating on add costs an API call against a 5/min free tier; say how this is handled (e.g. validate via the next poll, or a single-ticker lookup).
- **Missing error cases.** Not defined: duplicate watchlist add (idempotent 200 or 409?), watchlist full (50) code, DELETE of a ticker not on the list (404 which code?), FastAPI's default 422 validation response vs. the plan's 400 `validation_error` (needs a custom exception handler), unknown `/api/*` paths falling through to static serving.
- **Trade ticker not on watchlist.** The trade bar accepts any ticker. Does a successful buy auto-add it to tracking? (The "union" rule implies tracking, but say so.)
- **Ticker regex.** `^[A-Z][A-Z.]{0,4}$` allows `A.`, `A..B`. Prefer `^[A-Z]{1,5}(\.[A-Z]{1,2})?$` unless intentional.
- **Mock LLM rules.** "First ticker-looking word" is ambiguous: after uppercasing, "buy", "me", "a" all look like tickers. Specify a case-sensitive match on the original text, or an explicit pattern such as `buy <qty?> <TICKER>`, and exclude the command word itself. The reply "Mock: bought 1 AAPL." is hard-coded though the ticker can differ. Rule ordering ("buy" before "add") means "add NVDA and buy" hits buy; fine but document.
- **Chat response statuses.** Examples show `executed`/`failed`, but the 10-action cap reports "skipped". Add `skipped` to the enum and a reason field. Also the persisted `actions` column format is unspecified (reuse the response arrays).
- **LLM errors.** `no_api_key`/`llm_error` are listed as "200 with message", but the response shape for these (are `trades`/`watchlist_changes` empty arrays?) should be stated. Also add a timeout and whether the user message is stored when the LLM fails.
- **LLM-supplied quantities.** Chat trades pass through the 0.1 rounding; a model request for 0.04 shares would round to 0 and fail. Report as `validation_error` explicitly.
- **Daily change % naming.** For the simulator the reference is the seed price at process start, so "daily change" resets on every restart and drifts from "today". Either call it "session change" in the UI or persist the reference. Consider that after a restart with persisted positions, P&L continuity is fine but sparklines/ref reset.
- **SSE volume.** One event per ticker per 500ms for up to 50 tickers is ~100 events/s, including "flat" ones. For Massive (polled every 15s) it would repeat identical data. Suggest sending only on change (the existing version-based approach), plus an initial snapshot on connect.
- **Concurrency wording.** "Single asyncio lock and a SQLite transaction": if the sqlite3 driver is synchronous, it blocks the event loop; specify `aiosqlite` or `run_in_threadpool`. State uvicorn must run a single worker (in-memory cache and lock are per process).
- **Portfolio snapshots.** The 30s snapshot task and trade snapshots can interleave; fine under the lock, but say whether the snapshot value uses cache prices at that instant. 1000 snapshots at 30s is ~8 hours of history; the chart will silently window. Acceptable, but note it or downsample.
- **Initial snapshot** timestamp is seed time; after a long idle the chart shows a gap. Minor.

## Frontend / build notes

- **`rewrites` with `output: 'export'`.** Next.js warns (and may error in newer versions) when `rewrites` is configured together with a static export. Make the rewrite conditional on `NODE_ENV === 'development'` and say so in the plan.
- **SSE through the Next dev proxy** can buffer/compress responses. Consider having the dev frontend connect directly to `http://localhost:8000` for the stream, or document the workaround.
- **Recharts performance.** Ten sparklines plus a main chart updating at 2 Hz is fine, but cap retained points per ticker (e.g. 300) to avoid unbounded memory. Recharts' Treemap needs custom cell rendering for P&L colors; flag as a known effort item. The single-library mandate is reasonable.
- **Flash animation** via class add/remove should handle rapid repeated updates (restart the animation); mention.

## Docker / deployment

- `.gitattributes` with only `*.sh text eol=lf`: git is already warning about LF to CRLF on `settings.json` and `PLAN.md`. Prefer `* text=auto` plus `*.sh`, `*.ps1`, `Dockerfile` rules, and have the Dockerfile stage not depend on CRLF.
- Add a `.dockerignore` (excluding `.env`, `db/`, `node_modules`, `.git`) so the API key is never baked into the image. The plan says there is no `.env` in the container; this enforces it.
- `uv sync` should use `--frozen` for the lockfile guarantee.
- "Builds the image if not already built" can run stale code; note `--build` is needed after changes (already present).
- Security: the app has no auth and spends the user's OpenRouter key. The optional App Runner deployment would expose that publicly; add a warning or basic auth requirement.
- E2E: "fixed SIM_SEED" gives reproducible paths only per tick sequence; tests should still avoid exact values (already stated).

## Tooling changes

- `.claude/settings.json`: enabling `feature-dev@anthropic-plugin-directory` is fine and valid JSON. Note the `feature-dev` skill list already appears in the environment. No issues.
- `.claude/agents/reviewer.md`: valid frontmatter; the prompt hard-codes the file `planning/PLAN.md` and output `planning/REVIEW.md`. Suggest accepting the target file as an argument, and giving it criteria (correctness, consistency with code, testability) so reviews are not generic. Missing trailing newline.
- `.claude/commands/doc-review.md`: no frontmatter (`description`, `argument-hint`), missing trailing newline, and the final sentence ("...opportunities to simplify") is cut off by lack of punctuation. It overlaps the existing `doc-review` skill listed in the environment; consider keeping just one to avoid duplicate triggers. Note it appends to the document itself, while the reviewer agent writes to a separate REVIEW.md, so the two workflows conflict.
- CRLF/LF warnings on touched files suggest autocrlf is on; harmless but supports adding `.gitattributes`.

## Simplification opportunities

- Drop `reference_price`, `previous_price` duplication in `GET /api/watchlist` by returning the same object shape as an SSE event.
- Drop the Massive free-tier ticker validation requirement entirely for v1 (treat unknown as "no price"), reducing API-call coupling.
- Use one shared `Trade/ActionResult` model for REST trade and chat results.
- Skip the 10-action cap detail unless needed; a cap of "reasonable" in the prompt plus schema `maxItems` achieves the same.
