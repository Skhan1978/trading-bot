import requests
import time
import threading
from datetime import datetime, UTC
from http.server import BaseHTTPRequestHandler, HTTPServer

# 🔐 YOUR DETAILS
BOT_TOKEN = "8268157455:AAHDSkSixKEqBd5W_4pizVMOEWy9mIhKQNE"

CHAT_ID = "7216850185"

# ===== ANTI-SPAM =====
last_sent = {}

def can_send(symbol):
    now = time.time()
    if symbol in last_sent and now - last_sent[symbol] < 3600:
        return False
    last_sent[symbol] = now
    return True

# ===== TELEGRAM FUNCTION =====
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ===== KEEP RENDER ALIVE =====
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    port = 10000
    server = HTTPServer(("", port), Handler)
    server.serve_forever()

# ===== STOCK LIST (STRONG US STOCKS) =====
WATCHLIST = [
    "AAPL", "NVDA", "TSLA", "AMD", "META",
    "MSFT", "AMZN", "GOOGL", "NFLX", "PLTR",
    "SOFI", "COIN", "RIVN", "SNAP"
]

# ===== SIMPLE MARKET DATA (NO API KEY NEEDED) =====
def get_price(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
        data = requests.get(url).json()
        return data["quoteResponse"]["result"][0]["regularMarketPrice"]
    except:
        return None

# ===== FAKE RSI (LIGHT VERSION FOR NOW) =====
def get_rsi():
    import random
    return random.randint(45, 65)

# ===== HALAL FILTER (BASIC) =====
def is_halal(symbol):
    haram = ["COIN"]  # crypto exposure
    return symbol not in haram

# ===== STRATEGY =====
def sniper_scan():
    for stock in WATCHLIST:
        price = get_price(stock)
        if not price:
            continue

        rsi = get_rsi()

        # 🎯 CONDITIONS (STRONG SETUPS ONLY)
        if 50 <= rsi <= 60 and is_halal(stock):

            if not can_send(stock):
                continue

            message = f"""🚀 SNIPER ALERT

Stock: {stock}
Price: ${price}
RSI: {rsi}

Setup: Breakout / Pullback
Target: +8% to +12%
Stop: -4%

Halal: ✅
"""

            send_telegram(message)
            time.sleep(2)

# ===== MAIN LOOP =====
def bot_loop():
    send_telegram("✅ ELITE BOT STARTED")

    while True:
        hour = datetime.now(UTC).hour

        # US market hours (approx)
        if 13 <= hour <= 20:
            sniper_scan()

        time.sleep(900)  # every 15 min

# ===== RUN =====
if __name__ == "__main__":
    threading.Thread(target=run_server).start()
    bot_loop()
