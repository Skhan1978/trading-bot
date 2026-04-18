import requests
import time
import threading
from datetime import datetime, UTC
from http.server import BaseHTTPRequestHandler, HTTPServer

BOT_TOKEN = "8268157455:AAH--nPaj5uhoN22uu_wdukoqC3beY91N1Y"
CHAT_ID = "7216850185"

WATCHLIST = [
    "AAPL","NVDA","TSLA","AMD","META",
    "MSFT","AMZN","GOOGL","NFLX","PLTR",
    "SOFI","RIVN"
]

last_sent_day = None
pending_trade = None

# ===== TELEGRAM =====
def send(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except:
        pass

# ===== SERVER =====
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Running")

def run_server():
    HTTPServer(("", 10000), Handler).serve_forever()

# ===== DATA =====
def get_price(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1m"
        data = requests.get(url, timeout=10).json()
        return data["chart"]["result"][0]["meta"]["regularMarketPrice"]
    except:
        return None

def get_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=15m"
        data = requests.get(url, timeout=10).json()
        result = data["chart"]["result"][0]
        return result["indicators"]["quote"][0]["close"], result["indicators"]["quote"][0]["volume"]
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

# ===== FILTERS =====
def has_news(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={symbol}"
        data = requests.get(url, timeout=10).json()
        return len(data.get("news", [])) > 0
    except:
        return False

def is_gapping(prices):
    try:
        return ((prices[-1] - prices[-2]) / prices[-2]) * 100 > 2
    except:
        return False

def is_halal(symbol):
    return symbol not in ["COIN"]

# ===== FIND BEST TRADE =====
def find_best_trade():
    best = None

    for stock in WATCHLIST:
        prices, volumes = get_data(stock)
        if not prices or len(prices) < 20:
            continue

        price = prices[-1]
        rsi = calculate_rsi(prices)

        avg_vol = sum(volumes[-10:]) / 10
        current_vol = volumes[-1]

        breakout = price > max(prices[-10:])
        trend = prices[-1] > prices[-5] > prices[-10]
        volume = current_vol > avg_vol * 2   # stronger volume
        rsi_ok = 52 <= rsi <= 62            # tighter RSI

        catalyst = has_news(stock) or is_gapping(prices)

        score = sum([breakout, trend, volume, rsi_ok, catalyst])

        # 🎯 ONLY PERFECT SETUPS
        if score < 5 or not is_halal(stock):
            continue

        breakout_level = max(prices[-5:])
        entry = round(breakout_level, 2)

        stop = round(min(prices[-5:]), 2)
        risk = entry - stop
        if risk <= 0:
            continue

        target = round(entry + risk * 2, 2)

        best = {
            "stock": stock,
            "entry": entry,
            "stop": stop,
            "target": target,
            "rsi": round(rsi,1),
            "breakout_level": breakout_level
        }

        break  # only first perfect setup

    return best

# ===== MAIN LOOP =====
def bot_loop():
    global last_sent_day, pending_trade

    print("BOT LOOP STARTED")
    send("🔥 SNIPER BOT ACTIVE (FINAL MODE)")

    while True:
        try:
            today = datetime.now(UTC).date()

            # FIND TRADE
            if not pending_trade and last_sent_day != today:
                pending_trade = find_best_trade()

            # WAIT FOR RETEST ENTRY (PRO ENTRY)
            if pending_trade:
                current_price = get_price(pending_trade["stock"])

                if current_price:
                    entry = pending_trade["entry"]

                    # 🎯 RETEST ZONE ENTRY (NOT BREAKOUT CHASE)
                    if entry * 0.995 <= current_price <= entry * 1.005:

                        msg = f"""🎯 SNIPER TRADE CONFIRMED

Stock: {pending_trade['stock']}

Entry Zone: {entry}
Current Price: {round(current_price,2)}

Stop Loss: {pending_trade['stop']}
Take Profit: {pending_trade['target']}

RSI: {pending_trade['rsi']}

Strategy: Breakout + Retest + Volume

Execute now.
"""

                        send(msg)

                        last_sent_day = today
                        pending_trade = None

            time.sleep(60)

        except Exception as e:
            print("ERROR:", e)
            time.sleep(60)

# ===== RUN =====
if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    time.sleep(2)
    bot_loop()
