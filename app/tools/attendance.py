"""Attendance retrieval tool - calculates compliance based on policy."""
from datetime import datetime, timedelta
from app.db.database import db_cursor

POLICY_RULES = {
    "WEEKLY": {"days_required": 3, "period_days": 7},
    "MONTHLY": {"days_required": 12, "period_days": 30},
}

def fetch_attendance_summary(emp_sapid: str, policy_type: str = None) -> dict:
    """
    Fetch attendance summary for an employee.
    Returns compliance status for their assigned policy.
    """
    today = datetime.now().date()

    with db_cursor() as cur:
        # Get employee + policy if not given
        cur.execute("""
            SELECT emp_sapid, emp_name, emp_email, rm_email, slm_email, hr_email, policy_type
            FROM employees WHERE emp_sapid = ? AND active = 1
        """, (emp_sapid,))
        emp = cur.fetchone()
        if not emp:
            return {"error": f"Employee {emp_sapid} not found or inactive"}
        emp = dict(emp)

        policy = policy_type or emp["policy_type"]
        if policy == "EXEMPT":
            return {
                **emp,
                "policy_type": policy,
                "is_compliant": True,
                "reason": "Employee is EXEMPT from RTO policy",
            }

        rules = POLICY_RULES[policy]
        if policy == "WEEKLY":
            # Last 7 days
            period_start = today - timedelta(days=7)
        else:
            # Previous calendar month
            period_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)

        cur.execute("""
            SELECT COUNT(*) as days_present
            FROM attendance
            WHERE emp_sapid = ?
              AND date BETWEEN ? AND ?
              AND is_present = 1
        """, (emp_sapid, period_start, today))
        days_present = cur.fetchone()["days_present"]

    is_compliant = days_present >= rules["days_required"]

    return {
        **emp,
        "policy_type": policy,
        "period_start": str(period_start),
        "period_end": str(today),
        "days_present": days_present,
        "days_required": rules["days_required"],
        "is_compliant": is_compliant,
        "shortfall": max(0, rules["days_required"] - days_present),
    }

def list_employees_for_check(policy_type: str) -> list:
    """List all active employees matching a policy_type (for scheduler)."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT emp_sapid FROM employees
            WHERE policy_type = ? AND active = 1
        """, (policy_type,))
        return [row["emp_sapid"] for row in cur.fetchall()]
