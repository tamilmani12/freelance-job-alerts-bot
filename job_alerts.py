import feedparser
import requests
import time
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

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

# ── Tiny HTTP server so Render's port-scan health-check passes ──────────────
class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"FreelanceJobAlertsBot is running")
    def log_message(self, *args):
        pass  # silence access logs

def _run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), _Handler)
    print(f"Health-check server listening on port {port}")
    server.serve_forever()

threading.Thread(target=_run_http_server, daemon=True).start()
# ────────────────────────────────────────────────────────────────────────────

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
        time.sleep(5)

def send_alert(chat_id, source, title, link):
    msg = f"🚀 *New Job Alert!*\n\n*Source:* {source}\n*Title:* {title}\n*Link:* {link}"
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
            timeout=10
        )
    except Exception as e:
        print(f"Failed to send alert: {e}")

def check_feeds(chat_id):
    for source, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                job_id = entry.get("id") or entry.get("link")
                if job_id and job_id not in seen_jobs:
                    seen_jobs.add(job_id)
                    send_alert(chat_id, source, entry.get("title", "No title"), entry.get("link", ""))
        except Exception as e:
            print(f"Error checking {source}: {e}")

def main():
    global CHAT_ID
    CHAT_ID = get_chat_id()
    print("Bot is running! Checking feeds every 5 minutes...")
    while True:
        check_feeds(CHAT_ID)
        time.sleep(300)  # 5 minutes

if __name__ == "__main__":
    main()
