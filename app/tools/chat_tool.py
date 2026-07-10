"""
Internal Chat Tool - replaces Slack/Teams entirely.
Drop-in replacement for app/tools/slack_tool.py
"""
import uuid
import json
from datetime import datetime
from app.db.database import db_cursor
from app.config import settings

BOT_EMAIL = "rto-bot@compliance.local"
BOT_NAME = "RTO Compliance Bot"


def build_justification_request_message() -> str:
    return (
        "Action required: RM/SLM, please reply in this channel with the business "
        "justification for this RTO non-compliance. Include the reason, dates, "
        "and any approval reference. I will keep reminding this channel every "
        f"{settings.teams_reminder_label()} until a satisfactory response is received."
    )


def create_compliance_channel(emp_email: str, rm_email: str, slm_email: str,
                              emp_name: str, violation_summary: str) -> dict:
    """Create an internal chat channel with Employee + RM + SLM + Bot."""
    channel_id = f"CH-{uuid.uuid4().hex[:10].upper()}"
    safe_name = emp_name.replace(" ", "-")
    channel_name = f"rto-{safe_name}-{datetime.now().strftime('%Y%m%d-%H%M')}"

    with db_cursor() as cur:
        cur.execute("""
            INSERT INTO channels (channel_id, channel_name, status)
            VALUES (?, ?, 'ACTIVE')
        """, (channel_id, channel_name))

        members = [
            (emp_email, "EMPLOYEE"),
            (rm_email, "RM"),
            (slm_email, "SLM"),
            (BOT_EMAIL, "BOT"),
        ]
        for email, role in members:
            cur.execute("""
                INSERT OR IGNORE INTO channel_members
                (channel_id, member_email, member_role)
                VALUES (?, ?, ?)
            """, (channel_id, email, role))

        message_id = f"MSG-{uuid.uuid4().hex[:10].upper()}"
        cur.execute("""
            INSERT INTO messages
            (message_id, channel_id, sender_email, sender_role, sender_name,
             content, message_type)
            VALUES (?, ?, ?, ?, ?, ?, 'BOT_NOTICE')
        """, (message_id, channel_id, BOT_EMAIL, "BOT", BOT_NAME,
              violation_summary))

        reminder_message_id = f"MSG-{uuid.uuid4().hex[:10].upper()}"
        cur.execute("""
            INSERT INTO messages
            (message_id, channel_id, sender_email, sender_role, sender_name,
             content, message_type)
            VALUES (?, ?, ?, ?, ?, ?, 'BOT_REMINDER')
        """, (reminder_message_id, channel_id, BOT_EMAIL, "BOT", BOT_NAME,
              build_justification_request_message()))

    return {
        "slack_channel_id": channel_id,
        "channel_id": channel_id,
        "channel_name": channel_name,
        "message_ts": message_id,
        "reminder_message_ts": reminder_message_id,
        "members_invited": [emp_email, rm_email, slm_email],
    }


def post_message(channel_id: str, sender_email: str, content: str,
                 message_type: str = "TEXT", metadata: dict = None) -> dict:
    """Post a message to an existing channel."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT member_role FROM channel_members
            WHERE channel_id = ? AND member_email = ?
        """, (channel_id, sender_email))
        row = cur.fetchone()
        sender_role = row["member_role"] if row else "GUEST"

        sender_name = sender_email.split("@")[0]
        cur.execute("SELECT emp_name FROM employees WHERE emp_email = ? OR rm_email = ? OR slm_email = ?",
                    (sender_email, sender_email, sender_email))
        emp_row = cur.fetchone()
        if emp_row:
            sender_name = emp_row["emp_name"]
        if sender_email == BOT_EMAIL:
            sender_name = BOT_NAME

        message_id = f"MSG-{uuid.uuid4().hex[:10].upper()}"
        cur.execute("""
            INSERT INTO messages
            (message_id, channel_id, sender_email, sender_role, sender_name,
             content, message_type, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (message_id, channel_id, sender_email, sender_role, sender_name,
              content, message_type,
              json.dumps(metadata) if metadata else None))

    return {"message_id": message_id, "channel_id": channel_id,
            "sender_role": sender_role}


def get_channel_messages(channel_id: str, since_ts: str = None) -> list:
    with db_cursor() as cur:
        if since_ts:
            cur.execute("""
                SELECT * FROM messages
                WHERE channel_id = ? AND created_at > ?
                ORDER BY created_at
            """, (channel_id, since_ts))
        else:
            cur.execute("""
                SELECT * FROM messages
                WHERE channel_id = ?
                ORDER BY created_at
            """, (channel_id,))
        return [dict(row) for row in cur.fetchall()]


def list_channels_for_user(user_email: str) -> list:
    with db_cursor() as cur:
        cur.execute("""
            SELECT c.channel_id, c.channel_name, c.violation_id, c.status,
                   c.created_at, cm.member_role,
                   (SELECT COUNT(*) FROM messages m WHERE m.channel_id = c.channel_id) AS msg_count,
                   (SELECT content FROM messages m WHERE m.channel_id = c.channel_id
                    ORDER BY created_at DESC LIMIT 1) AS last_message,
                   (SELECT sender_name FROM messages m WHERE m.channel_id = c.channel_id
                    ORDER BY created_at DESC LIMIT 1) AS last_sender,
                   (SELECT created_at FROM messages m WHERE m.channel_id = c.channel_id
                    ORDER BY created_at DESC LIMIT 1) AS last_ts
            FROM channels c
            JOIN channel_members cm ON c.channel_id = cm.channel_id
            WHERE cm.member_email = ?
            ORDER BY c.created_at DESC
        """, (user_email,))
        return [dict(row) for row in cur.fetchall()]


def get_channel_members(channel_id: str) -> list:
    with db_cursor() as cur:
        cur.execute("""
            SELECT member_email, member_role, joined_at
            FROM channel_members WHERE channel_id = ?
        """, (channel_id,))
        return [dict(row) for row in cur.fetchall()]


def get_channel_info(channel_id: str) -> dict:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM channels WHERE channel_id = ?", (channel_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def mark_channel_resolved(channel_id: str):
    with db_cursor() as cur:
        cur.execute("UPDATE channels SET status = 'RESOLVED' WHERE channel_id = ?",
                    (channel_id,))


# Drop-in replacement for slack_tool.safe_create_channel
def safe_create_channel(*args, **kwargs):
    return create_compliance_channel(*args, **kwargs)
