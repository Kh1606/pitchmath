# MetaRen — Full Strategic Roadmap
**Prepared after analysis of the v5 codebase**
**Date: February 2026**

---

## 1. Current State Assessment

### What You Built (and Why It's a Good Foundation)

After reading your full codebase — `app.py`, `data_access.py`, `extractors/core/db.py`, `logic/stat_engine.py`, and all components — here's an honest picture:

**Strengths you already have:**
- Clean modular architecture: components are isolated (match analyzer, team analyzer, player analyzer, fixtures)
- Config-driven extraction system — 14 competitions already defined in YAML, trivially extensible
- Good unified DB schema: `fixtures`, `competitions`, `teams`, `players`, `stats_team`, `stats_player` with proper foreign keys and indexes
- WAL mode on SQLite — already better than default for concurrent reads
- Smart stat engine: derived stats (2nd half = full − 1st half), venue filtering, perspective switching (team only vs total match)
- The logic is solid. The analysis side is genuinely good

**Honest weaknesses to fix:**
- SQLite: fine for MVP, but will bottleneck when you add multiple competitions, concurrent users, and background jobs writing simultaneously
- No automation: every extraction is a manual `python -m extractors.run --config ...` command
- No user layer: no accounts, no auth, no personalization
- Streamlit: great for data exploration, not good for a public-facing product (slow rerenders, no proper routing, ugly URLs, hard to customise deeply)
- All data loaded at startup into pandas: `load_matches()`, `load_team_stats()`, `load_player_stats()` — this becomes a memory and latency problem as the DB grows
- No odds integration yet despite API having it
- The `matches` legacy table is duplicating data from `fixtures` — dead weight

---

## 2. The Core Decision: Migration Strategy

You have **two paths**. I'll explain both, then tell you which I'd recommend for your situation.

---

### PATH A — Incremental Migration (Lower Risk, Slower)

Keep Streamlit running, add a backend layer behind it, migrate piece by piece.

> Streamlit → FastAPI backend → PostgreSQL → then eventually swap Streamlit for React

**Pros:** Never breaks what's working. Lower cognitive load. Easier to keep shipping.
**Cons:** You'll be maintaining two systems simultaneously for months. Streamlit's ceiling is real — it will fight you on anything interactive (real-time updates, auth, subscription gating). You'll accumulate technical debt migrating twice.

---

### PATH B — One Clean Rebuild (Recommended for your case)

Rebuild the frontend once, properly. Keep your Python backend logic — it's good and reusable.

> **PostgreSQL + FastAPI + React (Next.js)**

**Why this makes sense for you:**
- You're a solo developer — doing this incrementally means you'll never fully escape Streamlit's limitations
- Your stat engine and extractor logic translate directly into FastAPI endpoints — it's not a rewrite, it's a relocation
- Next.js gives you SSR (good for SEO if you ever want organic traffic from search), proper routing, and a professional UI you can actually be proud of showing in your marketing shorts
- The rebuild is probably 3–5 weeks of focused work, not months, because your data layer is already well-designed
- Once done, you're free — no more fighting the framework

---

## 3. Recommended Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Database | **PostgreSQL** (self-hosted on VPS) | ACID compliant, handles concurrent writes from the pipeline, much better indexing for analytical queries |
| Backend API | **FastAPI** (Python) | You already write Python, your stat engine moves here as-is, async support for background tasks |
| Background Jobs | **APScheduler** or **Celery + Redis** | Automated pipeline for fixture fetching and stat extraction |
| Frontend | **Next.js (React)** | SSR for SEO, proper routing, professional look, easy to deploy |
| Auth | **Supabase Auth** or **Auth.js** | Don't build this yourself — use a library |
| Hosting | **Single VPS** (Hetzner or DigitalOcean) | Start at €5–6/month. Hetzner CX22 (2 vCPU, 4GB RAM) is perfect for now |
| Deployment | **Docker Compose** | Keep all services in one place: postgres, api, frontend, worker |
| Domain | Any registrar | ~€10–12/year |

**Total monthly cost starting out: ~€15–20/month** (VPS + domain amortised). Scales only when you need it to.

---

## 4. Database Migration Plan

### From SQLite to PostgreSQL

Your schema is already clean — migration is mostly a port, not a redesign. Key changes:

**Keep as-is (just port the DDL):**
- `competitions`, `teams`, `players`, `fixtures`, `stats_team`, `stats_player`

**Drop:**
- The legacy `matches` table — your UI already reads from `fixtures`, this is dead weight

