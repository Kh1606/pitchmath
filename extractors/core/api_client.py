"""
API-Football Client
====================
Thin wrapper around the API-Football v3 REST API.
Handles rate-limiting, retries, and request counting.
"""

import time
import logging
import requests
from typing import Optional, List

logger = logging.getLogger("metaren.api")

BASE_URL = "https://v3.football.api-sports.io"

# Statuses that mean "this match is done"
FINISHED_STATUSES = {"FT", "AET", "PEN"}


class APIFootballClient:
    """Thin HTTP wrapper for API-Football v3."""

    def __init__(self, api_key: str, request_delay: float = 0.25):
        self.session = requests.Session()
        self.session.headers.update({"x-apisports-key": api_key})
        self.request_delay = request_delay
        self.request_count = 0

    # ------------------------------------------------------------------
    # Low-level request
    # ------------------------------------------------------------------

    def _request(self, endpoint: str, params: dict) -> Optional[dict]:
        url = f"{BASE_URL}{endpoint}"
        self.request_count += 1

        if self.request_count > 1:
            time.sleep(self.request_delay)

        try:
            resp = self.session.get(url, params=params, timeout=30)

            if resp.status_code == 429:
                logger.warning("Rate limit 429 — sleeping 15s then retry…")
                time.sleep(15)
                return self._request(endpoint, params)

            resp.raise_for_status()
            data = resp.json()

            if data.get("errors") and len(data["errors"]) > 0:
                logger.error(f"API error: {data['errors']}")
                return None

            remaining = resp.headers.get("x-ratelimit-remaining", "?")
            logger.debug(f"  Req #{self.request_count}  credits left: {remaining}")
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Public endpoint helpers
    # ------------------------------------------------------------------

    def fetch_season_fixtures(self, league_id: int, season: int) -> List[dict]:
        """Fetch ALL fixtures for a league+season in one call."""
        data = self._request("/fixtures", {"league": league_id, "season": season})
        return data.get("response", []) if data else []

    def fetch_round_fixtures(self, league_id: int, season: int, round_name: str) -> List[dict]:
        """Fetch fixtures for a specific round."""
        data = self._request("/fixtures", {"league": league_id, "season": season, "round": round_name})
        return data.get("response", []) if data else []

    def fetch_full_stats(self, game_id: int) -> List[dict]:
        """Full-time team statistics for a fixture."""
        data = self._request("/fixtures/statistics", {"fixture": game_id})
        return data.get("response", []) if data else []

    def fetch_events(self, game_id: int) -> List[dict]:
        """Match events (goals, cards, subs)."""
        data = self._request("/fixtures/events", {"fixture": game_id})
        return data.get("response", []) if data else []

    def fetch_players(self, game_id: int) -> List[dict]:
        """Player-level statistics for a fixture."""
        data = self._request("/fixtures/players", {"fixture": game_id})
        return data.get("response", []) if data else []

    def list_rounds(self, league_id: int, season: int) -> List[str]:
        """Get all round names for a league+season."""
        data = self._request("/fixtures/rounds", {"league": league_id, "season": season})
        return data.get("response", []) if data else []
