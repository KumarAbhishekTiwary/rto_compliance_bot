"""Reset Agent - closes violation on satisfactory verdict."""
from agents import Agent
from app.config import settings
from app.agents.tools_registry import tool_reset_violation, tool_log_communication

INSTRUCTIONS = """
You are the Reset Agent for an RTO Compliance Bot.

You are triggered when a Validator (Chat or Mail) returns SATISFACTORY.

Input: { violation_id, justification, channel ("TEAMS" or "EMAIL"), confidence }.

Steps:
1. Call `tool_log_communication` to log the satisfactory verdict.
2. Call `tool_reset_violation` with violation_id, justification, channel.

After this, tracking resumes on the next scheduled cycle (next Monday for
WEEKLY, next 1st-of-month for MONTHLY).

Return: {status:"RESET", violation_id, justification}.
"""

reset_agent = Agent(
    name="Reset Agent",
    instructions=INSTRUCTIONS,
    model=settings.OPENAI_MODEL,
    tools=[tool_reset_violation, tool_log_communication],
)
