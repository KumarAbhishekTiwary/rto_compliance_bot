"""
Orchestrator - runs the end-to-end compliance pipeline for one employee.

This is the main entry point used by the scheduler and webhooks. We use direct
agent invocations (Runner) rather than LLM-decided handoffs so the workflow is
deterministic and audit-friendly.
"""
import asyncio
import json
from agents import Runner

from app.agents.retrieval import retrieval_agent
from app.agents.meeting_planner import meeting_planner_agent
from app.agents.chat_validator import chat_validator_agent
from app.agents.mail_validator import mail_validator_agent
from app.agents.reset import reset_agent
from app.tools import email_tool
from app.tools.chat_tool import BOT_EMAIL, mark_channel_resolved, post_message
from app.tools.violation import (
    log_audit,
    get_violation,
    is_sla_breached,
    log_communication,
    mark_email_escalated,
)

async def run_compliance_check(emp_sapid: str, policy_type: str = "") -> dict:
    """
    End-to-end pipeline:
      Retrieval → (if non-compliant) Meeting Planner → Slack group + SLA timer.
    Chat / Mail validators are invoked from webhooks (separate flow).
    """
    log_audit(emp_sapid, "CHECK_STARTED", "SCHEDULER",
              f"policy_type={policy_type}")

    # 1. Retrieval
    input_str = json.dumps({"emp_sapid": emp_sapid, "policy_type": policy_type})
    result = await Runner.run(retrieval_agent, input_str)
    compliance = result.final_output  # ComplianceResult Pydantic model

    if compliance.is_compliant:
        log_audit(emp_sapid, "COMPLIANT", "SYSTEM",
                  f"days={compliance.days_present}/{compliance.days_required}")
        return {"emp_sapid": emp_sapid, "status": "COMPLIANT",
                "days_present": compliance.days_present,
                "days_required": compliance.days_required}

    # 2. Non-compliant → Meeting Planner
    mp_input = compliance.model_dump_json()
    mp_result = await Runner.run(meeting_planner_agent, mp_input)
    log_audit(emp_sapid, "TEAMS_NOTIFIED", "SYSTEM", str(mp_result.final_output))

    return {
        "emp_sapid": emp_sapid,
        "status": "VIOLATION_OPENED",
        "compliance": compliance.model_dump(),
        "meeting_planner": str(mp_result.final_output),
    }

async def validate_chat_reply(violation_id: str, chat_history: str) -> dict:
    """Called by Teams chat webhook when a new RM message arrives."""
    result = await Runner.run(chat_validator_agent, chat_history)
    verdict = result.final_output  # ValidationVerdict

    if verdict.verdict == "SATISFACTORY" and verdict.confidence >= 0.7:
        vio = get_violation(violation_id)
        reset_input = json.dumps({
            "violation_id": violation_id,
            "justification": verdict.justification,
            "channel": "TEAMS",
            "confidence": verdict.confidence,
        })
        await Runner.run(reset_agent, reset_input)
        email_result = None
        if vio:
            from app.tools.attendance import fetch_attendance_summary
            emp = fetch_attendance_summary(vio["emp_sapid"], vio["period_type"])
            subject = (
                f"[RTO RESOLVED] [RTO-ID:{violation_id}] "
                f"{emp['emp_name']} ({emp['emp_sapid']})"
            )
            html = email_tool.build_validation_response_html(
                "SATISFACTORY",
                "The justification was approved in the Teams channel.",
            )
            email_result = email_tool.send_escalation_email(
                to=[emp["rm_email"], emp["slm_email"]],
                cc=[emp["hr_email"]] if emp.get("hr_email") else [],
                subject=subject,
                html_body=html,
            )
            log_communication(
                violation_id, "EMAIL", "OUTBOUND", "SYSTEM", subject,
                "SATISFACTORY", verdict.justification, verdict.confidence,
            )
        return {"verdict": "SATISFACTORY", "action": "RESET",
                "violation_id": violation_id,
                "response_email": email_result}

    return {"verdict": verdict.verdict,
            "confidence": verdict.confidence,
            "reasoning": verdict.reasoning,
            "violation_id": violation_id}

