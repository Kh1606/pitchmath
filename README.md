# PitchMath — Football Analytics Platform

A full-stack football analytics platform: an **extraction pipeline** pulls fixtures,
team and player stats from [API-Football](https://www.api-football.com/) into a
**Postgres (or SQLite)** database, and a **Streamlit** app turns that data into
match/team/player analysis, form lines and a "Team DNA" radar.

> Internally the codebase is named `metaren`; PitchMath is the product name.

**Stack:** Python · Streamlit · Plotly · Postgres / SQLite · API-Football

## Project Structure

```
metaren/
├── app.py                          # Streamlit entry point
├── data_access.py                  # DB queries for Streamlit UI
├── ui_style.py                     # CSS + league constants
├── components/                     # Streamlit UI components
│   ├── match_analyzer.py
│   ├── team_analyzer.py
│   ├── player_analyzer.py
│   ├── team_dna.py
│   └── charts.py
├── logic/
│   └── stat_engine.py              # Stat computation engine
├── extractors/                     # Data extraction pipeline
│   ├── run.py                      # CLI runner
│   └── core/
│       ├── api_client.py           # API-Football HTTP client
│       ├── db.py                   # Schema + upsert helpers
│       ├── parser.py               # JSON transformers
│       └── season_extractor.py     # Core extraction engine
├── configs/                        # YAML configs per competition
│   ├── country/
│   │   ├── england/  (epl, fa_cup, efl_cup)
│   │   ├── spain/    (laliga, copa_del_rey)
│   │   ├── italy/    (serie_a, coppa_italia)
│   │   ├── germany/  (bundesliga, dfb_pokal)
│   │   └── france/   (ligue1, coupe_de_france)
│   └── europe/       (ucl, uel, uecl)
└── db/
    └── football.db                 # Single unified database
```

## Setup

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure secrets — copy the example and fill in your values
copy .env.example .env
#   APIFOOTBALL_KEY  — your API-Football key (required to extract)
#   PG_*             — Postgres connection (only needed for --db pg)
```

Postgres is optional — the extractor defaults to SQLite. To run Postgres locally:

```powershell
docker compose -f docker-compose.pg.yml up -d
```

## How to Run

### 1. Extract Data

From the project root directory:

```powershell
# Full EPL extraction
python -m extractors.run --config configs/country/england/epl.yml

# Multiple leagues at once
python -m extractors.run --config configs/country/england/epl.yml configs/country/italy/serie_a.yml configs/europe/ucl.yml

# Only specific rounds
python -m extractors.run --config configs/country/italy/serie_a.yml --round-from 1 --round-to 25

# Daily update mode (upsert fixtures, only fetch stats for new finished games)
python -m extractors.run --config configs/country/england/epl.yml --update-only

# Custom DB path
python -m extractors.run --config configs/country/england/epl.yml --db my_database.db
```

### 2. Launch Streamlit

```powershell
streamlit run app.py
```

### 3. What you'll see

- **Match Analyzer**: Head-to-head analysis with form-line engine
- **Team Analyzer**: Single team form, stat lines, Team DNA radar
- **Player Analyzer**: Player props and per-match stats
- **Fixtures**: Upcoming match schedule from all extracted competitions

## Database Schema

One SQLite DB (`db/football.db`) with these tables:

| Table | Purpose |
|-------|---------|
| `competitions` | Competition metadata (id, name, country, type) |
| `teams` | Team lookup (team_id, name) |
| `players` | Player lookup (player_id, name) |
| `fixtures` | Master schedule — played + upcoming (with IDs) |
| `matches` | Legacy played-match table (used by Streamlit analyzers) |
| `stats_team` | Team stats per match (with competition_id, team_id) |
| `stats_player` | Player stats per match (with competition_id, team_id, player_id) |

All tables use UPSERT (INSERT OR REPLACE) — safe to run repeatedly.

## Config Format (YAML)

```yaml
competition_id: 39
name: "Premier League"
country: "England"
type: "league"          # league | cup | europe
season: 2024
mode: "league"          # league | cup

# Round filtering (leagues with numbered rounds)
round_prefix: "Regular Season"
round_start: 1
round_end: 38

# For cups with named rounds (optional):
# rounds_exact: ["Round of 32", "Quarter-finals", "Semi-finals", "Final"]

request_delay: 0.25

endpoints:
  fetch_fixtures: true
  fetch_team_stats: true
  fetch_player_stats: true
  fetch_events: false
```

## Key Design Decisions

- **IDs stored everywhere** (team_id, player_id, competition_id) but **names cached** in every row so the UI always works with display names.
- **One DB for all competitions** — the extractor just upserts, so you can run EPL, UCL, FA Cup into the same `football.db`.
- **Legacy `matches` table kept** for backward compatibility with existing Streamlit analyzers. The new `fixtures` table is the master schedule.
- **UPSERT always** — no data is deleted. Re-running the same config just updates what changed.
- **`--update-only` flag** for daily cron jobs — re-fetches the fixture list and only pulls stats for newly finished matches.
