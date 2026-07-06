"""Retrieval Agent - fetches attendance + computes compliance."""
from agents import Agent
from app.config import settings
from app.agents.schemas import ComplianceResult
from app.agents.tools_registry import tool_fetch_attendance

INSTRUCTIONS = """
You are the Retrieval Agent for an RTO Compliance Bot.

Your job:
1. Receive an input with `emp_sapid` and optionally `policy_type`.
2. Call the `tool_fetch_attendance` tool to get attendance summary.
3. Return a structured ComplianceResult.

Rules:
- Do not invent any data. Use the tool output exactly as returned.
- If the tool returns an error, return is_compliant=true with shortfall=0 (defensive).
- Always preserve all employee fields (emp_name, rm_email, slm_email, hr_email).
"""

retrieval_agent = Agent(
    name="Retrieval Agent",
    instructions=INSTRUCTIONS,
    model=settings.OPENAI_MODEL,
    tools=[tool_fetch_attendance],
    output_type=ComplianceResult,
)
