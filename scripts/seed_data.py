import os
import sys
import random
import uuid
from datetime import date, timedelta

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import get_connection

EMPLOYEES = [
    ("E001", "Alice Johnson",  "alice@example.com",  "rm1@example.com", "slm1@example.com", "WEEKLY",  3),
    ("E002", "Bob Smith",      "bob@example.com",    "rm1@example.com", "slm1@example.com", "WEEKLY",  3),
    ("E003", "Carol White",    "carol@example.com",  "rm2@example.com", "slm1@example.com", "MONTHLY", 12),
    ("E004", "David Brown",    "david@example.com",  "rm2@example.com", "slm2@example.com", "MONTHLY", 12),
    ("E005", "Eve Davis",      "eve@example.com",    "rm1@example.com", "slm2@example.com", "WEEKLY",  3),
    ("E006", "Frank Miller",   "frank@example.com",  "rm2@example.com", "slm2@example.com", "WEEKLY",  3),
]

AUTHORIZED_USERS = [
    ("hr@example.com",         "HR"),
    ("leadership@example.com", "LEADERSHIP"),
    ("admin@example.com",      "ADMIN"),
]

def seed():
    conn = get_connection()

    # Employees
    employee_rows = [
        (emp_sapid, name, email, rm_email, slm_email, "hr@example.com", policy)
        for emp_sapid, name, email, rm_email, slm_email, policy, _ in EMPLOYEES
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO employees
        (emp_sapid, emp_name, emp_email, rm_email, slm_email, hr_email, policy_type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        employee_rows
    )
    print(f"✅ Seeded {len(EMPLOYEES)} employees")

    # Attendance — last 35 days, compliant pattern for E001/E003/E005, non-compliant for E002/E004/E006
    today = date.today()
    rows = []
    for emp_sapid, _, _, _, _, policy, req in EMPLOYEES:
        compliant = emp_sapid in ("E001", "E003", "E005")
        for i in range(35):
            d = today - timedelta(days=i)
            if d.weekday() >= 5:  # skip weekends
                continue
            if compliant:
                present = 1 if random.random() < 0.85 else 0
            else:
                present = 1 if random.random() < 0.35 else 0
            acs_hours = 8.0 if present else 0.0
            rows.append((emp_sapid, d.isoformat(), acs_hours, present))
    conn.executemany(
        """
        INSERT OR IGNORE INTO attendance
        (emp_sapid, date, acs_hours, is_present)
        VALUES (?, ?, ?, ?)
        """,
        rows
    )
    print(f"✅ Seeded attendance for {len(EMPLOYEES)} employees (last 35 days)")

    # Authorized users
    authorized_rows = [
        (f"U-{uuid.uuid5(uuid.NAMESPACE_DNS, email).hex[:10].upper()}", email, role)
        for email, role in AUTHORIZED_USERS
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO authorized_users
        (user_id, user_email, user_role)
        VALUES (?, ?, ?)
        """,
        authorized_rows
    )
    print(f"✅ Seeded {len(AUTHORIZED_USERS)} authorized users")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    seed()
