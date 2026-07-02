from datetime import date, timedelta
from app.db.database import get_connection


def get_attendance_summary(emp_sapid: str, policy_type: str) -> dict:
    conn = get_connection()
    emp = conn.execute(
        "SELECT * FROM employees WHERE emp_sapid=?", (emp_sapid,)
    ).fetchone()
    if not emp:
        conn.close()
        return {"error": f"Employee {emp_sapid} not found"}

    today = date.today()
    if policy_type == "WEEKLY":
        # current Mon–Sun week
        period_start = today - timedelta(days=today.weekday())
        period_end = period_start + timedelta(days=6)
    else:
        # current calendar month
        period_start = today.replace(day=1)
        next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
        period_end = next_month - timedelta(days=1)

    rows = conn.execute(
        "SELECT date, present FROM attendance WHERE emp_sapid=? AND date BETWEEN ? AND ?",
        (emp_sapid, period_start.isoformat(), period_end.isoformat()),
    ).fetchall()
    conn.close()

    days_present = sum(r["present"] for r in rows)
    required = emp["required_days"]
    compliant = days_present >= required

    return {
        "emp_sapid": emp_sapid,
        "name": dict(emp)["name"],
        "email": dict(emp)["email"],
        "rm_email": dict(emp)["rm_email"],
        "slm_email": dict(emp)["slm_email"],
        "policy_type": policy_type,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "days_present": days_present,
        "days_required": required,
        "compliant": compliant,
    }
