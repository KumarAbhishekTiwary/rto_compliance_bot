"""Database connection helper - lightweight sqlite3 wrapper."""
import sqlite3
from contextlib import contextmanager
from app.config import settings

def get_connection():
    """Get a sqlite3 connection with row factory."""
    conn = sqlite3.connect(settings.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextmanager
def db_cursor():
    """Context manager for cursor with auto-commit / rollback."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
