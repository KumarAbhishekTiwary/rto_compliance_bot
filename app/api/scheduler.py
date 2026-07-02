from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio


scheduler = AsyncIOScheduler()


async def _weekly_sweep():
    from app.db.database import get_connection
    from app.agents.orchestrator import run_compliance_check
    conn = get_connection()
    emps = conn.execute("SELECT emp_sapid FROM employees WHERE policy_type='WEEKLY'").fetchall()
    conn.close()
    for e in emps:
        await run_compliance_check(e["emp_sapid"], "WEEKLY")


async def _monthly_sweep():
    from app.db.database import get_connection
    from app.agents.orchestrator import run_compliance_check
    conn = get_connection()
    emps = conn.execute("SELECT emp_sapid FROM employees WHERE policy_type='MONTHLY'").fetchall()
    conn.close()
    for e in emps:
        await run_compliance_check(e["emp_sapid"], "MONTHLY")


async def _sla_sweep():
    from app.tools.violation import get_open_violations
    violations = get_open_violations()
    # Future: escalate violations open > SLA threshold


def start_scheduler():
    scheduler.add_job(_weekly_sweep,  CronTrigger(day_of_week="mon", hour=6, minute=0), id="weekly")
    scheduler.add_job(_monthly_sweep, CronTrigger(day=1,             hour=6, minute=0), id="monthly")
    scheduler.add_job(_sla_sweep,     CronTrigger(minute=0),                            id="sla_hourly")
    scheduler.start()
    print("✅ Scheduler started: weekly (Mon 06:00), monthly (1st 06:00), SLA hourly")


def stop_scheduler():
    scheduler.shutdown(wait=False)
