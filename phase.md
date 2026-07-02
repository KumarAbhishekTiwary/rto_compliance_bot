# 🚀 Phased Implementation Guide
 
This document walks you through each phase. Follow them in order.
 
> **What changed in v2:**
> - ✨ Replaced Slack with a custom **Teams-like in-app chat UI** (no external API needed)
> - 🔐 Added corporate proxy + SSL certificate handling
> - 🪟 Added Windows-specific command syntax
> - 🐛 Added fixes for common issues (UTF-8 encoding, OpenAI tracing noise)
 
---
 
## ✅ PHASE 1 — Project Setup + Database (1 hour)
 
### Goal
Get the project skeleton + SQLite DB with seed data working.
 
### Steps
 
**Linux / Mac:**
```bash
cd rto_compliance_bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/init_db.py
python scripts/seed_data.py
python tests/test_compliance.py
```
 
**Windows (CMD / PowerShell):**
```cmd
cd rto_compliance_bot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts\init_db.py
python scripts\seed_data.py
python tests\test_compliance.py
```
 
### Database Schema (8 tables total)
 
The DB now has **8 tables** — including 3 new ones for the in-app chat:
 
| Table | Purpose |
|---|---|
| `employees` | Master employee data + policy |
| `attendance` | Daily attendance records |
| `violations` | Non-compliance tracking |
| `communication_log` | All inbound/outbound messages |
| `audit_log` | Immutable audit trail |
| `authorized_users` | Chatbot access control |
| **`channels`** 🆕 | In-app chat channels (Teams replacement) |
| **`channel_members`** 🆕 | Channel membership (Employee + RM + SLM + Bot) |
| **`messages`** 🆕 | All chat messages with verdict metadata |
 
### Expected Output
```
✅ Database initialized at: rto.db
✅ Seeded 6 employees
✅ Seeded attendance for 6 employees (last 35 days)
✅ Seeded 3 authorized users
✅ Lifecycle test passed
✅ SQL safety test passed
🎉 All smoke tests passed!
```
 
### What you have now
- SQLite DB with 6 sample employees (Alice, Bob, Carol, David, Eve, Frank)
- ~25 days of attendance per employee (some compliant, some not)
- 3 authorized users (HR, Leadership, Admin)
- Tables ready for the in-app Teams-like chat
 
---

## ✅ PHASE 2 — Core Tools (3 hours)
 
### Goal
Verify each tool works standalone.
 
### Built (in `app/tools/`)
| Tool | Purpose |
|---|---|
| `attendance.py` | Fetch attendance + compute compliance |
| **`chat_tool.py`** 🆕 | **In-app chat** (replaces Slack/Teams entirely) |
| `email_tool.py` | Send SMTP emails (Outlook replacement) |
| `violation.py` | Create / reset violations + audit |
| `query.py` | Safe SELECT-only SQL execution |
 
### 🆕 In-App Chat Tool — Key Functions
 
`chat_tool.py` exposes the same `safe_create_channel()` interface as `slack_tool.py`, so **no agent code changes are needed**:
 
| Function | Purpose |
|---|---|
| `safe_create_channel()` | Creates channel + adds Employee + RM + SLM + Bot + posts notice |
| `post_message()` | Post a new message in a channel |
| `get_channel_messages()` | Fetch all messages in a channel |
| `list_channels_for_user()` | List channels user is a member of (for sidebar) |
| `mark_channel_resolved()` | Mark channel RESOLVED when violation is RESET |
 
### Activate the Chat Tool
 
Edit `app/agents/tools_registry.py` and change **one import line**:
```python
# Before:
from app.tools import slack_tool
 
# After:
from app.tools import chat_tool as slack_tool   # drop-in replacement
```
 
### Gmail Setup (Optional - Phase 2 works in mock mode without it)
 
1. Enable 2FA: https://myaccount.google.com/security
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Paste into `.env`:
   ```
   GMAIL_USER=your.email@gmail.com
   GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
   ```
 
### Test the Chat Tool
```bash
python -c "
from app.tools.chat_tool import safe_create_channel
r = safe_create_channel(
    emp_email='bob@example.com',
    rm_email='rm1@example.com',
    slm_email='slm1@example.com',
    emp_name='Bob Smith',
    violation_summary='Test violation notice'
)
print(r)
"
```
 
