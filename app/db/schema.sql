-- ============================================================
-- RTO Compliance Bot - SQLite Schema
-- ============================================================

-- Employee master
CREATE TABLE IF NOT EXISTS employees (
    emp_sapid       TEXT PRIMARY KEY,
    emp_name        TEXT NOT NULL,
    emp_email       TEXT,
    rm_email        TEXT,
    slm_email       TEXT,
    hr_email        TEXT,
    policy_type     TEXT CHECK(policy_type IN ('WEEKLY','MONTHLY','EXEMPT')),
    active          INTEGER DEFAULT 1,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily attendance
CREATE TABLE IF NOT EXISTS attendance (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_sapid       TEXT NOT NULL,
    date            DATE NOT NULL,
    acs_hours       REAL,
    is_present      INTEGER DEFAULT 0,
    source          TEXT DEFAULT 'MANUAL',
    FOREIGN KEY (emp_sapid) REFERENCES employees(emp_sapid),
    UNIQUE(emp_sapid, date)
);

-- Violation tracking
CREATE TABLE IF NOT EXISTS violations (
    violation_id    TEXT PRIMARY KEY,
    emp_sapid       TEXT NOT NULL,
    period_type     TEXT,
    period_start    DATE,
    period_end      DATE,
    days_present    INTEGER,
    days_required   INTEGER,
    status          TEXT DEFAULT 'OPEN',
    slack_channel_id TEXT,
    sla_due_at      TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at       TIMESTAMP,
    FOREIGN KEY (emp_sapid) REFERENCES employees(emp_sapid)
);

-- Communication log
CREATE TABLE IF NOT EXISTS communication_log (
    log_id          TEXT PRIMARY KEY,
    violation_id    TEXT NOT NULL,
    channel         TEXT,
    direction       TEXT,
    sender          TEXT,
    message         TEXT,
    llm_verdict     TEXT,
    justification   TEXT,
    confidence      REAL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (violation_id) REFERENCES violations(violation_id)
);

-- Audit log
CREATE TABLE IF NOT EXISTS audit_log (
    audit_id        TEXT PRIMARY KEY,
    emp_sapid       TEXT,
    action          TEXT,
    actor           TEXT,
    details         TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Authorized users (for chatbot)
CREATE TABLE IF NOT EXISTS authorized_users (
    user_id         TEXT PRIMARY KEY,
    user_email      TEXT UNIQUE NOT NULL,
    user_role       TEXT,
    active          INTEGER DEFAULT 1,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_attendance_emp_date ON attendance(emp_sapid, date);
CREATE INDEX IF NOT EXISTS idx_violations_status ON violations(status);
CREATE INDEX IF NOT EXISTS idx_violations_emp ON violations(emp_sapid);
CREATE INDEX IF NOT EXISTS idx_comm_violation ON communication_log(violation_id);

-- ============================================================
-- Additional tables for in-app Teams-like chat
-- ============================================================

CREATE TABLE IF NOT EXISTS channels (
    channel_id      TEXT PRIMARY KEY,
    channel_name    TEXT NOT NULL,
    violation_id    TEXT,
    status          TEXT DEFAULT 'ACTIVE',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (violation_id) REFERENCES violations(violation_id)
);

CREATE TABLE IF NOT EXISTS channel_members (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id      TEXT NOT NULL,
    member_email    TEXT NOT NULL,
    member_role     TEXT,
    joined_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id),
    UNIQUE(channel_id, member_email)
);

CREATE TABLE IF NOT EXISTS messages (
    message_id      TEXT PRIMARY KEY,
    channel_id      TEXT NOT NULL,
    sender_email    TEXT NOT NULL,
    sender_role     TEXT,
    sender_name     TEXT,
    content         TEXT NOT NULL,
    message_type    TEXT DEFAULT 'TEXT',
    metadata        TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel_id, created_at);
CREATE INDEX IF NOT EXISTS idx_members_channel ON channel_members(channel_id);
CREATE INDEX IF NOT EXISTS idx_members_email ON channel_members(member_email);
