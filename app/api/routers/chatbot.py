"""Chatbot query endpoint (used by Streamlit UI)."""
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents import Runner
from app.agents.query import query_agent
from app.tools.query import check_authorization
from app.tools.violation import log_audit

router = APIRouter()

class ChatRequest(BaseModel):
    user_email: str
    question: str

@router.post("/chatbot/query")
async def chatbot_query(req: ChatRequest):
    # 1. Auth check
    user = check_authorization(req.user_email)
    if not user:
        log_audit(None, "UNAUTHORIZED_QUERY", req.user_email, req.question)
        raise HTTPException(403, "You are not authorized to query this system.")

    # 2. Run query agent
    result = await Runner.run(query_agent, req.question)
    query_result = result.final_output  # QueryResult Pydantic

    # 3. Audit
    log_audit(None, "QUERIED", req.user_email,
              f"q={req.question[:120]} | sql={query_result.sql_used[:200]}")

    return {
        "user": user,
        "question": req.question,
        "answer": query_result.answer,
        "sql_used": query_result.sql_used,
        "row_count": query_result.row_count,
        "success": query_result.success,
    }
