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
from app.agents.email_planner import email_planner_agent
from app.agents.mail_validator import mail_validator_agent
from app.agents.reset import reset_agent
from app.tools.violation import log_audit, get_violation

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
    """Called by Slack webhook when a new RM message arrives."""
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
    """Called by SLA timer when 24h elapses without satisfactory chat verdict."""
    vio = get_violation(violation_id)
    if not vio:
        return {"error": f"Violation {violation_id} not found"}

    # Get employee details for the email
    from app.tools.attendance import fetch_attendance_summary
    emp = fetch_attendance_summary(vio["emp_sapid"], vio["period_type"])

    input_data = {
        "violation_id": violation_id,
        "rm_email": emp["rm_email"],
        "slm_email": emp["slm_email"],
        "hr_email": emp["hr_email"],
        "emp_name": emp["emp_name"],
        "emp_sapid": emp["emp_sapid"],
        "period_type": vio["period_type"],
        "period_start": vio["period_start"],
        "period_end": vio["period_end"],
        "days_present": vio["days_present"],
        "days_required": vio["days_required"],
    }
    result = await Runner.run(email_planner_agent, json.dumps(input_data))
    log_audit(emp["emp_sapid"], "EMAIL_ESCALATED", "SYSTEM",
              f"violation_id={violation_id}")
    return {"violation_id": violation_id, "status": "EMAIL_ESCALATED",
            "result": str(result.final_output)}

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
