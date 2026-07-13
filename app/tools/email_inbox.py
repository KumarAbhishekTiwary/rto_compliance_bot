"""Read Gmail replies over IMAP and route them to the mail validator."""
import email
import email.message
import imaplib
import re
from datetime import datetime, timedelta
from email.header import decode_header, make_header
from email.utils import parseaddr

from app.config import settings
from app.db.database import get_connection


def _decode(value: str) -> str:
    return str(make_header(decode_header(value or "")))


def _body(message: email.message.Message) -> str:
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                return part.get_payload(decode=True).decode(
                    part.get_content_charset() or "utf-8", errors="replace"
                )
        return ""
    payload = message.get_payload(decode=True) or b""
    return payload.decode(message.get_content_charset() or "utf-8", errors="replace")


def _violation_from_subject(subject: str) -> str | None:
    id_match = re.search(r"\[RTO-ID:([^\]]+)\]", subject, re.IGNORECASE)
    if id_match:
        return id_match.group(1).strip()

    sapid_match = re.search(r"\((E\d+)\)", subject, re.IGNORECASE)
    if not sapid_match:
        return None
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT violation_id FROM violations
               WHERE emp_sapid = ? AND status != 'RESET'
               ORDER BY created_at DESC LIMIT 1""",
            (sapid_match.group(1).upper(),),
        ).fetchone()
        return row["violation_id"] if row else None
    finally:
        conn.close()


def _already_processed(message_id: str) -> bool:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM audit_log WHERE action = 'EMAIL_REPLY_RECEIVED' AND details = ? LIMIT 1",
            (message_id,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def poll_email_replies(handler) -> list[dict]:
    """Poll recent escalation replies; ``handler`` accepts parsed reply fields."""
    if not settings.GMAIL_IMAP_ENABLED or not settings.GMAIL_USER or not settings.GMAIL_APP_PASSWORD:
        return []

    results = []
    since = (datetime.now() - timedelta(days=14)).strftime("%d-%b-%Y")
    with imaplib.IMAP4_SSL("imap.gmail.com", 993) as mailbox:
        mailbox.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
        mailbox.select("INBOX")
        status, data = mailbox.search(None, "SINCE", since, "SUBJECT", '"RTO ESCALATION"')
        if status != "OK":
            return []

        for message_num in data[0].split():
            status, fetched = mailbox.fetch(message_num, "(BODY.PEEK[])")
            if status != "OK" or not fetched or not isinstance(fetched[0], tuple):
                continue
            message = email.message_from_bytes(fetched[0][1])
            message_id = (message.get("Message-ID") or "").strip()
            if not message_id or _already_processed(message_id):
                continue
            sender = parseaddr(message.get("From", ""))[1].lower()
            if sender == settings.GMAIL_USER.lower():
                continue
            subject = _decode(message.get("Subject", ""))
            violation_id = _violation_from_subject(subject)
            if not violation_id:
                continue
            results.append(handler(
                violation_id=violation_id,
                email_thread=_body(message),
                sender_email=sender,
                reply_subject=subject,
                in_reply_to=message_id,
            ))
    return results
