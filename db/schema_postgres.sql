CREATE TABLE IF NOT EXISTS competitions (
  competition_id INTEGER PRIMARY KEY,
  name           TEXT NOT NULL,
  country        TEXT,
  type           TEXT,
  season_start   INTEGER,
  season_end     INTEGER
);

CREATE TABLE IF NOT EXISTS teams (
  team_id  INTEGER PRIMARY KEY,
  name     TEXT NOT NULL,
  country  TEXT
);

CREATE TABLE IF NOT EXISTS players (
  player_id INTEGER PRIMARY KEY,
  name      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fixtures (
  game_id         INTEGER PRIMARY KEY,
  date            TEXT,
  competition_id  INTEGER REFERENCES competitions(competition_id),
  season          INTEGER,
  round           TEXT,
  home_team_id    INTEGER REFERENCES teams(team_id),
  away_team_id    INTEGER REFERENCES teams(team_id),
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
  referee         TEXT
);

CREATE INDEX IF NOT EXISTS idx_fix_comp_season_round ON fixtures(competition_id, season, round);
CREATE INDEX IF NOT EXISTS idx_fix_date             ON fixtures(date);
CREATE INDEX IF NOT EXISTS idx_fix_home_team        ON fixtures(home_team_id);
CREATE INDEX IF NOT EXISTS idx_fix_away_team        ON fixtures(away_team_id);

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
);

CREATE TABLE IF NOT EXISTS stats_team (
  id             BIGSERIAL PRIMARY KEY,
  game_id        INTEGER NOT NULL REFERENCES fixtures(game_id),
  competition_id INTEGER,
  season         INTEGER,
  team_id        INTEGER,
  team_name      TEXT NOT NULL,
  stat_type      TEXT NOT NULL,
  value          DOUBLE PRECISION,
  period         TEXT NOT NULL,
  UNIQUE(game_id, team_id, stat_type, period)
);

CREATE INDEX IF NOT EXISTS idx_st_game_team ON stats_team(game_id, team_name, stat_type, period);

CREATE TABLE IF NOT EXISTS stats_player (
  id                BIGSERIAL PRIMARY KEY,
  game_id           INTEGER NOT NULL REFERENCES fixtures(game_id),
  competition_id    INTEGER,
  season            INTEGER,
  team_id           INTEGER,
  team_name         TEXT NOT NULL,
  player_id         INTEGER REFERENCES players(player_id),
  player_name       TEXT NOT NULL,
  position          TEXT,
  rating            DOUBLE PRECISION,
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
  UNIQUE(game_id, player_id)
);
