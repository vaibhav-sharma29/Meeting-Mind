"""
Zoom Local Recording Watcher
Zoom folder ko monitor karta hai — nai .m4a/.mp4 file aate hi
automatically MeetingMind pipeline chala deta hai.
"""
import os
import time
import httpx
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

ZOOM_FOLDER = os.getenv(
    "ZOOM_LOCAL_FOLDER",
    r"C:\Users\ak\OneDrive\Documents\Zoom"
)
API_URL = os.getenv("MEETINGMIND_API", "http://localhost:8000")
POLL_INTERVAL = 3  # seconds
AUDIO_EXTENSIONS = {".m4a", ".mp4", ".mp3", ".wav"}

def get_all_audio_files(folder: str) -> dict:
    """Return dict of {filepath: mtime} for all audio files."""
    result = {}
    for root, dirs, files in os.walk(folder):
        for f in files:
            if Path(f).suffix.lower() in AUDIO_EXTENSIONS:
                full = os.path.join(root, f)
                try:
                    result[full] = os.path.getmtime(full)
                except:
                    pass
    return result

def is_file_stable(filepath: str, wait: int = 5) -> bool:
    """Check if file size is stable (not still being written)."""
    try:
        size1 = os.path.getsize(filepath)
        time.sleep(wait)
        size2 = os.path.getsize(filepath)
        return size1 == size2 and size1 > 0
    except:
        return False

def process_recording(filepath: str):
    """Send recording to MeetingMind backend for processing."""
    filename = os.path.basename(filepath)
    folder_name = os.path.basename(os.path.dirname(filepath))
    logger.info(f"🎬 New recording detected: {filename}")
    logger.info(f"📁 Meeting folder: {folder_name}")

    # Wait for file to finish writing
    logger.info("⏳ Waiting for file to finish writing...")
    if not is_file_stable(filepath, wait=3):
        logger.warning("⚠️ File not stable, skipping.")
        return

    logger.info(f"🚀 Sending to MeetingMind: {filename}")
    try:
        with open(filepath, "rb") as f:
            ext = Path(filepath).suffix.lower()
            mime = "audio/mp4" if ext in (".m4a", ".mp4") else "audio/mpeg"
            res = httpx.post(
                f"{API_URL}/process-meeting",
                files={"audio": (filename, f, mime)},
                timeout=300,
            )
        data = res.json()
        if data.get("success"):
            logger.info(f"✅ Meeting processed! ID: {data.get('meeting_id')}")
            logger.info(f"📝 Summary: {data.get('summary', '')[:100]}")
        else:
            logger.error(f"❌ Processing failed: {data.get('error')}")
    except Exception as e:
        logger.error(f"❌ Error sending to backend: {e}")

def watch():
    logger.info(f"👀 Watching Zoom folder: {ZOOM_FOLDER}")
    logger.info(f"🔗 Backend: {API_URL}")
    logger.info("Waiting for new recordings...\n")

    if not os.path.exists(ZOOM_FOLDER):
        logger.error(f"❌ Folder not found: {ZOOM_FOLDER}")
        logger.error("Zoom mein Settings → Recording → Local Recording folder check karo")
        return

    # Initial snapshot
    known_files = get_all_audio_files(ZOOM_FOLDER)
    logger.info(f"📂 Found {len(known_files)} existing recordings (will be ignored)")

    while True:
        time.sleep(POLL_INTERVAL)
        try:
            current_files = get_all_audio_files(ZOOM_FOLDER)
            new_files = {f for f in current_files if f not in known_files}

            for filepath in new_files:
                process_recording(filepath)

            known_files = current_files
        except KeyboardInterrupt:
            logger.info("👋 Watcher stopped.")
            break
        except Exception as e:
            logger.error(f"Watcher error: {e}")

if __name__ == "__main__":
    watch()
