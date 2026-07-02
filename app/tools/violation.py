from datetime import datetime
from app.db.database import get_connection


def create_violation(
    emp_sapid: str,
    policy_type: str,
    period_start: str,
    period_end: str,
    days_present: int,
    days_required: int,
) -> dict:
    conn = get_connection()
    # Check for existing OPEN violation for same period
    existing = conn.execute(
        "SELECT id FROM violations WHERE emp_sapid=? AND policy_type=? AND period_start=? AND status='OPEN'",
        (emp_sapid, policy_type, period_start),
    ).fetchone()
    if existing:
        conn.close()
        return {"violation_id": existing["id"], "created": False, "reason": "already_open"}

    cur = conn.execute(
        """INSERT INTO violations
           (emp_sapid, policy_type, period_start, period_end, days_present, days_required, status)
           VALUES (?,?,?,?,?,?,?)""",
        (emp_sapid, policy_type, period_start, period_end, days_present, days_required, "OPEN"),
    )
    violation_id = cur.lastrowid
    _audit(conn, emp_sapid, "VIOLATION_CREATED", f"period={period_start}/{period_end} present={days_present}/{days_required}")
    conn.commit()
    conn.close()
    return {"violation_id": violation_id, "created": True}


def reset_violation(violation_id: int, channel_ref: str = None) -> dict:
    conn = get_connection()
    conn.execute(
        "UPDATE violations SET status='RESET', resolved_at=? WHERE id=?",
        (datetime.utcnow().isoformat(), violation_id),
    )
    v = conn.execute("SELECT emp_sapid FROM violations WHERE id=?", (violation_id,)).fetchone()
    if v:
        _audit(conn, v["emp_sapid"], "VIOLATION_RESET", f"violation_id={violation_id}")
    conn.commit()
    conn.close()
    return {"violation_id": violation_id, "status": "RESET"}


def update_violation_channel(violation_id: int, channel_ref: str):
    conn = get_connection()
    conn.execute(
        "UPDATE violations SET channel_id=? WHERE id=?",
        (channel_ref, violation_id),
    )
    conn.commit()
    conn.close()


def get_open_violations() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT v.*, e.name, e.email FROM violations v JOIN employees e ON v.emp_sapid=e.emp_sapid WHERE v.status='OPEN'"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _audit(conn, emp_sapid, action, details):
    conn.execute(
        "INSERT INTO audit_log (emp_sapid, action, details) VALUES (?,?,?)",
        (emp_sapid, action, details),
    )
