"""Compliance check endpoints."""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.agents.orchestrator import run_compliance_check, trigger_email_escalation
from app.tools.attendance import list_employees_for_check
from app.tools.violation import get_sla_breached_violations, get_violation
from app.db.database import db_cursor

router = APIRouter()

class CheckRequest(BaseModel):
    emp_sapid: str
    policy_type: Optional[str] = ""

class BulkCheckRequest(BaseModel):
    policy_type: str  # "WEEKLY" or "MONTHLY"

@router.post("/compliance/check")
async def check_one(req: CheckRequest):
    """Run a compliance check for a single employee."""
    return await run_compliance_check(req.emp_sapid, req.policy_type or "")

@router.post("/compliance/bulk_check")
async def check_bulk(req: BulkCheckRequest, background: BackgroundTasks):
    """Run compliance checks for all employees with a given policy."""
    emp_ids = list_employees_for_check(req.policy_type)
    results = []
    for sapid in emp_ids:
        try:
            r = await run_compliance_check(sapid, req.policy_type)
            results.append(r)
        except Exception as e:
            results.append({"emp_sapid": sapid, "error": str(e)})
    return {"checked": len(results), "results": results}

@router.get("/violations")
def list_violations(status: Optional[str] = None, emp_sapid: Optional[str] = None):
    """List violations with optional filters."""
    sql = "SELECT * FROM violations WHERE 1=1"
    params = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    if emp_sapid:
        sql += " AND emp_sapid = ?"
        params.append(emp_sapid)
    sql += " ORDER BY created_at DESC LIMIT 100"
    with db_cursor() as cur:
        cur.execute(sql, params)
        return {"violations": [dict(r) for r in cur.fetchall()]}

@router.get("/violations/{violation_id}")
def violation_detail(violation_id: str):
    v = get_violation(violation_id)
    if not v:
        raise HTTPException(404, "Violation not found")
    # Get comms
    with db_cursor() as cur:
        cur.execute("""
            SELECT * FROM communication_log
            WHERE violation_id = ? ORDER BY created_at
        """, (violation_id,))
        comms = [dict(r) for r in cur.fetchall()]
    return {"violation": v, "communications": comms}

@router.post("/compliance/sla_sweep")
async def sla_sweep():
    """Manually trigger SLA sweep (also runs on schedule)."""
    breached = get_sla_breached_violations()
    results = []
    for v in breached:
        r = await trigger_email_escalation(v["violation_id"])
        results.append(r)
    return {"breached_count": len(breached), "results": results}
