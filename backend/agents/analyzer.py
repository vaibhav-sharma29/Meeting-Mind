import os
import json
import time
import logging
from groq import Groq
from dotenv import load_dotenv
from database import get_pending_tasks

load_dotenv()
logger = logging.getLogger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def analyze_meeting(transcript: str) -> dict:
    if not transcript or len(transcript.strip()) < 10:
        return {"summary": "No meaningful content found.", "action_items": []}

    # Load past pending tasks for cross-meeting memory
    pending_tasks = get_pending_tasks()
    past_context = ""
    if pending_tasks:
        past_lines = []
        for t in pending_tasks[-10:]:  # last 10 tasks max
            past_lines.append(f"- [{t['meeting_date']}] {t['assignee']}: {t['task']} (deadline: {t['deadline'] or 'none'}, priority: {t['priority']})")
        past_context = "\n\nPrevious meetings pending tasks (use this to detect if someone is repeatedly missing tasks):\n" + "\n".join(past_lines)

    prompt = f"""You are an expert meeting analyst with memory of past meetings. The transcript may be in Hindi, English, or Hinglish (mixed).
Analyze the transcript and extract:

1. A concise summary in the SAME language as the transcript (2-3 lines)
2. Action items with assignee, task, and deadline
3. Meeting sentiment: overall mood (positive/negative/neutral)
4. Risks or blockers mentioned in the meeting
5. Meeting effectiveness score (1-10) with one line reason
6. Repeated misses: if someone had a pending task from a previous meeting and it came up again, flag it

Important:
- If transcript is in Hindi, write summary and tasks in Hindi
- If transcript is in English, write in English
- If mixed (Hinglish), use Hinglish
- Assignee names should be kept as-is from the transcript

Transcript:
{transcript}{past_context}

Return ONLY valid JSON in this exact format (no extra text):
{{
    "summary": "meeting summary here",
    "sentiment": "positive/negative/neutral",
    "effectiveness_score": 7,
    "effectiveness_reason": "one line reason",
    "risks": ["risk 1", "risk 2"],
    "repeated_misses": ["John missed landing page task again from last meeting"],
    "action_items": [
        {{
            "assignee": "person name",
            "task": "what they need to do",
            "deadline": "YYYY-MM-DD or null",
            "priority": "high/medium/low"
        }}
    ]
}}"""

    last_error = None
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1024,
            )
            text = response.choices[0].message.content.strip()

            # Strip markdown code fences if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            result = json.loads(text)

            # Validate structure
            if "summary" not in result:
                result["summary"] = "Meeting analyzed."
            if "action_items" not in result or not isinstance(result["action_items"], list):
                result["action_items"] = []
            result.setdefault("sentiment", "neutral")
            result.setdefault("risks", [])
            result.setdefault("effectiveness_score", 5)
            result.setdefault("effectiveness_reason", "")
            result.setdefault("repeated_misses", [])

            # Normalize each action item
            for item in result["action_items"]:
                item.setdefault("assignee", "Team")
                item.setdefault("task", "")
                item.setdefault("deadline", None)
                item.setdefault("priority", "medium")
                if item["deadline"] in ("null", "", "N/A", "None"):
                    item["deadline"] = None

            logger.info(f"✅ Found {len(result['action_items'])} action items")
            return result

        except json.JSONDecodeError as e:
            last_error = f"JSON parse error: {e}"
            logger.warning(f"Attempt {attempt+1}: {last_error}")
            time.sleep(1)
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Attempt {attempt+1}: Groq error: {e}")
            time.sleep(2)

    logger.error(f"All attempts failed: {last_error}")
    return {"summary": "Could not analyze meeting.", "action_items": [], "error": last_error}
