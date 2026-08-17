
# Pitch Inbox — REITs (V1)

Quick, persistent dashboard that checks the same pitch-oriented sources used by the REIT Ideas workflow, keeps only investment pitches tied to a defined coverage universe, and displays them as a simple linked list.

Every visible item answers three questions immediately:
1. What company is this?
2. Where did the pitch come from?
3. What is the one-line thesis?

> V1 is intentionally narrow: read-only list, manually triggered, local file, no hosting/auth/database. Scheduling, saved/dismissed states, sharing are deferred — architecture allows adding later without reworking collection.

## Architecture

**Normalized feed + generated static HTML (no server/DB)**

- Collection agents append accepted pitches to an append-only JSONL feed (the durable product)
- A separate render step generates a self-contained HTML file from that feed (the disposable presentation layer)

Two architectures considered and rejected:
- Obsidian Dataview/Bases dashboard — needs one note per pitch or custom DataviewJS, vault clutter, filtering awkward
- Hosted web app with DB — disproportionate overhead (auth, hosting, migrations) for a private linked list

```
coverage.json + sources.json
        ↓
  initialize (validate configs, set run_id + lookback window, create run folder)
        ↓
  collect (parallel collectors, each source ends complete/unavailable/failed)
        ↓
  normalize (resolve ticker/company, classify sector, write 18-40w one-liners, reject generic news, route ambiguous to QA)
        ↓
  deduplicate (canonical URL or source-native ID first; fallback = source + ticker + normalized title + pub date)
        ↓
  render (build candidate HTML from feed + staged)
        ↓
  validate (all quality gates must pass)
        ↓
  complete (atomically append staged batch + publish HTML)
```

## Agent Team

| Agent | Role | Runs | Tool Access |
|-------|------|------|-------------|
| Orchestrator | Reads state, chooses phase, launches collectors, merges, enforces gates | Sequential | state, configs |
| Pitch Platforms Collector | Pulls Yellowbrick, BuySide Digest | Parallel | pitch-platform connectors only |
| Open Web & Fund Commentary Collector | Searches VIC, SumZero, Substack, Seeking Alpha, fund letters | Parallel | web search only, no inbox |
| Inbox Pitch Collector | Finds explicit company pitches in broker/internal email | Parallel | email connector only, no web |
| Normalization & Coverage Agent | Resolves ticker/company, classifies sector, writes one-liners, tags exact-vs-sector match | After collectors | coverage.json |
| QA Agent | Reviews only ambiguous or failed deterministic cases | Exception-only | manual review queue |

Progressive disclosure: each collector only gets the tool access it needs — reduces blast radius.

## Sources (per spec)

**Included — must contain an actual investable thesis to qualify:**

Pitch platforms:
- **Yellowbrick** (trending and long-form investment pitches)
- **BuySide Digest** (pitches and fund letters)

Value-investing idea communities:
- **Value Investors Club (VIC)** — public ideas, snippets only due to membership
- **SumZero** — public results/snippets

Newsletters / commentary:
- **Substack subscriptions and selected investment publications** — RSS, filtered for explicit company thesis
- **Named fund letters and manager commentary** — quarterly cadence

Thesis-style articles:
- **Seeking Alpha thesis articles, when accessible** — paywall often, link only

Inbox:
- **Broker research emails** and **internal emails** that contain an explicit company thesis (not just a research note or price update) — disabled in V1 local run, enable via email connector

**Explicitly excluded, even from these same sources, unless a genuine investable thesis is attached:**
- Generic company/sector news
- Routine regulatory filings (8-K, 10-Q, 10-K)
- Price-action recaps
- Unsourced social posts
- Broad macro commentary with no specific company or subsector angle

### Coverage Matching

Pitches kept only if tied to `coverage.json` universe (ticker + company aliases + sector classification).

- Exact company match and sector match both allowed but labeled distinctly — don't collapse distinction
- Ambiguous short symbols (ARE, O, WELL, AMT, CUBE, DOC, CPT, ESS, MAA, KIM, REG, STAG, WY) require company-name or source-metadata confirmation — keyword match on symbol alone is NOT sufficient
- Example: `ARE` needs "Alexandria Real Estate" in title/body, not just the word "are"
- Example: `O` needs "Realty Income", not just letter O

### Deduplication Rule

- Canonical URL or source-native ID controls first
- Fallback fingerprint = `source + primary ticker + normalized title + publication date` (for sources with missing/tracking-param URLs)
- A second pitch on same ticker is NOT suppressed if source, thesis, or catalyst materially differs

## Files

- `coverage.json` — tickers, aliases, sector classification, ambiguous-symbol rules, sector_match_rules
- `sources.json` — source registry (name, type, family, priority, access mode, lookback, enabled)
- `pitches.jsonl` — durable append-only feed (the actual product), one JSON object per line
- `state.json` — cross-run checkpoint: phase, per-source status, counts, errors, quality gates
- `build.py` — reads JSONL, renders self-contained HTML
- `refresh.py` — full 7-phase orchestrator (initialize→collect→normalize→deduplicate→render→validate→complete)
- `pitch_inbox.html` — user-facing dashboard (disposable, regeneratable)
- `runs/` — per-run folders with state snapshots

