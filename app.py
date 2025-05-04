import asyncio
from dateutil import parser
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from datetime import datetime, timedelta
import os.path
import pickle
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

# Access environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SCOPES = os.getenv('SCOPES').split(',')


def get_calendar_service():
    creds = None
    if os.path.exists('token.pkl'):
        with open('token.pkl', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=8080)
        with open('token.pkl', 'wb') as token:
            pickle.dump(creds, token)
    return build('calendar', 'v3', credentials=creds)


def get_today_events():
    service = get_calendar_service()
    now = datetime.utcnow()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
    end_of_day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
    events_result = service.events().list(calendarId='primary', timeMin=start_of_day,
                                          timeMax=end_of_day, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])
    return events


async def send_message(text):
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=text)


def daily_job():
    events = get_today_events()
    if not events:
        message = "📅 You have no events today."
    else:
        message = "🔔 Your Schedule for Today:\n\n"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            parsed_time = parser.isoparse(start)
            event_time = parsed_time.strftime('%I:%M %p') if 'dateTime' in event['start'] else start
            message += f"• {event['summary']} at {event_time}\n"
        message += "\nStay organized and have a productive day! 💼"

    asyncio.run(send_message(message))


daily_job()
