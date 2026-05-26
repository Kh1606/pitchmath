"""
Database Layer
==============
Creates / migrates the unified football.db schema and provides
upsert helpers used by the season extractor.
"""

import sqlite3
import logging
from typing import Set

logger = logging.getLogger("metaren.db")


# ======================================================================
# SCHEMA INIT
# ======================================================================

def init_database(db_path: str) -> sqlite3.Connection:
    """Create all tables + indexes if they don't exist.  Returns connection."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()

    # 1) competitions -------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS competitions (
            competition_id INTEGER PRIMARY KEY,
            name           TEXT NOT NULL,
            country        TEXT,
            type           TEXT,
            season_start   INTEGER,
            season_end     INTEGER
        )
    """)

    # 2) teams --------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            team_id  INTEGER PRIMARY KEY,
            name     TEXT NOT NULL,
            country  TEXT
        )
    """)

    # 3) players ------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_id INTEGER PRIMARY KEY,
            name      TEXT NOT NULL
        )
    """)

    # 4) fixtures (master schedule — played + upcoming) ---------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fixtures (
            game_id         INTEGER PRIMARY KEY,
            date            TEXT,
            competition_id  INTEGER,
            season          INTEGER,
            round           TEXT,
            home_team_id    INTEGER,
            away_team_id    INTEGER,
            home_team_name  TEXT,
            away_team_name  TEXT,
            status_short    TEXT,
            status_long     TEXT,
            home_score      INTEGER,
            away_score      INTEGER,
            home_score_ht   INTEGER,
            away_score_ht   INTEGER,
            venue_name      TEXT,
            venue_city      TEXT,
            referee         TEXT,
            FOREIGN KEY (competition_id) REFERENCES competitions(competition_id),
            FOREIGN KEY (home_team_id)   REFERENCES teams(team_id),
            FOREIGN KEY (away_team_id)   REFERENCES teams(team_id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fix_comp_season_round ON fixtures(competition_id, season, round)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fix_date             ON fixtures(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fix_home_team        ON fixtures(home_team_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fix_away_team        ON fixtures(away_team_id)")

    # 5) matches (kept for backward-compat with Streamlit UI) --------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            game_id        INTEGER PRIMARY KEY,
            date           TEXT NOT NULL,
            league_name    TEXT NOT NULL,
            home_team      TEXT NOT NULL,
            away_team      TEXT NOT NULL,
            home_score     INTEGER,
            away_score     INTEGER,
            home_score_ht  INTEGER,
            away_score_ht  INTEGER
        )
    """)

    # 6) stats_team ---------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stats_team (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id        INTEGER NOT NULL,
            competition_id INTEGER,
            season         INTEGER,
            team_id        INTEGER,
            team_name      TEXT NOT NULL,
            stat_type      TEXT NOT NULL,
            value          REAL,
            period         TEXT NOT NULL,
            FOREIGN KEY (game_id) REFERENCES fixtures(game_id),
            UNIQUE(game_id, team_id, stat_type, period)
        )
    """)
    # Fallback unique for legacy rows that may lack team_id
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_st_game_team ON stats_team(game_id, team_name, stat_type, period)
    """)

    # 7) stats_player -------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stats_player (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id           INTEGER NOT NULL,
            competition_id    INTEGER,
            season            INTEGER,
            team_id           INTEGER,
            team_name         TEXT NOT NULL,
            player_id         INTEGER,
            player_name       TEXT NOT NULL,
            position          TEXT,
            rating            REAL,
            minutes           INTEGER,
            shots_total       INTEGER,
            shots_on          INTEGER,
            goals             INTEGER,
            assists           INTEGER,
            key_passes        INTEGER,
            passes_total      INTEGER,
            passes_accuracy   INTEGER,
            dribbles_attempts INTEGER,
            dribbles_success  INTEGER,
            duels_total       INTEGER,
            duels_won         INTEGER,
            tackles           INTEGER,
            interceptions     INTEGER,
            blocks            INTEGER,
            fouls_drawn       INTEGER,
            fouls_committed   INTEGER,
            yellow_cards      INTEGER,
            red_cards         INTEGER,
            saves             INTEGER,
            FOREIGN KEY (game_id)   REFERENCES fixtures(game_id),
            FOREIGN KEY (player_id) REFERENCES players(player_id),
            UNIQUE(game_id, player_id)
        )
    """)

    conn.commit()
    logger.info(f"DB ready: {db_path}")
    return conn


# ======================================================================
# UPSERT HELPERS
# ======================================================================

