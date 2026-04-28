import os

# 🔥 AUTO-INSTALL FIX (so Render never fails)
os.system("pip install yfinance pandas requests --quiet")

import requests
import time
from datetime import datetime, UTC
import yfinance as yf

# ===== CONFIG =====
TELEGRAM_TOKEN = os.getenv("8268157455:AAElh_Fi0znhxEhVkwbK1Y2fhRMoUA65TI4")
CHAT_ID = os.getenv("7216850185")

CHECK_INTERVAL = 300  # 5 min

# ===== STATE =====
active_trade = None
last_heartbeat = 0

# ===== TELEGRAM =====
def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except Exception as e:
        print("Telegram error:", e, flush=True)

# ===== DATA =====
def get_data(symbol):
    try:
        data = yf.download(symbol, period="5d", interval="5m", progress=False)
        closes = data["Close"].dropna().tolist()
        return closes
    except Exception as e:
        print(f"DATA ERROR {symbol}:", e, flush=True)
        return None

# ===== SCANNER =====
def find_stock():
    watchlist = [
        "AAPL","NVDA","MSFT","AMD","TSLA",
        "META","AMZN","GOOGL","PLTR","SOFI"
    ]

    best = None
    best_score = -1

    for s in watchlist:
        closes = get_data(s)
        if not closes or len(closes) < 50:
            continue

        price = closes[-1]
        ma20 = sum(closes[-20:]) / 20
        ma50 = sum(closes[-50:]) / 50

        if price > ma20 > ma50:
            score = (price - ma20) / ma20

            if score > best_score:
                best_score = score
                best = s

    print("Selected stock:", best, flush=True)
    return best

# ===== TRADE MANAGEMENT =====
def manage_trade():
    global active_trade

    symbol = active_trade["symbol"]
    closes = get_data(symbol)

    if not closes:
        return

    price = closes[-1]

    # update highest
    if price > active_trade["highest"]:
        active_trade["highest"] = price

    profit = ((price - active_trade["entry"]) / active_trade["entry"]) * 100

    # ===== UPDATE =====
    send(f"📊 {symbol} | Price: {price:.2f} | {profit:.2f}%")

    # ===== LOCK PROFIT =====
    if profit > 5 and not active_trade["locked"]:
        active_trade["locked"] = True
        send(f"🔒 LOCK PROFIT {symbol} +{profit:.2f}%")

    # ===== TRAILING EXIT =====
    drop = ((active_trade["highest"] - price) / active_trade["highest"]) * 100
    if active_trade["locked"] and drop > 2:
        send(f"⚠️ EXIT (Trailing) {symbol} +{profit:.2f}%")
        active_trade = None
        return

    # ===== STOP LOSS =====
    if price <= active_trade["stop"]:
        send(f"❌ STOP LOSS {symbol} at {price:.2f}")
        active_trade = None
        return

    # ===== TARGET =====
    if price >= active_trade["target"]:
        send(f"🎯 TARGET HIT {symbol} +{profit:.2f}%")
        active_trade = None

# ===== MAIN =====
def run():
    global active_trade, last_heartbeat

    send("🚀 BOT LIVE (Single Trade Manager)")

    while True:
        try:
            now = time.time()

            # HEARTBEAT
            if now - last_heartbeat > 3600:
                send(f"💓 Alive {datetime.now(UTC).strftime('%H:%M:%S')}")
                last_heartbeat = now

            # ===== NO ACTIVE TRADE =====
            if not active_trade:
                stock = find_stock()

                if stock:
                    closes = get_data(stock)
                    if not closes:
                        continue

                    price = closes[-1]

                    active_trade = {
                        "symbol": stock,
                        "entry": price,
                        "target": price * 1.12,
                        "stop": price * 0.95,
                        "highest": price,
                        "locked": False
                    }

                    send(f"""🚀 NEW TRADE: {stock}

Entry: {price:.2f}
Target: {price*1.12:.2f}
Stop: {price*0.95:.2f}

Mode: Single Trade Active
""")

                else:
                    print("No valid stock found", flush=True)

            else:
                manage_trade()

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print("ERROR:", e, flush=True)
            time.sleep(5)

# ===== START =====
if __name__ == "__main__":
    run()
