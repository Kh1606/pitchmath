"""
Season Extractor Engine
========================
Given a loaded config dict, fetches fixtures and stats for a whole
competition-season and upserts everything into the unified DB.
"""

import logging
from typing import Optional, List

from extractors.core.api_client import APIFootballClient, FINISHED_STATUSES
from extractors.core.parser import (
    parse_fixture, parse_match_legacy, parse_team_stats,
    parse_1h_from_events, parse_player_stats,
)

logger = logging.getLogger("metaren.extractor")


class SeasonExtractor:
    """Extracts one competition-season worth of data."""

    def __init__(self, config, conn, client, dbmod):
        self.config = config
        self.conn = conn
        self.client = client
        self.db = dbmod
        self.cfg = config

        # Core identifiers
        self.comp_id = config["competition_id"]
        self.comp_name = config["name"]
        self.season = config["season"]

        # Endpoint toggles
        ep = config.get("endpoints", {})
        self.fetch_team_stats = ep.get("fetch_team_stats", True)
        self.fetch_player_stats = ep.get("fetch_player_stats", True)
        self.fetch_events = ep.get("fetch_events", False)

        # Counters
        self.totals = {
            "fixtures_upserted": 0,
            "played_processed": 0,
            "skipped_existing": 0,
            "upcoming": 0,
            "stats_rows": 0,
            "player_rows": 0,
        }

    # ------------------------------------------------------------------
    # ROUND FILTERING
    # ------------------------------------------------------------------

    def _build_round_filter(self, round_from: Optional[int] = None,
                            round_to: Optional[int] = None) -> Optional[set]:
        """
        Build a set of accepted round strings for filtering.
        Returns None if no filtering (process all fixtures).
        """
        cfg = self.cfg

        # Exact rounds list from config (cups)
        if cfg.get("rounds_exact"):
            return set(cfg["rounds_exact"])

        prefix = cfg.get("round_prefix")
        if not prefix:
            return None  # No filtering

        r_start = round_from or cfg.get("round_start", 1)
        r_end = round_to or cfg.get("round_end", 99)

        return {f"{prefix} - {n}" for n in range(r_start, r_end + 1)}

    # ------------------------------------------------------------------
    # MAIN ENTRY
    # ------------------------------------------------------------------

    def run(self, round_from: Optional[int] = None,
            round_to: Optional[int] = None,
            update_only: bool = False):
        """
        Execute the full extraction pipeline.

        Args:
            round_from/round_to: override round range (league mode only)
            update_only: if True, only fetch stats for games missing in DB
        """
        # Register competition
        self.db.upsert_competition(self.conn, {
            "competition_id": self.comp_id,
            "name":           self.comp_name,
            "country":        self.cfg.get("country"),
            "type":           self.cfg.get("type"),
        })

        # 1) Fetch all fixtures for the season
        logger.info(f"Fetching season fixtures: {self.comp_name} {self.season}…")
        all_fixtures = self.client.fetch_season_fixtures(self.comp_id, self.season)
        logger.info(f"  → {len(all_fixtures)} fixtures returned")

        if not all_fixtures:
            logger.warning("No fixtures returned from API. Aborting.")
            return self.totals

        # 2) Build round filter
        round_filter = self._build_round_filter(round_from, round_to)

        # 3) Get existing stats
        existing_ids = self.db.get_existing_stats_game_ids(self.conn, self.comp_id, self.season)
        logger.info(f"  Matches already with stats in DB: {len(existing_ids)}")

        # 4) Process each fixture
        for fx in all_fixtures:
            self._process_fixture(fx, round_filter, existing_ids, update_only)

        self.conn.commit()
        return self.totals

    # ------------------------------------------------------------------
    # PER-FIXTURE PROCESSING
    # ------------------------------------------------------------------

    def _process_fixture(self, fx: dict, round_filter: Optional[set],
                         existing_ids: set, update_only: bool):
        """Process a single fixture JSON blob."""
        f = fx.get("fixture", {}) or {}
        lg = fx.get("league", {}) or {}
        t = fx.get("teams", {}) or {}
        game_id = f.get("id")
        if not game_id:
            return

        rnd = lg.get("round", "")
        status = (f.get("status", {}) or {}).get("short", "")
        home_info = t.get("home", {}) or {}
        away_info = t.get("away", {}) or {}
        home_name = home_info.get("name", "?")
        away_name = away_info.get("name", "?")
        home_id = home_info.get("id")
        away_id = away_info.get("id")

        # Round filtering
        if round_filter and rnd not in round_filter:
            return

        # --- Always upsert fixture ---
        # Upsert teams lookup FIRST (needed for Postgres foreign keys)
        if home_id:
            self.db.upsert_team(self.conn, home_id, home_name)
        if away_id:
            self.db.upsert_team(self.conn, away_id, away_name)
        
        # --- Then upsert fixture ---
        fix_row = parse_fixture(fx, self.comp_id, self.comp_name, self.season)
        if fix_row["game_id"]:
            self.db.upsert_fixture(self.conn, fix_row)
            self.totals["fixtures_upserted"] += 1
        
        # --- Check if finished ---
        if status not in FINISHED_STATUSES:
            self.totals["upcoming"] += 1
            return

        # --- Already extracted? ---
        if game_id in existing_ids:
            self.totals["skipped_existing"] += 1
            return

        # --- Finished + new → extract stats ---
        self.totals["played_processed"] += 1

        # Upsert legacy matches table
        match_row = parse_match_legacy(fx, self.comp_name)
        self.db.upsert_match(self.conn, match_row)

        # Team stats (Full)
        if self.fetch_team_stats:
            full_raw = self.client.fetch_full_stats(game_id)
            if full_raw:
                rows = parse_team_stats(full_raw, "Full")
                self.totals["stats_rows"] += self.db.save_team_stats(
                    self.conn, game_id, self.comp_id, self.season, rows
                )

        # Events → 1H goals & cards
        if self.fetch_events:
            events = self.client.fetch_events(game_id)
            if events:
                rows_1h = parse_1h_from_events(events, home_name, away_name, home_id, away_id)
                self.totals["stats_rows"] += self.db.save_team_stats(
                    self.conn, game_id, self.comp_id, self.season, rows_1h
                )

        # Player stats
        if self.fetch_player_stats:
            players_raw = self.client.fetch_players(game_id)
            if players_raw:
                player_rows = parse_player_stats(
                    players_raw, game_id, self.comp_id, self.season
                )
                # Upsert player lookup
                for pr in player_rows:
                    self.db.upsert_player(self.conn, pr["player_id"], pr["player_name"])
                self.totals["player_rows"] += self.db.save_player_stats(self.conn, player_rows)

        existing_ids.add(game_id)
        logger.info(f"  ✓ {home_name} vs {away_name}  "
                     f"({fix_row.get('home_score', '?')}-{fix_row.get('away_score', '?')})")