def upsert_competition(conn: sqlite3.Connection, comp: dict) -> None:
    """Insert or update the competitions table."""
    conn.execute("""
        INSERT OR REPLACE INTO competitions
            (competition_id, name, country, type, season_start, season_end)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        comp["competition_id"], comp["name"], comp.get("country"),
        comp.get("type"), comp.get("season_start"), comp.get("season_end"),
    ))
    conn.commit()


def upsert_team(conn: sqlite3.Connection, team_id: int, name: str, country: str = None) -> None:
    conn.execute("""
        INSERT OR REPLACE INTO teams (team_id, name, country)
        VALUES (?, ?, ?)
    """, (team_id, name, country))


def upsert_player(conn: sqlite3.Connection, player_id: int, name: str) -> None:
    if player_id:
        conn.execute("""
            INSERT OR REPLACE INTO players (player_id, name) VALUES (?, ?)
        """, (player_id, name))


def upsert_fixture(conn: sqlite3.Connection, row: dict) -> None:
    """Upsert a single fixture row."""
    conn.execute("""
        INSERT OR REPLACE INTO fixtures (
            game_id, date, competition_id, season, round,
            home_team_id, away_team_id, home_team_name, away_team_name,
            status_short, status_long,
            home_score, away_score, home_score_ht, away_score_ht,
            venue_name, venue_city, referee
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        row["game_id"], row["date"], row["competition_id"], row["season"], row["round"],
        row["home_team_id"], row["away_team_id"],
        row["home_team_name"], row["away_team_name"],
        row["status_short"], row["status_long"],
        row["home_score"], row["away_score"],
        row["home_score_ht"], row["away_score_ht"],
        row["venue_name"], row["venue_city"], row["referee"],
    ))


def upsert_match(conn: sqlite3.Connection, m: dict) -> None:
    """Upsert into the legacy 'matches' table (used by Streamlit UI)."""
    conn.execute("""
        INSERT OR REPLACE INTO matches
            (game_id, date, league_name, home_team, away_team,
             home_score, away_score, home_score_ht, away_score_ht)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        m["game_id"], m["date"], m["league_name"],
        m["home_team"], m["away_team"],
        m["home_score"], m["away_score"],
        m["home_score_ht"], m["away_score_ht"],
    ))


def save_team_stats(conn: sqlite3.Connection, game_id: int,
                    competition_id: int, season: int, stats: list) -> int:
    """Upsert team stat rows. Returns count saved."""
    saved = 0
    cur = conn.cursor()
    for s in stats:
        try:
            cur.execute("""
                INSERT OR REPLACE INTO stats_team
                    (game_id, competition_id, season, team_id, team_name,
                     stat_type, value, period)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                game_id, competition_id, season,
                s.get("team_id"), s["team_name"],
                s["stat_type"], s["value"], s["period"],
            ))
            saved += 1
        except sqlite3.Error:
            pass
    conn.commit()
    return saved


def save_player_stats(conn: sqlite3.Connection, players: list) -> int:
    """Upsert player stat rows. Returns count saved."""
    saved = 0
    cur = conn.cursor()
    for p in players:
        try:
            cur.execute("""
                INSERT OR REPLACE INTO stats_player
                    (game_id, competition_id, season, team_id, team_name,
                     player_id, player_name, position, rating, minutes,
                     shots_total, shots_on, goals, assists, key_passes,
                     passes_total, passes_accuracy,
                     dribbles_attempts, dribbles_success,
                     duels_total, duels_won,
                     tackles, interceptions, blocks,
                     fouls_drawn, fouls_committed,
                     yellow_cards, red_cards, saves)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                p["game_id"], p.get("competition_id"), p.get("season"),
                p.get("team_id"), p["team_name"],
                p["player_id"], p["player_name"], p.get("position"),
                p.get("rating"), p.get("minutes"),
                p.get("shots_total", 0), p.get("shots_on", 0),
                p.get("goals", 0), p.get("assists", 0), p.get("key_passes", 0),
                p.get("passes_total", 0), p.get("passes_accuracy", 0),
                p.get("dribbles_attempts", 0), p.get("dribbles_success", 0),
                p.get("duels_total", 0), p.get("duels_won", 0),
                p.get("tackles", 0), p.get("interceptions", 0), p.get("blocks", 0),
                p.get("fouls_drawn", 0), p.get("fouls_committed", 0),
                p.get("yellow_cards", 0), p.get("red_cards", 0), p.get("saves", 0),
            ))
            saved += 1
        except sqlite3.Error:
            pass
    conn.commit()
    return saved


def get_existing_stats_game_ids(conn: sqlite3.Connection) -> Set[int]:
    """Return set of game_ids that already have team-stat rows."""
    cur = conn.execute("SELECT DISTINCT game_id FROM stats_team")
    return {row[0] for row in cur.fetchall()}
