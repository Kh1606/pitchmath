"""
Data Access Layer for MetaRen Analytics
========================================
Handles all SQLite database operations.

Tables used:
  - fixtures     → master schedule (played + upcoming, with competition_id/season)
  - competitions → competition metadata
  - stats_team   → team stats per match
  - stats_player → player stats per match (has competition_id + season columns)
"""
import os
from dotenv import load_dotenv

import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime
from typing import Optional, List, Dict, Any

load_dotenv()

# Database path (relative to app.py working directory)
PG = dict(
    host=os.getenv("PG_HOST", "127.0.0.1"),
    port=int(os.getenv("PG_PORT", "5433")),
    dbname=os.getenv("PG_DB", "metaren"),
    user=os.getenv("PG_USER", "metaren"),
    password=os.getenv("PG_PASSWORD", "metaren_pw"),
)


@st.cache_resource
def get_db_connection():
    return psycopg2.connect(**PG)



# =========================
# Core loaders (fixtures-driven)
# =========================

@st.cache_data(ttl=300)
def load_matches() -> pd.DataFrame:
    """
    Load PLAYED matches from fixtures table joined with competitions.
    Replaces the legacy matches-table loader.
    Includes competition_id and season for filtering.
    """
    conn = get_db_connection()
    query = """
        SELECT
            f.game_id,
            f.date,
            COALESCE(c.name, 'Unknown') AS league_name,
            f.competition_id,
            f.season,
            f.home_team_name AS home_team,
            f.away_team_name AS away_team,
            f.home_score,
            f.away_score,
            COALESCE(f.home_score_ht, 0) AS home_score_ht,
            COALESCE(f.away_score_ht, 0) AS away_score_ht
        FROM fixtures f
        LEFT JOIN competitions c ON f.competition_id = c.competition_id
        WHERE f.status_short IN ('FT', 'AET', 'PEN')
           OR (f.home_score IS NOT NULL AND f.away_score IS NOT NULL AND f.status_short != 'NS')
        ORDER BY f.date DESC
    """
    df = pd.read_sql_query(query, conn)

    # Add computed columns
    df["total_goals"] = df["home_score"] + df["away_score"]
    df["total_goals_ht"] = df["home_score_ht"] + df["away_score_ht"]

    return df


@st.cache_data(ttl=300)
def load_team_stats() -> pd.DataFrame:
    """Load all team statistics from database."""
    conn = get_db_connection()
    query = """
        SELECT game_id, team_name, stat_type, value, period
        FROM stats_team
    """
    return pd.read_sql_query(query, conn)


@st.cache_data(ttl=300)
def load_player_stats() -> pd.DataFrame:
    """
    Load all player statistics joined with fixtures+competitions
    so we get season, competition_id, date, home/away teams.
    """
    conn = get_db_connection()

    query = """
        SELECT
            sp.*,
            COALESCE(c.name, 'Unknown') AS league_name,
            f.date,
            f.home_team_name AS home_team,
            f.away_team_name AS away_team
        FROM stats_player sp
        JOIN fixtures f ON sp.game_id = f.game_id
        LEFT JOIN competitions c ON f.competition_id = c.competition_id
        ORDER BY f.date DESC
    """
    try:
        df = pd.read_sql_query(query, conn)
    except Exception:
        # Fallback: stats_player already has competition_id and season
        query = """
            SELECT sp.game_id, sp.competition_id, sp.season,
                   sp.team_name, sp.player_name, sp.rating,
                   sp.minutes, sp.shots_total, sp.shots_on, sp.goals,
                   sp.key_passes, sp.tackles,
                   COALESCE(c.name, 'Unknown') AS league_name,
                   f.date, f.home_team_name AS home_team, f.away_team_name AS away_team
            FROM stats_player sp
            JOIN fixtures f ON sp.game_id = f.game_id
            LEFT JOIN competitions c ON f.competition_id = c.competition_id
            ORDER BY f.date DESC
        """
        df = pd.read_sql_query(query, conn)

    # Ensure all expected columns exist
    for col in [
        "assists", "dribbles_attempts", "dribbles_success",
        "duels_total", "duels_won", "interceptions", "blocks",
        "fouls_drawn", "fouls_committed", "yellow_cards", "red_cards",
        "position", "minutes", "passes_total"
    ]:
        if col not in df.columns:
            df[col] = 0

    return df


