"""
MetaRen Extractor — CLI Runner
================================

Usage (from project root):

  # Full extraction for EPL
  python -m extractors.run --config configs/country/england/epl.yml

  # Only rounds 1-25 of Serie A
  python -m extractors.run --config configs/country/italy/serie_a.yml --round-from 1 --round-to 25

  # Daily update (upsert fixtures, fetch missing stats only)
  python -m extractors.run --config configs/country/england/epl.yml --update-only

  # Multiple configs at once
  python -m extractors.run --config configs/country/england/epl.yml configs/europe/ucl.yml
"""

import argparse
import logging
import os
from dotenv import load_dotenv
import sys
import yaml
import psycopg2
from extractors.core import db_pg
from extractors.core.api_client import APIFootballClient
from extractors.core.db import init_database
from extractors.core.season_extractor import SeasonExtractor

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("metaren.run")

# Default DB path (relative to project root)
DEFAULT_DB = os.path.join("db", "football.db")


def load_config(path: str) -> dict:
    """Load a YAML config file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_config(config: dict, db_backend: str, db_path: str, api_key: str,
               round_from=None, round_to=None, update_only=False):

    """Run extraction for a single config."""

    comp_name = config["name"]
    season = config["season"]
    delay = config.get("request_delay", 0.25)

    logger.info("=" * 65)
    logger.info(f"MetaRen Extractor")
    logger.info(f"  Competition : {comp_name} (id={config['competition_id']})")
    logger.info(f"  Season      : {season}")
    logger.info(f"  DB          : {db_backend} ({'pg:5433' if db_backend=='pg' else db_path})")
    logger.info(f"  Mode        : {'update-only' if update_only else 'full'}")
    if round_from or round_to:
        logger.info(f"  Rounds      : {round_from or 'start'} → {round_to or 'end'}")
    logger.info("=" * 65)

    # Ensure db directory exists
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    if db_backend == "pg":
        conn = psycopg2.connect(
            host=os.getenv("PG_HOST", "127.0.0.1"),
            port=int(os.getenv("PG_PORT", "5433")),
            dbname=os.getenv("PG_DB", "metaren"),
            user=os.getenv("PG_USER", "metaren"),
            password=os.getenv("PG_PASSWORD", "metaren_pw"),
        )
        
        dbmod = db_pg
    else:
        conn = init_database(db_path)
        from extractors.core import db as dbmod


    client = APIFootballClient(api_key, request_delay=delay)
    extractor = SeasonExtractor(config, conn, client, dbmod)


    totals = extractor.run(
        round_from=round_from,
        round_to=round_to,
        update_only=update_only,
    )

    conn.close()

    # Summary
    logger.info("")
    logger.info("=" * 65)
    logger.info("EXTRACTION COMPLETE")
    logger.info(f"  Fixtures upserted   : {totals['fixtures_upserted']}")
    logger.info(f"  Played processed    : {totals['played_processed']}")
    logger.info(f"  Skipped existing    : {totals['skipped_existing']}")
    logger.info(f"  Upcoming / NS       : {totals['upcoming']}")
    logger.info(f"  Team stat rows      : {totals['stats_rows']}")
    logger.info(f"  Player stat rows    : {totals['player_rows']}")
    logger.info(f"  Total API requests  : {client.request_count}")
    logger.info("=" * 65)

    return totals


def main():
    parser = argparse.ArgumentParser(
        description="MetaRen Football Extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
    "--db",
    choices=["sqlite", "pg"],
    default="sqlite",
    help="Database backend: sqlite (default) or pg (Postgres)",
    )
    parser.add_argument(
        "--config", nargs="+", required=True,
        help="Path(s) to YAML config file(s)"
    )
    parser.add_argument(
    "--db-path", default=DEFAULT_DB,
    help=f"SQLite database path (default: {DEFAULT_DB})"
    )
    parser.add_argument(
        "--api-key", default=None,
        help="API-Football key (default: APIFOOTBALL_KEY env var)"
    )
    parser.add_argument(
        "--round-from", type=int, default=None,
        help="Start round number (overrides config)"
    )
    parser.add_argument(
        "--round-to", type=int, default=None,
        help="End round number (overrides config)"
    )
    parser.add_argument(
        "--update-only", action="store_true",
        help="Upsert fixtures and only fetch stats for new finished matches"
    )

    args = parser.parse_args()

    # Resolve API key (CLI arg takes priority, else APIFOOTBALL_KEY env var)
    api_key = args.api_key or os.environ.get("APIFOOTBALL_KEY")
    if not api_key:
        logger.error(
            "No API-Football key found. Set APIFOOTBALL_KEY in your .env "
            "(see .env.example) or pass --api-key."
        )
        sys.exit(1)

    for config_path in args.config:
        if not os.path.isfile(config_path):
            logger.error(f"Config not found: {config_path}")
            sys.exit(1)

        config = load_config(config_path)
        run_config(
            config, args.db, args.db_path, api_key,
            round_from=args.round_from,
            round_to=args.round_to,
            update_only=args.update_only,
        )



if __name__ == "__main__":
    main()
