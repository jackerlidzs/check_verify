import sqlite3

conn = sqlite3.connect('data/k12_verify.db')
cursor = conn.cursor()

# Get tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
print(f"Tables: {tables}")

# Get sample teachers
if 'teachers' in tables:
    cursor.execute("SELECT * FROM teachers LIMIT 5")
    cols = [d[0] for d in cursor.description]
    print(f"\nColumns: {cols}")
    for row in cursor.fetchall():
        print(row)

conn.close()