You should see a channel created in the DB with all members invited.
 
---

## ✅ PHASE 3 — Agents using OpenAI Agents SDK (4 hours)
 
### Goal
Wire the 7 agents using the OpenAI Agents SDK.
 
### Setup
1. Get OpenAI API key: https://platform.openai.com/api-keys
2. Add to `.env`:
   ```
   OPENAI_API_KEY=sk-...
   OPENAI_MODEL=gpt-4o-mini
   ```
 
### 🔐 Corporate Proxy + SSL Setup (NEW - REQUIRED for JNJ/corporate networks)
 
If you're behind a corporate proxy (ZScaler/BlueCoat), OpenAI calls will fail with `SSL: CERTIFICATE_VERIFY_FAILED`. Follow these steps:
 
#### Step 1: Add to `.env`
```bash
# Corporate proxy (replace with your actual proxy URL)
HTTPS_PROXY=http://proxy.jnj.com:8080
HTTP_PROXY=http://proxy.jnj.com:8080
NO_PROXY=localhost,127.0.0.1
 
# Dev mode: disable SSL verification (NOT for production)
DISABLE_SSL_VERIFY=true
 
# OR (production-grade): point to corporate CA bundle
# REQUESTS_CA_BUNDLE=C:\path\to\jnj_ca_bundle.pem
```
 
#### Step 2: Create `app/agents/openai_client.py`
```python
"""OpenAI client configured for corporate proxy + SSL."""
import os
import ssl
import httpx
from openai import AsyncOpenAI
from agents import set_default_openai_client, set_tracing_disabled
 
# Disable tracing (stops [non-fatal] Tracing: ... noise)
set_tracing_disabled(True)
 
DISABLE_SSL = os.getenv("DISABLE_SSL_VERIFY", "false").lower() == "true"
CA_BUNDLE = os.getenv("REQUESTS_CA_BUNDLE") or os.getenv("SSL_CERT_FILE")
PROXY = os.getenv("HTTPS_PROXY")
 
if CA_BUNDLE and os.path.exists(CA_BUNDLE):
    verify_setting = ssl.create_default_context(cafile=CA_BUNDLE)
    print(f"✅ Using corporate CA bundle: {CA_BUNDLE}")
elif DISABLE_SSL:
    verify_setting = False
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    print("⚠️  SSL verification DISABLED (dev mode)")
else:
    verify_setting = True
 
http_client = httpx.AsyncClient(
    verify=verify_setting,
    timeout=60.0,
    proxy=PROXY,
)
 
custom_openai = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    http_client=http_client,
)
set_default_openai_client(custom_openai)
print(f"✅ OpenAI client configured (proxy: {PROXY or 'none'})")
```
 
#### Step 3: Import at TOP of `app/api/main.py`
```python
# CRITICAL: must be first to configure SSL/proxy before agents
from app.agents import openai_client  # noqa: F401
 
from fastapi import FastAPI
# ... rest of imports
```
 
### Built (in `app/agents/`)
| Agent | File | Purpose |
|---|---|---|
| Retrieval Agent | `retrieval.py` | Fetch attendance |
| Meeting Planner | `meeting_planner.py` | Create in-app channel (was Slack) |
| Chat Validator | `chat_validator.py` | LLM judges RM reply |
| Email Planner | `email_planner.py` | Send escalation email |
| Mail Validator | `mail_validator.py` | LLM judges email reply |
| Reset Agent | `reset.py` | Close violation |
| Query Agent | `query.py` | NL→SQL for chatbot |
| Orchestrator | `orchestrator.py` | End-to-end pipeline |
| **OpenAI Client** 🆕 | `openai_client.py` | Proxy/SSL configuration |
 
### Test the full pipeline
```bash
python -c "
import asyncio
from app.agents.orchestrator import run_compliance_check
result = asyncio.run(run_compliance_check('E002', 'WEEKLY'))
print(result)
"
```
 
### Expected Output
```
✅ SSL verification DISABLED (dev mode)
✅ OpenAI client configured (proxy: http://proxy.jnj.com:8080)
✅ Channel CH-ABC123 created for Bob Smith
   Members: bob@example.com, rm1@example.com, slm1@example.com
{'emp_sapid': 'E002', 'status': 'VIOLATION_OPENED', ...}
```
 
