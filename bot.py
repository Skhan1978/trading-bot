import requests
import time
import threading
from datetime import datetime, UTC
from http.server import BaseHTTPRequestHandler, HTTPServer

# 🔐 YOUR DETAILS
BOT_TOKEN = "8522684488:AAHrUC1qBwUYK7x3-GMYVsSqONslUnH5WL8"
CHAT_ID = "7216850185"

sent_signals = set()

# ===== TELEGRAM FUNCTION =====
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

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

# ===== MARKET DATA =====
def get_market_data():
    url = "https://financialmodelingprep.com/api/v3/stock_market/actives?apikey=demo"
    try:
        res = requests.get(url)
        data = res.json()
        if isinstance(data, list):
            return data
        return []
    except:
        return []

# ===== SNIPER LOGIC =====
def sniper_scan():
    global sent_signals

    stocks = get_market_data()

    if not stocks:
        send_telegram("⚠️ Market data unavailable")
        return

    found = False

    for stock in stocks[:10]:
        try:
            symbol = stock.get("symbol")
            price = float(stock.get("price", 0))
            change = float(stock.get("changesPercentage", "0").replace('%',''))

            # 🎯 FILTER CONDITIONS
            if not (5 <= price <= 50 and change > 5):
                continue

            if symbol in sent_signals:
                continue

            sent_signals.add(symbol)
            found = True

            entry = round(price * 1.01, 2)
            target = round(price * 1.10, 2)
            stop = round(price * 0.96, 2)

            msg = f"""
🚀 SNIPER ALERT

Stock: {symbol}
Price: ${price}
Move: +{change}%

Entry: ${entry}
Target: ${target}
Stop: ${stop}

Halal: ⚠️ Check manually
"""
            send_telegram(msg)

        except:
            continue

    if not found:
        send_telegram("⚠️ No strong setups right now.")

# ===== MAIN BOT LOOP =====
def bot_loop():
    send_telegram("✅ BOT STARTED SUCCESSFULLY")

    while True:
        hour = datetime.now(UTC).hour

        if 11 <= hour <= 21:
            sniper_scan()

        time.sleep(1800)  # every 30 minutes

# ===== MAIN =====
if __name__ == "__main__":
    threading.Thread(target=run_server).start()
    bot_loop()
