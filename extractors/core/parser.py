"""
Response Parsers
================
Transform raw API-Football JSON into flat dicts ready for DB upsert.
"""

from typing import List, Optional


def parse_fixture(fx: dict, competition_id: int, competition_name: str, season: int) -> dict:
    """Parse a fixture JSON blob into a flat dict for the fixtures table."""
    f = fx.get("fixture", {}) or {}
    lg = fx.get("league", {}) or {}
    t = fx.get("teams", {}) or {}
    g = fx.get("goals", {}) or {}
    sc = fx.get("score", {}) or {}
    st = f.get("status", {}) or {}
    v = f.get("venue", {}) or {}
    ht = sc.get("halftime", {}) or {}

    home = t.get("home", {}) or {}
    away = t.get("away", {}) or {}

    return {
        "game_id":        f.get("id"),
        "date":           (f.get("date") or "")[:19],
        "competition_id": competition_id,
        "season":         season,
        "round":          lg.get("round", ""),
        "home_team_id":   home.get("id"),
        "away_team_id":   away.get("id"),
        "home_team_name": home.get("name", "Unknown"),
        "away_team_name": away.get("name", "Unknown"),
        "status_short":   st.get("short", ""),
        "status_long":    st.get("long", ""),
        "home_score":     g.get("home"),
        "away_score":     g.get("away"),
        "home_score_ht":  ht.get("home"),
        "away_score_ht":  ht.get("away"),
        "venue_name":     v.get("name"),
        "venue_city":     v.get("city"),
        "referee":        f.get("referee"),
        # extras for convenience
        "league_name":    competition_name,
    }


def parse_match_legacy(fx: dict, competition_name: str) -> dict:
    """Build a row for the legacy 'matches' table that the Streamlit UI reads."""
    f = fx.get("fixture", {}) or {}
    t = fx.get("teams", {}) or {}
    g = fx.get("goals", {}) or {}
    ht = (fx.get("score", {}) or {}).get("halftime", {}) or {}

    return {
        "game_id":       f.get("id"),
        "date":          (f.get("date") or "")[:10],
        "league_name":   competition_name,
        "home_team":     (t.get("home", {}) or {}).get("name", "Unknown"),
        "away_team":     (t.get("away", {}) or {}).get("name", "Unknown"),
        "home_score":    g.get("home", 0) or 0,
        "away_score":    g.get("away", 0) or 0,
        "home_score_ht": ht.get("home", 0) or 0,
        "away_score_ht": ht.get("away", 0) or 0,
    }


def parse_team_stats(api_response: list, period: str) -> list:
    """Extract team stats from /fixtures/statistics response."""
    results = []
    for team_data in api_response:
        team_info = team_data.get("team", {}) or {}
        team_id = team_info.get("id")
        team_name = team_info.get("name", "Unknown")
        for stat in team_data.get("statistics", []):
            val = stat.get("value")
            if val is None:
                val = 0
            elif isinstance(val, str):
                val = float(val.replace("%", "")) if "%" in val else 0
            results.append({
                "team_id":   team_id,
                "team_name": team_name,
                "stat_type": stat.get("type", ""),
                "value":     float(val),
                "period":    period,
            })
    return results


def parse_1h_from_events(events: list, home_name: str, away_name: str,
                         home_id: int = None, away_id: int = None) -> list:
    """Derive 1H Goals & Cards from events (elapsed ≤ 45). No corners."""
    counters = {
        home_name: {"Yellow Cards": 0, "Red Cards": 0, "Goals": 0, "id": home_id},
        away_name: {"Yellow Cards": 0, "Red Cards": 0, "Goals": 0, "id": away_id},
    }
    for ev in events:
        elapsed = ev.get("time", {}).get("elapsed", 0) or 0
        if elapsed > 45:
            continue
        team = ev.get("team", {}).get("name")
        if team not in counters:
            continue
        ev_type = ev.get("type")
        ev_detail = ev.get("detail", "")
        if ev_type == "Card":
            if "Yellow" in ev_detail:
                counters[team]["Yellow Cards"] += 1
            elif "Red" in ev_detail:
                counters[team]["Red Cards"] += 1
        elif ev_type == "Goal":
            counters[team]["Goals"] += 1

    rows = []
    for team, metrics in counters.items():
        tid = metrics.pop("id", None)
        for stat_type, val in metrics.items():
            rows.append({
                "team_id":   tid,
                "team_name": team,
                "stat_type": stat_type,
                "value":     float(val),
                "period":    "1st Half",
            })
    return rows


def parse_player_stats(players_data: list, game_id: int,
                       competition_id: int = None, season: int = None) -> list:
    """Parse /fixtures/players response into flat dicts."""
    results = []
    for team_data in players_data:
        team_info = team_data.get("team", {}) or {}
        team_id = team_info.get("id")
        team_name = team_info.get("name", "Unknown")
        for p_entry in team_data.get("players", []):
            p = p_entry.get("player", {})
            stats_list = p_entry.get("statistics", [])
            if not stats_list:
                continue
            s = stats_list[0]

            def gi(d, k):
                return int(d.get(k) or 0) if d else 0

            g = s.get("games", {}) or {}
            sh = s.get("shots", {}) or {}
            go = s.get("goals", {}) or {}
            pa = s.get("passes", {}) or {}
            ta = s.get("tackles", {}) or {}
            du = s.get("duels", {}) or {}
            dr = s.get("dribbles", {}) or {}
            fo = s.get("fouls", {}) or {}
            ca = s.get("cards", {}) or {}

            results.append({
                "game_id":           game_id,
                "competition_id":    competition_id,
                "season":            season,
                "team_id":           team_id,
                "team_name":         team_name,
                "player_id":         p.get("id"),
                "player_name":       p.get("name", "Unknown"),
                "position":          g.get("position"),
                "rating":            float(g.get("rating") or 0) if g.get("rating") else None,
                "minutes":           gi(g, "minutes"),
                "shots_total":       gi(sh, "total"),
                "shots_on":          gi(sh, "on"),
                "goals":             gi(go, "total"),
                "assists":           gi(go, "assists"),
                "key_passes":        gi(pa, "key"),
                "passes_total":      gi(pa, "total"),
                "passes_accuracy":   gi(pa, "accuracy"),
                "dribbles_attempts": gi(dr, "attempts"),
                "dribbles_success":  gi(dr, "success"),
                "duels_total":       gi(du, "total"),
                "duels_won":         gi(du, "won"),
                "tackles":           gi(ta, "total"),
                "interceptions":     gi(ta, "interceptions"),
                "blocks":            gi(ta, "blocks"),
                "fouls_drawn":       gi(fo, "drawn"),
                "fouls_committed":   gi(fo, "committed"),
                "yellow_cards":      gi(ca, "yellow"),
                "red_cards":         gi(ca, "red"),
                "saves":             gi(s.get("goals", {}), "saves"),
            })
    return results