**Add (new tables needed for the product):**
```
users              — id, email, password_hash, created_at, subscription_tier
user_favorites     — user_id, entity_type (team/player/competition), entity_id
notifications      — user_id, type, payload, read_at
odds               — game_id, bookmaker, market, selection, odd_value, fetched_at
ai_suggestions     — game_id, model_version, content, created_at
comments           — game_id, user_id, content, created_at, updated_at
```

**Add these indexes (PostgreSQL-specific, will help a lot):**
```sql
CREATE INDEX idx_fixtures_date_status ON fixtures(date, status_short);
CREATE INDEX idx_stats_team_gameid ON stats_team(game_id);
CREATE INDEX idx_stats_player_gameid ON stats_player(game_id);
CREATE INDEX idx_odds_gameid ON odds(game_id, market);
```

---

## 5. The Automated Pipeline — This Is Your Most Important Piece

You said you want to "do it once and be free." This is the right mindset. Here's the architecture:

### Pipeline Design

```
┌─────────────────────────────────────────────────────┐
│                   APScheduler (4 jobs)               │
├──────────────┬──────────────┬──────────────┬─────────┤
│  Fixture     │  Result      │  Odds        │  Stats  │
│  Sync        │  Updater     │  Fetcher     │  Filler │
│  Every 6hrs  │  Every 1hr   │  Every 3hrs  │  Daily  │
│              │  (matchdays) │  (pre-match) │  2am    │
└──────────────┴──────────────┴──────────────┴─────────┘
         ↓              ↓              ↓           ↓
                   PostgreSQL DB
```

**Job 1 — Fixture Sync (every 6 hours):**
Pull upcoming fixtures for all active competitions. Insert new ones, update status of pending ones. This is basically your current `season_extractor` run in loop mode.

**Job 2 — Result Updater (every 1 hour, smarter on matchdays):**
Check fixtures with `status_short = 'NS'` that have `date <= now`. Poll their results. When finished, mark as `FT` and queue for stat filling. You can make this smarter: on days with no matches, it barely runs. On a busy Saturday it runs every 15 minutes.

**Job 3 — Odds Fetcher (every 3 hours, pre-match):**
For fixtures within next 72 hours, fetch odds from api-football. Store in `odds` table. Simple.

**Job 4 — Stats Filler (daily at 2am, or triggered post-match):**
For matches that finished yesterday but have no stats yet, backfill team stats and player stats. Your current extractor code already has `update_only` logic — this job wraps it.

**Key principle:** Each job checks what needs to be done before touching the API. Never fetch what you already have. Your `get_existing_stats_game_ids()` function is already doing this correctly.

### API Rate Limit Awareness

You have the Pro plan (100 requests/minute, 7,500/day roughly). With 5 leagues + cups + UCL/UEL/UECL, on a heavy matchday you might have 30–40 matches. Each match needs fixtures + stats = 3 requests. That's 120 requests for a full round, easily within limits. The automation just needs to be patient and spread requests out.

When you scale to 2nd tier leagues, just add more YAML configs. The pipeline handles them automatically because it reads from the `competitions` table.

---

## 6. FastAPI Backend Structure

Your existing logic moves almost unchanged:

```
api/
├── main.py                  ← FastAPI app, CORS, startup events
├── routers/
│   ├── fixtures.py          ← GET /fixtures, GET /fixtures/{id}
│   ├── matches.py           ← GET /matches/h2h, GET /matches/team/{name}
│   ├── teams.py             ← GET /teams, GET /teams/{id}/stats
│   ├── players.py           ← GET /players/{id}/stats
│   ├── competitions.py      ← GET /competitions
│   ├── odds.py              ← GET /odds/{game_id}
│   ├── analysis.py          ← POST /analysis/match  (your stat engine becomes an endpoint)
│   └── ai.py                ← POST /ai/suggest
├── services/
│   ├── stat_engine.py       ← Your current logic/stat_engine.py, almost unchanged
│   ├── pipeline.py          ← The 4 automated jobs
│   └── ai_service.py        ← LLM integration
├── models/
│   └── db.py                ← SQLAlchemy models
└── auth/
    └── dependencies.py      ← JWT verification
```

**The key insight:** Your `stat_engine.py` and `data_access.py` logic doesn't need to be rewritten. It gets refactored into FastAPI service functions and exposed as REST endpoints. The frontend then calls these endpoints instead of querying SQLite directly.

---

## 7. Frontend (Next.js)

The structure mirrors your current Streamlit pages:

```
pages/
├── index.tsx                ← Landing page (public, marketing)
├── dashboard/
│   ├── index.tsx            ← Match Analyzer
│   ├── teams/[name].tsx     ← Team Analyzer
│   ├── players/[id].tsx     ← Player Analyzer
│   └── fixtures.tsx         ← Upcoming fixtures
├── auth/
│   ├── login.tsx
│   └── register.tsx
└── account/
    ├── favorites.tsx
    └── subscription.tsx
```