---

## ✅ PHASE 4 — FastAPI Backend + Scheduler + Chat API (3 hours)
 
### Goal
HTTP endpoints + auto-scheduling + chat backend.
 
### Built (in `app/api/`)
- `main.py` - FastAPI app with lifespan management (now imports `openai_client` first)
- `routers/compliance.py` - `/compliance/check`, `/violations`, `/sla_sweep`
- `routers/chatbot.py` - `/chatbot/query`
- `routers/webhooks.py` - `/webhooks/email_reply`
- **`routers/chat.py`** 🆕 - **In-app chat backend**
- `scheduler.py` - APScheduler cron jobs
 
### 🆕 New Chat Endpoints
| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/chat` | GET | Serves the Teams-like HTML UI |
| `/api/v1/chat/users` | GET | List all users (for login picker) |
| `/api/v1/chat/channels?user_email=X` | GET | List channels for user (sidebar) |
| `/api/v1/chat/channels/{id}/messages` | GET | Fetch messages |
| `/api/v1/chat/channels/{id}/info` | GET | Channel + members + violation |
| `/api/v1/chat/send` | POST | Send a message (triggers Chat Validator async) |
 
### Register the Chat Router
 
Edit `app/api/main.py`:
```python
from app.api.routers import compliance, chatbot, webhooks, chat  # ← add chat
 
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])  # ← add line
```
 
### Run
```bash
uvicorn app.api.main:app --reload --port 8000
```
 
### Test endpoints
 
**Windows CMD** (note the escaped quotes):
```cmd
curl -X POST http://localhost:8000/api/v1/compliance/check -H "Content-Type: application/json" -d "{\"emp_sapid\":\"E002\",\"policy_type\":\"WEEKLY\"}"
```
 
**PowerShell**:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/compliance/check" `
  -Method POST -ContentType "application/json" `
  -Body '{"emp_sapid":"E002","policy_type":"WEEKLY"}'
```
 
**Linux / Mac**:
```bash
curl -X POST http://localhost:8000/api/v1/compliance/check \
  -H "Content-Type: application/json" \
  -d '{"emp_sapid":"E002","policy_type":"WEEKLY"}'
```
 
**Easiest: Use Swagger UI** → http://localhost:8000/docs
 
### Scheduler
Automatically starts when FastAPI starts:
```
✅ Scheduler started: weekly (Mon 06:00), monthly (1st 06:00), SLA hourly
```
 
### Open API Docs
http://localhost:8000/docs (Swagger UI auto-generated)
 
---

## ✅ PHASE 5 — Custom Teams-Like Chat UI + Streamlit Chatbot (3 hours)
 
### Goal
Two complementary UIs:
1. **Teams-like chat** for Employees/RMs/SLMs to interact with violations
2. **Streamlit chatbot** for HR/Leadership to query data
 
### 5A. 🆕 Teams-Like Chat UI
 
#### File
- `app/ui/chat_ui.html` — Single-page HTML/CSS/JS (no build step)
 
#### Access
**http://localhost:8000/api/v1/chat**
 
#### Features
| Feature | Detail |
|---|---|
| **Login modal** | Pick from Employee / RM / SLM / HR users |
| **Sidebar** | Lists all channels user is a member of |
| **Channel status badges** | `ACTIVE` (yellow) / `RESOLVED` (green) |
| **Chat panel** | Teams-style bubbles with role-colored avatars |
| **Violation banner** | Shows current compliance status at top |
| **Composer** | Enter to send, Shift+Enter for newline |
| **2-second polling** | Real-time feel without WebSockets |
| **Auto-bot verdict** | When RM sends a message, Chat Validator runs in background and bot posts verdict |
 
#### Color Coding
| Role | Avatar Color |
|---|---|
| Employee | 🟠 Orange |
| RM | 🔵 Blue |
| SLM | 🟣 Purple |
| HR | 🟢 Teal |
| Bot | 🟣 Teams-purple |
 
