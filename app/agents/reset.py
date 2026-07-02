"""Reset Agent — closes a violation and marks channel resolved."""
from app.tools.violation import reset_violation
from app.tools.chat_tool import mark_channel_resolved


async def run_reset(violation_id: int, channel_ref: str = None) -> dict:
    result = reset_violation(violation_id, channel_ref)
    if channel_ref:
        mark_channel_resolved(channel_ref)
    return result
