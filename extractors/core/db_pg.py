from __future__ import annotations
import zlib
from typing import Set, List, Dict, Any
import psycopg2
from psycopg2.extras import execute_values


def get_existing_stats_game_ids(conn, competition_id: int, season: int) -> Set[int]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT game_id
            FROM stats_team
            WHERE competition_id = %s AND season = %s
            """,
            (competition_id, season),
        )
        return {r[0] for r in cur.fetchall()}


def upsert_competition(conn, comp: Dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO competitions (competition_id, name, country, type, season_start, season_end)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (competition_id) DO UPDATE SET
              name=EXCLUDED.name,
              country=EXCLUDED.country,
              type=EXCLUDED.type,
              season_start=EXCLUDED.season_start,
              season_end=EXCLUDED.season_end
            """,
            (
                comp.get("competition_id"),
                comp.get("name"),
                comp.get("country"),
                comp.get("type"),
                comp.get("season_start"),
                comp.get("season_end"),
            ),
        )
    conn.commit()


def upsert_team(conn, team_id: int, name: str, country: str = None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO teams (team_id, name, country)
            VALUES (%s,%s,%s)
            ON CONFLICT (team_id) DO UPDATE SET
              name=EXCLUDED.name,
              country=EXCLUDED.country
            """,
            (team_id, name, country),
        )
    conn.commit()


def upsert_player(conn, player_id: int, name: str) -> None:
    # Keep Phase-1 compatibility: if player_id is missing/0, store as 0 Unknown
    pid = int(player_id) if player_id is not None else 0
    if pid == 0:
        name = name or "Unknown"

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO players (player_id, name)
            VALUES (%s,%s)
            ON CONFLICT (player_id) DO UPDATE SET
              name=EXCLUDED.name
            """,
            (pid, name),
        )
    conn.commit()


