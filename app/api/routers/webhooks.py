"""Webhook endpoints for Slack message events and incoming email replies."""
from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.agents.orchestrator import validate_chat_reply, validate_mail_reply
from app.db.database import db_cursor

router = APIRouter()

class SlackEvent(BaseModel):
    challenge: str | None = None
    event: dict | None = None
    type: str | None = None

@router.post("/webhooks/slack")
async def slack_webhook(payload: SlackEvent):
    """
    Slack Events API webhook.
    First call: returns challenge for URL verification.
    Subsequent calls: handle message events.
    """
    # URL verification handshake
    if payload.challenge:
        return {"challenge": payload.challenge}

    event = payload.event or {}
    if event.get("type") == "message" and not event.get("bot_id"):
        channel_id = event.get("channel")
        text = event.get("text", "")
        user = event.get("user", "")

        # Find violation linked to this channel
        with db_cursor() as cur:
            cur.execute("""
                SELECT violation_id FROM violations
                WHERE slack_channel_id = ? AND status IN ('TEAMS_NOTIFIED','EMAIL_ESCALATED')
            """, (channel_id,))
            row = cur.fetchone()

        if row:
            violation_id = row["violation_id"]
            chat_history = f"From RM ({user}): {text}"
            verdict = await validate_chat_reply(violation_id, chat_history)
            return {"ok": True, "verdict": verdict}

    return {"ok": True}

class MailEvent(BaseModel):
    violation_id: str
    email_thread: str

@router.post("/webhooks/email_reply")
async def email_reply_webhook(payload: MailEvent):
    """
    Manual / IMAP-poller webhook for incoming email replies.
    Pass the thread text + violation_id and we validate.
    """
    verdict = await validate_mail_reply(payload.violation_id, payload.email_thread)
    return {"ok": True, "verdict": verdict}
