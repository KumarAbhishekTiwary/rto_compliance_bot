"""
SMTP email tool - replaces Outlook in Phase 1.
Sends escalation emails via Gmail SMTP.
"""
import smtplib
from html import escape
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings


def send_escalation_email(to: list[str], cc: list[str], subject: str,
                          html_body: str, in_reply_to: str = "") -> dict:
    """Send escalation email via Gmail SMTP, or mock it when credentials are absent."""
    if not settings.GMAIL_USER or not settings.GMAIL_APP_PASSWORD:
        return _send_email_mock(to, cc, subject, html_body)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.GMAIL_USER
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    msg.attach(MIMEText(html_body, "html"))

    recipients = to + cc
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
            server.sendmail(settings.GMAIL_USER, recipients, msg.as_string())
        return {"status": "sent", "to": to, "cc": cc, "subject": subject}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def _send_email_mock(to: list[str], cc: list[str], subject: str, body: str) -> dict:
    """Mock implementation for testing without Gmail credentials."""
    preview = body[:300].encode("ascii", errors="replace").decode("ascii")
    print("\n[MOCK EMAIL]")
    print(f"  To: {to}")
    print(f"  CC: {cc}")
    print(f"  Subject: {subject}")
    print(f"  Body (first 300 chars): {preview}")
    return {"status": "mock-sent", "to": to, "cc": cc, "subject": subject, "mock": True}


def build_escalation_html(emp_name: str, emp_sapid: str, period_type: str,
                          days_present: int, days_required: int,
                          period_start: str, period_end: str) -> str:
    """Build the HTML body for an escalation email."""
    return f"""
<html>
<body style="font-family:Arial,sans-serif;color:#333;">
  <div style="max-width:600px;margin:auto;border:1px solid #ddd;border-radius:8px;padding:20px;">
    <h2 style="color:#c62828;">RTO Compliance Escalation</h2>
    <p>Dear Reporting Manager / Senior Line Manager,</p>
    <p>This is an automated escalation regarding the following RTO compliance issue:</p>
    <table style="width:100%;border-collapse:collapse;margin:15px 0;">
      <tr><td style="padding:8px;background:#f5f5f5;"><b>Employee</b></td>
          <td style="padding:8px;">{emp_name} ({emp_sapid})</td></tr>
      <tr><td style="padding:8px;background:#f5f5f5;"><b>Policy</b></td>
          <td style="padding:8px;">{period_type}</td></tr>
      <tr><td style="padding:8px;background:#f5f5f5;"><b>Period</b></td>
          <td style="padding:8px;">{period_start} to {period_end}</td></tr>
      <tr><td style="padding:8px;background:#f5f5f5;"><b>Days Present</b></td>
          <td style="padding:8px;color:#c62828;"><b>{days_present}</b> (required: {days_required})</td></tr>
    </table>
    <p><b>Action Required:</b> Please respond on this email thread OR in the Teams
    channel with confirmation that you have discussed this with the employee and
    provide justification.</p>
    <p style="color:#888;font-size:12px;">
      This is an automated notice from the RTO Compliance Bot. Reply on the tracked
      thread or Teams channel for audit purposes.
    </p>
  </div>
</body>
</html>
"""


def build_validation_response_html(verdict: str, reasoning: str) -> str:
    """Build the acknowledgement sent after validating an RM/SLM reply."""
    if verdict == "SATISFACTORY":
        heading = "Justification accepted"
        message = (
            "Thank you. The justification has been accepted and the current "
            "RTO compliance violation has been closed."
        )
        color = "#2e7d32"
    elif verdict == "UNSATISFACTORY":
        heading = "More information required"
        message = (
            "The reply does not contain enough specific information to close "
            "the violation. Please reply with the business reason, relevant "
            "dates, and any approval or supporting reference."
        )
        color = "#c62828"
    else:
        heading = "Response pending"
        message = (
            "The reply could not yet be treated as a complete justification. "
            "Please provide the reason, relevant dates, and approval details."
        )
        color = "#ed6c02"

    safe_reasoning = escape(reasoning or "No additional validation details.")
    return f"""
<html><body style="font-family:Arial,sans-serif;color:#333;">
  <div style="max-width:600px;margin:auto;border:1px solid #ddd;border-radius:8px;padding:20px;">
    <h2 style="color:{color};">{heading}</h2>
    <p>{message}</p>
    <p><b>Validation details:</b> {safe_reasoning}</p>
    <p style="color:#888;font-size:12px;">Automated response from the RTO Compliance Bot.</p>
  </div>
</body></html>
"""
