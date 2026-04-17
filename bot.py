import requests
import time
import threading
from datetime import datetime, UTC
from http.server import BaseHTTPRequestHandler, HTTPServer

# 🔐 YOUR DETAILS
BOT_TOKEN ="8522684488:AAHrUC1qBwUYK7x3-GMYVsSqONslUnH5WL8" 
CHAT_ID = "7216850185"

# ===== TELEGRAM FUNCTION =====
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ===== KEEP RENDER ALIVE (WEB SERVER) =====
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    port = 10000
    server = HTTPServer(("", port), Handler)
    server.serve_forever()

# ===== BOT LOGIC =====
def bot_loop():
    send_telegram("✅ BOT STARTED SUCCESSFULLY")

    while True:
        now = datetime.now(UTC).hour

        # simple test alert every 30 mins during market hours
        if 11 <= now <= 21:
            send_telegram("🚀 Bot is active and scanning market...")

        time.sleep(1800)

# ===== MAIN =====
if __name__ == "__main__":
    # run web server (for Render)
    threading.Thread(target=run_server).start()

    # run bot
    bot_loop()