### Canonical Pitch Record

```json
{
  "pitch_id": "sha256-canonical-fingerprint",
  "discovered_at": "ISO timestamp",
  "published_at": "YYYY-MM-DD",
  "primary_ticker": "ARE",
  "tickers": ["ARE"],
  "company": "Alexandria Real Estate Equities",
  "sector": "REITs",
  "subsector": "Life Science",
  "coverage_match": "exact_company | sector_match",
  "stance": "long | short",
  "source_name": "Yellowbrick",
  "source_type": "pitch_platform | open_web | inbox",
  "author_or_fund": null,
  "title": "original source title",
  "one_liner": "18-40 word statement of the variant thesis, not a headline restate",
  "url": "https://source/pitch",
  "quality": "high",
  "status": "active",
  "run_id": "PITCH_INBOX_YYYYMMDD_HHMMSS"
}
```

### Dashboard V1 Spec

- Header: title, last successful refresh, source coverage summary (which sources succeeded/failed this run)
- Controls: free-text search, sector filter, source filter, time window toggle (30 / 90 / all days)
- List item format:
  ```
  [TICKER]  Company Name                    [Published date]
  [Source]  [Coverage or Sector Match] [long|short] [Subsector]
  [Clickable one-line thesis]                          Open -->
  ```
- Default: newest first, most recent 90 days, all sectors
- Deliberately excluded: charts, KPI cards, scoring, saved states, notes panel

## Usage

### Quick start (render only, no collection)

```bash
cd pitch_inbox
python build.py
open pitch_inbox.html
```

### Full refresh (with collection)

```bash
# Normal run — checks all enabled sources, degrades cleanly if one family unavailable
python refresh.py

# Test with mock new pitches to validate dedup + gates + atomic publish
python refresh.py --mock

# After refresh, dashboard is auto-published
open pitch_inbox.html
```

Expected runtime: ~2-5 minutes total (config validation <10s, parallel collection 1-3 min, normalize 20-60s, dedup <10s, render+validate 15-45s)

### Adding a new source

1. Add entry to `sources.json` with id, name, type, family, priority, access_mode, lookback_days, enabled
2. Add collector function in `refresh.py` COLLECTOR_MAP
3. Keep family as one of: `pitch_platforms`, `open_web`, `inbox` — source minimum gate requires at least one family complete

### Enabling inbox

Set `enabled: true` for `broker_email` / `internal_email` in `sources.json` and implement email connector in `collect_broker_email` / `collect_internal_email` (Gmail API). Only emails with explicit company thesis qualify — filter subject/body for ticker + thesis markers.

## Quality Gates (all must pass before publishing)

- Config integrity: coverage/source configs parse; every ticker has company + sector
- Source minimum: at least one source family returned valid records (or explicit zero-new) — otherwise fail without touching output
- Record schema: every accepted record has all required fields
- Coverage match: exact or approved sector match; ambiguous symbols resolved, not guessed
- Pitch quality: explicit investable thesis, one-liner 18-40 words, not headline restate
- Link quality: valid HTTPS URL or approved fallback — never dead placeholder
- Deduplication: no duplicate ID or canonical URL
- Copyright boundary: store headline, metadata, link, short original synthesis only — never long copyrighted excerpts
- Feed consistency: JSONL parses line by line; append is atomic
- Dashboard completeness/behavior: all active records in display window render; search/filters return reconciled counts
- Responsive layout: no horizontal overflow at desktop or narrow width
- Source disclosure: last refresh + which sources succeeded/failed visible on dashboard

Minimum viable output: a refresh can validly produce zero new pitches as long as at least one source was successfully checked, and prior working feed/dashboard must never be touched by a failed run.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `source_minimum` gate fails | All families unavailable/failed | Check `sources.json` enabled flags, network, credentials; at least one family must complete |
| Duplicate pitch on re-run | Canonical URL not normalized | Check `canonical_fingerprint` strips tracking params and lowercases |
| Ambiguous ticker accepted without company name | Rule missing in `coverage.json` | Add entry to `ambiguous_symbol_rules` with `require_any` list |
| HTML empty but feed has data | Time window filter default 90d | Click "All" or check `published_at` dates are within 90 days |
| Inbox sources always unavailable | Disabled in V1 | Enable in `sources.json` after implementing email connector |
| One-liner word count fails gate | Synthesis too short/long | Ensure normalization pads/trims to 18-40w and is not headline restate |

## Key Design Decisions to Preserve

1. JSONL feed is the product; HTML is replaceable presentation layer — never couple collection logic to display format
2. Manually triggered in V1, but state is resumable so schedule can be bolted on later without redesign (state.json phase checkpoint)
3. Exact company matches and sector matches both allowed but labeled distinctly
4. Pitch inbox, not general intelligence feed — routine news and filings explicitly out of scope
5. Read-only and local by design in V1 to keep build/maintenance cost proportional to private linked list

## License

Private internal tool — no distribution.
