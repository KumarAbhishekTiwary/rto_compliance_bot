"""Pydantic schemas for agent structured outputs."""
from pydantic import BaseModel, Field
from typing import Literal

class ComplianceResult(BaseModel):
    """Output of Retrieval Agent."""
    emp_sapid: str
    emp_name: str
    emp_email: str
    rm_email: str
    slm_email: str
    hr_email: str
    policy_type: str
    period_start: str
    period_end: str
    days_present: int
    days_required: int
    is_compliant: bool
    shortfall: int

class ValidationVerdict(BaseModel):
    """Output of Chat / Mail Validator Agents."""
    verdict: Literal["SATISFACTORY", "UNSATISFACTORY", "PENDING"]
    justification: str = Field(description="Extracted justification text or empty string")
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(description="Brief reasoning for the verdict")

class QueryResult(BaseModel):
    """Output of Query Agent for chatbot."""
    answer: str = Field(description="Human-readable answer")
    sql_used: str = Field(description="SQL query that was executed")
    row_count: int
    success: bool
