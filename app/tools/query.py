import re
from app.db.database import get_connection


ALLOWED_TABLES = {
    "employees", "attendance", "violations",
    "communication_log", "audit_log", "authorized_users",
    "channels", "channel_members", "messages",
}

BLOCKED_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|ATTACH|DETACH)\b",
    re.IGNORECASE,
)


def run_safe_query(sql: str) -> dict:
    sql_stripped = sql.strip()
    if not sql_stripped.upper().startswith("SELECT"):
        return {"error": "Only SELECT queries are allowed"}
    if BLOCKED_KEYWORDS.search(sql_stripped):
        return {"error": "Query contains disallowed keywords"}

    conn = get_connection()
    try:
        rows = conn.execute(sql_stripped).fetchall()
        return {"rows": [dict(r) for r in rows], "count": len(rows)}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()
