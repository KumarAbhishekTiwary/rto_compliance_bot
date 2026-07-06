"""FastAPI router for the in-app chat (Teams-like UI backend)."""
import asyncio
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path

from app.tools.chat_tool import (
    post_message, get_channel_messages, list_channels_for_user,
    get_channel_members, get_channel_info, mark_channel_resolved,
    BOT_EMAIL, BOT_NAME,
)
from app.tools.violation import log_communication
from app.agents.orchestrator import validate_chat_reply
from app.db.database import db_cursor

router = APIRouter()


class SendMessageRequest(BaseModel):
    channel_id: str
    sender_email: str
    content: str


@router.get("/chat/channels")
def list_channels(user_email: str):
    return {"channels": list_channels_for_user(user_email)}


@router.get("/chat/channels/{channel_id}/messages")
def get_messages(channel_id: str, since: str = None):
    msgs = get_channel_messages(channel_id, since)
    return {"messages": msgs}


@router.get("/chat/channels/{channel_id}/info")
def channel_info(channel_id: str):
    info = get_channel_info(channel_id)
    if not info:
        raise HTTPException(404, "Channel not found")
    members = get_channel_members(channel_id)
    violation = None
    with db_cursor() as cur:
        cur.execute("SELECT * FROM violations WHERE slack_channel_id = ?",
                    (channel_id,))
        row = cur.fetchone()
        if row:
            violation = dict(row)
    return {"channel": info, "members": members, "violation": violation}


@router.post("/chat/send")
async def send_message(req: SendMessageRequest):
    result = post_message(req.channel_id, req.sender_email, req.content)

    if result["sender_role"] in ("RM", "SLM"):
        violation = None
        with db_cursor() as cur:
            cur.execute("SELECT * FROM violations WHERE slack_channel_id = ?",
                        (req.channel_id,))
            row = cur.fetchone()
            if row:
                violation = dict(row)

        if violation and violation["status"] in ("OPEN", "TEAMS_NOTIFIED", "EMAIL_ESCALATED"):
            msgs = get_channel_messages(req.channel_id)
            chat_history = "\n".join([
                f"{m['sender_name']} ({m['sender_role']}): {m['content']}"
                for m in msgs
            ])
            asyncio.create_task(_validate_and_respond(
                violation["violation_id"], req.channel_id, chat_history
            ))

    return result


async def _validate_and_respond(violation_id: str, channel_id: str,
                                chat_history: str):
    try:
        result = await validate_chat_reply(violation_id, chat_history)
        verdict = result.get("verdict", "PENDING")

        if verdict == "SATISFACTORY" and result.get("action") == "RESET":
            bot_msg = (
                "✅ Thank you. Your justification has been accepted.\n"
                "This violation has been marked as RESET. "
                "Tracking will resume on the next scheduled cycle."
            )
            metadata = {"verdict": "SATISFACTORY", "action": "RESET"}
            mark_channel_resolved(channel_id)
        elif verdict == "UNSATISFACTORY":
            bot_msg = (
                "⚠️ The justification does not meet our criteria. "
                "Please provide more specific details (business reason, dates, "
                "approval references). If unresolved within 24 hours, this will "
                "be escalated via email to SLM and HR."
            )
            metadata = {"verdict": "UNSATISFACTORY",
                        "confidence": result.get("confidence")}
        else:
            bot_msg = "⏳ Acknowledged. Awaiting more information to make a decision."
            metadata = {"verdict": "PENDING"}

        post_message(channel_id, BOT_EMAIL, bot_msg,
                     message_type="VERDICT", metadata=metadata)
        log_communication(violation_id, "TEAMS", "OUTBOUND", BOT_EMAIL,
                          bot_msg, verdict=verdict)
    except Exception as e:
        post_message(channel_id, BOT_EMAIL,
                     f"⚠️ Internal error: {str(e)[:200]}",
                     message_type="SYSTEM")


@router.get("/chat/users")
def list_all_users():
    with db_cursor() as cur:
        cur.execute("""
            SELECT DISTINCT emp_email as email, emp_name as name, 'EMPLOYEE' as role
            FROM employees WHERE emp_email IS NOT NULL
            UNION
            SELECT DISTINCT rm_email as email, 'Reporting Manager' as name, 'RM' as role
            FROM employees WHERE rm_email IS NOT NULL
            UNION
            SELECT DISTINCT slm_email as email, 'Senior Line Manager' as name, 'SLM' as role
            FROM employees WHERE slm_email IS NOT NULL
            UNION
            SELECT DISTINCT hr_email as email, 'HR' as name, 'HR' as role
            FROM employees WHERE hr_email IS NOT NULL
        """)
        users = [dict(r) for r in cur.fetchall()]
    return {"users": users}


@router.get("/chat", response_class=HTMLResponse)
def chat_ui():
    html_path = Path(__file__).resolve().parents[3] / "app" / "ui" / "chat_ui.html"
    if not html_path.exists():
        raise HTTPException(404, f"UI file not found at {html_path}")
    return HTMLResponse(html_path.read_text(encoding="utf-8"))
