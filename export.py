import os
import sqlite3
import pandas as pd

DB_PATH = "db/football.db"
OUT_DIR = "csv"

os.makedirs(OUT_DIR, exist_ok=True)

con = sqlite3.connect(DB_PATH)

# list tables
tables = pd.read_sql(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name",
    con
)["name"].tolist()

print("Tables:", tables)

# export each table + schema
schema_rows = []
for t in tables:
    # schema
    info = pd.read_sql(f"PRAGMA table_info('{t}')", con)
    info["table"] = t
    schema_rows.append(info)

    # data
    df = pd.read_sql(f"SELECT * FROM '{t}'", con)
    df.to_csv(os.path.join(OUT_DIR, f"{t}.csv"), index=False)

pd.concat(schema_rows, ignore_index=True).to_csv(os.path.join(OUT_DIR, "_schema.csv"), index=False)

print(f"Exported {len(tables)} tables to: {OUT_DIR}")
con.close()
