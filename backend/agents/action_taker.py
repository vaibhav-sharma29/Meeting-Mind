import os
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from datetime import datetime, timedelta
from calendar_service import create_calendar_event
from notion_service import create_notion_task
from ppt_service import create_powerpoint, should_generate_ppt

load_dotenv()
logger = logging.getLogger(__name__)

def take_actions(action_items: list) -> list:
    actions_taken = []

    if not action_items:
        return ["ℹ️ No action items to process."]

    for item in action_items:
        assignee = item.get("assignee", "Team")
        task = item.get("task", "")
        deadline = item.get("deadline")
        priority = item.get("priority", "medium")

        if not task:
            continue

        # PPT Generation (if task involves presentation)
        if should_generate_ppt(task):
            ppt_path = create_powerpoint(assignee, task, deadline)
            if ppt_path:
                # Upload to Slack
                ppt_uploaded = upload_file_to_slack(ppt_path, assignee, task)
                if ppt_uploaded:
                    actions_taken.append(f"✅ PPT: Generated and sent to {assignee}")
                else:
                    actions_taken.append(f"⚠️ PPT: Generated but failed to send to {assignee}")
            else:
                actions_taken.append(f"⚠️ PPT: Failed to generate for {assignee}")

        # Slack notification
        slack_ok = send_slack_message(assignee, task, deadline, priority)
        if slack_ok:
            actions_taken.append(f"✅ Slack: Notified {assignee} — {task[:60]}")
        else:
            actions_taken.append(f"⚠️ Slack: Failed to notify {assignee}")

        # Notion task creation
        notion_ok = create_notion_task(assignee, task, deadline, priority)
        if notion_ok:
            actions_taken.append(f"✅ Notion: Task created for {assignee}")
        else:
            actions_taken.append(f"⚠️ Notion: Failed to create task for {assignee}")

        # Calendar event (only if deadline is set)
        if deadline:
            cal_ok = create_calendar_event(assignee, task, deadline)
            if cal_ok:
                actions_taken.append(f"✅ Calendar: Event created for {assignee} on {deadline}")
            else:
                actions_taken.append(f"⚠️ Calendar: Could not create event for {assignee}")

    return actions_taken

def upload_file_to_slack(file_path: str, assignee: str, task: str) -> bool:
    """Upload generated file to Slack."""
    token = os.getenv("SLACK_BOT_TOKEN")
    channel = os.getenv("SLACK_CHANNEL_ID")
    if not token or not channel:
        return False
    
    slack_client = WebClient(token=token)
    
    try:
        with open(file_path, "rb") as f:
            response = slack_client.files_upload_v2(
                channel=channel,
                file=f,
                filename=os.path.basename(file_path),
                title=f"PPT for {assignee}",
                initial_comment=f"🎨 **Auto-generated PPT for {assignee}**\n\n📝 Task: {task}\n🤖 Created by MeetingMind AI\n\n@{assignee} Your presentation is ready!"
            )
        logger.info(f"File uploaded to Slack: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Slack file upload failed: {e}")
        return False

def send_slack_message(assignee: str, task: str, deadline: str, priority: str) -> bool:
    token = os.getenv("SLACK_BOT_TOKEN")
    channel = os.getenv("SLACK_CHANNEL_ID")
    if not channel or not token:
        logger.warning("Slack not configured, skipping notification.")
        return False
    slack_client = WebClient(token=token)

    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "🟡")
    deadline_str = deadline or "Not specified / निर्धारित नहीं"
    message = (
        f"{priority_emoji} *MeetingMind — Action Item*\n\n"
        f"👤 *Assignee / जिम्मेदार:* {assignee}\n"
        f"📋 *Task / काम:* {task}\n"
        f"📅 *Deadline / समय सीमा:* {deadline_str}\n"
        f"⚡ *Priority / प्राथमिकता:* {priority.upper()}\n\n"
        f"_Auto-captured by MeetingMind AI 🤖_"
    )

    try:
        slack_client.chat_postMessage(channel=channel, text=message)
        logger.info(f"Slack message sent for {assignee}")
        return True
    except SlackApiError as e:
        logger.error(f"Slack error: {e.response['error']}")
        return False
    except Exception as e:
        logger.error(f"Slack unexpected error: {e}")
        return False