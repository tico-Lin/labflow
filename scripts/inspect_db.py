import sqlite3
import os

DB_PATH = os.getenv("DATABASE_URL", "labflow.db")
if DB_PATH.startswith("sqlite:///"):
    DB_PATH = DB_PATH.replace("sqlite:///", "")

if not os.path.exists(DB_PATH):
    print(f"Database file not found: {DB_PATH}")
    raise SystemExit(1)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("SELECT name, type, sql FROM sqlite_master WHERE type IN ('table','index') ORDER BY name;")
rows = cur.fetchall()
tables = [r for r in rows if r[1] == 'table']

print(f"Connected to: {DB_PATH}\n")
print("Tables:")
for name, typ, sql in tables:
    print(f"- {name}")
    # fetch columns
    try:
        cur2 = conn.execute(f"PRAGMA table_info('{name}')")
        cols = cur2.fetchall()
        for c in cols:
            cid, colname, coltype, notnull, dflt_value, pk = c
            print(f"    {colname} {coltype} {'PK' if pk else ''}")
    except Exception as e:
        print(f"    (failed to inspect columns: {e})")

conn.close()
