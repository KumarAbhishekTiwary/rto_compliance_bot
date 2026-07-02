from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agents.orchestrator import run_compliance_check
from app.tools.violation import get_open_violations

router = APIRouter()


class ComplianceCheckRequest(BaseModel):
    emp_sapid: str
    policy_type: str = "WEEKLY"


@router.post("/compliance/check")
async def compliance_check(req: ComplianceCheckRequest):
    result = await run_compliance_check(req.emp_sapid, req.policy_type)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/violations")
def list_violations():
    return get_open_violations()


@router.post("/sla_sweep")
async def sla_sweep():
    """Run compliance check for all employees (triggered by scheduler or manually)."""
    from app.db.database import get_connection
    conn = get_connection()
    employees = conn.execute("SELECT emp_sapid, policy_type FROM employees").fetchall()
    conn.close()
    results = []
    for emp in employees:
        r = await run_compliance_check(emp["emp_sapid"], emp["policy_type"])
        results.append(r)
    return {"swept": len(results), "results": results}
