from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agents.query import run_query_agent

router = APIRouter()


class ChatbotQueryRequest(BaseModel):
    question: str
    user_email: str


@router.post("/chatbot/query")
async def chatbot_query(req: ChatbotQueryRequest):
    result = await run_query_agent(req.question, req.user_email)
    if result.get("status") == 403:
        raise HTTPException(status_code=403, detail="Unauthorized")
    if result.get("status") == 500:
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result
