import feedparser
import requests
import time
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL  = f"https://api.telegram.org/bot{BOT_TOKEN}"

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
CHAT_ID   = None

# ── Tiny HTTP server so Render port-scan health-check passes ────────────────
class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"FreelanceJobAlertsBot is running")
    def log_message(self, *args):
        pass

def _run_http_server():
    port = int(os.environ.get("PORT", 10000))
    print(f"Health-check server listening on port {port}", flush=True)
    HTTPServer(("0.0.0.0", port), _Handler).serve_forever()

threading.Thread(target=_run_http_server, daemon=True).start()
# ────────────────────────────────────────────────────────────────────────────

def send_message(chat_id, text):
    """Send a plain-text Telegram message."""
    try:
        requests.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10
        )
    except Exception as e:
        print(f"[send_message error] {e}", flush=True)

def get_chat_id():
    """Poll getUpdates until a user sends any message, then return their chat_id."""
    print("Waiting for user to send /start to @FreelanceJobAlerts_bot ...", flush=True)
    offset = 0
    while True:
        try:
            r = requests.get(
                f"{BASE_URL}/getUpdates",
                params={"offset": offset, "timeout": 10},
                timeout=15
            )
            updates = r.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "")
                if chat_id:
                    print(f"Chat ID found: {chat_id}  (message: {text!r})", flush=True)
                    # Send welcome acknowledgement
                    send_message(chat_id,
                        "Hello! I am your *FreelanceJobAlertsBot*\n\n"
                        "I will notify you the moment new *web* or *mobile app* jobs appear on Upwork and Freelancer.\n\n"
                        "Monitoring has started — sit back and I will alert you every 5 minutes!"
                    )
                    return chat_id
        except Exception as e:
            print(f"[getUpdates error] {e}", flush=True)
        time.sleep(2)

def send_alert(chat_id, source, title, link):
    msg = (
        f"New Job Alert!\n\n"
        f"Source: {source}\n"
        f"Title: {title}\n"
        f"Link: {link}"
    )
    send_message(chat_id, msg)

def check_feeds(chat_id):
    new_count = 0
    for source, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                job_id = entry.get("id") or entry.get("link")
                if job_id and job_id not in seen_jobs:
                    seen_jobs.add(job_id)
                    send_alert(chat_id, source, entry.get("title", "No title"), entry.get("link", ""))
                    new_count += 1
        except Exception as e:
            print(f"[feed error] {source}: {e}", flush=True)
    print(f"Feed check done — {new_count} new jobs sent.", flush=True)

def main():
    global CHAT_ID
    CHAT_ID = get_chat_id()
    print("Bot running! Checking feeds every 5 minutes.", flush=True)
    # First immediate check
    check_feeds(CHAT_ID)
    while True:
        time.sleep(300)  # 5 minutes
        check_feeds(CHAT_ID)

if __name__ == "__main__":
    main()
