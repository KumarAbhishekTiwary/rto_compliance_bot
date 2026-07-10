"""Shared structured output schemas for agents."""
from pydantic import BaseModel, Field


class ComplianceResult(BaseModel):
    emp_sapid: str = ""
    emp_name: str = ""
    emp_email: str = ""
    rm_email: str = ""
    slm_email: str = ""
    hr_email: str = ""
    policy_type: str = ""
    period_start: str = ""
    period_end: str = ""
    days_present: int = 0
    days_required: int = 0
    is_compliant: bool = True
    shortfall: int = 0
    reason: str = ""


class ValidationVerdict(BaseModel):
    verdict: str = Field(default="PENDING", pattern="^(SATISFACTORY|UNSATISFACTORY|PENDING)$")
    justification: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = ""


class QueryResult(BaseModel):
    answer: str = ""
    sql_used: str = ""
    row_count: int = 0
    success: bool = False
