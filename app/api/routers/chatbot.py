"""Chatbot query endpoint (used by Streamlit UI)."""
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents import Runner
from app.agents.query import query_agent
from app.tools.query import check_authorization, resolve_employee_reference
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

    # 2. Resolve employee references before asking the query agent to write SQL.
    resolution = resolve_employee_reference(req.question)
    if resolution["status"] == "ambiguous":
        matches = resolution["matches"]
        log_audit(None, "EMPLOYEE_DISAMBIGUATION", req.user_email,
                  f"q={req.question[:120]} | matches={len(matches)}")
        return {
            "user": user,
            "question": req.question,
            "answer": (
                "I found multiple employees matching that name. "
                "Please select one below, or enter the complete name or employee code."
            ),
            "sql_used": "",
            "row_count": len(matches),
            "success": None,
            "needs_disambiguation": True,
            "employee_matches": matches,
            "total_matches": resolution.get("total_matches", len(matches)),
        }

    agent_question = req.question
    if resolution["status"] == "resolved":
        employee = resolution["employee"]
        agent_question = (
            f"{req.question}\n\nResolved employee: {employee['emp_name']} "
            f"(employee code {employee['emp_sapid']}). Filter using exactly "
            f"employees.emp_sapid = '{employee['emp_sapid']}'."
        )

    # 3. Run query agent
    result = await Runner.run(query_agent, agent_question)
    query_result = result.final_output  # QueryResult Pydantic

    # 4. Audit
    log_audit(None, "QUERIED", req.user_email,
              f"q={req.question[:120]} | sql={query_result.sql_used[:200]}")

    return {
        "user": user,
        "question": req.question,
        "answer": query_result.answer,
        "sql_used": query_result.sql_used,
        "row_count": query_result.row_count,
        "success": query_result.success,
        "needs_disambiguation": False,
        "employee_matches": [],
    }
