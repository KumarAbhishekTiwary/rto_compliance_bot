"""
Wraps app.tools.* as @function_tool for the OpenAI Agents SDK.
"""
from agents import function_tool
from app.tools import attendance as att
from app.tools import chat_tool as slack_tool 
from app.tools import email_tool
from app.tools import violation as vio
from app.tools import query as qry

# ---------- Retrieval ----------
@function_tool
def tool_fetch_attendance(emp_sapid: str, policy_type: str = "") -> dict:
    """
    Fetch attendance summary for an employee for their RTO compliance period.
    Returns days_present, days_required, is_compliant, plus employee contact info.
    """
    return att.fetch_attendance_summary(emp_sapid, policy_type or None)

# ---------- Meeting Planner ----------
@function_tool
def tool_create_slack_channel(emp_email: str, rm_email: str, slm_email: str,
                              emp_name: str, violation_summary: str) -> dict:
    """
    Create a private Slack channel with Employee + RM + SLM and post the
    violation notice. Returns slack_channel_id and message_ts.
    """
    return slack_tool.safe_create_channel(
        emp_email=emp_email,
        rm_email=rm_email,
        slm_email=slm_email,
        emp_name=emp_name,
        violation_summary=violation_summary,
    )

@function_tool
def tool_create_violation(emp_sapid: str, period_type: str, period_start: str,
                          period_end: str, days_present: int, days_required: int) -> str:
    """Create a new violation record and return the violation_id."""
    return vio.create_violation(emp_sapid, period_type, period_start,
                                period_end, days_present, days_required)

@function_tool
def tool_link_slack_to_violation(violation_id: str, slack_channel_id: str) -> str:
    """Link a Slack channel to a violation record."""
    vio.update_violation_slack(violation_id, slack_channel_id)
    return f"Linked channel {slack_channel_id} to violation {violation_id}"

# ---------- Email Planner ----------
@function_tool
def tool_send_escalation_email(emp_email: str, rm_email: str, slm_email: str, hr_email: str,
                               emp_name: str, emp_sapid: str, period_type: str,
                               days_present: int, days_required: int,
                               period_start: str, period_end: str) -> dict:
    """
    Send an escalation email via SMTP.
    To: RM + SLM, CC: Employee + HR.
    """
    html = email_tool.build_escalation_html(
        emp_name, emp_sapid, period_type, days_present, days_required,
        period_start, period_end
    )
    subject = f"[RTO ESCALATION] {emp_name} ({emp_sapid}) - {period_type} non-compliance"
    return email_tool.send_escalation_email(
        to=[rm_email, slm_email],
        cc=[address for address in (emp_email, hr_email) if address],
        subject=subject, html_body=html
    )

@function_tool
def tool_mark_email_escalated(violation_id: str) -> str:
    """Update violation status to EMAIL_ESCALATED."""
    vio.mark_email_escalated(violation_id)
    return f"Violation {violation_id} marked EMAIL_ESCALATED"

# ---------- Reset Agent ----------
@function_tool
def tool_reset_violation(violation_id: str, justification: str, channel: str = "TEAMS") -> dict:
    """
    Mark violation as RESET when RM provides satisfactory justification.
    Tracking resumes from the next scheduled cycle.
    """
    return vio.reset_violation(violation_id, justification, channel)

# ---------- Query Agent (Chatbot) ----------
@function_tool
def tool_run_sql(sql: str) -> dict:
    """
    Execute a SELECT-only SQL query against the RTO database.
    Returns rows or error if the query is unsafe.
    """
    return qry.execute_safe_query(sql)

@function_tool
def tool_get_schema() -> str:
    """Return the database schema description (for NL→SQL planning)."""
    return qry.SCHEMA_DESCRIPTION

# ---------- Communication logging ----------
@function_tool
def tool_log_communication(violation_id: str, channel: str, direction: str,
                           sender: str, message: str,
                           verdict: str = "", justification: str = "",
                           confidence: float = 0.0) -> str:
    """Log an inbound/outbound message tied to a violation."""
    vio.log_communication(violation_id, channel, direction, sender, message,
                          verdict or None, justification or None,
                          confidence if confidence > 0 else None)
    return "logged"
