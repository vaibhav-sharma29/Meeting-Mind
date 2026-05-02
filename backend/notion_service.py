"""Notion API service for task management."""
import os
import logging
import httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
NOTION_API_URL = "https://api.notion.com/v1"

def create_notion_task(assignee: str, task: str, deadline: str = None, priority: str = "medium", meeting_source: str = "MeetingMind") -> bool:
    """Create a task in Notion database."""
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        logger.warning("Notion not configured, skipping task creation.")
        return False

    # Format deadline for Notion
    deadline_obj = None
    if deadline:
        try:
            deadline_obj = {"start": deadline}
        except Exception:
            pass

    # Priority mapping
    priority_map = {"high": "High", "medium": "Medium", "low": "Low"}
    notion_priority = priority_map.get(priority.lower(), "Medium")

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": f"{assignee} - {task[:50]}"}}]
            },
            "Assignee": {
                "rich_text": [{"text": {"content": assignee}}]
            },
            "Task": {
                "rich_text": [{"text": {"content": task}}]
            },
            "Priority": {
                "select": {"name": notion_priority}
            },
            "Status": {
                "select": {"name": "To-Do"}
            },
            "Meeting Source": {
                "rich_text": [{"text": {"content": meeting_source}}]
            }
        }
    }

    if deadline_obj:
        payload["properties"]["Deadline"] = {"date": deadline_obj}

    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    try:
        response = httpx.post(
            f"{NOTION_API_URL}/pages",
            json=payload,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"Notion task created for {assignee}: {task[:30]}")
        return True
    except Exception as e:
        logger.error(f"Notion task creation failed: {e}")
        return False

def update_task_status(task_id: str, status: str) -> bool:
    """Update task status in Notion."""
    if not NOTION_TOKEN:
        return False

    payload = {
        "properties": {
            "Status": {"select": {"name": status}}
        }
    }

    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    try:
        response = httpx.patch(
            f"{NOTION_API_URL}/pages/{task_id}",
            json=payload,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Notion status update failed: {e}")
        return False