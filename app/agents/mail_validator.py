"""Mail Validator Agent — LLM judges email reply."""
import os
import json


async def validate_email_reply(emp_sapid: str, reply_body: str) -> dict:
    try:
        from agents import Agent, Runner

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        agent = Agent(
            name="MailValidator",
            model=model,
            instructions="""You are an RTO compliance email validator.
Given an employee's email reply to a compliance violation notice,
decide if it is SATISFACTORY or UNSATISFACTORY.

SATISFACTORY: specific reason with supporting details.
UNSATISFACTORY: vague or no reason.

Respond ONLY with valid JSON:
{"verdict": "SATISFACTORY" or "UNSATISFACTORY", "reason": "brief explanation"}""",
        )
        result = await Runner.run(agent, f"Email reply: {reply_body}")
        text = result.final_output.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        data = json.loads(text[start:end])
        return {"emp_sapid": emp_sapid, **data}

    except Exception as e:
        lower = reply_body.lower()
        keywords = ["approved", "client", "visit", "medical", "travel", "ticket", "leave"]
        verdict = "SATISFACTORY" if any(k in lower for k in keywords) else "UNSATISFACTORY"
        return {
            "emp_sapid": emp_sapid,
            "verdict": verdict,
            "reason": f"Heuristic fallback (LLM unavailable: {str(e)[:60]})",
        }