**Charting:** Use **Recharts** (React-native, lightweight) or **ECharts** for more power. Both are much faster than Plotly in Streamlit.

**Styling:** Use **Tailwind CSS** — fast to write, professional results. You can build dark mode by default which fits a football analytics app perfectly.

---

## 8. AI/LLM Integration

This is exciting but needs to be planned carefully so it's actually useful, not gimmicky.

### Realistic AI Features (in order of difficulty)

**Level 1 — Pattern-based "AI" (actually rules + stats, no LLM):**
Generate pre-match insight text from your stat engine output. Things like:
- "Arsenal have scored in 8 of their last 9 home games"
- "This fixture averages 3.1 goals over the last 5 H2H meetings"
- "Liverpool haven't kept a clean sheet away in 6 games"

This is not an LLM — it's templated text generated from your existing stats. It's fast, free, reliable, and looks like AI to users. **Do this first.**

**Level 2 — LLM-powered Match Summaries:**
After a match, send the stats JSON to an LLM (OpenAI GPT-4o-mini or Claude Haiku — both are cheap) and generate a 3-4 sentence analysis. Cache the result. Cost: roughly $0.001 per match. For 1,000 matches/season across 5 leagues = ~$1/season. Completely negligible.

**Level 3 — Pre-match Betting Suggestions:**
Build a structured prompt: current form, H2H history, home/away stats, odds. Ask the LLM to suggest the highest-value bet with reasoning. This is where the app becomes genuinely differentiated. Use GPT-4o-mini or Claude Haiku for cost. Offer this as a **paid feature only**.

**Level 4 — Personalised AI (harder, later):**
User has favourited Arsenal → AI always leads with Arsenal context. Users's past viewing history informs suggestions. This requires storing user behaviour data and incorporating it into prompts. Worth building after you have paying users.

### LLM Cost Estimate
- GPT-4o-mini: ~$0.15 per 1M input tokens, $0.60 per 1M output tokens
- For a typical match analysis prompt (1,500 tokens in, 300 tokens out): ~$0.0004
- For 50 active users each viewing 10 analyses/day: ~$0.20/day = $6/month
- Very manageable even at early stage

---

## 9. Monetisation & Subscription Tiers

Keep it simple at launch. Three tiers is the classic SaaS model:

### Free Tier
- Access to top 5 leagues, current season only
- Match Analyzer (limited H2H depth — last 5 games only)
- Fixtures view
- No odds, no AI suggestions

### Pro Tier (~€9.99/month or €79/year)
- All competitions including cups, 2nd tier, UCL/UEL/UECL
- Full historical depth (all seasons)
- Odds analysis
- Level 2 & 3 AI features (LLM summaries + betting suggestions)
- Favourites/personalisation
- Early access to new features

### Premium/Founder Tier (~€19.99/month)
- Everything in Pro
- Priority in comment sections (badge)
- Direct feedback channel with you
- Lifetime price lock
- First 50–100 users at discounted "founder" rate to build community

**Important note:** Don't build Stripe integration until you have real users asking to pay. Start with manual payments or a simple Gumroad subscription if needed. Stripe takes time to set up properly with subscription management and webhooks.

---

## 10. The Comment System

Keep this simple. A `comments` table (game_id, user_id, content, created_at). Display under each match analysis. Users can post pre-match predictions and post-match analysis.

**Why this is valuable for your marketing:**
- Comments create community, and community creates retention
- The best comments become social media content (screenshot a great prediction that came true → post as a Short with "our community called it")
- Comments signal to users that others are using the app, reducing churn

Moderation: since you're solo, just add a simple report flag. Don't build a full moderation system yet.

---

## 11. Marketing Strategy — Your Plan Is Good, Here's How to Sharpen It

Your plan (daily Shorts: morning bet + morning result + new bet cycle) is smart. Here's my honest analysis:

**What will work:**
- Consistency beats quality at first. 2 posts/day × 30 days = 60 touchpoints. The algorithm rewards regularity.
- The cycle is inherently compelling: yesterday's bet result forces viewers to come back. This is the retention mechanic of good content.
- No camera, voice + screen recording is totally fine for this niche — the football analytics audience cares about the data, not your face
- Posting same content to YouTube Shorts, Reels, and TikTok is correct — repurpose everything

