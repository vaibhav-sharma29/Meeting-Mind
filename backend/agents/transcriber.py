import os
import logging
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def transcribe_audio(audio_path: str) -> str:
    if audio_path == "mic":
        return _transcribe_mic()
    return _transcribe_with_groq(audio_path)

def _transcribe_with_groq(audio_path: str) -> str:
    ext = audio_path.lower().rsplit(".", 1)[-1]
    mime_map = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "m4a": "audio/mp4",
        "mp4": "audio/mp4",
        "webm": "audio/webm",
        "ogg": "audio/ogg",
    }
    mime_type = mime_map.get(ext, "audio/mp4")
    logger.info(f"Transcribing {audio_path} as {mime_type} using Groq Whisper")

    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(audio_path), f, mime_type),
            model="whisper-large-v3",
            response_format="text",
            language=None,  # auto-detect Hindi/English/Hinglish
        )

    transcript = transcription if isinstance(transcription, str) else transcription.text
    logger.info(f"Groq transcript: {transcript[:150]}")
    return transcript.strip()

def _transcribe_mic() -> str:
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            logger.info("Listening... Speak now!")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=30, phrase_time_limit=120)
            return recognizer.recognize_google(audio)
    except Exception as e:
        return f"Mic transcription error: {e}"
