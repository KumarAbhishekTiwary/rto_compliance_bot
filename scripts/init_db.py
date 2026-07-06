"""Initialize the SQLite database from schema.sql"""
import sqlite3
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings

def init_db():
    schema_path = Path(__file__).resolve().parent.parent / "app" / "db" / "schema.sql"
    with open(schema_path, "r") as f:
        schema = f.read()

    conn = sqlite3.connect(settings.DB_PATH)
    conn.executescript(schema)
    conn.commit()
    conn.close()
    print(f"✅ Database initialized at: {settings.DB_PATH}")

if __name__ == "__main__":
    init_db()
