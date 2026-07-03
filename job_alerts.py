import requests
import time
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL  = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Keywords to match (case-insensitive)
KEYWORDS = [
    "web application", "web app", "mobile app", "mobile application",
    "react", "flutter", "android", "ios", "react native",
    "frontend", "full stack", "fullstack"
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
    print(f"[HTTP] Health-check server on port {port}", flush=True)
    HTTPServer(("0.0.0.0", port), _Handler).serve_forever()

threading.Thread(target=_run_http_server, daemon=True).start()
# ────────────────────────────────────────────────────────────────────────────

def send_message(chat_id, text):
    try:
        r = requests.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10
        )
        if not r.ok:
            print(f"[Telegram error] {r.status_code} {r.text}", flush=True)
    except Exception as e:
        print(f"[send_message error] {e}", flush=True)

def get_chat_id():
    print("[Bot] Waiting for /start from user...", flush=True)
    offset = 0
    while True:
        try:
            r = requests.get(
                f"{BASE_URL}/getUpdates",
                params={"offset": offset, "timeout": 10},
                timeout=15
            )
            for update in r.json().get("result", []):
                offset = update["update_id"] + 1
                msg     = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                if chat_id:
                    print(f"[Bot] Chat ID: {chat_id}", flush=True)
                    send_message(chat_id,
                        "Hello! I am your Freelance Job Alerts Bot.\n\n"
                        "I will send you new web & mobile app jobs from RemoteOK and Remotive every 5 minutes.\n\n"
                        "Monitoring has started!"
                    )
                    return chat_id
        except Exception as e:
            print(f"[getUpdates error] {e}", flush=True)
        time.sleep(2)

def matches_keywords(text):
    t = text.lower()
    return any(kw in t for kw in KEYWORDS)

def fetch_remoteok(chat_id):
    """RemoteOK public API - no key needed, returns real remote jobs"""
    count = 0
    try:
        headers = {"User-Agent": "FreelanceJobAlertsBot/1.0"}
        r = requests.get("https://remoteok.com/api", headers=headers, timeout=15)
        jobs = r.json()
        print(f"[RemoteOK] Got {len(jobs)} items", flush=True)
        for job in jobs:
            if not isinstance(job, dict):
                continue
            job_id = str(job.get("id", ""))
            if not job_id or job_id in seen_jobs:
                continue
            title = job.get("position", "") or ""
            tags  = " ".join(job.get("tags", []))
            desc  = job.get("description", "") or ""
            text  = f"{title} {tags} {desc}"
            if matches_keywords(text):
                seen_jobs.add(job_id)
                company = job.get("company", "Unknown")
                url     = job.get("url", "https://remoteok.com")
                msg = (
                    f"New Remote Job!\n\n"
                    f"Source: RemoteOK\n"
                    f"Title: {title}\n"
                    f"Company: {company}\n"
                    f"Link: {url}"
                )
                send_message(chat_id, msg)
                count += 1
    except Exception as e:
        print(f"[RemoteOK error] {e}", flush=True)
    return count

def fetch_remotive(chat_id):
    """Remotive public API - no key needed, categorized remote jobs"""
    count = 0
    search_terms = ["web", "mobile", "react", "flutter", "android"]
    for term in search_terms:
        try:
            r = requests.get(
                f"https://remotive.com/api/remote-jobs",
                params={"search": term, "limit": 20},
                timeout=15
            )
            jobs = r.json().get("jobs", [])
            print(f"[Remotive] '{term}' -> {len(jobs)} jobs", flush=True)
            for job in jobs:
                job_id = str(job.get("id", ""))
                if not job_id or job_id in seen_jobs:
                    continue
                title = job.get("title", "") or ""
                desc  = job.get("description", "") or ""
                text  = f"{title} {desc}"
                if matches_keywords(text):
                    seen_jobs.add(job_id)
                    company = job.get("company_name", "Unknown")
                    url     = job.get("url", "https://remotive.com")
                    msg = (
                        f"New Remote Job!\n\n"
                        f"Source: Remotive\n"
                        f"Title: {title}\n"
                        f"Company: {company}\n"
                        f"Link: {url}"
                    )
                    send_message(chat_id, msg)
                    count += 1
        except Exception as e:
            print(f"[Remotive error] term={term}: {e}", flush=True)
        time.sleep(1)
    return count

def check_feeds(chat_id):
    print("[Bot] Checking feeds...", flush=True)
    total = 0
    total += fetch_remoteok(chat_id)
    total += fetch_remotive(chat_id)
    print(f"[Bot] Done — {total} new jobs sent. Total seen: {len(seen_jobs)}", flush=True)

def main():
    global CHAT_ID
    CHAT_ID = get_chat_id()
    print("[Bot] Running! Checking every 5 minutes.", flush=True)
    check_feeds(CHAT_ID)   # immediate first check
    while True:
        time.sleep(300)
        check_feeds(CHAT_ID)

if __name__ == "__main__":
    main()
