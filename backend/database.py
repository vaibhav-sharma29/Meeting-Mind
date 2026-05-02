"""Simple JSON-based meeting history storage."""
import json
import os
from datetime import datetime

DB_FILE = "meetings_history.json"


def _load() -> list:
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: list):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_meeting(transcript: str, summary: str, action_items: list, actions_taken: list, source: str = "upload") -> dict:
    meetings = _load()
    meeting = {
        "id": len(meetings) + 1,
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "transcript": transcript,
        "summary": summary,
        "action_items": action_items,
        "actions_taken": actions_taken,
    }
    meetings.append(meeting)
    _save(meetings)
    return meeting


def get_all_meetings() -> list:
    return _load()


def get_meeting_by_id(meeting_id: int) -> dict:
    for m in _load():
        if m["id"] == meeting_id:
            return m
    return None


def get_pending_tasks() -> list:
    """Return all action items from past meetings that are still pending."""
    meetings = _load()
    pending = []
    for m in meetings:
        for item in m.get("action_items", []):
            pending.append({
                "meeting_id": m["id"],
                "meeting_date": m["timestamp"][:10],
                "assignee": item.get("assignee", "Team"),
                "task": item.get("task", ""),
                "deadline": item.get("deadline"),
                "priority": item.get("priority", "medium"),
            })
    return pending
