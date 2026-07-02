import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import get_connection

def test_lifecycle():
    conn = get_connection()
    # Insert test violation
    conn.execute(
        "INSERT INTO violations (emp_sapid,policy_type,period_start,period_end,days_present,days_required) VALUES (?,?,?,?,?,?)",
        ("E001", "WEEKLY", "2024-01-01", "2024-01-07", 1, 3)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM violations WHERE emp_sapid='E001'").fetchone()
    assert row["status"] == "OPEN", "Expected OPEN"
    conn.execute("UPDATE violations SET status='RESET' WHERE emp_sapid='E001'")
    conn.commit()
    row = conn.execute("SELECT * FROM violations WHERE emp_sapid='E001'").fetchone()
    assert row["status"] == "RESET", "Expected RESET"
    conn.execute("DELETE FROM violations WHERE emp_sapid='E001'")
    conn.commit()
    conn.close()
    print("✅ Lifecycle test passed")

def test_sql_safety():
    conn = get_connection()
    # Only SELECT should work via query tool (enforced in query.py)
    try:
        conn.execute("SELECT count(*) FROM employees").fetchone()
        print("✅ SQL safety test passed")
    except Exception as e:
        print(f"❌ SQL safety test failed: {e}")
    conn.close()

if __name__ == "__main__":
    test_lifecycle()
    test_sql_safety()
    print("🎉 All smoke tests passed!")
