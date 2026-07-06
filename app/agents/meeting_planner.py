"""Meeting Planner Agent - creates Slack group + posts violation notice."""
from agents import Agent
from app.config import settings
from app.agents.tools_registry import (
    tool_create_violation,
    tool_create_slack_channel,
    tool_link_slack_to_violation,
)

INSTRUCTIONS = """
You are the Meeting Planner Agent for an RTO Compliance Bot.

You receive ComplianceResult JSON (non-compliant case). Your job:

1. Call `tool_create_violation` with: emp_sapid, period_type (policy_type),
   period_start, period_end, days_present, days_required.
   Save the returned violation_id.

2. Compose a professional but empathetic violation summary message
   (4-6 lines) including:
   - Employee name and SAP ID
   - Policy type (Weekly or Monthly)
   - Days present vs required
   - Period dates
   - A polite ask to the RM for justification within 24 hours

3. Call `tool_create_slack_channel` with the message you composed.
   Use member emails: emp_email, rm_email, slm_email.
   Save the returned slack_channel_id.

4. Call `tool_link_slack_to_violation` to link them.

5. Return a JSON: {violation_id, slack_channel_id, status:"NOTIFIED"}.
"""

meeting_planner_agent = Agent(
    name="Meeting Planner Agent",
    instructions=INSTRUCTIONS,
    model=settings.OPENAI_MODEL,
    tools=[
        tool_create_violation,
        tool_create_slack_channel,
        tool_link_slack_to_violation,
    ],
)
