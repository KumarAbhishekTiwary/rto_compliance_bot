"""Email Planner Agent - sends escalation email via SMTP."""
from agents import Agent
from app.config import settings
from app.agents.tools_registry import (
    tool_send_escalation_email,
    tool_mark_email_escalated,
)

INSTRUCTIONS = """
You are the Email Planner Agent for an RTO Compliance Bot.

You are triggered when the 24-hour SLA expires without a satisfactory RM response.

Input: violation context including emp details, period, days_present, days_required.

Steps:
1. Call `tool_send_escalation_email` with:
   - rm_email, slm_email, hr_email
   - emp_name, emp_sapid, period_type
   - days_present, days_required
   - period_start, period_end
   The tool composes the HTML body; you just pass the data.

2. Call `tool_mark_email_escalated` with violation_id.

3. Return a JSON: {status:"ESCALATED", violation_id, to, cc}.
"""

email_planner_agent = Agent(
    name="Email Planner Agent",
    instructions=INSTRUCTIONS,
    model=settings.OPENAI_MODEL,
    tools=[tool_send_escalation_email, tool_mark_email_escalated],
)
