import os
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from calendar_service import create_calendar_event

load_dotenv()
logger = logging.getLogger(__name__)

slack_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN", ""))
CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "")


def take_actions(action_items: list) -> list:
    actions_taken = []

    if not action_items:
        return ["ℹ️ No action items to process."]

    for item in action_items:
        assignee = item.get("assignee", "Team")
        task     = item.get("task", "")
        deadline = item.get("deadline")
        priority = item.get("priority", "medium")

        if not task:
            continue

        # Slack notification
        slack_ok = send_slack_message(assignee, task, deadline, priority)
        if slack_ok:
            actions_taken.append(f"✅ Slack: Notified {assignee} — {task[:60]}")

        # Google Calendar event
        if deadline:
            try:
                cal_ok = create_calendar_event(assignee, task, deadline)
                if cal_ok:
                    actions_taken.append(f"✅ Calendar: Event created for {assignee} on {deadline}")
                else:
                    actions_taken.append(f"⚠️ Calendar: Could not create event for {assignee}")
            except Exception:
                pass

    return actions_taken


def send_slack_message(assignee: str, task: str, deadline: str, priority: str) -> bool:
    if not CHANNEL_ID or not os.getenv("SLACK_BOT_TOKEN"):
        logger.warning("Slack not configured, skipping.")
        return False

    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "🟡")
    deadline_str   = deadline or "Not specified"
    message = (
        f"{priority_emoji} *MeetingMind — Action Item*\n\n"
        f"👤 *Assignee:* {assignee}\n"
        f"📋 *Task:* {task}\n"
        f"📅 *Deadline:* {deadline_str}\n"
        f"⚡ *Priority:* {priority.upper()}\n\n"
        f"_Auto-captured by MeetingMind AI 🤖_"
    )

    try:
        slack_client.chat_postMessage(channel=CHANNEL_ID, text=message)
        logger.info(f"Slack message sent for {assignee}")
        return True
    except SlackApiError as e:
        logger.error(f"Slack error: {e.response['error']}")
        return False
    except Exception as e:
        logger.error(f"Slack unexpected error: {e}")
        return False
