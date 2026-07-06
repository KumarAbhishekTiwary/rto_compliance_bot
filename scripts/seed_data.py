"""Seed sample employees, attendance, and authorized users for testing."""
import sys
import uuid
from pathlib import Path
from datetime import datetime, timedelta
import random

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db.database import db_cursor

EMPLOYEES = [
    # (sapid, name, email, rm_email, slm_email, hr_email, policy)
    ("E001", "Alice Johnson",  "alice@example.com",  "rm1@example.com", "slm1@example.com", "hr@example.com", "WEEKLY"),
    ("E002", "Bob Smith",      "bob@example.com",    "rm1@example.com", "slm1@example.com", "hr@example.com", "WEEKLY"),
    ("E003", "Carol Davis",    "carol@example.com",  "rm2@example.com", "slm1@example.com", "hr@example.com", "MONTHLY"),
    ("E004", "David Miller",   "david@example.com",  "rm2@example.com", "slm1@example.com", "hr@example.com", "MONTHLY"),
    ("E005", "Eve Wilson",     "eve@example.com",    "rm1@example.com", "slm1@example.com", "hr@example.com", "WEEKLY"),
    ("E006", "Frank Brown",    "frank@example.com",  "rm2@example.com", "slm1@example.com", "hr@example.com", "EXEMPT"),
]

AUTHORIZED_USERS = [
    ("U001", "hr@example.com", "HR"),
    ("U002", "leadership@example.com", "LEADERSHIP"),
    ("U003", "admin@example.com", "ADMIN"),
]

def seed_employees():
    with db_cursor() as cur:
        for emp in EMPLOYEES:
            cur.execute("""
                INSERT OR REPLACE INTO employees
                (emp_sapid, emp_name, emp_email, rm_email, slm_email, hr_email, policy_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, emp)
    print(f"✅ Seeded {len(EMPLOYEES)} employees")

def seed_attendance():
    """Generate attendance for last 35 days. Some employees will be non-compliant."""
    today = datetime.now().date()
    with db_cursor() as cur:
        # Clear old
        cur.execute("DELETE FROM attendance")

        for sapid, name, *_ in EMPLOYEES:
            # Compliance probability — make some non-compliant
            if sapid == "E001":   # Compliant
                attend_prob = 0.85
            elif sapid == "E002": # Non-compliant weekly (will trigger)
                attend_prob = 0.30
            elif sapid == "E003": # Compliant monthly
                attend_prob = 0.75
            elif sapid == "E004": # Non-compliant monthly (will trigger)
                attend_prob = 0.35
            elif sapid == "E005": # Borderline weekly
                attend_prob = 0.55
            else:
                attend_prob = 0.90

            for d in range(35):
                date = today - timedelta(days=d)
                # Skip weekends
                if date.weekday() >= 5:
                    continue
                present = 1 if random.random() < attend_prob else 0
                hours = round(random.uniform(7.5, 9.5), 2) if present else 0.0
                cur.execute("""
                    INSERT OR IGNORE INTO attendance
                    (emp_sapid, date, acs_hours, is_present, source)
                    VALUES (?, ?, ?, ?, 'SEED')
                """, (sapid, date, hours, present))
    print(f"✅ Seeded attendance for {len(EMPLOYEES)} employees (last 35 days)")

def seed_authorized_users():
    with db_cursor() as cur:
        for user in AUTHORIZED_USERS:
            cur.execute("""
                INSERT OR REPLACE INTO authorized_users
                (user_id, user_email, user_role)
                VALUES (?, ?, ?)
            """, user)
    print(f"✅ Seeded {len(AUTHORIZED_USERS)} authorized users")

if __name__ == "__main__":
    random.seed(42)
    seed_employees()
    seed_attendance()
    seed_authorized_users()
    print("\n🎉 Seed complete! Run: python -c \"from scripts.seed_data import show_summary; show_summary()\"")

def show_summary():
    with db_cursor() as cur:
        cur.execute("SELECT emp_sapid, emp_name, policy_type FROM employees")
        for row in cur.fetchall():
            print(dict(row))
