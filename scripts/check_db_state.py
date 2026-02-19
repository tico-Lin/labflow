import sqlite3

conn = sqlite3.connect("labflow.db")
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cur.fetchall()]
print(tables)
if "alembic_version" in tables:
    cur.execute("SELECT version_num FROM alembic_version")
    print("alembic_version:", cur.fetchall())
else:
    print("no alembic_version")
conn.close()
