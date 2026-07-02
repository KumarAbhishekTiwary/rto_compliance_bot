from fastapi import APIRouter
from pydantic import BaseModel
from app.agents.mail_validator import validate_email_reply

router = APIRouter()


class EmailReplyWebhook(BaseModel):
    emp_sapid: str
    reply_body: str


@router.post("/webhooks/email_reply")
async def email_reply_webhook(req: EmailReplyWebhook):
    result = await validate_email_reply(req.emp_sapid, req.reply_body)
    return result
