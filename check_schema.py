# check_schema.py
import sqlite3

DB = "voting.db"
conn = sqlite3.connect(DB)

print("== tables ==")
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(tables)

print("\n== alembic_version ==")
print(conn.execute("SELECT * FROM alembic_version").fetchall())

print("\n== candidate schema ==")
schema = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='candidate'").fetchone()
print(schema[0] if schema else "❌ candidate 表不存在")

print("\n== candidate_old schema ==")
schema_old = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='candidate_old'").fetchone()
print(schema_old[0] if schema_old else "❌ candidate_old 表不存在")

print("\n== candidate indexes ==")
if schema:
    indexes = conn.execute("PRAGMA index_list(candidate)").fetchall()
    print(indexes)
    for idx in indexes:
        name = idx[1]
        cols = conn.execute(f"PRAGMA index_info({name})").fetchall()
        print(f" -> {name}: {cols}")
else:
    print("（跳過，因為 candidate 不存在）")

conn.close()
