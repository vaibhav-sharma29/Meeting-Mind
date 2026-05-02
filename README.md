# 🤖 MeetingMind AI

Agentic AI system jo Zoom meetings ko automatically process karta hai — recording aate hi transcribe, analyze, Slack notify, aur Calendar event create karta hai.

## How It Works

```
Zoom Meeting Ends
      ↓
Zoom Webhook → MeetingMind Backend
      ↓
[Agent 1] Transcriber  — VTT transcript ya audio download + Gemini transcription
      ↓
[Agent 2] Analyzer     — Gemini AI se summary + action items extract
      ↓
[Agent 3] Action Taker — Slack notification + Google Calendar events
      ↓
History saved + PDF export available
```

## Setup

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
```

Fill in `.env`:
```
GEMINI_API_KEY=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...
ZOOM_WEBHOOK_SECRET=...
ZOOM_ACCOUNT_ID=...
ZOOM_CLIENT_ID=...
ZOOM_CLIENT_SECRET=...
```

Run:
```bash
uvicorn main:app --reload
```

### 2. Frontend

```bash
cd frontend
npm install
npm start
```

### 3. Zoom Webhook Setup

1. Go to [Zoom Marketplace](https://marketplace.zoom.us) → Your App → Feature → Event Subscriptions
2. Add webhook URL: `https://your-domain.com/zoom-webhook`
3. Subscribe to events:
   - `meeting.ended`
   - `recording.completed`
4. Copy Webhook Secret Token → paste in `.env` as `ZOOM_WEBHOOK_SECRET`

> For local testing use [ngrok](https://ngrok.com): `ngrok http 8000`

### 4. Google Calendar

First time run karne pe browser mein OAuth popup aayega — allow kar do. `token.pickle` save ho jaayega.

## Features

| Feature | Status |
|---------|--------|
| Zoom webhook auto-processing | ✅ |
| VTT transcript download | ✅ |
| Audio recording download + Gemini transcription | ✅ |
| Manual audio file upload (.wav/.mp3/.m4a/.mp4) | ✅ |
| Browser mic recording | ✅ |
| Gemini AI meeting analysis | ✅ |
| Slack notifications per action item | ✅ |
| Google Calendar event creation | ✅ |
| Meeting history (JSON) | ✅ |
| PDF report export | ✅ |
| Real-time agent status (WebSocket) | ✅ |
| Copy action items to clipboard | ✅ |
