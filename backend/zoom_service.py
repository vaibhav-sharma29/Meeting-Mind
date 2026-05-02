"""Zoom OAuth + Recording download service."""
import os
import httpx
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

ZOOM_TOKEN_URL = "https://zoom.us/oauth/token"
ZOOM_API_BASE = "https://api.zoom.us/v2"


async def get_zoom_access_token() -> str:
    """Get Zoom Server-to-Server OAuth token."""
    account_id = os.getenv("ZOOM_ACCOUNT_ID", "")
    client_id = os.getenv("ZOOM_CLIENT_ID", "")
    client_secret = os.getenv("ZOOM_CLIENT_SECRET", "")

    if not all([account_id, client_id, client_secret]):
        raise ValueError("Zoom credentials not configured in .env")

    async with httpx.AsyncClient() as client:
        res = await client.post(
            ZOOM_TOKEN_URL,
            params={"grant_type": "account_credentials", "account_id": account_id},
            auth=(client_id, client_secret),
            timeout=10,
        )
        res.raise_for_status()
        token = res.json().get("access_token", "")
        if not token:
            raise ValueError("Failed to get Zoom access token")
        return token


async def get_recording_files(meeting_id: str) -> list:
    """Fetch recording files list for a meeting."""
    token = await get_zoom_access_token()
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{ZOOM_API_BASE}/meetings/{meeting_id}/recordings",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if res.status_code == 404:
            logger.warning(f"No recordings found for meeting {meeting_id}")
            return []
        res.raise_for_status()
        data = res.json()
        return data.get("recording_files", [])


async def download_transcript(download_url: str) -> str:
    """Download VTT/transcript file from Zoom."""
    token = await get_zoom_access_token()
    async with httpx.AsyncClient(follow_redirects=True) as client:
        res = await client.get(
            download_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
        res.raise_for_status()
        return res.text


async def download_audio_recording(download_url: str, save_path: str) -> str:
    """Download MP4/M4A audio recording from Zoom and save locally."""
    token = await get_zoom_access_token()
    async with httpx.AsyncClient(follow_redirects=True) as client:
        async with client.stream(
            "GET",
            download_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=300,
        ) as res:
            res.raise_for_status()
            with open(save_path, "wb") as f:
                async for chunk in res.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
    logger.info(f"✅ Recording downloaded: {save_path}")
    return save_path


def parse_vtt_transcript(vtt_text: str) -> str:
    """Convert Zoom VTT caption file to plain text transcript."""
    lines = vtt_text.splitlines()
    transcript_lines = []
    skip_next = False

    for line in lines:
        line = line.strip()
        if line == "WEBVTT" or line == "":
            continue
        # Skip timestamp lines like "00:00:01.000 --> 00:00:05.000"
        if "-->" in line:
            skip_next = False
            continue
        # Skip numeric cue identifiers
        if line.isdigit():
            continue
        if not skip_next and line:
            transcript_lines.append(line)

    return " ".join(transcript_lines)
