# RTO Compliance Bot — End-to-End Demo Recording Guide

Target duration: 8–12 minutes.

## What the recording demonstrates

1. Deterministic RTO non-compliance detection for employee `E007`.
2. Automatic Teams-like channel creation for Employee, RM, and SLM.
3. Timed escalation email with Employee and HR in CC.
4. RM email justification validation and synchronized Teams resolution.
5. The reverse path: Teams approval followed by a resolution email.
6. Natural-language compliance analytics in the chatbot.

## Demo identities

| Role | Name | Account |
|---|---|---|
| Employee | Abhishek Tiwary | `abhitiwary0001@gmail.com` |
| Reporting manager | Manohar Bediya | `pandahai477@gmail.com` |
| SLM | Demo SLM | `slm2@example.com` |
| HR chatbot user | Demo HR | `hr@example.com` |
| Employee code | — | `E007` |

`E007` is seeded with zero attendance and is always non-compliant with the weekly three-day policy.

## 1. Private preparation — do not record secrets

Activate the virtual environment and install dependencies:

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Confirm `.env` contains real values. Do not show this file in the recording:

```env
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
GMAIL_USER=...
GMAIL_APP_PASSWORD=...
GMAIL_IMAP_ENABLED=true
EMAIL_POLL_SECONDS=10
SLA_MINUTES=1
TEAMS_REMINDER_MINUTES=1
EMAIL_REMINDER_MINUTES=1
```

Use a Gmail App Password, not the normal Gmail password. The account must be able to use SMTP and IMAP.

## 2. Prepare a clean demo database

Stop the API before replacing the database. Preserve an existing database rather than deleting it:

```powershell
if (Test-Path .\rto.db) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    Move-Item .\rto.db ".\rto-before-demo-$stamp.db"
}
python scripts/init_db.py
python scripts/seed_data.py
```

Expected output:

```text
Database initialized at: rto.db
Seeded 7 employees
Seeded attendance for 7 employees
Seeded 3 authorized users
```

Optional verification:

```powershell
python -c "import sqlite3; c=sqlite3.connect('rto.db'); print(c.execute(\"SELECT emp_sapid,emp_name,emp_email,rm_email FROM employees WHERE emp_sapid='E007'\").fetchone()); print('present days:',c.execute(\"SELECT SUM(is_present) FROM attendance WHERE emp_sapid='E007'\").fetchone()[0])"
```

Expected employee: Abhishek Tiwary; expected present days: `0`.

## 3. Start the application

Terminal 1 — API, scheduler, email poller, and Teams-like UI:

```powershell
uvicorn app.api.main:app --reload --port 8000
```

Terminal 2 — analytics chatbot:

```powershell
streamlit run app/ui/chatbot_app.py --server.port 8501
```

Verify before recording:

- API health: <http://localhost:8000/api/v1/health>
- Teams-like UI: <http://localhost:8000/api/v1/chat>
- Chatbot: <http://localhost:8501>
- API documentation (optional): <http://localhost:8000/docs>

## 4. Arrange the recording tabs

Open these tabs/windows before recording:

1. Teams UI signed in as `abhitiwary0001@gmail.com` (Employee).
2. Teams UI signed in as `pandahai477@gmail.com` (RM). Use an incognito window or separate browser profile.
3. The RM Gmail inbox for `pandahai477@gmail.com`.
4. Chatbot at `http://localhost:8501`.
5. A PowerShell terminal for trigger commands.

Keep `.env`, API keys, and Gmail App Passwords outside the captured area.

---

# Recording script

## Scene 1 — Introduction (30–45 seconds)

Show the RTO Compliance chatbot landing page.

Suggested narration:

> “This is an end-to-end RTO compliance workflow. It detects attendance shortfalls, creates a collaboration channel, requests manager justification, escalates by email, validates responses using an agent, synchronizes resolution across channels, and exposes read-only analytics through a chatbot.”

## Scene 2 — Trigger the compliance check (45–60 seconds)

In PowerShell, run:

```powershell
$body = @{ emp_sapid = "E007"; policy_type = "WEEKLY" } | ConvertTo-Json
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/v1/compliance/check" `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json -Depth 8
```

Point out:

- Employee `E007` is non-compliant.
- Required attendance is three days.
- A violation and Teams-like channel are created.

Suggested narration:

> “I am running a weekly check for E007. The seeded attendance is deliberately non-compliant, so the retrieval agent identifies the shortfall and the meeting planner creates a private compliance channel.”

## Scene 3 — Show the collaboration channel (45 seconds)

Refresh the Employee and RM Teams tabs. Open the newest channel.

Show:

- Employee, RM, SLM, and bot membership.
- Violation notification.
- Request for a specific business justification.
- Reminder interval.

Suggested narration:

> “The same case is visible to the relevant participants. The bot requests the reason, dates, and an approval reference, and maintains an auditable conversation.”

## Scene 4 — Show timed email escalation (1–2 minutes)

Wait until the one-minute email interval is due. The scheduler checks every 30 seconds. To trigger the due sweep immediately after the minute has elapsed:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/v1/compliance/sla_sweep" |
  ConvertTo-Json -Depth 8
```

