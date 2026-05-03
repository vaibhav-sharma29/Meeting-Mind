# 🧠 MeetingMind AI

**Autonomous Meeting Agent — Listens, Understands, Acts**

> Built for Hackathon | Powered by Groq + LangGraph + ElevenLabs + Slack + Notion

---

## 🎬 Demo Video

https://github.com/vaibhav-sharma29/Meeting-Mind/raw/main/assets/demo.mp4

---

## 🚀 What is MeetingMind?

MeetingMind is an AI-powered autonomous agent that automatically processes meetings end-to-end. Upload a recording or connect Zoom — MeetingMind handles everything else.

---

## ✨ Features

| Feature | Status |
|---------|--------|
| 🎤 Audio transcription (Hindi/English/Hinglish) | ✅ |
| 🧠 AI meeting analysis + action items | ✅ |
| 📞 Zoom webhook auto-processing | ✅ |
| 💬 Slack notifications per assignee | ✅ |
| 📅 Google Calendar event creation | ✅ |
| 📓 Notion meeting page auto-created | ✅ |
| 📊 Auto PPT generation + Slack upload | ✅ |
| 🎙️ Voice briefing (audio summary) | ✅ |
| 📄 PDF report export | ✅ |
| 🔴 Real-time agent status (WebSocket) | ✅ |
| 👥 Admin + Team viewer roles | ✅ |

---

## 🔄 How It Works

```
Audio Upload / Zoom Recording
        ↓
🎤 Transcriber Agent (Groq Whisper)
        ↓
🧠 Analyzer Agent (Groq LLaMA 3.3 70B)
        ↓
⚡ Action Taker Agent
   ├── 💬 Slack notification
   ├── 📅 Google Calendar event
   ├── 📊 PPT generation + Slack upload
   └── 📓 Notion page
        ↓
🎙️ Voice Briefing (gTTS)
📄 PDF Report
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React.js |
| Backend | FastAPI + Python |
| Transcription | Groq Whisper |
| AI Analysis | Groq LLaMA 3.3 70B |
| Orchestration | LangGraph |
| Voice | gTTS |
| Notifications | Slack SDK |
| Calendar | Google Calendar API |
| Presentations | python-pptx + Groq AI |
| Notes | Notion API |
| Deployment | Railway + Vercel |

---

## 🌐 Live Demo

- **Team View:** https://meeting-mind-six.vercel.app
- **Admin View:** https://meeting-mind-six.vercel.app?admin=meetingmind2024

---

## ⚙️ Setup

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm start
```

### Environment Variables (.env)
```
GROQ_API_KEY=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
NOTION_TOKEN=...
NOTION_DATABASE_ID=...
ZOOM_WEBHOOK_SECRET=...
ZOOM_ACCOUNT_ID=...
ZOOM_CLIENT_ID=...
ZOOM_CLIENT_SECRET=...
ELEVENLABS_API_KEY=...
```

---

## 👥 Access Levels

- **Admin** `?admin=meetingmind2024` — Upload, history, PDF, all actions
- **Team** — Summary + action items only
