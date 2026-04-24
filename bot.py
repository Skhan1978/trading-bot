from flask import Flask
import requests
import os
import time
import threading

app import threading


def start_tracker():
    thread = threading.Thread(target=run_tracker)
    thread.daemon = True
    thread.start()

start_tracker()

# ===== CONFIG =====
TELEGRAM_TOKEN = os.environ.get("8268157455:AAF807pO5yASxEZ-RKSowuIA4LlGRWkE1Vs")
TELEGRAM_CHAT_ID = os.environ.get("7216850185")

STOCK = "SPY"   # change if needed
CHECK_INTERVAL = 60  # seconds

# ===== TELEGRAM =====
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    })

# ===== PRICE FETCH (FREE API) =====
def get_price(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
        data = requests.get(url).json()
        return data["quoteResponse"]["result"][0]["regularMarketPrice"]
    except:
        return None

# ===== PROFIT MANAGER =====
class ProfitManager:
    def __init__(self, entry_price):
        self.entry = entry_price
        self.highest = entry_price
        self.partial_taken = False

    def update(self, price):
        alert = None

        if price > self.highest:
            self.highest = price

        profit_pct = ((price - self.entry) / self.entry) * 100

        # Take profit
        if profit_pct >= 5 and not self.partial_taken:
            self.partial_taken = True
            alert = f"🚀 {STOCK}: Take Profit (+{profit_pct:.2f}%)"

        # Trailing stop
        drop = ((self.highest - price) / self.highest) * 100
        if drop >= 2:
            alert = f"⚠️ {STOCK}: Price dropping ({drop:.2f}%) → Lock Profit"

        return alert

# ===== MAIN TRACKER =====
def run_tracker():
    print("📡 Tracker started...")

    entry_price = get_price(STOCK)
    if not entry_price:
        print("Error getting price")
        return

    manager = ProfitManager(entry_price)

    send_telegram(f"📊 Tracking {STOCK} at {entry_price}")

    while True:
        price = get_price(STOCK)

        if price:
            print(f"{STOCK}: {price}")
            alert = manager.update(price)

            if alert:
                send_telegram(alert)

        time.sleep(CHECK_INTERVAL)

# ===== START BACKGROUND THREAD =====
threading.Thread(target=run_tracker).start()

# ===== WEB ROUTE =====
@app.route("/")
def home():
    return "✅ Bot running + tracking"
