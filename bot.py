import requests
import time
import threading
from datetime import datetime, UTC
from http.server import BaseHTTPRequestHandler, HTTPServer

BOT_TOKEN = "8268157455:AAHDSkSixKEqBd5W_4pizVMOEWy9mIhKQNE"

CHAT_ID = "7216850185"


last_sent = {}

# ===== TELEGRAM =====
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def can_send(symbol):
    now = time.time()
    if symbol in last_sent and now - last_sent[symbol] < 3600:
        return False
    last_sent[symbol] = now
    return True

# ===== KEEP RENDER ALIVE =====
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Running")

def run_server():
    server = HTTPServer(("", 10000), Handler)
    server.serve_forever()

# ===== WATCHLIST =====
WATCHLIST = [
    "AAPL","NVDA","TSLA","AMD","META",
    "MSFT","AMZN","GOOGL","NFLX","PLTR",
    "SOFI","RIVN"
]

# ===== MARKET DATA =====
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

# ===== RSI =====
def calculate_rsi(prices, period=14):
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ===== NEWS =====
def has_news(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={symbol}"
        data = requests.get(url).json()
        return len(data.get("news", [])) > 0
    except:
        return False

# ===== GAP =====
def is_gapping(prices):
    try:
        prev = prices[-2]
        current = prices[-1]
        return ((current - prev) / prev) * 100 > 2
    except:
        return False

# ===== HALAL FILTER =====
def is_halal(symbol):
    return symbol not in ["COIN"]

# ===== PRE-MARKET =====
def premarket_scan():
    for stock in WATCHLIST:

        prices, volumes = get_data(stock)
        if not prices or len(prices) < 10:
            continue

        current = prices[-1]
        prev = prices[-2]
        gap = ((current - prev) / prev) * 100

        avg_vol = sum(volumes[-10:]) / 10
        current_vol = volumes[-1]

        news = has_news(stock)

        if gap > 2 and current_vol > avg_vol * 1.5 and news:

            if not can_send(stock):
                continue

            msg = f"""🚀 PRE-MARKET SNIPER

Stock: {stock}
Gap: +{round(gap,2)}%
Price: ${round(current,2)}

Catalyst: NEWS 📰
Volume: Strong

Plan:
Wait for breakout after market open
Target: +10% to +25%
"""

            send_telegram(msg)
            time.sleep(2)

# ===== MAIN STRATEGY =====
def sniper_scan():
    for stock in WATCHLIST:

        prices, volumes = get_data(stock)
        if not prices or len(prices) < 20:
            continue

        price = prices[-1]
        rsi = round(calculate_rsi(prices), 1)

        avg_vol = sum(volumes[-10:]) / 10
        current_vol = volumes[-1]

        breakout = price > max(prices[-10:])
        trend = prices[-1] > prices[-5] > prices[-10]
        volume = current_vol > avg_vol * 1.8
        rsi_ok = 52 <= rsi <= 65

        news = has_news(stock)
        gap = is_gapping(prices)

        if breakout and trend and volume and rsi_ok and (news or gap) and is_halal(stock):

            if not can_send(stock):
                continue

            catalyst = "NEWS 📰" if news else "GAP 🚀"

            msg = f"""🚀 ELITE ALERT

Stock: {stock}
Price: ${round(price,2)}
RSI: {rsi}

Catalyst: {catalyst}
Setup: Breakout + Trend + Volume

Target: +10% to +20%
Stop: -4%
"""

            send_telegram(msg)
            time.sleep(2)

# ===== LOOP =====
def bot_loop():
    send_telegram("🔥 FULL ELITE SYSTEM ACTIVE")

    while True:
        hour = datetime.now(UTC).hour

        # PRE-MARKET
        if 10 <= hour < 13:
            premarket_scan()

        # MARKET HOURS
        if 13 <= hour <= 20:
            sniper_scan()

        time.sleep(900)

# ===== RUN =====
if __name__ == "__main__":
    threading.Thread(target=run_server).start()
    bot_loop()
