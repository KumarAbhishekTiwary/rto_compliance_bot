import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.db.database import get_connection


def send_escalation_email(
    to: list,
    cc: list,
    subject: str,
    html_body: str,
    emp_sapid: str = None,
) -> dict:
    gmail_user = os.getenv("GMAIL_USER", "")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD", "")

    if not gmail_user or not gmail_pass:
        print(f"[MOCK EMAIL] To: {to} | Subject: {subject}")
        _log(emp_sapid, to, cc, subject, html_body)
        return {"status": "MOCK_SENT", "to": to, "subject": subject}

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, to + cc, msg.as_string())
        _log(emp_sapid, to, cc, subject, html_body)
        return {"status": "SENT", "to": to, "subject": subject}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def _log(emp_sapid, to, cc, subject, body):
    if not emp_sapid:
        return
    conn = get_connection()
    conn.execute(
        "INSERT INTO communication_log (emp_sapid, direction, channel, subject, body) VALUES (?,?,?,?,?)",
        (emp_sapid, "OUTBOUND", "EMAIL", subject, body[:2000]),
    )
    conn.commit()
    conn.close()
