import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "rto.db")

def get_connection():
    conn = sqlite3.connect(os.path.abspath(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_db_path():
    return os.path.abspath(DB_PATH)
