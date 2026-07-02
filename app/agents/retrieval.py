"""Retrieval Agent — fetches attendance summary for an employee."""
import os
from app.tools.attendance import get_attendance_summary


async def run_retrieval(emp_sapid: str, policy_type: str) -> dict:
    return get_attendance_summary(emp_sapid, policy_type)