#### ⚠️ Windows UTF-8 Fix
The HTML file contains emojis that crash on Windows default `cp1252` encoding. The fix is already applied in `chat.py`:
```python
return HTMLResponse(html_path.read_text(encoding="utf-8"))
```
 
Or even better — use `FileResponse`:
```python
from fastapi.responses import FileResponse
return FileResponse(html_path, media_type="text/html")
```
 
#### Demo Flow
1. Open http://localhost:8000/api/v1/chat in **3 browser tabs**
2. **Tab A**: Sign in as `bob@example.com` (Employee)
3. **Tab B**: Sign in as `rm1@example.com` (RM)
4. **Tab C**: Sign in as `slm1@example.com` (SLM)
5. Trigger compliance check for E002 via Swagger UI
6. **All 3 tabs see the new channel appear** with bot's violation notice
7. **As RM (Tab B)**, type:
   > *"Discussed with Bob — was on approved client visit to NY. Ticket ABC-123."*
8. Bot validates within ~5s → posts ✅ SATISFACTORY → violation marked RESET
9. **Violation banner turns green** in all 3 tabs
 
### 5B. Streamlit Chatbot UI (for HR/Leadership)
 
#### Run
```bash
streamlit run app/ui/chatbot_app.py
```
 
#### Test
1. Open http://localhost:8501
2. Enter authorized email: `hr@example.com`
3. Try:
   - *"How many employees on WEEKLY policy?"*
   - *"Show me the last 5 violations"*
   - *"Show all violations of Alice"*
   - *"Which violations are currently OPEN?"*
 
#### Expected behavior
- ✅ Authorized email → answers + SQL shown
- ❌ Unauthorized email → blocked with 403
 
---
 
## ✅ PHASE 6 — Testing + Demo + Migration Prep (2 hours)
 
### Goal
End-to-end demo + plan for swapping in-app chat → Teams + SMTP → Outlook.
 
### End-to-End Demo Script
 
#### Linux / Mac:
```bash
# 1. Reset
rm rto.db
python scripts/init_db.py
python scripts/seed_data.py
 
# 2. Run backend
uvicorn app.api.main:app --reload --port 8000 &
 
# 3. Open chat UI in 3 browser tabs:
#    - Tab A: Login as Bob (Employee)
#    - Tab B: Login as RM1
#    - Tab C: Login as SLM1
open http://localhost:8000/api/v1/chat
 
# 4. Trigger compliance check for non-compliant E002
curl -X POST http://localhost:8000/api/v1/compliance/check \
  -H "Content-Type: application/json" \
  -d '{"emp_sapid":"E002","policy_type":"WEEKLY"}'
```
 
#### Windows CMD:
```cmd
:: 1. Reset
del rto.db
python scripts\init_db.py
python scripts\seed_data.py
 
:: 2. Run backend
start uvicorn app.api.main:app --reload --port 8000
 
:: 3. Open chat UI in 3 browser tabs:
start http://localhost:8000/api/v1/chat
 
:: 4. Trigger compliance check
curl -X POST http://localhost:8000/api/v1/compliance/check -H "Content-Type: application/json" -d "{\"emp_sapid\":\"E002\",\"policy_type\":\"WEEKLY\"}"
```
 
### Manual Test Steps in the UI
 
5. **As RM (Tab B)**, type a **good** justification:
   > *"Discussed with Bob, he was on approved client visit. JIRA: ABC-123"*
   - Bot posts SATISFACTORY verdict → violation RESET → banner turns green ✅
 
6. **Trigger another check** for E004 (Carol, MONTHLY policy)
 
7. **As RM (Tab B)**, type a **bad** justification:
   > *"ok will check"*
   - Bot posts UNSATISFACTORY verdict → asks for more details
 
8. **Verify in DB**:
```bash
curl http://localhost:8000/api/v1/violations
```
 
### Migration Plan: In-App Chat → Teams + SMTP → Outlook
 
When MS Graph API access is available, swap **two files only**:
 