# =========================
# Fixtures (Played + Upcoming)
# =========================

@st.cache_data(ttl=300)
def load_fixtures() -> pd.DataFrame:
    """Load ALL fixtures (played + upcoming) from the fixtures table."""
    conn = get_db_connection()
    try:
        query = """
            SELECT
                f.game_id,
                f.date,
                f.competition_id,
                COALESCE(c.name, 'Unknown') AS league_name,
                f.season,
                f.round,
                f.home_team_name AS home_team,
                f.away_team_name AS away_team,
                f.home_team_id,
                f.away_team_id,
                f.status_short,
                f.status_long,
                f.home_score,
                f.away_score,
                f.home_score_ht,
                f.away_score_ht,
                f.venue_name,
                f.venue_city,
                f.referee
            FROM fixtures f
            LEFT JOIN competitions c ON f.competition_id = c.competition_id
            ORDER BY f.date ASC
        """
        return pd.read_sql_query(query, conn)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_upcoming_fixtures(season: Optional[int] = None,
                           competition_id: Optional[int] = None) -> pd.DataFrame:
    """
    Load upcoming / not-started fixtures.
    Optionally filter by season and/or competition_id.
    """
    conn = get_db_connection()
    today = datetime.now().strftime("%Y-%m-%d")

    params: list = [today]
    clauses = []
    if season is not None:
        clauses.append("AND f.season = %s")
        params.append(season)
    if competition_id is not None:
        clauses.append("AND f.competition_id = %s")
        params.append(competition_id)

    extra = " ".join(clauses)

    try:
        query = f"""
            SELECT
                f.game_id,
                f.date,
                f.competition_id,
                COALESCE(c.name, 'Unknown') AS league_name,
                f.season,
                f.round,
                f.home_team_name AS home_team,
                f.away_team_name AS away_team,
                f.status_short,
                f.status_long,
                f.venue_name,
                f.venue_city,
                f.referee
            FROM fixtures f
            LEFT JOIN competitions c ON f.competition_id = c.competition_id
            WHERE f.date >= %s
              AND (f.status_short IN ('NS', 'TBD', '')
                   OR f.home_score IS NULL)
              {extra}
            ORDER BY f.date ASC
        """
        return pd.read_sql_query(query, conn, params=params)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_competitions() -> pd.DataFrame:
    """Load the competitions lookup table."""
    conn = get_db_connection()
    try:
        return pd.read_sql_query("SELECT * FROM competitions ORDER BY name", conn)
    except Exception:
        return pd.DataFrame()


# =========================
# Season / Competition helpers
# =========================

@st.cache_data(ttl=300)
def get_available_seasons() -> List[int]:
    """Return distinct seasons from fixtures, sorted descending."""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT DISTINCT season FROM fixtures ORDER BY season DESC", conn)
    return df["season"].tolist()


@st.cache_data(ttl=300)
def get_competitions_for_season(season: int) -> pd.DataFrame:
    """
    Return competitions that have at least one fixture in the given season.
    Includes country from competitions table for grouping.
    """
    conn = get_db_connection()
    query = """
        SELECT DISTINCT
            c.competition_id,
            c.name,
            c.type,
            c.country
        FROM fixtures f
        JOIN competitions c ON f.competition_id = c.competition_id
        WHERE f.season = %s
        ORDER BY c.country, c.name
    """
    return pd.read_sql_query(query, conn, params=[season])


def format_season_label(season: int) -> str:
    """Format season int to display label: 2025 -> '2025/26'."""
    return f"{season}/{(season + 1) % 100:02d}"


# =========================
# Utility
# =========================

