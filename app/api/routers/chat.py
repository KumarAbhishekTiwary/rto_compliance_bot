import asyncio
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.tools.chat_tool import (
    list_channels_for_user,
    get_channel_messages,
    get_channel_info,
    post_message,
    list_all_users,
)
from app.agents.chat_validator import validate_chat_reply
from app.agents.reset import run_reset

router = APIRouter()

UI_PATH = Path(__file__).parent.parent.parent / "ui" / "chat_ui.html"


@router.get("/chat")
def serve_chat_ui():
    if not UI_PATH.exists():
        raise HTTPException(status_code=404, detail="chat_ui.html not found")
    return FileResponse(str(UI_PATH), media_type="text/html")


@router.get("/chat/users")
def get_users():
    return list_all_users()


@router.get("/chat/channels")
def get_channels(user_email: str):
    return list_channels_for_user(user_email)


@router.get("/chat/channels/{channel_ref}/messages")
def get_messages(channel_ref: str):
    return get_channel_messages(channel_ref)


@router.get("/chat/channels/{channel_ref}/info")
def get_info(channel_ref: str):
    info = get_channel_info(channel_ref)
    if not info:
        raise HTTPException(status_code=404, detail="Channel not found")
    return info


class SendMessageRequest(BaseModel):
    channel_ref: str
    sender_email: str
    sender_role: str
    body: str


@router.post("/chat/send")
async def send_message(req: SendMessageRequest, background_tasks: BackgroundTasks):
    post_message(req.channel_ref, req.sender_email, req.sender_role, req.body)

    # If RM sends a message, trigger Chat Validator in background
    if req.sender_role.upper() == "RM":
        background_tasks.add_task(_validate_and_respond, req.channel_ref, req.body)

    return {"status": "sent"}


async def _validate_and_respond(channel_ref: str, rm_message: str):
    try:
        info = get_channel_info(channel_ref)
        context = {}
        if info.get("violation"):
            v = info["violation"]
            context = {
                "emp_name": info.get("emp_sapid", ""),
                "summary": f"present={v.get('days_present')}/{v.get('days_required')} days",
            }

        result = await validate_chat_reply(channel_ref, rm_message, context)
        verdict = result.get("verdict", "UNSATISFACTORY")
        reason = result.get("reason", "")

        if verdict == "SATISFACTORY":
            bot_msg = f"✅ SATISFACTORY — {reason}\nViolation will be marked RESET."
            post_message(channel_ref, "bot@system", "BOT", bot_msg, verdict="SATISFACTORY")
            # Reset violation
            if info.get("violation"):
                await run_reset(info["violation"]["id"], channel_ref)
        else:
            bot_msg = f"❌ UNSATISFACTORY — {reason}\nPlease provide more specific details."
            post_message(channel_ref, "bot@system", "BOT", bot_msg, verdict="UNSATISFACTORY")
    except Exception as e:
        post_message(channel_ref, "bot@system", "BOT", f"⚠️ Validation error: {str(e)[:100]}")
