"""Violation CRUD + lifecycle management."""
import uuid
from datetime import datetime, timedelta
from app.db.database import db_cursor
from app.config import settings

def create_violation(emp_sapid: str, period_type: str, period_start: str,
                     period_end: str, days_present: int, days_required: int) -> str:
    """Create a new violation record. Returns violation_id."""
    violation_id = f"V-{uuid.uuid4().hex[:10].upper()}"
    # sla_due = datetime.now() + timedelta(hours=settings.SLA_HOURS)
    # Use SLA_MINUTES if set (for testing), else SLA_HOURS
    if settings.SLA_MINUTES > 0:
        sla_due = datetime.now() + timedelta(minutes=settings.SLA_MINUTES)
        print(f"⏱️  SLA set to {settings.SLA_MINUTES} minutes (test mode)")
    else:
        sla_due = datetime.now() + timedelta(hours=settings.SLA_HOURS)
    with db_cursor() as cur:
        cur.execute("""
            INSERT INTO violations
            (violation_id, emp_sapid, period_type, period_start, period_end,
             days_present, days_required, status, sla_due_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
        """, (violation_id, emp_sapid, period_type, period_start, period_end,
              days_present, days_required, sla_due))
    log_audit(emp_sapid, "VIOLATION_CREATED", "SYSTEM",
              f"violation_id={violation_id}, period={period_type}")
    return violation_id

def update_violation_slack(violation_id: str, slack_channel_id: str):
    with db_cursor() as cur:
        cur.execute("""
            UPDATE violations SET slack_channel_id = ?, status = 'TEAMS_NOTIFIED'
            WHERE violation_id = ?
        """, (slack_channel_id, violation_id))

def mark_email_escalated(violation_id: str):
    with db_cursor() as cur:
        cur.execute("""
            UPDATE violations SET status = 'EMAIL_ESCALATED'
            WHERE violation_id = ?
        """, (violation_id,))

def reset_violation(violation_id: str, justification: str, channel: str = "TEAMS") -> dict:
    """Mark violation as RESET. Tracking resumes next cycle."""
    with db_cursor() as cur:
        cur.execute("""
            UPDATE violations
            SET status = 'RESET', closed_at = CURRENT_TIMESTAMP
            WHERE violation_id = ?
        """, (violation_id,))
        cur.execute("""
            INSERT INTO communication_log
            (log_id, violation_id, channel, direction, sender, message,
             llm_verdict, justification)
            VALUES (?, ?, ?, 'INBOUND', 'RM', ?, 'SATISFACTORY', ?)
        """, (f"L-{uuid.uuid4().hex[:10]}", violation_id, channel,
              justification, justification))
        # Get emp_sapid for audit
        cur.execute("SELECT emp_sapid FROM violations WHERE violation_id = ?",
                    (violation_id,))
        row = cur.fetchone()
        emp_sapid = row["emp_sapid"] if row else None

    log_audit(emp_sapid, "VIOLATION_RESET", "RM",
              f"violation_id={violation_id}, justification={justification[:80]}")
    return {"violation_id": violation_id, "status": "RESET"}

def log_communication(violation_id: str, channel: str, direction: str,
                       sender: str, message: str, verdict: str = None,
                       justification: str = None, confidence: float = None):
    """Log every inbound/outbound message."""
    with db_cursor() as cur:
        cur.execute("""
            INSERT INTO communication_log
            (log_id, violation_id, channel, direction, sender, message,
             llm_verdict, justification, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (f"L-{uuid.uuid4().hex[:10]}", violation_id, channel, direction,
              sender, message, verdict, justification, confidence))

def log_audit(emp_sapid: str, action: str, actor: str, details: str = ""):
    """Audit log entry."""
    with db_cursor() as cur:
        cur.execute("""
            INSERT INTO audit_log (audit_id, emp_sapid, action, actor, details)
            VALUES (?, ?, ?, ?, ?)
        """, (f"A-{uuid.uuid4().hex[:10]}", emp_sapid, action, actor, details))

def get_sla_breached_violations() -> list:
    """Find violations where SLA timer has expired (for Email Planner trigger)."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT * FROM violations
            WHERE status = 'TEAMS_NOTIFIED'
              AND sla_due_at < CURRENT_TIMESTAMP
        """)
        return [dict(row) for row in cur.fetchall()]

def get_violation(violation_id: str) -> dict | None:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM violations WHERE violation_id = ?", (violation_id,))
        row = cur.fetchone()
        return dict(row) if row else None