Open the RM Gmail inbox and show the escalation email.

Point out:

- RM and SLM are in **To**.
- Employee and HR are in **CC**.
- Employee details, policy, period, present days, and required days are shown.
- The subject carries a unique `RTO-ID` for correlation.

If the message does not arrive, check Terminal 1 for `EMAIL_FAILED`, verify the Gmail App Password, and confirm the interval is due.

## Scene 5 — Resolve through email and show Teams synchronization (1–2 minutes)

From the assigned RM account `pandahai477@gmail.com`, reply in the same thread with:

```text
I discussed this with Abhishek. He was on an approved client visit from 6 July to 10 July 2026 and worked from the client location. Approval reference: CLIENT-TRAVEL-4821. Please treat this as an approved business exception.
```

Wait up to the configured poll interval plus model processing time (normally 10–30 seconds).

Show:

1. The validation response in the same email thread.
2. The Teams channel bot message stating that the email justification was accepted.
3. The channel status marked resolved.

Verify through the API if useful:

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/violations?emp_sapid=E007" |
  ConvertTo-Json -Depth 8
```

Expected status: `RESET`.

Suggested narration:

> “The inbox poller correlates the reply to the violation, verifies that the sender is the assigned RM, and asks the mail validator to assess the justification. A satisfactory high-confidence result resets the case and publishes the resolution back into Teams.”

## Scene 6 — Demonstrate the reverse Teams-to-email path (optional, 1–2 minutes)

Run the E007 compliance check again to create a new cycle/channel:

```powershell
$body = @{ emp_sapid = "E007"; policy_type = "WEEKLY" } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/api/v1/compliance/check" `
  -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 8
```

In the newest RM Teams channel, submit:

```text
Discussed with Abhishek. The missing office days were due to approved client travel from 6 July to 10 July 2026. Approval reference: CLIENT-TRAVEL-4821.
```

Show:

- Teams bot accepts and resolves the case.
- RM, SLM, and HR receive the resolution email.

Suggested narration:

> “Resolution is bidirectional. A justification accepted in Teams closes the same violation and sends a resolution email to the stakeholders.”

## Scene 7 — Demonstrate the analytics chatbot (1–2 minutes)

Open the chatbot and sign in with:

```text
hr@example.com
```

Demonstrate these prompts:

1. Click **Show the last 5 violations**.
2. Ask: `Show the compliance history for Abhishek`.
3. Ask with a minor typo: `Show violations for Abhisek`.
4. Expand **SQL used** to show read-only query transparency.

Point out:

- Authorization is checked before querying.
- Partial and slightly misspelled employee names resolve to the unique SAP ID.
- Ambiguous names return up to five clickable employee choices.
- Generated SQL is restricted to `SELECT` operations.

Suggested narration:

> “Authorized HR and leadership users can ask natural-language questions. Employee references are resolved against the master data, ambiguous names become clickable choices, and every generated query remains read-only and auditable.”

## Scene 8 — Close (20–30 seconds)

Return to the dashboard or resolved Teams channel.

Suggested narration:

> “This completes the workflow from attendance detection through collaboration, timed escalation, AI-assisted validation, synchronized resolution, audit logging, and compliance analytics.”

---

## Quick recovery checklist

### No channel appears

- Confirm API health.
- Check Terminal 1 for an OpenAI or database error.
- Confirm `E007` exists and attendance is seeded.
- Refresh the Teams page and open the newest channel.

### No escalation email arrives

- Wait until `EMAIL_REMINDER_MINUTES` is due.
- Run `/api/v1/compliance/sla_sweep` manually.
- Confirm `GMAIL_USER` and `GMAIL_APP_PASSWORD`.
- Check spam and Terminal 1 for `EMAIL_FAILED`.

### Email reply is not processed

- Reply from the assigned RM address: `pandahai477@gmail.com`.
- Keep `RTO ESCALATION` and `RTO-ID` in the subject/thread.
- Confirm `GMAIL_IMAP_ENABLED=true`.
- Check Terminal 1 for `[Scheduler] Email polling error`.
- Allow at least one `EMAIL_POLL_SECONDS` interval.

### Chatbot cannot sign in

- Confirm seed data ran successfully.
- Use `hr@example.com`, `leadership@example.com`, or `admin@example.com`.
- Confirm Streamlit uses `http://localhost:8000/api/v1` as `API_BASE`.

### Start again cleanly

Stop the API and Streamlit, preserve `rto.db`, run initialization and seeding again, then restart both services.
