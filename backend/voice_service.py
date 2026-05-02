import os
import logging
from elevenlabs import ElevenLabs
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# Free premade voice - Sarah (clear, professional)
VOICE_ID = "EXAVITQu4vr4xnSDxMaL"

def generate_meeting_briefing(summary: str, action_items: list) -> bytes | None:
    """Generate full meeting audio briefing."""
    try:
        lines = ["Meeting Mind AI — Meeting Briefing."]
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

        audio = client.text_to_speech.convert(
            voice_id=VOICE_ID,
            text=script,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        audio_bytes = b"".join(audio)
        logger.info(f"✅ Briefing generated: {len(audio_bytes)} bytes")
        return audio_bytes

    except Exception as e:
        logger.error(f"ElevenLabs briefing error: {e}")
        return None
