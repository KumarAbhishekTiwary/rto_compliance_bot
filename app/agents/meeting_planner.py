"""Meeting Planner Agent — creates in-app channel for a violation."""
from app.agents.tools_registry import slack_tool, update_violation_channel


async def run_meeting_planner(
    emp_email: str,
    rm_email: str,
    slm_email: str,
    emp_name: str,
    violation_summary: str,
    violation_id: int,
    emp_sapid: str,
) -> dict:
    result = slack_tool.safe_create_channel(
        emp_email=emp_email,
        rm_email=rm_email,
        slm_email=slm_email,
        emp_name=emp_name,
        violation_summary=violation_summary,
        violation_id=violation_id,
        emp_sapid=emp_sapid,
    )
    channel_ref = result.get("channel_ref") or result.get("slack_channel_id")
    if channel_ref and violation_id:
        update_violation_channel(violation_id, channel_ref)
    return result
