import uuid
import sys
from datetime import datetime
from app.db.database import get_connection

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


def safe_create_channel(
    emp_email: str,
    rm_email: str,
    slm_email: str,
    emp_name: str,
    violation_summary: str,
    violation_id: int = None,
    emp_sapid: str = None,
) -> dict:
    channel_ref = f"CH-{uuid.uuid4().hex[:8].upper()}"
    conn = get_connection()
    conn.execute(
        "INSERT INTO channels (channel_ref, emp_sapid, violation_id, status) VALUES (?,?,?,?)",
        (channel_ref, emp_sapid or "", violation_id, "ACTIVE"),
    )
    members = [
        (channel_ref, emp_email,       "EMPLOYEE"),
        (channel_ref, rm_email,        "RM"),
        (channel_ref, slm_email,       "SLM"),
        (channel_ref, "bot@system",    "BOT"),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO channel_members (channel_ref, email, role) VALUES (?,?,?)",
        members,
    )
    # Post initial bot notice
    conn.execute(
        "INSERT INTO messages (channel_ref, sender_email, sender_role, body) VALUES (?,?,?,?)",
        (channel_ref, "bot@system", "BOT", violation_summary),
    )
    conn.commit()
    conn.close()
    print(f"✅ Channel {channel_ref} created for {emp_name}")
    print(f"   Members: {emp_email}, {rm_email}, {slm_email}")
    return {
        "slack_channel_id": channel_ref,
        "channel_id": channel_ref,
        "channel_ref": channel_ref,
        "message_ts": datetime.utcnow().isoformat(),
        "members_invited": [emp_email, rm_email, slm_email],
    }


def post_message(channel_ref: str, sender_email: str, sender_role: str, body: str, verdict: str = None) -> dict:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO messages (channel_ref, sender_email, sender_role, body, verdict) VALUES (?,?,?,?,?)",
        (channel_ref, sender_email, sender_role, body, verdict),
    )
    conn.commit()
    msg_id = cur.lastrowid
    conn.close()
    return {"message_id": msg_id, "channel_ref": channel_ref}


def get_channel_messages(channel_ref: str) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM messages WHERE channel_ref=? ORDER BY id ASC",
        (channel_ref,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_channels_for_user(email: str) -> list:
    conn = get_connection()
    rows = conn.execute(
        """SELECT c.*, cm.role as user_role
           FROM channels c
           JOIN channel_members cm ON c.channel_ref = cm.channel_ref
           WHERE cm.email=?
           ORDER BY c.id DESC""",
        (email,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_channel_resolved(channel_ref: str) -> dict:
    conn = get_connection()
    conn.execute(
        "UPDATE channels SET status='RESOLVED' WHERE channel_ref=?",
        (channel_ref,),
    )
    conn.commit()
    conn.close()
    return {"channel_ref": channel_ref, "status": "RESOLVED"}


def list_all_users() -> list:
    conn = get_connection()
    emp_rows = conn.execute("SELECT email, name, 'EMPLOYEE' as role FROM employees").fetchall()
    rm_rows = conn.execute("SELECT DISTINCT rm_email as email, rm_email as name, 'RM' as role FROM employees").fetchall()
    slm_rows = conn.execute("SELECT DISTINCT slm_email as email, slm_email as name, 'SLM' as role FROM employees").fetchall()
    auth_rows = conn.execute("SELECT email, email as name, role FROM authorized_users").fetchall()
    conn.close()
    seen = set()
    users = []
    for r in list(emp_rows) + list(rm_rows) + list(slm_rows) + list(auth_rows):
        d = dict(r)
        if d["email"] not in seen:
            seen.add(d["email"])
            users.append(d)
    return users


def get_channel_info(channel_ref: str) -> dict:
    conn = get_connection()
    ch = conn.execute("SELECT * FROM channels WHERE channel_ref=?", (channel_ref,)).fetchone()
    if not ch:
        conn.close()
        return {}
    members = conn.execute(
        "SELECT email, role FROM channel_members WHERE channel_ref=?", (channel_ref,)
    ).fetchall()
    violation = None
    if ch["violation_id"]:
        v = conn.execute("SELECT * FROM violations WHERE id=?", (ch["violation_id"],)).fetchone()
        violation = dict(v) if v else None
    conn.close()
    return {
        **dict(ch),
        "members": [dict(m) for m in members],
        "violation": violation,
    }
