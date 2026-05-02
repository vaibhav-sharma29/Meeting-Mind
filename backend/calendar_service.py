import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pickle

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build("calendar", "v3", credentials=creds)

def create_calendar_event(assignee: str, task: str, deadline: str) -> bool:
    try:
        service = get_calendar_service()

        # Default: kal ka event banao agar deadline parse na ho
        try:
            event_date = datetime.strptime(deadline, "%Y-%m-%d")
        except:
            event_date = datetime.now() + timedelta(days=1)

        event = {
            "summary": f"[MeetingMind] {task}",
            "description": f"Assigned to: {assignee}\nTask: {task}\nAuto-created by MeetingMind AI",
            "start": {
                "dateTime": event_date.strftime("%Y-%m-%dT10:00:00"),
                "timeZone": "Asia/Kolkata",
            },
            "end": {
                "dateTime": event_date.strftime("%Y-%m-%dT11:00:00"),
                "timeZone": "Asia/Kolkata",
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},
                    {"method": "popup", "minutes": 30},
                ],
            },
        }

        service.events().insert(calendarId="primary", body=event).execute()
        print(f"✅ Calendar event created for {assignee}")
        return True
    except Exception as e:
        print(f"❌ Calendar error: {e}")
        return False