**`app/tools/chat_tool.py`** → rename to `teams_tool.py`, replace internals:
```python
import httpx
from app.config import settings
 
TEAMS_BASE = "https://graph.microsoft.com/v1.0"
 
async def create_compliance_channel(emp_email, rm_email, slm_email, emp_name, summary):
    token = settings.GRAPH_TOKEN  # from Azure AD
    async with httpx.AsyncClient() as client:
        chat = await client.post(
            f"{TEAMS_BASE}/chats",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "chatType": "group",
                "members": [
                    {"@odata.type":"#microsoft.graph.aadUserConversationMember",
                     "roles":["owner"], "user@odata.bind":f"...{email}"}
                    for email in [emp_email, rm_email, slm_email]
                ]
            }
        )
        chat_id = chat.json()["id"]
        msg = await client.post(
            f"{TEAMS_BASE}/chats/{chat_id}/messages",
            headers={"Authorization": f"Bearer {token}"},
            json={"body":{"content":summary, "contentType":"html"}}
        )
        return {
            "slack_channel_id": chat_id,  # keep same key for compatibility
            "channel_id": chat_id,
            "message_ts": msg.json()["id"],
            "members_invited": [emp_email, rm_email, slm_email],
        }
 
def safe_create_channel(*args, **kwargs):
    import asyncio
    return asyncio.run(create_compliance_channel(*args, **kwargs))
```
 
**`app/tools/email_tool.py`** → swap SMTP for Graph:
```python
async def send_escalation_email(to, cc, subject, html_body):
    token = settings.GRAPH_TOKEN
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TEAMS_BASE}/me/sendMail",
            headers={"Authorization": f"Bearer {token}"},
            json={"message":{
                "subject": subject,
                "body": {"contentType":"HTML", "content": html_body},
                "toRecipients":[{"emailAddress":{"address":e}} for e in to],
                "ccRecipients":[{"emailAddress":{"address":e}} for e in cc],
            }}
        )
```
 
**Then update import in `app/agents/tools_registry.py`:**
```python
# Toggle between in-app chat and real Teams via config flag
from app.config import settings
if settings.USE_TEAMS:
    from app.tools import teams_tool as slack_tool
else:
    from app.tools import chat_tool as slack_tool
```
 
**Zero changes** needed in agents, orchestrator, or scheduler — same function signatures.
 
### 💡 Hybrid Approach (Recommended)
Keep the in-app chat as an alternative even after Teams integration:
- **Internal users** (employees, RMs) → real Teams
- **Demo / training / contractors** → in-app chat
- **Failover** → if Teams is down, use in-app
 
---
 
## 🎯 Production Readiness Checklist
 
### Infrastructure
- [ ] Replace SQLite with PostgreSQL (for > 1000 employees)
- [ ] Move secrets from `.env` to Azure Key Vault
- [ ] Containerize with Docker
- [ ] Add Application Insights / OpenTelemetry tracing
 
### Security
- [ ] Add Azure AD SSO for both UIs (chat + chatbot)
- [ ] Replace `DISABLE_SSL_VERIFY=true` with proper corporate CA bundle
- [ ] Add rate limiting on `/chat/send` endpoint
- [ ] Add CSRF tokens on form posts
 
### Features
- [ ] Add admin UI for managing employees + authorized users
- [ ] Add WebSocket support for real-time chat (replace 2s polling)
- [ ] Add browser push notifications
- [ ] Add file attachments in chat (proof of approval)
- [ ] Add L4 escalation tier (when needed)
- [ ] Add Prometheus metrics endpoint
 
### Observability
- [ ] Add retry logic for Graph API rate limits
- [ ] Add dashboard for compliance trends
- [ ] Add SLA monitoring alerts
 
---
 
## 🆘 Troubleshooting
 
### General Issues
| Issue | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'agents'` | `pip install openai-agents` |
| `OPENAI_API_KEY not set` | Add to `.env` and restart server |
| Streamlit can't connect | Make sure FastAPI is on :8000 first |
| Scheduler doesn't trigger | Check timezone; jobs use system TZ |
| LLM returns wrong verdict | Tune prompt in `chat_validator.py` |
 
### 🪟 Windows-Specific Issues
| Issue | Fix |
|---|---|
| `UnicodeDecodeError: charmap codec can't decode byte 0x8f` | Use `read_text(encoding="utf-8")` or switch to `FileResponse` |
| `curl: (3) URL rejected: Bad hostname` | Use Windows curl syntax with `\"` instead of `'` |
| Multi-line `\` doesn't work | Use `^` in CMD or `` ` `` in PowerShell |
| `Bad request - JSON decode error` | Check JSON quotes are properly escaped |
 
