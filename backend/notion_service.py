import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def create_notion_meeting_page(summary: str, action_items: list, source: str = "upload") -> bool:
    """Create a meeting summary page in Notion database."""
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        logger.warning("Notion not configured, skipping.")
        return False

    try:
        # Build action items text
        actions_text = ""
        for i, item in enumerate(action_items, 1):
            assignee = item.get("assignee", "Team")
            task = item.get("task", "")
            deadline = item.get("deadline", "No deadline")
            priority = item.get("priority", "medium").upper()
            actions_text += f"{i}. [{priority}] {assignee}: {task} (Due: {deadline})\n"

        if not actions_text:
            actions_text = "No action items identified."

        # Create Notion page
        payload = {
            "parent": {"database_id": NOTION_DATABASE_ID},
            "properties": {
                "Name": {
                    "title": [{"text": {"content": f"Meeting Summary — {source}"}}]
                },
            },
            "children": [
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "📝 Summary"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": summary or "No summary available."}}]
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "✅ Action Items"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": actions_text}}]
                    }
                },
            ]
        }

        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers=HEADERS,
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            logger.info("✅ Notion page created successfully")
            return True
        else:
            logger.error(f"Notion error: {response.status_code} — {response.text}")
            return False

    except Exception as e:
        logger.error(f"Notion unexpected error: {e}")
        return False
