"""Email Planner Agent — sends escalation email."""
from app.tools.email_tool import send_escalation_email


async def run_email_planner(
    emp_name: str,
    emp_email: str,
    rm_email: str,
    slm_email: str,
    days_present: int,
    days_required: int,
    period_start: str,
    period_end: str,
    policy_type: str,
    emp_sapid: str,
) -> dict:
    subject = f"RTO Compliance Alert: {emp_name} — {policy_type} Policy Violation"
    html_body = f"""
    <h2>RTO Compliance Violation Notice</h2>
    <p>Dear {emp_name},</p>
    <p>Our records show you attended the office <strong>{days_present} out of {days_required} required days</strong>
    for the period <strong>{period_start} to {period_end}</strong> under the <strong>{policy_type}</strong> policy.</p>
    <p>Please provide justification via the compliance chat channel.</p>
    <p>This is an automated notification from the RTO Compliance System.</p>
    """
    return send_escalation_email(
        to=[emp_email],
        cc=[rm_email, slm_email],
        subject=subject,
        html_body=html_body,
        emp_sapid=emp_sapid,
    )