### 🔐 Corporate Proxy / SSL Issues
| Issue | Fix |
|---|---|
| `SSL: CERTIFICATE_VERIFY_FAILED` | Set `DISABLE_SSL_VERIFY=true` in `.env` (dev only) |
| `[non-fatal] Tracing: request failed` | Add `set_tracing_disabled(True)` in `openai_client.py` |
| `Connection refused` | Verify proxy URL with `netsh winhttp show proxy` |
| `407 Proxy Authentication Required` | Use `http://user:pass@proxy:8080` |
| Connection timeout | Wrong proxy URL — check with IT |
 
### 💬 Chat UI Issues
| Issue | Fix |
|---|---|
| 500 error on `/api/v1/chat` | UTF-8 encoding fix (see Phase 5A) |
| Empty channel list | Trigger a compliance check first |
| Bot doesn't respond to messages | Check OPENAI_API_KEY + proxy/SSL config |
| Channel doesn't update | Hard refresh browser (Ctrl+Shift+R) |
| `404 chat_ui.html not found` | Verify path: `app/ui/chat_ui.html` |
| Verdict never appears | Check FastAPI logs for `validate_chat_reply` errors |
 
---
 
## 📚 Architecture Reference
 
For full architecture documentation, see:
- `RTO_Compliance_Bot_Architecture.docx` (technical doc)
- `RTO_Compliance_Bot_Architecture.drawio` (visual diagram)
 
---
 
## 🎬 Quick Demo Cheat Sheet
 
```
┌─────────────────────────────────────────────────────────────┐
│  1. Start backend:    uvicorn app.api.main:app --reload     │
│  2. Open Swagger:     http://localhost:8000/docs            │
│  3. Open chat UI:     http://localhost:8000/api/v1/chat     │
│  4. Open chatbot:     streamlit run app/ui/chatbot_app.py   │
│                       (port 8501)                            │
│                                                              │
│  Trigger check for E002 (non-compliant Bob)                 │
│   → Channel auto-created with Bob + RM + SLM + Bot          │
│   → Bot posts violation notice                              │
│   → RM replies with justification                           │
│   → LLM validates → posts verdict                           │
│   → Violation marked RESET (if SATISFACTORY)                │
└─────────────────────────────────────────────────────────────┘
```
 
---
 
## 📦 File Structure (Updated)
 
```
rto_compliance_bot/
├── .env                          # secrets + proxy + SSL config
├── requirements.txt
├── PHASES.md                     # this file
├── rto.db                        # SQLite (8 tables)
│
├── app/
│   ├── config.py
│   ├── db/
│   │   ├── schema.sql            # Now includes channels/members/messages
│   │   └── database.py
│   ├── tools/
│   │   ├── attendance.py
│   │   ├── chat_tool.py          # 🆕 In-app chat (Teams replacement)
│   │   ├── email_tool.py
│   │   ├── violation.py
│   │   └── query.py
│   ├── agents/
│   │   ├── openai_client.py      # 🆕 Proxy/SSL config (LOAD FIRST!)
│   │   ├── retrieval.py
│   │   ├── meeting_planner.py
│   │   ├── chat_validator.py
│   │   ├── email_planner.py
│   │   ├── mail_validator.py
│   │   ├── reset.py
│   │   ├── query.py
│   │   ├── orchestrator.py
│   │   └── tools_registry.py     # Updated to use chat_tool
│   ├── api/
│   │   ├── main.py               # Imports openai_client FIRST
│   │   ├── routers/
│   │   │   ├── compliance.py
│   │   │   ├── chatbot.py
│   │   │   ├── webhooks.py
│   │   │   └── chat.py           # 🆕 In-app chat endpoints
│   │   └── scheduler.py
│   └── ui/
│       ├── chatbot_app.py        # Streamlit (HR queries)
│       └── chat_ui.html          # 🆕 Teams-like chat UI
│
├── scripts/
│   ├── init_db.py
│   ├── seed_data.py
│   └── run_local.sh
│
└── tests/
    └── test_compliance.py
 
