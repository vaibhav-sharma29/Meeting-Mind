"""ElevenLabs voice generation — Meeting Briefing + Per-Person Voice Alerts."""
import os
import logging
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

load_dotenv()
logger = logging.getLogger(__name__)

# Professional voices
BRIEFING_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"   # Rachel — clear professional English
ALERT_VOICE_ID    = "AZnzlk1XvdvUeBnXmlld"   # Domi — energetic, good for alerts

VOICE_SETTINGS = VoiceSettings(
    stability=0.55,
    similarity_boost=0.75,
    style=0.0,
    use_speaker_boost=True,
)


def _get_client():
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        logger.warning("ElevenLabs API key not set")
        return None
    return ElevenLabs(api_key=api_key)


def _generate_audio(client, text: str, voice_id: str) -> bytes | None:
    """Generate audio bytes from text."""
    try:
        # Trim to safe limit
        if len(text) > 2500:
            text = text[:2500]

        audio = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_turbo_v2",
            voice_settings=VOICE_SETTINGS,
        )
        return b"".join(audio)
    except Exception as e:
        logger.error(f"ElevenLabs TTS error: {e}")
        return None


# ── 1. Full Meeting Voice Briefing ────────────────────────────────────────────

def build_briefing_text(meeting_data: dict) -> str:
    """Build a natural, professional spoken briefing from meeting data."""
    summary    = meeting_data.get("summary", "")
    items      = meeting_data.get("action_items", [])
    risks      = meeting_data.get("risks", [])
    score      = meeting_data.get("effectiveness_score", 5)
    sentiment  = meeting_data.get("sentiment", "neutral")

    lines = [
        "Hello! Here is your MeetingMind AI briefing.",
        f"This meeting scored {score} out of 10 for effectiveness, with a {sentiment} overall sentiment.",
        f"Summary: {summary}",
    ]

    if items:
        lines.append(f"There are {len(items)} action items from this meeting.")
        for i, item in enumerate(items, 1):
            assignee = item.get("assignee", "Team")
            task     = item.get("task", "")
            deadline = item.get("deadline")
            priority = item.get("priority", "medium")
            deadline_str = f"by {deadline}" if deadline else "with no specific deadline"
            lines.append(
                f"Item {i}: {assignee} is responsible for — {task}, {deadline_str}. Priority is {priority}."
            )

    if risks:
        lines.append(f"Risks and blockers to watch: {'. '.join(risks)}.")

    lines.append("That's all for this meeting. Stay productive!")
    return " ".join(lines)


def generate_voice_summary(meeting_data: dict) -> bytes | None:
    client = _get_client()
    if not client:
        return None
    text = build_briefing_text(meeting_data)
    logger.info("Generating meeting voice briefing...")
    return _generate_audio(client, text, BRIEFING_VOICE_ID)


def save_voice_summary(meeting_data: dict, meeting_id: int) -> str | None:
    """Generate and save the full meeting voice briefing."""
    audio = generate_voice_summary(meeting_data)
    if not audio:
        return None
    os.makedirs("generated_files", exist_ok=True)
    filepath = f"generated_files/voice_summary_{meeting_id}.mp3"
    with open(filepath, "wb") as f:
        f.write(audio)
    logger.info(f"Voice briefing saved: {filepath}")
    return filepath


# ── 2. Per-Person Voice Alert ─────────────────────────────────────────────────

def build_personal_alert_text(assignee: str, task: str, deadline: str | None, priority: str) -> str:
    """Build a personal voice alert for one assignee."""
    deadline_str = f"by {deadline}" if deadline else "as soon as possible"
    priority_phrase = {
        "high":   "This is a high priority task — please treat it urgently.",
        "medium": "This is a medium priority task.",
        "low":    "This is a low priority task, but please don't forget it.",
    }.get(priority, "")

    return (
        f"Hey {assignee}! This is your MeetingMind AI action alert. "
        f"You have been assigned a task from the recent meeting. "
        f"Your task is: {task}. "
        f"Please complete this {deadline_str}. "
        f"{priority_phrase} "
        f"Good luck, and have a great day!"
    )


def generate_personal_voice_alert(assignee: str, task: str, deadline: str | None, priority: str) -> bytes | None:
    """Generate a personal voice alert audio for one person."""
    client = _get_client()
    if not client:
        return None
    text = build_personal_alert_text(assignee, task, deadline, priority)
    logger.info(f"Generating voice alert for {assignee}...")
    return _generate_audio(client, text, ALERT_VOICE_ID)


def save_personal_voice_alert(assignee: str, task: str, deadline: str | None, priority: str, meeting_id: int, item_index: int) -> str | None:
    """Generate and save a personal voice alert, return file path."""
    audio = generate_personal_voice_alert(assignee, task, deadline, priority)
    if not audio:
        return None
    os.makedirs("generated_files", exist_ok=True)
    safe_name = assignee.replace(" ", "_").lower()
    filepath = f"generated_files/alert_{meeting_id}_{item_index}_{safe_name}.mp3"
    with open(filepath, "wb") as f:
        f.write(audio)
    logger.info(f"Voice alert saved: {filepath}")
    return filepath
