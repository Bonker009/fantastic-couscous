import asyncio
import logging
import os.path
import pickle
from datetime import datetime, timedelta

import pytz
from aiohttp import web
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from telegram import Bot

load_dotenv()
logging.basicConfig(level=logging.INFO)
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
    await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='Markdown')


async def daily_job():
    print('Starting daily job')
    events = get_today_events()
    if not events:
        await send_message("You have no events today.")
    else:
        message = "🗓️ *Your schedule for today:*\n"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            try:
                event_time = datetime.fromisoformat(start.replace("Z", "+00:00")).strftime('%I:%M %p')
            except:
                event_time = start
            message += f"• {event['summary']} at `{event_time}`\n"
        print(message)

        await send_message(message)


async def wait_until_6_am():
    print('Waiting until 6:00 AM')

    local_tz = pytz.timezone("Asia/Phnom_Penh")  # Adjust as needed
    now = datetime.now(local_tz)  # Local time


    next_time = now.replace(hour=11, minute=40, second=0, microsecond=0)
    print('Next time:', next_time)

    if now >= next_time:
        next_time += timedelta(days=1)
        print("now >= next_time, adjusting to the next day:", next_time)

    print("now >= next_time check:", now, next_time)

    seconds_until_target = (next_time - now).total_seconds()
    logging.info(f"Seconds until target: {seconds_until_target}")

    await asyncio.sleep(seconds_until_target)


async def repeat_daily():
    while True:
        await wait_until_6_am()
        await daily_job()


async def handle(request):
    return web.Response(text="Bot is running.")


async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", 8080)))
    await site.start()


async def main():
    await asyncio.gather(start_web_server(), repeat_daily())


if __name__ == "__main__":
    print("Application started.")

    asyncio.run(main())
