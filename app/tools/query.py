"""Query tool for chatbot - NL→SQL with safety enforcement."""
import re
from difflib import SequenceMatcher
from app.db.database import db_cursor

ALLOWED_TABLES = {"employees", "attendance", "violations", "communication_log", "audit_log"}
FORBIDDEN_KEYWORDS = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "REPLACE"]

SCHEMA_DESCRIPTION = """
Tables (SQLite):
- employees(emp_sapid PK, emp_name, emp_email, rm_email, slm_email, hr_email, policy_type, active, created_at)
- attendance(id PK, emp_sapid FK, date, acs_hours, is_present, source)
- violations(violation_id PK, emp_sapid FK, period_type, period_start, period_end,
  days_present, days_required, status, slack_channel_id, sla_due_at, created_at, closed_at)
- communication_log(log_id PK, violation_id FK, channel, direction, sender, message,
  llm_verdict, justification, confidence, created_at)
- audit_log(audit_id PK, emp_sapid, action, actor, details, created_at)

Notes:
- policy_type values: 'WEEKLY', 'MONTHLY', 'EXEMPT'
- violations.status: 'OPEN','TEAMS_NOTIFIED','EMAIL_ESCALATED','RESET'
- llm_verdict: 'SATISFACTORY','UNSATISFACTORY','PENDING'
- Always use parameterless SELECT; no joins needed unless explicitly required
"""

def is_safe_sql(sql: str) -> tuple[bool, str]:
    """Validate SQL is SELECT-only and references only allowed tables."""
    s = sql.strip().upper()
    if not s.startswith("SELECT"):
        return False, "Only SELECT queries are allowed."
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", s):
            return False, f"Forbidden keyword: {kw}"
    # Check semicolons (only at end allowed)
    if ";" in sql.rstrip(";").rstrip():
        return False, "Multiple statements not allowed."
    return True, "OK"

def execute_safe_query(sql: str, limit: int = 100) -> dict:
    """Execute a SELECT-only query and return results."""
    ok, reason = is_safe_sql(sql)
    if not ok:
        return {"error": reason, "sql": sql}
    # Auto-apply limit if missing
    if "LIMIT" not in sql.upper():
        sql = sql.rstrip(";").rstrip() + f" LIMIT {limit}"
    try:
        with db_cursor() as cur:
            cur.execute(sql)
            rows = [dict(r) for r in cur.fetchall()]
        return {"rows": rows, "row_count": len(rows), "sql": sql}
    except Exception as e:
        return {"error": str(e), "sql": sql}

def check_authorization(user_email: str) -> dict:
    """Check if user is in authorized_users table."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT user_id, user_email, user_role
            FROM authorized_users
            WHERE user_email = ? AND active = 1
        """, (user_email,))
        row = cur.fetchone()
        return dict(row) if row else None


def resolve_employee_reference(question: str, limit: int = 5) -> dict:
    """Resolve exact, partial, or slightly misspelled employee references."""
    normalized_question = " ".join(re.findall(r"[a-z0-9]+", question.lower()))
    question_tokens = set(normalized_question.split())
    with db_cursor() as cur:
        cur.execute("""
            SELECT emp_sapid, emp_name, emp_email
            FROM employees
            WHERE active = 1
            ORDER BY emp_name, emp_sapid
        """)
        employees = [dict(row) for row in cur.fetchall()]

    # Employee code or email is an explicit, unique selection.
    for employee in employees:
        sapid = employee["emp_sapid"].lower()
        email = (employee.get("emp_email") or "").lower()
        if re.search(rf"\b{re.escape(sapid)}\b", question.lower()) or (
            email and email in question.lower()
        ):
            return {"status": "resolved", "employee": employee, "matches": [employee]}

    full_matches = []
    scored_matches = []
    for employee in employees:
        normalized_name = " ".join(re.findall(r"[a-z0-9]+", employee["emp_name"].lower()))
        if normalized_name and normalized_name in normalized_question:
            full_matches.append(employee)
            continue

        name_tokens = [token for token in normalized_name.split() if len(token) >= 3]
        token_scores = [
            max(
                (SequenceMatcher(None, name_token, word).ratio() for word in question_tokens),
                default=0.0,
            )
            for name_token in name_tokens
        ]
        best_score = max(token_scores, default=0.0)
        if best_score >= 0.84:
            scored_matches.append((best_score, employee))

    matches = full_matches or [
        employee for _, employee in sorted(
            scored_matches,
            key=lambda item: (-item[0], item[1]["emp_name"], item[1]["emp_sapid"]),
        )
    ]
    if not matches:
        return {"status": "none", "matches": []}
    if len(matches) == 1:
        return {"status": "resolved", "employee": matches[0], "matches": matches}
    return {
        "status": "ambiguous",
        "matches": matches[:limit],
        "total_matches": len(matches),
    }
