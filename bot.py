import requests
import time
import threading
from datetime import datetime, UTC
from http.server import BaseHTTPRequestHandler, HTTPServer

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

# ===== TELEGRAM =====
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
    server = HTTPServer(("", 10000), Handler)
    server.serve_forever()

# ===== WATCHLIST =====
WATCHLIST = [
    "AAPL","NVDA","TSLA","AMD","META",
    "MSFT","AMZN","GOOGL","NFLX","PLTR","SOFI"
]

# ===== GET HISTORICAL DATA =====
def get_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=15m"
        data = requests.get(url).json()
        result = data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        volumes = result["indicators"]["quote"][0]["volume"]
        return closes, volumes
    except:
        return None, None

# ===== REAL RSI =====
def calculate_rsi(prices, period=14):
    gains = []
    losses = []

    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ===== STRATEGY =====
def sniper_scan():
    for stock in WATCHLIST:

        prices, volumes = get_data(stock)
        if not prices or len(prices) < 20:
            continue

        current_price = prices[-1]
        rsi = round(calculate_rsi(prices), 1)

        avg_volume = sum(volumes[-10:]) / 10
        current_volume = volumes[-1]

        # 🎯 PRO CONDITIONS
        breakout = current_price > max(prices[-10:])
        volume_spike = current_volume > avg_volume * 1.5
        rsi_good = 50 <= rsi <= 65

        if breakout and volume_spike and rsi_good:

            if not can_send(stock):
                continue

            message = f"""🚀 PRO SNIPER ALERT

Stock: {stock}
Price: ${round(current_price,2)}
RSI: {rsi}

Setup: Breakout + Volume Surge
Target: +8% to +15%
Stop: -4%

Confidence: HIGH 📈
"""

            send_telegram(message)
            time.sleep(2)

# ===== MAIN LOOP =====
def bot_loop():
    send_telegram("🔥 PRO BOT ACTIVATED")

    while True:
        hour = datetime.now(UTC).hour

        # US market hours
        if 13 <= hour <= 20:
            sniper_scan()

        time.sleep(900)

# ===== RUN =====
if __name__ == "__main__":
    threading.Thread(target=run_server).start()
    bot_loop()
