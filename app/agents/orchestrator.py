"""Orchestrator — end-to-end compliance check pipeline."""
from app.agents.retrieval import run_retrieval
from app.agents.meeting_planner import run_meeting_planner
from app.agents.email_planner import run_email_planner
from app.tools.violation import create_violation


async def run_compliance_check(emp_sapid: str, policy_type: str) -> dict:
    # Step 1: Fetch attendance
    summary = await run_retrieval(emp_sapid, policy_type)
    if "error" in summary:
        return summary

    if summary["compliant"]:
        return {
            "emp_sapid": emp_sapid,
            "status": "COMPLIANT",
            "days_present": summary["days_present"],
            "days_required": summary["days_required"],
        }

    # Step 2: Create violation record
    v = create_violation(
        emp_sapid=emp_sapid,
        policy_type=policy_type,
        period_start=summary["period_start"],
        period_end=summary["period_end"],
        days_present=summary["days_present"],
        days_required=summary["days_required"],
    )
    violation_id = v["violation_id"]

    violation_summary = (
        f"⚠️ RTO Compliance Violation\n"
        f"Employee: {summary['name']} ({emp_sapid})\n"
        f"Period: {summary['period_start']} to {summary['period_end']}\n"
        f"Attended: {summary['days_present']}/{summary['days_required']} required days\n"
        f"Policy: {policy_type}\n\n"
        f"Please provide justification for the missed days."
    )

    # Step 3: Create in-app channel
    channel_result = await run_meeting_planner(
        emp_email=summary["email"],
        rm_email=summary["rm_email"],
        slm_email=summary["slm_email"],
        emp_name=summary["name"],
        violation_summary=violation_summary,
        violation_id=violation_id,
        emp_sapid=emp_sapid,
    )

    # Step 4: Send email notification
    email_result = await run_email_planner(
        emp_name=summary["name"],
        emp_email=summary["email"],
        rm_email=summary["rm_email"],
        slm_email=summary["slm_email"],
        days_present=summary["days_present"],
        days_required=summary["days_required"],
        period_start=summary["period_start"],
        period_end=summary["period_end"],
        policy_type=policy_type,
        emp_sapid=emp_sapid,
    )

    return {
        "emp_sapid": emp_sapid,
        "status": "VIOLATION_OPENED",
        "violation_id": violation_id,
        "channel_ref": channel_result.get("channel_ref"),
        "days_present": summary["days_present"],
        "days_required": summary["days_required"],
        "email_status": email_result.get("status"),
        "already_existed": not v.get("created", True),
    }
