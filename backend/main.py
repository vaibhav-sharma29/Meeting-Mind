import asyncio
import hashlib
import hmac
import json
import logging
import os
import shutil

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Request, BackgroundTasks, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from agents.analyzer import analyze_meeting
from agents.action_taker import take_actions
from agents.transcriber import transcribe_audio
from agents.orchestrator import decision_node
from live_insights import extract_live_data, generate_chart_config, should_generate_chart
from database import get_all_meetings, get_meeting_by_id, save_meeting
from pdf_export import generate_meeting_pdf
from zoom_service import (
    download_audio_recording,
    download_transcript,
    get_recording_files,
    parse_vtt_transcript,
)

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MeetingMind AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

connected_clients: list[WebSocket] = []


async def broadcast(message: dict):
    dead = []
    for client in connected_clients:
        try:
            await client.send_text(json.dumps(message))
        except Exception:
            dead.append(client)
    for d in dead:
        connected_clients.remove(d)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        if websocket in connected_clients:
            connected_clients.remove(websocket)


async def run_pipeline(transcript: str, source: str = "upload") -> dict:
    await broadcast({"step": "analyzer", "status": "running", "message": "🧠 Analyzing meeting..."})
    result = analyze_meeting(transcript)
    action_items = result.get("action_items", [])
    summary = result.get("summary", "")
    sentiment = result.get("sentiment", "neutral")
    risks = result.get("risks", [])
    effectiveness_score = result.get("effectiveness_score", 5)
    effectiveness_reason = result.get("effectiveness_reason", "")
    repeated_misses = result.get("repeated_misses", [])
    await broadcast({
        "step": "analyzer", "status": "done",
        "message": f"✅ Found {len(action_items)} action items! Sentiment: {sentiment}",
        "data": result,
    })

    # Smart decision agent
    decision_result = decision_node({
        "action_items": action_items,
        "risks": risks,
        "effectiveness_score": effectiveness_score,
        "sentiment": sentiment,
    })
    action_items = decision_result.get("action_items", action_items)
    agent_decisions = decision_result.get("agent_decisions", [])
    for d in agent_decisions:
        await broadcast({"step": "analyzer", "status": "running", "message": d})

    await broadcast({"step": "action_taker", "status": "running", "message": "⚡ Sending to Slack + Calendar..."})
    actions = take_actions(action_items)
    await broadcast({"step": "action_taker", "status": "done", "message": "✅ All done!", "data": actions})

    meeting = save_meeting(transcript, summary, action_items, actions, source=source)
    return {
        "meeting": meeting,
        "summary": summary,
        "sentiment": sentiment,
        "risks": risks,
        "effectiveness_score": effectiveness_score,
        "effectiveness_reason": effectiveness_reason,
        "repeated_misses": repeated_misses,
        "agent_decisions": agent_decisions,
        "action_items": action_items,
        "actions_taken": actions,
    }


@app.post("/process-meeting")
async def process_meeting(audio: UploadFile = File(...)):
    if not audio.filename.lower().endswith((".wav", ".mp3", ".m4a", ".mp4")):
        return JSONResponse({"success": False, "error": "Unsupported file format. Use .wav, .mp3, .m4a"}, status_code=400)

    audio_path = f"temp_{audio.filename}"
    with open(audio_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    try:
        await broadcast({"step": "transcriber", "status": "running", "message": "🎤 Transcribing audio..."})
        transcript = transcribe_audio(audio_path)
        await broadcast({"step": "transcriber", "status": "done", "message": "✅ Transcript ready!", "data": transcript})

        pipeline = await run_pipeline(transcript, source="upload")
        meeting = pipeline["meeting"]

        return JSONResponse({
            "success": True,
            "meeting_id": meeting["id"],
            "transcript": transcript,
            "summary": pipeline["summary"],
            "sentiment": pipeline["sentiment"],
            "risks": pipeline["risks"],
            "effectiveness_score": pipeline["effectiveness_score"],
            "effectiveness_reason": pipeline["effectiveness_reason"],
            "repeated_misses": pipeline["repeated_misses"],
            "agent_decisions": pipeline["agent_decisions"],
            "action_items": pipeline["action_items"],
            "actions_taken": pipeline["actions_taken"],
        })

    except Exception as e:
        logger.error(f"process-meeting error: {e}")
        await broadcast({"step": "error", "status": "error", "message": f"❌ Error: {str(e)}"})
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


@app.get("/meetings")
def list_meetings():
    meetings = get_all_meetings()
    return JSONResponse([
        {
            "id": m["id"],
            "timestamp": m["timestamp"],
            "summary": m["summary"],
            "action_items_count": len(m.get("action_items", [])),
            "source": m.get("source", "upload"),
        }
        for m in reversed(meetings)
    ])


@app.get("/meetings/{meeting_id}")
def get_meeting(meeting_id: int):
    meeting = get_meeting_by_id(meeting_id)
    if not meeting:
        return JSONResponse({"error": "Meeting not found"}, status_code=404)
    return JSONResponse(meeting)


@app.get("/meetings/{meeting_id}/pdf")
def download_pdf(meeting_id: int):
    meeting = get_meeting_by_id(meeting_id)
    if not meeting:
        return JSONResponse({"error": "Meeting not found"}, status_code=404)
    pdf_bytes = generate_meeting_pdf(meeting)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=meeting_{meeting_id}.pdf"},
    )