def split_upcoming_played_fixtures(df_fx: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Split fixtures into upcoming vs played."""
    if df_fx is None or len(df_fx) == 0:
        return {"upcoming": df_fx, "played": df_fx}

    df = df_fx.copy()
    df["status_short"] = df["status_short"].fillna("").astype(str).str.upper().str.strip()

    finished = {"FT", "AET", "PEN"}
    played_mask = (
        df["status_short"].isin(finished)
        | (~df["home_score"].isna() & ~df["away_score"].isna() & df["status_short"].ne("NS"))
    )
    played = df[played_mask].copy()
    upcoming = df[~played_mask].copy()

    return {"upcoming": upcoming, "played": played}


# =========================
# Team helpers
# =========================

def get_available_teams(df_matches: pd.DataFrame, league_filter: Optional[str] = None) -> List[str]:
    """Get list of unique teams from matches. league_filter kept for compat but ignored (filtering done upstream)."""
    df = df_matches
    home_teams = df["home_team"].unique().tolist()
    away_teams = df["away_team"].unique().tolist()
    all_teams = list(set(home_teams + away_teams))
    return sorted(all_teams)


def filter_matches_by_team(
    df_matches: pd.DataFrame,
    team_name: str,
    venue: str = "All",
    league_filter: Optional[str] = None
) -> pd.DataFrame:
    """Filter matches involving a specific team with venue filter.
    league_filter kept for signature compat but ignored (filtering done upstream).
    """
    df = df_matches.copy()

    # Team filter
    if venue == "Home":
        mask = df["home_team"].str.contains(team_name, case=False, na=False)
    elif venue == "Away":
        mask = df["away_team"].str.contains(team_name, case=False, na=False)
    else:
        mask = (
            df["home_team"].str.contains(team_name, case=False, na=False)
            | df["away_team"].str.contains(team_name, case=False, na=False)
        )

    df = df[mask].copy()
    if len(df) == 0:
        return df

    # Add team-specific columns
    df["is_home"] = df["home_team"].str.contains(team_name, case=False, na=False)
    df["team_score"] = df.apply(lambda r: r["home_score"] if r["is_home"] else r["away_score"], axis=1)
    df["opponent_score"] = df.apply(lambda r: r["away_score"] if r["is_home"] else r["home_score"], axis=1)
    df["team_score_ht"] = df.apply(lambda r: r["home_score_ht"] if r["is_home"] else r["away_score_ht"], axis=1)
    df["opponent_score_ht"] = df.apply(lambda r: r["away_score_ht"] if r["is_home"] else r["home_score_ht"], axis=1)

    df["result"] = df.apply(
        lambda r: "Win" if r["team_score"] > r["opponent_score"]
        else ("Draw" if r["team_score"] == r["opponent_score"] else "Loss"),
        axis=1
    )
    df["opponent"] = df.apply(lambda r: r["away_team"] if r["is_home"] else r["home_team"], axis=1)

    # 2nd half derived
    df["team_score_2h"] = df["team_score"] - df["team_score_ht"]
    df["opponent_score_2h"] = df["opponent_score"] - df["opponent_score_ht"]
    df["total_goals_2h"] = df["total_goals"] - df["total_goals_ht"]

    return df


def get_head_to_head_matches(df_matches: pd.DataFrame, team_a: str, team_b: str) -> pd.DataFrame:
    """Get all matches between two teams."""
    mask = (
        ((df_matches["home_team"].str.contains(team_a, case=False, na=False)) &
         (df_matches["away_team"].str.contains(team_b, case=False, na=False))) |
        ((df_matches["home_team"].str.contains(team_b, case=False, na=False)) &
         (df_matches["away_team"].str.contains(team_a, case=False, na=False)))
    )
    return df_matches[mask].copy()


def get_team_stat_for_match(
    df_team_stats: pd.DataFrame,
    game_id: int,
    team_name: str,
    stat_type: str,
    period: str
) -> Optional[float]:
    """Get a specific stat value for a team in a match."""
    mask = (
        (df_team_stats["game_id"] == game_id) &
        (df_team_stats["team_name"].str.contains(team_name, case=False, na=False)) &
        (df_team_stats["stat_type"].astype(str).str.strip().str.lower() == str(stat_type).strip().lower()) &
        (df_team_stats["period"].astype(str).str.strip().str.lower() == str(period).strip().lower())
    )

    stats = df_team_stats[mask]
    if len(stats) > 0:
        return stats["value"].iloc[0]
    return None
