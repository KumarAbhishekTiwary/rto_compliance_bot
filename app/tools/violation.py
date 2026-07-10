"""Violation CRUD + lifecycle management."""
import uuid
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.db.database import db_cursor


def _sla_due_at() -> datetime:
    """Compute initial email escalation due time in UTC."""
    return _email_due_at()


def _add_interval(start: datetime, minutes: int, hours: int) -> datetime:
    if minutes > 0:
        return start + timedelta(minutes=minutes)
    return start + timedelta(hours=hours)


def _email_due_at() -> datetime:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return _add_interval(
        now,
        settings.EMAIL_REMINDER_MINUTES,
        settings.EMAIL_REMINDER_HOURS,
    )


def _next_email_due_at() -> datetime:
    return _email_due_at()


def _next_teams_reminder_due_at() -> datetime:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return _add_interval(
        now,
        settings.TEAMS_REMINDER_MINUTES,
        settings.TEAMS_REMINDER_HOURS,
    )


def _ensure_escalation_columns():
    """Add repeat-escalation columns for existing local databases."""
    with db_cursor() as cur:
        cur.execute("PRAGMA table_info(violations)")
        columns = {row["name"] for row in cur.fetchall()}
        if "teams_reminded_at" not in columns:
            cur.execute("ALTER TABLE violations ADD COLUMN teams_reminded_at TIMESTAMP")
        if "next_teams_reminder_due_at" not in columns:
            cur.execute("ALTER TABLE violations ADD COLUMN next_teams_reminder_due_at TIMESTAMP")
        if "email_escalated_at" not in columns:
            cur.execute("ALTER TABLE violations ADD COLUMN email_escalated_at TIMESTAMP")
        if "next_email_due_at" not in columns:
            cur.execute("ALTER TABLE violations ADD COLUMN next_email_due_at TIMESTAMP")
        cur.execute("""
            UPDATE violations
            SET next_teams_reminder_due_at = COALESCE(sla_due_at, CURRENT_TIMESTAMP)
            WHERE status IN ('TEAMS_NOTIFIED', 'EMAIL_ESCALATED')
              AND slack_channel_id IS NOT NULL
              AND next_teams_reminder_due_at IS NULL
        """)
        cur.execute("""
            UPDATE violations
            SET next_email_due_at = CURRENT_TIMESTAMP
            WHERE status = 'EMAIL_ESCALATED'
              AND next_email_due_at IS NULL
        """)


def create_violation(emp_sapid: str, period_type: str, period_start: str,
                     period_end: str, days_present: int, days_required: int) -> str:
    """Create a new violation record. Returns violation_id."""
    _ensure_escalation_columns()
    violation_id = f"V-{uuid.uuid4().hex[:10].upper()}"
    sla_due = _sla_due_at()
    teams_reminder_due = _next_teams_reminder_due_at()
    with db_cursor() as cur:
        cur.execute("""
            INSERT INTO violations
            (violation_id, emp_sapid, period_type, period_start, period_end,
             days_present, days_required, status, sla_due_at, next_teams_reminder_due_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)
        """, (violation_id, emp_sapid, period_type, period_start, period_end,
              days_present, days_required, sla_due, teams_reminder_due))
    log_audit(emp_sapid, "VIOLATION_CREATED", "SYSTEM",
              f"violation_id={violation_id}, period={period_type}")
    return violation_id


def update_violation_slack(violation_id: str, slack_channel_id: str):
    _ensure_escalation_columns()
    with db_cursor() as cur:
        cur.execute("""
            UPDATE violations
            SET slack_channel_id = ?,
                status = 'TEAMS_NOTIFIED',
                next_teams_reminder_due_at = COALESCE(next_teams_reminder_due_at, ?)
            WHERE violation_id = ?
        """, (slack_channel_id, _next_teams_reminder_due_at(), violation_id))


