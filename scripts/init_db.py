import sqlite3
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import get_connection, get_db_path

def init_db():
    schema_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "app", "db", "schema.sql")
    )
    conn = get_connection()
    with open(schema_file, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"✅ Database initialized at: {get_db_path()}")

if __name__ == "__main__":
    init_db()
