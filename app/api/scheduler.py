"""APScheduler jobs - weekly Monday + monthly 1st-of-month + SLA sweep."""
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.agents.orchestrator import run_compliance_check, trigger_email_escalation
from app.tools.attendance import list_employees_for_check
from app.tools.violation import get_sla_breached_violations, log_audit
from apscheduler.triggers.interval import IntervalTrigger

scheduler = BackgroundScheduler()

def _run_async(coro):
    """Run a coroutine in a fresh event loop (for sync scheduler context)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def job_weekly_check():
    """Every Monday at 06:00 - check WEEKLY policy employees."""
    log_audit(None, "SCHEDULER_TRIGGERED", "WEEKLY_JOB", "")
    emps = list_employees_for_check("WEEKLY")
    print(f"[Scheduler] WEEKLY check for {len(emps)} employees")
    for sapid in emps:
        try:
            _run_async(run_compliance_check(sapid, "WEEKLY"))
        except Exception as e:
            print(f"[Scheduler] Error for {sapid}: {e}")

def job_monthly_check():
    """1st of every month at 06:00 - check MONTHLY policy employees."""
    log_audit(None, "SCHEDULER_TRIGGERED", "MONTHLY_JOB", "")
    emps = list_employees_for_check("MONTHLY")
    print(f"[Scheduler] MONTHLY check for {len(emps)} employees")
    for sapid in emps:
        try:
            _run_async(run_compliance_check(sapid, "MONTHLY"))
        except Exception as e:
            print(f"[Scheduler] Error for {sapid}: {e}")

def job_sla_sweep():
    """Every hour - find SLA-breached violations and escalate via email."""
    breached = get_sla_breached_violations()
    if not breached:
        return
    print(f"[Scheduler] SLA sweep: {len(breached)} breached")
    for v in breached:
        try:
            _run_async(trigger_email_escalation(v["violation_id"]))
        except Exception as e:
            print(f"[Scheduler] SLA escalation error: {e}")

def start_scheduler():
    scheduler.add_job(job_weekly_check, CronTrigger(day_of_week="mon", hour=6, minute=0),
                      id="weekly_check", replace_existing=True)
    scheduler.add_job(job_monthly_check, CronTrigger(day=1, hour=6, minute=0),
                      id="monthly_check", replace_existing=True)
    # scheduler.add_job(job_sla_sweep, CronTrigger(minute=0),
                    #   id="sla_sweep", replace_existing=True)
    
    scheduler.add_job(job_sla_sweep, IntervalTrigger(seconds=30),
                    id="sla_sweep", replace_existing=True)

    scheduler.start()
    print("✅ Scheduler started: weekly (Mon 06:00), monthly (1st 06:00), SLA hourly")

def shutdown_scheduler():
    scheduler.shutdown()
    print("⏹️ Scheduler stopped")
