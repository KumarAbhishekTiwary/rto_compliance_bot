"""Query Agent — converts natural language to SQL and runs it."""
import os
import json
from app.tools.query import run_safe_query
from app.db.database import get_connection


SCHEMA_HINT = """
Tables:
- employees(emp_sapid, name, email, rm_email, slm_email, policy_type, required_days)
- attendance(id, emp_sapid, date, present)
- violations(id, emp_sapid, policy_type, period_start, period_end, days_present, days_required, status, channel_id, created_at, resolved_at)
- authorized_users(id, email, role)
- channels(id, channel_ref, emp_sapid, violation_id, status, created_at)
- messages(id, channel_ref, sender_email, sender_role, body, verdict, created_at)
"""


async def run_query_agent(natural_language: str, user_email: str) -> dict:
    # Auth check
    conn = get_connection()
    auth = conn.execute(
        "SELECT role FROM authorized_users WHERE email=?", (user_email,)
    ).fetchone()
    conn.close()
    if not auth:
        return {"error": "Unauthorized", "status": 403}

    try:
        from agents import Agent, Runner

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        agent = Agent(
            name="QueryAgent",
            model=model,
            instructions=f"""You are a SQL generator for an RTO compliance database.
{SCHEMA_HINT}
Convert the user's question to a single valid SQLite SELECT query.
Respond ONLY with the raw SQL query, no markdown, no explanation.""",
        )
        result = await Runner.run(agent, natural_language)
        sql = result.final_output.strip().strip("```sql").strip("```").strip()
        query_result = run_safe_query(sql)
        return {"sql": sql, "result": query_result, "user": user_email}

    except Exception as e:
        return {"error": str(e), "status": 500}
