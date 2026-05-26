import sqlite3
import psycopg2

SQLITE_PATH = r"db\football.db"

PG = dict(
    host="127.0.0.1",
    port=5433,
    dbname="metaren",
    user="metaren",
    password="metaren_pw",
)

TABLES_IN_ORDER = ["stats_player"]


def copy_table(sqlite_con, pg_con, table: str):
    s_cur = sqlite_con.cursor()
    p_cur = pg_con.cursor()

    s_cur.execute(f"SELECT * FROM {table}")
    rows = s_cur.fetchall()

    if not rows:
        print(f"{table}: 0 rows (skip)")
        return

    col_names = [d[0] for d in s_cur.description]
    cols_sql = ",".join(col_names)
    placeholders = ",".join(["%s"] * len(col_names))

    # wipe destination table so we don't duplicate data
    p_cur.execute(f"TRUNCATE {table} RESTART IDENTITY CASCADE;")

    p_cur.executemany(
        f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders})",
        rows
    )
    pg_con.commit()
    print(f"{table}: {len(rows)} rows copied")

def main():
    sqlite_con = sqlite3.connect(SQLITE_PATH)
    pg_con = psycopg2.connect(**PG)

    for t in TABLES_IN_ORDER:
        copy_table(sqlite_con, pg_con, t)

    sqlite_con.close()
    pg_con.close()
    print("DONE")

if __name__ == "__main__":
    main()