def upsert_fixture(conn, row: Dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO fixtures (
              game_id, date, competition_id, season, round,
              home_team_id, away_team_id, home_team_name, away_team_name,
              status_short, status_long,
              home_score, away_score, home_score_ht, away_score_ht,
              venue_name, venue_city, referee
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (game_id) DO UPDATE SET
              date=EXCLUDED.date,
              competition_id=EXCLUDED.competition_id,
              season=EXCLUDED.season,
              round=EXCLUDED.round,
              home_team_id=EXCLUDED.home_team_id,
              away_team_id=EXCLUDED.away_team_id,
              home_team_name=EXCLUDED.home_team_name,
              away_team_name=EXCLUDED.away_team_name,
              status_short=EXCLUDED.status_short,
              status_long=EXCLUDED.status_long,
              home_score=EXCLUDED.home_score,
              away_score=EXCLUDED.away_score,
              home_score_ht=EXCLUDED.home_score_ht,
              away_score_ht=EXCLUDED.away_score_ht,
              venue_name=EXCLUDED.venue_name,
              venue_city=EXCLUDED.venue_city,
              referee=EXCLUDED.referee
            """,
            (
                row.get("game_id"),
                row.get("date"),
                row.get("competition_id"),
                row.get("season"),
                row.get("round"),
                row.get("home_team_id"),
                row.get("away_team_id"),
                row.get("home_team_name"),
                row.get("away_team_name"),
                row.get("status_short"),
                row.get("status_long"),
                row.get("home_score"),
                row.get("away_score"),
                row.get("home_score_ht"),
                row.get("away_score_ht"),
                row.get("venue_name"),
                row.get("venue_city"),
                row.get("referee"),
            ),
        )
    conn.commit()

def upsert_match(conn, m: Dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO matches (
              game_id, date, league_name, home_team, away_team,
              home_score, away_score, home_score_ht, away_score_ht
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (game_id) DO UPDATE SET
              date=EXCLUDED.date,
              league_name=EXCLUDED.league_name,
              home_team=EXCLUDED.home_team,
              away_team=EXCLUDED.away_team,
              home_score=EXCLUDED.home_score,
              away_score=EXCLUDED.away_score,
              home_score_ht=EXCLUDED.home_score_ht,
              away_score_ht=EXCLUDED.away_score_ht
            """,
            (
                m.get("game_id"),
                m.get("date"),
                m.get("league_name"),
                m.get("home_team"),
                m.get("away_team"),
                m.get("home_score"),
                m.get("away_score"),
                m.get("home_score_ht"),
                m.get("away_score_ht"),
            ),
        )
    conn.commit()


def save_team_stats(conn, game_id: int, competition_id: int, season: int, rows) -> int:
    """
    Accepts rows in the same format as SQLite version:
    rows = list of dicts with keys: team_id, team_name, stat_type, value, period
    """
    if not rows:
        return 0

    values = []
    for r in rows:
        values.append((
            game_id,
            competition_id,
            season,
            r.get("team_id"),
            r.get("team_name"),
            r.get("stat_type"),
            r.get("value"),
            r.get("period"),
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO stats_team (game_id, competition_id, season, team_id, team_name, stat_type, value, period)
            VALUES %s
            ON CONFLICT (game_id, team_id, stat_type, period) DO UPDATE SET
              value=EXCLUDED.value,
              competition_id=EXCLUDED.competition_id,
              season=EXCLUDED.season,
              team_name=EXCLUDED.team_name
            """,
            values
        )
    conn.commit()
    return len(values)


def save_player_stats(conn, rows):
    """
    rows: list[dict] from parse_player_stats()
    Must be unique within the batch by (game_id, player_id) for ON CONFLICT.
    """
    dedup = {}  # (game_id, player_id) -> tuple

    for r in rows:
        game_id = int(r.get("game_id") or 0)
        competition_id = int(r.get("competition_id") or 0)
        season = int(r.get("season") or 0)

        team_id = int(r.get("team_id") or 0)
        team_name = (r.get("team_name") or "").strip() or "Unknown Team"

        player_id = int(r.get("player_id") or 0)
        player_name = (r.get("player_name") or "").strip() or "Unknown"
        position = (r.get("position") or "").strip() or None

        # If player_id missing => generate stable synthetic id
        if player_id == 0:
            key_str = f"{game_id}:{team_id}:{player_name}:{position or ''}"
            h = zlib.crc32(key_str.encode("utf-8")) & 0x7fffffff  # 0..2,147,483,647
            player_id = -(h or 1)  # -1..-2,147,483,647 (never 0)


        row_tuple = (
            game_id,
            competition_id,
            season,
            team_id,
            team_name,
            player_id,
            player_name,
            position,
            r.get("rating"),
            r.get("minutes"),
            r.get("shots_total"),
            r.get("shots_on"),
            r.get("goals"),
            r.get("assists"),
            r.get("key_passes"),       # ✅ matches DB
            r.get("passes_total"),
            r.get("passes_accuracy"),  # ✅ matches DB
            r.get("dribbles_attempts"),# ✅ matches DB
            r.get("dribbles_success"),
            r.get("duels_total"),
            r.get("duels_won"),
            r.get("tackles"),          # ✅ matches DB
            r.get("interceptions"),
            r.get("blocks"),
            r.get("fouls_drawn"),
            r.get("fouls_committed"),
            r.get("yellow_cards"),     # ✅ matches DB
            r.get("red_cards"),        # ✅ matches DB
            r.get("saves"),
        )

        dedup[(game_id, player_id)] = row_tuple

    values = list(dedup.values())
    if not values:
        return 0

    q = """
    INSERT INTO stats_player (
        game_id, competition_id, season,
        team_id, team_name,
        player_id, player_name, position,
        rating, minutes,
        shots_total, shots_on,
        goals, assists,
        key_passes,
        passes_total, passes_accuracy,
        dribbles_attempts, dribbles_success,
        duels_total, duels_won,
        tackles, interceptions, blocks,
        fouls_drawn, fouls_committed,
        yellow_cards, red_cards,
        saves
    )
    VALUES %s
    ON CONFLICT (game_id, player_id) DO UPDATE SET
        competition_id = EXCLUDED.competition_id,
        season = EXCLUDED.season,
        team_id = EXCLUDED.team_id,
        team_name = EXCLUDED.team_name,
        player_name = EXCLUDED.player_name,
        position = EXCLUDED.position,
        rating = EXCLUDED.rating,
        minutes = EXCLUDED.minutes,
        shots_total = EXCLUDED.shots_total,
        shots_on = EXCLUDED.shots_on,
        goals = EXCLUDED.goals,
        assists = EXCLUDED.assists,
        key_passes = EXCLUDED.key_passes,
        passes_total = EXCLUDED.passes_total,
        passes_accuracy = EXCLUDED.passes_accuracy,
        dribbles_attempts = EXCLUDED.dribbles_attempts,
        dribbles_success = EXCLUDED.dribbles_success,
        duels_total = EXCLUDED.duels_total,
        duels_won = EXCLUDED.duels_won,
        tackles = EXCLUDED.tackles,
        interceptions = EXCLUDED.interceptions,
        blocks = EXCLUDED.blocks,
        fouls_drawn = EXCLUDED.fouls_drawn,
        fouls_committed = EXCLUDED.fouls_committed,
        yellow_cards = EXCLUDED.yellow_cards,
        red_cards = EXCLUDED.red_cards,
        saves = EXCLUDED.saves;
    """
    # ensure all player_ids exist in players (FK requirement)
    # ensure all player_ids exist in players (FK requirement)
    player_values = [(player_id, player_name) for (
        _game_id, _comp_id, _season, _team_id, _team_name, player_id, player_name, *_rest
    ) in values]

    # dedup
    player_values = list({(pid, pname) for pid, pname in player_values})

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO players (player_id, name)
            VALUES %s
            ON CONFLICT (player_id) DO UPDATE SET
              name = EXCLUDED.name
            """,
            player_values,
            page_size=1000,
        )

        # now insert stats_player
        execute_values(cur, q, values, page_size=1000)

    conn.commit()
    return len(values)