def mark_email_escalated(violation_id: str):
    _ensure_escalation_columns()
    next_due = _next_email_due_at()
    with db_cursor() as cur:
        cur.execute("""
            UPDATE violations
            SET status = 'EMAIL_ESCALATED',
                email_escalated_at = CURRENT_TIMESTAMP,
                next_email_due_at = ?
            WHERE violation_id = ? AND status IN ('TEAMS_NOTIFIED', 'EMAIL_ESCALATED')
        """, (next_due, violation_id))


def reset_violation(violation_id: str, justification: str, channel: str = "TEAMS") -> dict:
    """Mark violation as RESET. Tracking resumes next cycle."""
    with db_cursor() as cur:
        cur.execute("""
            UPDATE violations
            SET status = 'RESET',
                closed_at = CURRENT_TIMESTAMP,
                next_teams_reminder_due_at = NULL,
                next_email_due_at = NULL
            WHERE violation_id = ?
        """, (violation_id,))
        cur.execute("""
            INSERT INTO communication_log
            (log_id, violation_id, channel, direction, sender, message,
             llm_verdict, justification)
            VALUES (?, ?, ?, 'INBOUND', 'RM', ?, 'SATISFACTORY', ?)
        """, (f"L-{uuid.uuid4().hex[:10]}", violation_id, channel,
              justification, justification))
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
    _ensure_escalation_columns()
    with db_cursor() as cur:
        cur.execute("""
            SELECT * FROM violations
            WHERE (
                status = 'TEAMS_NOTIFIED'
                AND sla_due_at IS NOT NULL
                AND datetime(sla_due_at) <= CURRENT_TIMESTAMP
            )
            OR (
                status = 'EMAIL_ESCALATED'
                AND next_email_due_at IS NOT NULL
                AND datetime(next_email_due_at) <= CURRENT_TIMESTAMP
            )
        """)
        return [dict(row) for row in cur.fetchall()]


def get_teams_reminder_due_violations() -> list:
    """Find active violations where a Teams justification reminder is due."""
    _ensure_escalation_columns()
    with db_cursor() as cur:
        cur.execute("""
            SELECT * FROM violations
            WHERE status IN ('TEAMS_NOTIFIED', 'EMAIL_ESCALATED')
              AND slack_channel_id IS NOT NULL
              AND next_teams_reminder_due_at IS NOT NULL
              AND datetime(next_teams_reminder_due_at) <= CURRENT_TIMESTAMP
        """)
        return [dict(row) for row in cur.fetchall()]


def mark_teams_reminded(violation_id: str):
    """Record that a Teams reminder was posted and schedule the next reminder."""
    _ensure_escalation_columns()
    next_due = _next_teams_reminder_due_at()
    with db_cursor() as cur:
        cur.execute("""
            UPDATE violations
            SET teams_reminded_at = CURRENT_TIMESTAMP,
                next_teams_reminder_due_at = ?
            WHERE violation_id = ?
              AND status IN ('TEAMS_NOTIFIED', 'EMAIL_ESCALATED')
        """, (next_due, violation_id))


def get_violation(violation_id: str) -> dict | None:
    _ensure_escalation_columns()
    with db_cursor() as cur:
        cur.execute("SELECT * FROM violations WHERE violation_id = ?", (violation_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def is_sla_breached(violation_id: str) -> bool:
    """Return True when a violation is due for initial or repeat email escalation."""
    _ensure_escalation_columns()
    with db_cursor() as cur:
        cur.execute("""
            SELECT 1 FROM violations
            WHERE violation_id = ? AND (
                (
                    status = 'TEAMS_NOTIFIED'
                    AND sla_due_at IS NOT NULL
                    AND datetime(sla_due_at) <= CURRENT_TIMESTAMP
                )
                OR (
                    status = 'EMAIL_ESCALATED'
                    AND next_email_due_at IS NOT NULL
                    AND datetime(next_email_due_at) <= CURRENT_TIMESTAMP
                )
              )
        """, (violation_id,))
        return cur.fetchone() is not None
