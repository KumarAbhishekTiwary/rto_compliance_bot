"""Add SLA tracking columns to violations table."""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import settings

def migrate():
    conn = sqlite3.connect(settings.DB_PATH)
    cur = conn.cursor()

    # Get existing columns
    cur.execute("PRAGMA table_info(violations)")
    existing_cols = {row[1] for row in cur.fetchall()}

    # Add missing columns
    migrations = [
        ("sla_due_at", "TIMESTAMP"),
        ("notified_at", "TIMESTAMP"),
        ("escalated_at", "TIMESTAMP"),
    ]

    for col_name, col_type in migrations:
        if col_name not in existing_cols:
            cur.execute(f"ALTER TABLE violations ADD COLUMN {col_name} {col_type}")
            print(f"✅ Added column: {col_name}")
        else:
            print(f"⏭️  Column already exists: {col_name}")

    # Clean up bad/stuck violations
    cur.execute("""
        UPDATE violations
        SET status='RESET', resolved_at=CURRENT_TIMESTAMP
        WHERE status IN ('OPEN', 'TEAMS_NOTIFIED', 'NOTIFIED')
    """)
    print(f"🧹 Cleaned up {cur.rowcount} old violations")

    conn.commit()
    conn.close()
    print("✅ Migration complete!")

if __name__ == "__main__":
    migrate()