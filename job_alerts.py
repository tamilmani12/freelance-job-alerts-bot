import feedparser
import requests
import time
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")

RSS_FEEDS = [
    ("Upwork - Web App",        "https://www.upwork.com/ab/feed/jobs/rss?q=web+application&sort=recency&paging=0;10"),
    ("Upwork - Mobile App",     "https://www.upwork.com/ab/feed/jobs/rss?q=mobile+application&sort=recency&paging=0;10"),
    ("Upwork - React",          "https://www.upwork.com/ab/feed/jobs/rss?q=react+web+app&sort=recency&paging=0;10"),
    ("Upwork - Flutter",        "https://www.upwork.com/ab/feed/jobs/rss?q=flutter+mobile+app&sort=recency&paging=0;10"),
    ("Upwork - Android",        "https://www.upwork.com/ab/feed/jobs/rss?q=android+app+development&sort=recency&paging=0;10"),
    ("Freelancer - Web App",    "https://www.freelancer.com/rss/projects.xml?keyword=web+application"),
    ("Freelancer - Mobile App", "https://www.freelancer.com/rss/projects.xml?keyword=mobile+application"),
]

seen_jobs = set()
CHAT_ID = None

def get_chat_id():
    print("Waiting for you to press START on @FreelanceJobAlerts_bot in Telegram...")
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates", timeout=10)
            updates = r.json().get("result", [])
            if updates:
                chat_id = updates[-1]["message"]["chat"]["id"]
                print(f"Chat ID found: {chat_id}")
                return chat_id
        except Exception as e:
            print(f"Waiting... {e}")
        time.sleep(3)

def send_alert(chat_id, message):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            timeout=10
        )
    except Exception as e:
        print(f"Failed to send alert: {e}")

def check_feeds(chat_id):
    for source, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if entry.link not in seen_jobs:
                    seen_jobs.add(entry.link)
                    msg = (
                        f"New Job Alert!\n"
                        f"Source: {source}\n"
                        f"Title: {entry.title}\n"
                        f"Link: {entry.link}"
                    )
                    send_alert(chat_id, msg)
                    print(f"Alert sent: {entry.title}")
                    time.sleep(0.5)
        except Exception as e:
            print(f"Error checking {source}: {e}")

print("FreelanceJobAlerts Bot Starting...")
CHAT_ID = get_chat_id()
send_alert(CHAT_ID, "Job Alert Bot is LIVE! You will get instant notifications for new Web and Mobile App jobs from Upwork and Freelancer. Checking every 60 seconds.")

print("Monitoring job feeds...")
while True:
    check_feeds(CHAT_ID)
    print("Checked all feeds. Sleeping 60 seconds...")
    time.sleep(60)