def verify_zoom_signature(request_body: bytes, timestamp: str, signature: str) -> bool:
    secret = os.getenv("ZOOM_WEBHOOK_SECRET", "")
    if not secret:
        return True
    message = f"v0:{timestamp}:{request_body.decode()}"
    expected = "v0=" + hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.post("/zoom-webhook")
async def zoom_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    timestamp = request.headers.get("x-zm-request-timestamp", "")
    signature = request.headers.get("x-zm-signature", "")
    if timestamp and signature:
        if not verify_zoom_signature(body, timestamp, signature):
            return JSONResponse({"error": "Invalid signature"}, status_code=401)

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    event = payload.get("event")
    logger.info(f"Zoom webhook event: {event}")

    if event == "endpoint.url_validation":
        token = payload["payload"]["plainToken"]
        secret = os.getenv("ZOOM_WEBHOOK_SECRET", "")
        hashed = hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()
        return {"plainToken": token, "encryptedToken": hashed}

    if event == "meeting.ended":
        meeting_topic = payload["payload"]["object"].get("topic", "Zoom Meeting")
        await broadcast({"step": "transcriber", "status": "running", "message": f"📞 Meeting '{meeting_topic}' ended. Waiting for recording..."})
        return {"status": "meeting ended, waiting for recording"}

    if event == "recording.completed":
        obj = payload["payload"]["object"]
        meeting_id = obj["id"]
        meeting_topic = obj.get("topic", "Zoom Meeting")
        recording_files = obj.get("recording_files", [])
        background_tasks.add_task(process_zoom_recording_ready, meeting_id, meeting_topic, recording_files)
        return {"status": "recording processing started"}

    return {"status": "event received"}


async def process_zoom_recording_ready(meeting_id: str, meeting_topic: str, recording_files: list):
    await broadcast({"step": "transcriber", "status": "running", "message": f"🎬 Processing recording for '{meeting_topic}'..."})
    transcript = ""

    vtt_file = next((f for f in recording_files if f.get("file_type") == "TRANSCRIPT"), None)
    if vtt_file:
        try:
            vtt_text = await download_transcript(vtt_file["download_url"])
            transcript = parse_vtt_transcript(vtt_text)
            await broadcast({"step": "transcriber", "status": "done", "message": "✅ Zoom transcript downloaded!", "data": transcript})
        except Exception as e:
            logger.warning(f"VTT download failed: {e}")

    if not transcript:
        audio_file = next((f for f in recording_files if f.get("file_type") in ("MP4", "M4A", "AUDIO_ONLY")), None)
        if audio_file:
            try:
                ext = "mp4" if audio_file.get("file_type") == "MP4" else "m4a"
                save_path = f"temp_zoom_{meeting_id}.{ext}"
                await download_audio_recording(audio_file["download_url"], save_path)
                transcript = transcribe_audio(save_path)
                if os.path.exists(save_path):
                    os.remove(save_path)
                await broadcast({"step": "transcriber", "status": "done", "message": "✅ Audio transcribed!", "data": transcript})
            except Exception as e:
                logger.error(f"Audio transcribe failed: {e}")
                await broadcast({"step": "error", "status": "error", "message": f"❌ Transcription failed: {e}"})
                return

    if not transcript:
        await broadcast({"step": "error", "status": "error", "message": "❌ Could not get transcript from Zoom recording."})
        return

    try:
        await run_pipeline(transcript, source=f"zoom:{meeting_topic}")
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        await broadcast({"step": "error", "status": "error", "message": f"❌ Pipeline error: {str(e)}"})


@app.get("/health")
def health():
    return {
        "status": "MeetingMind AI is running 🚀",
        "zoom_configured": bool(os.getenv("ZOOM_ACCOUNT_ID")),
        "slack_configured": bool(os.getenv("SLACK_BOT_TOKEN")),
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
    }

@app.post("/live-insight")
async def process_live_text(request: dict):
    """Process live meeting text for instant insights."""
    text = request.get("text", "")
    
    if should_generate_chart(text):
        live_data = extract_live_data(text)
        if live_data:
            chart_config = generate_chart_config(live_data)
            if chart_config:
                await broadcast({
                    "step": "live_insight",
                    "status": "chart", 
                    "message": "📈 Live insight generated",
                    "data": {
                        "chart": chart_config,
                        "text": text
                    }
                })
                return JSONResponse({"success": True, "chart": chart_config})
    
    return JSONResponse({"success": False, "message": "No insights found"})
