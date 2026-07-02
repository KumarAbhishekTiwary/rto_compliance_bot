"""Chat Validator Agent — LLM judges RM reply in the chat channel."""
import os
import json


async def validate_chat_reply(channel_ref: str, rm_message: str, context: dict = None) -> dict:
    try:
        from agents import Agent, Runner
        import asyncio

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        agent = Agent(
            name="ChatValidator",
            model=model,
            instructions="""You are an RTO compliance validator.
Given an RM's justification message for an employee's office attendance violation,
decide if it is SATISFACTORY or UNSATISFACTORY.

SATISFACTORY: specific reason given (client visit, approved WFH, medical, travel with ticket/reference).
UNSATISFACTORY: vague, no reason, or just acknowledgement.

Respond ONLY with valid JSON:
{"verdict": "SATISFACTORY" or "UNSATISFACTORY", "reason": "brief explanation"}""",
        )

        prompt = f"RM message: {rm_message}"
        if context:
            prompt = f"Employee: {context.get('emp_name','')}, Violation: {context.get('summary','')}\n{prompt}"

        result = await Runner.run(agent, prompt)
        text = result.final_output.strip()
        # Extract JSON
        start = text.find("{")
        end = text.rfind("}") + 1
        data = json.loads(text[start:end])
        return {"channel_ref": channel_ref, **data}

    except Exception as e:
        # Fallback: keyword-based heuristic
        lower = rm_message.lower()
        keywords = ["approved", "client", "visit", "medical", "travel", "ticket", "jira", "wfh", "leave"]
        verdict = "SATISFACTORY" if any(k in lower for k in keywords) else "UNSATISFACTORY"
        return {
            "channel_ref": channel_ref,
            "verdict": verdict,
            "reason": f"Heuristic fallback (LLM unavailable: {str(e)[:60]})",
        }
