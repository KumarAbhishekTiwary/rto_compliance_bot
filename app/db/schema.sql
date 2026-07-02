CREATE TABLE IF NOT EXISTS employees (
    emp_sapid      TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    email          TEXT NOT NULL,
    rm_email       TEXT NOT NULL,
    slm_email      TEXT NOT NULL,
    policy_type    TEXT NOT NULL CHECK(policy_type IN ('WEEKLY','MONTHLY')),
    required_days  INTEGER NOT NULL,
    created_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS attendance (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_sapid   TEXT NOT NULL REFERENCES employees(emp_sapid),
    date        TEXT NOT NULL,
    present     INTEGER NOT NULL DEFAULT 0,
    UNIQUE(emp_sapid, date)
);

CREATE TABLE IF NOT EXISTS violations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_sapid       TEXT NOT NULL REFERENCES employees(emp_sapid),
    policy_type     TEXT NOT NULL,
    period_start    TEXT NOT NULL,
    period_end      TEXT NOT NULL,
    days_present    INTEGER NOT NULL,
    days_required   INTEGER NOT NULL,
    status          TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN','RESET')),
    channel_id      TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    resolved_at     TEXT
);

CREATE TABLE IF NOT EXISTS communication_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_sapid   TEXT NOT NULL,
    direction   TEXT NOT NULL CHECK(direction IN ('INBOUND','OUTBOUND')),
    channel     TEXT NOT NULL,
    subject     TEXT,
    body        TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_sapid   TEXT NOT NULL,
    action      TEXT NOT NULL,
    details     TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS authorized_users (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    email   TEXT NOT NULL UNIQUE,
    role    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS channels (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_ref     TEXT NOT NULL UNIQUE,
    emp_sapid       TEXT NOT NULL,
    violation_id    INTEGER REFERENCES violations(id),
    status          TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE','RESOLVED')),
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS channel_members (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_ref TEXT NOT NULL REFERENCES channels(channel_ref),
    email       TEXT NOT NULL,
    role        TEXT NOT NULL,
    UNIQUE(channel_ref, email)
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_ref     TEXT NOT NULL REFERENCES channels(channel_ref),
    sender_email    TEXT NOT NULL,
    sender_role     TEXT NOT NULL,
    body            TEXT NOT NULL,
    verdict         TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);
