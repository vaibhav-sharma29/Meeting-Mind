import os
import io
import logging
from gtts import gTTS
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def generate_meeting_briefing(summary: str, action_items: list) -> bytes | None:
    """Generate full meeting audio briefing using gTTS."""
    try:
        lines = ["MeetingMind AI — Meeting Briefing."]
        lines.append(f"Summary: {summary}")

        if action_items:
            lines.append(f"There are {len(action_items)} action items from this meeting.")
            for i, item in enumerate(action_items, 1):
                assignee = item.get("assignee", "Team")
                task     = item.get("task", "")
                deadline = item.get("deadline")
                priority = item.get("priority", "medium")
                deadline_str = f"by {deadline}" if deadline else "no deadline set"
                lines.append(
                    f"Action item {i}: {assignee} needs to {task}. "
                    f"Priority is {priority}. Due {deadline_str}."
                )
        else:
            lines.append("No action items were identified in this meeting.")

        lines.append("End of briefing. Have a productive day!")
        script = " ".join(lines)

        # Detect language - use Hindi if Hindi text present
        lang = "hi" if any(ord(c) > 2304 and ord(c) < 2432 for c in script) else "en"

        buf = io.BytesIO()
        tts = gTTS(text=script, lang=lang, slow=False)
        tts.write_to_fp(buf)
        audio_bytes = buf.getvalue()

        logger.info(f"✅ Voice briefing generated: {len(audio_bytes)} bytes")
        return audio_bytes

    except Exception as e:
        logger.error(f"gTTS briefing error: {e}")
        return None