**What to add:**
- Put the app URL in your bio from day 1 and mention it naturally ("full analysis on MetaRen, link in bio")
- When showing the app in videos, **make sure it looks good**. This is one more reason to rebuild the frontend — your Streamlit UI won't look great on a phone screen in a Short
- Engage with every comment in the first 3 months. Reply, ask questions. The algorithm notices engagement.
- Find 5–10 football betting accounts on each platform with 5k–50k followers. Don't ask for collabs yet — just engage genuinely on their content. You'll appear in their comment sections and get noticed.

**On the paid advertising:**
YouTube pre-roll ads for your Shorts content is genuinely a good play — target "football betting", "Premier League stats", "over/under football". Start with €5–10/day budget, test creative variations. You'll learn quickly what converts.

**The friend situation:**
Your instinct is right. A 70-30 split where you do 100% of the work isn't worth it even if 70 feels large. Better to do it alone and own 100%, offer him a free Pro account for life and occasional feedback sessions. If later he actually delivers something material, revisit. But don't do a formal partnership now.

---

## 12. Phased Execution Plan

### Phase 1 — Infrastructure (Weeks 1–4)
*Goal: Real backend, real DB, automated pipeline running*

1. Set up a Hetzner CX22 VPS with Docker Compose
2. Migrate SQLite → PostgreSQL (port your schema, run migration script)
3. Convert extractor jobs into APScheduler tasks in a standalone service
4. Get the 4 pipeline jobs running, verify data flows automatically
5. Build basic FastAPI with your core endpoints (fixtures, matches, stats)
6. Verify everything works with your existing Streamlit frontend still querying the new PostgreSQL DB (via psycopg2 instead of sqlite3 — minimal change)

**At end of Phase 1:** Your app is still Streamlit, but data is now fully automated and in PostgreSQL. You can stop running extractors manually.

### Phase 2 — Frontend Rebuild (Weeks 5–10)
*Goal: Professional UI, auth, basic personalisation*

1. Set up Next.js project with Tailwind
2. Rebuild the 4 pages (Match Analyzer, Team Analyzer, Player Analyzer, Fixtures) as React components backed by your FastAPI
3. Add auth (login/register/JWT)
4. Add favourites system
5. Add comments section to match pages
6. Deploy to VPS, point your domain at it
7. Start marketing. You now have something you're proud to show in Shorts

**At end of Phase 2:** Public product, real URL, shareable, professional-looking. Start growing.

### Phase 3 — Monetisation & AI (Weeks 11–18)
*Goal: Revenue mechanism, AI features, odds integration*

1. Integrate odds from api-football into the match analysis views
2. Build Level 1 "AI" (templated stat insights — no LLM needed, high value)
3. Build Level 2 LLM match summaries (post-match)
4. Build Level 3 LLM pre-match suggestions
5. Gate Pro features behind subscription (Stripe or simple alternative)
6. Launch paid tier with early-adopter pricing
7. Ramp up paid marketing now that you have a conversion funnel

**At end of Phase 3:** Paying users, AI features live, full competition coverage.

### Phase 4 — Scale (Month 5+)
*Goal: More competitions, more leagues, deeper personalisation*

1. Add 2nd tier leagues, add more countries by simply adding YAML configs and registering in competitions table
2. Personalised AI (user history-aware prompts)
3. Push notifications (upcoming match alerts for favourited teams)
4. Consider mobile app (React Native reuses your component logic)
5. Revisit infrastructure costs and upgrade VPS if needed

---

## 13. Budget Summary

| Item | Cost |
|---|---|
| Hetzner CX22 VPS | ~€6/month |
| Domain | ~€10/year |
| api-football Pro | €19/month |
| LLM API (GPT-4o-mini) | €5–10/month (early stage) |
| YouTube/Meta Ads | €150–300/month (when ready) |
| **Total (pre-ads)** | **~€35/month** |
| **Total (with ads)** | **~€185–335/month** |

This is lean. You only add the ad spend when Phase 2 is complete and you have something worth advertising.

---

## 14. Most Important Personal Recommendation

The biggest risk to this project is not technical — it's scope creep and burnout from trying to build everything at once. You've described 6 months of work in one message.

**My advice:** Finish Phase 1 before thinking about AI. Finish Phase 2 before thinking about subscriptions. Each phase gives you something you can actually use and show. Each phase builds on real foundation, not plans.

The automation pipeline (Phase 1) is the single most leveraged thing you can build. Once the data flows automatically, everything else — analysis, AI, UI — runs on real, fresh data without you lifting a finger. That's the freedom you described wanting.

Your instincts are good. The plan is ambitious but achievable. The codebase you've built is a real foundation, not throwaway code. Go phase by phase, stay solo, stay lean, stay consistent with the content, and you'll have something real.

---

*End of MetaRen Strategic Roadmap — v1.0*
