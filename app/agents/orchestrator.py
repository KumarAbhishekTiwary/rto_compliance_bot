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
        reset_input = json.dumps({
            "violation_id": violation_id,
            "justification": verdict.justification,
            "channel": "TEAMS",
            "confidence": verdict.confidence,
        })
        await Runner.run(reset_agent, reset_input)
        return {"verdict": "SATISFACTORY", "action": "RESET",
                "violation_id": violation_id}

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
        f"[RTO ESCALATION] {emp['emp_name']} ({emp['emp_sapid']}) - "
        f"{vio['period_type']} non-compliance"
    )
    result = email_tool.send_escalation_email(
        to=[emp["rm_email"], emp["slm_email"]],
        cc=[emp["hr_email"]] if emp.get("hr_email") else [],
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

async def validate_mail_reply(violation_id: str, email_thread: str) -> dict:
    """Called by IMAP poller when a new email reply arrives."""
    result = await Runner.run(mail_validator_agent, email_thread)
    verdict = result.final_output

    if verdict.verdict == "SATISFACTORY" and verdict.confidence >= 0.7:
        reset_input = json.dumps({
            "violation_id": violation_id,
            "justification": verdict.justification,
            "channel": "EMAIL",
            "confidence": verdict.confidence,
        })
        await Runner.run(reset_agent, reset_input)
        return {"verdict": "SATISFACTORY", "action": "RESET"}

    return {"verdict": verdict.verdict,
            "confidence": verdict.confidence,
            "reasoning": verdict.reasoning}

# Sync wrappers (for scheduler / non-async callers)
def run_check_sync(emp_sapid: str, policy_type: str = "") -> dict:
    return asyncio.run(run_compliance_check(emp_sapid, policy_type))
