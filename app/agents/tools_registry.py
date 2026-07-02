"""Shared tool registry — swap chat_tool <-> teams_tool here only."""
import os
from app.tools import chat_tool as slack_tool  # drop-in replacement for Slack/Teams
from app.tools.attendance import get_attendance_summary
from app.tools.violation import create_violation, reset_violation, update_violation_channel, get_open_violations
from app.tools.email_tool import send_escalation_email
from app.tools.query import run_safe_query

__all__ = [
    "slack_tool",
    "get_attendance_summary",
    "create_violation",
    "reset_violation",
    "update_violation_channel",
    "get_open_violations",
    "send_escalation_email",
    "run_safe_query",
]
