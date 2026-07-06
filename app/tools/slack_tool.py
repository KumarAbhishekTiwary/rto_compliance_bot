"""
Slack tool - replaces Microsoft Teams in Phase 1.
Creates private channels with Employee + RM + SLM and posts messages.
"""
from datetime import datetime
from app.config import settings

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    _slack_available = True
except ImportError:
    _slack_available = False

def _get_client():
    if not _slack_available:
        raise RuntimeError("slack_sdk not installed. Run: pip install slack-sdk")
    if not settings.SLACK_BOT_TOKEN:
        raise RuntimeError("SLACK_BOT_TOKEN not configured in .env")
    return WebClient(token=settings.SLACK_BOT_TOKEN)

def _lookup_user_id(client, email: str) -> str | None:
    """Resolve email → Slack user_id. Returns None if not found (e.g., demo emails)."""
    try:
        r = client.users_lookupByEmail(email=email)
        return r["user"]["id"]
    except SlackApiError:
        return None

def create_compliance_channel(emp_email: str, rm_email: str, slm_email: str,
                              emp_name: str, violation_summary: str) -> dict:
    """
    Create a private Slack channel and invite Employee + RM + SLM.
    Posts the initial violation notice.

    Returns: { slack_channel_id, message_ts, members_invited }
    """
    client = _get_client()

    # Channel name (Slack: lowercase, no spaces, max 80 chars)
    safe_name = emp_name.lower().replace(" ", "-").replace(".", "")[:40]
    channel_name = f"rto-{safe_name}-{datetime.now().strftime('%Y%m%d-%H%M')}"

    # Create private channel
    try:
        ch = client.conversations_create(name=channel_name, is_private=True)
        channel_id = ch["channel"]["id"]
    except SlackApiError as e:
        return {"error": f"Channel creation failed: {e.response['error']}"}

    # Invite users
    members_invited = []
    for email in [emp_email, rm_email, slm_email]:
        uid = _lookup_user_id(client, email)
        if uid:
            try:
                client.conversations_invite(channel=channel_id, users=uid)
                members_invited.append(email)
            except SlackApiError:
                pass

    # Post initial bot message
    msg_resp = client.chat_postMessage(
        channel=channel_id,
        text=violation_summary,
        blocks=[
            {"type": "header", "text": {"type": "plain_text", "text": "🏢 RTO Compliance Notice"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": violation_summary}},
            {"type": "divider"},
            {"type": "context", "elements": [
                {"type": "mrkdwn", "text": "_Reporting Manager: please reply here with discussion outcome / justification within 24 hours._"}
            ]}
        ]
    )

    return {
        "slack_channel_id": channel_id,
        "channel_name": channel_name,
        "message_ts": msg_resp["ts"],
        "members_invited": members_invited,
    }

def post_message(channel_id: str, text: str) -> dict:
    """Post a message to an existing channel."""
    client = _get_client()
    r = client.chat_postMessage(channel=channel_id, text=text)
    return {"channel_id": channel_id, "message_ts": r["ts"]}

def fetch_messages(channel_id: str, since_ts: str = None) -> list:
    """Fetch messages from a channel (for polling). Returns list of {user, text, ts}."""
    client = _get_client()
    params = {"channel": channel_id, "limit": 50}
    if since_ts:
        params["oldest"] = since_ts
    r = client.conversations_history(**params)
    return [
        {"user": m.get("user", "unknown"), "text": m.get("text", ""), "ts": m.get("ts")}
        for m in r.get("messages", [])
        if not m.get("bot_id")  # exclude bot's own messages
    ]

# ---------- MOCK MODE (when Slack not configured) ----------
def create_compliance_channel_mock(emp_email: str, rm_email: str, slm_email: str,
                                   emp_name: str, violation_summary: str) -> dict:
    """Mock implementation for testing without Slack."""
    print(f"\n[MOCK SLACK] Channel created for {emp_name}")
    print(f"  Members: {emp_email}, {rm_email}, {slm_email}")
    print(f"  Message: {violation_summary[:200]}...")
    return {
        "slack_channel_id": f"MOCK-{datetime.now().timestamp()}",
        "channel_name": f"mock-{emp_name.lower().replace(' ','-')}",
        "message_ts": str(datetime.now().timestamp()),
        "members_invited": [emp_email, rm_email, slm_email],
        "mock": True,
    }

def safe_create_channel(*args, **kwargs):
    """Auto-fallback to mock if Slack not configured."""
    if not settings.SLACK_BOT_TOKEN:
        return create_compliance_channel_mock(*args, **kwargs)
    return create_compliance_channel(*args, **kwargs)
