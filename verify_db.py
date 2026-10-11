import sqlite3

conn = sqlite3.connect("smart_retail.db")

tables = conn.execute("""
SELECT name
FROM sqlite_master
WHERE type = 'table'
ORDER BY name
""").fetchall()

print("SQLite tables:")
for table in tables:
    print("-", table[0])

conn.close()