async def trigger_email_escalation(violation_id: str) -> dict:
    """Called by SLA sweep when an initial or repeat email escalation is due."""
    vio = get_violation(violation_id)
    if not vio:
        return {"error": f"Violation {violation_id} not found"}
    if not is_sla_breached(violation_id):
        return {
            "violation_id": violation_id,
            "status": "SKIPPED",
            "reason": "Email escalation interval is not due or violation is already reset",
            "current_status": vio.get("status"),
            "sla_due_at": vio.get("sla_due_at"),
            "next_email_due_at": vio.get("next_email_due_at"),
        }

    # Get employee details for the email
    from app.tools.attendance import fetch_attendance_summary
    emp = fetch_attendance_summary(vio["emp_sapid"], vio["period_type"])

    html = email_tool.build_escalation_html(
        emp_name=emp["emp_name"],
        emp_sapid=emp["emp_sapid"],
        period_type=vio["period_type"],
        days_present=vio["days_present"],
        days_required=vio["days_required"],
        period_start=vio["period_start"],
        period_end=vio["period_end"],
    )
    subject = (
        f"[RTO ESCALATION] [RTO-ID:{violation_id}] "
        f"{emp['emp_name']} ({emp['emp_sapid']}) - "
        f"{vio['period_type']} non-compliance"
    )
    result = email_tool.send_escalation_email(
        to=[emp["rm_email"], emp["slm_email"]],
        cc=[address for address in (emp.get("emp_email"), emp.get("hr_email"))
            if address],
        subject=subject,
        html_body=html,
    )
    if result.get("status") not in ("sent", "mock-sent"):
        log_audit(emp["emp_sapid"], "EMAIL_ESCALATION_FAILED", "SYSTEM",
                  f"violation_id={violation_id}, result={result}")
        return {"violation_id": violation_id, "status": "EMAIL_FAILED",
                "result": result}

    mark_email_escalated(violation_id)
    log_communication(
        violation_id,
        "EMAIL",
        "OUTBOUND",
        "SYSTEM",
        subject,
    )
    log_audit(emp["emp_sapid"], "EMAIL_ESCALATED", "SYSTEM",
              f"violation_id={violation_id}")
    return {"violation_id": violation_id, "status": "EMAIL_ESCALATED",
            "result": result}

async def validate_mail_reply(violation_id: str, email_thread: str,
                              sender_email: str = "", reply_subject: str = "",
                              in_reply_to: str = "") -> dict:
    """Called by IMAP poller when a new email reply arrives."""
    vio = get_violation(violation_id)
    if not vio:
        return {"verdict": "REJECTED", "reasoning": "Violation not found"}
    if vio.get("status") == "RESET":
        return {"verdict": "REJECTED", "reasoning": "Violation is already closed"}

    from app.tools.attendance import fetch_attendance_summary
    emp = fetch_attendance_summary(vio["emp_sapid"], vio["period_type"])
    sender = sender_email.strip().lower()
    allowed_senders = {
        str(emp.get("rm_email") or "").strip().lower(),
        str(emp.get("slm_email") or "").strip().lower(),
    }
    allowed_senders.discard("")
    if not sender or sender not in allowed_senders:
        log_audit(vio["emp_sapid"], "EMAIL_REPLY_REJECTED", sender or "UNKNOWN",
                  f"violation_id={violation_id}; sender is not assigned RM/SLM")
        return {
            "verdict": "REJECTED",
            "reasoning": "Reply sender is not the assigned RM or SLM",
        }

    log_communication(violation_id, "EMAIL", "INBOUND", sender, email_thread)
    validator_input = (
        f"Authorized sender: {sender}\nViolation: {violation_id}\n\n"
        f"Email thread:\n{email_thread}"
    )
    result = await Runner.run(mail_validator_agent, validator_input)
    verdict = result.final_output
    effective_verdict = verdict.verdict
    if verdict.verdict == "SATISFACTORY" and verdict.confidence < 0.7:
        effective_verdict = "PENDING"

    if verdict.verdict == "SATISFACTORY" and verdict.confidence >= 0.7:
        reset_input = json.dumps({
            "violation_id": violation_id,
            "justification": verdict.justification,
            "channel": "EMAIL",
            "confidence": verdict.confidence,
        })
        await Runner.run(reset_agent, reset_input)
        action = "RESET"
        channel_id = vio.get("slack_channel_id")
        if channel_id:
            teams_message = (
                "✅ The email justification has been validated and accepted. "
                "This violation is now resolved. Tracking will resume on the "
                "next scheduled cycle."
            )
            post_message(
                channel_id, BOT_EMAIL, teams_message,
                message_type="VERDICT",
                metadata={
                    "verdict": "SATISFACTORY",
                    "action": "RESET",
                    "source": "EMAIL",
                },
            )
            mark_channel_resolved(channel_id)
            log_communication(
                violation_id, "TEAMS", "OUTBOUND", BOT_EMAIL, teams_message,
                "SATISFACTORY", verdict.justification, verdict.confidence,
            )
    else:
        action = "REQUEST_MORE_INFORMATION"

    response_html = email_tool.build_validation_response_html(
        effective_verdict, verdict.reasoning
    )
    response_subject = reply_subject.strip()
    if not response_subject.lower().startswith("re:"):
        response_subject = f"Re: {response_subject}" if response_subject else (
            f"Re: RTO compliance justification - {vio['emp_sapid']}"
        )
    send_result = email_tool.send_escalation_email(
        to=[sender], cc=[], subject=response_subject, html_body=response_html,
        in_reply_to=in_reply_to,
    )
    log_communication(
        violation_id, "EMAIL", "OUTBOUND", "SYSTEM", response_subject,
        effective_verdict, verdict.justification, verdict.confidence,
    )

    return {"verdict": effective_verdict,
            "confidence": verdict.confidence,
            "reasoning": verdict.reasoning,
            "action": action,
            "response_email": send_result}

# Sync wrappers (for scheduler / non-async callers)
def run_check_sync(emp_sapid: str, policy_type: str = "") -> dict:
    return asyncio.run(run_compliance_check(emp_sapid, policy_type))
