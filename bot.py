import requests
import time
import os
from datetime import datetime, UTC

# ===== CONFIG =====
TELEGRAM_TOKEN = os.getenv("8268157455:AAElh_Fi0znhxEhVkwbK1Y2fhRMoUA65TI4")
CHAT_ID = os.getenv("7216850185")
FMP_API_KEY = os.getenv("412cc787d78a4975804e17b245ca3c68")

CHECK_INTERVAL = 300  # 5 min

# ===== STATE =====
active_trade = None
last_heartbeat = 0

# ===== TELEGRAM =====
def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except:
        pass

# ===== DATA =====
def get_data(symbol):
    url = f"https://financialmodelingprep.com/api/v3/historical-chart/5min/{symbol}?apikey={FMP_API_KEY}"
    data = requests.get(url).json()

    closes = [c["close"] for c in data[:100]]
    closes.reverse()

    return closes

# ===== FIND BEST STOCK =====
def find_stock():
    url = f"https://financialmodelingprep.com/api/v3/stock-screener?marketCapMoreThan=2000000000&marketCapLowerThan=20000000000&volumeMoreThan=500000&limit=100&apikey={FMP_API_KEY}"
    stocks = [s["symbol"] for s in requests.get(url).json()]

    best = None
    best_score = 0

    for s in stocks:
        try:
            closes = get_data(s)
            if len(closes) < 50:
                continue

            price = closes[-1]
            ma20 = sum(closes[-20:]) / 20
            ma50 = sum(closes[-50:]) / 50

            if price > ma20 > ma50:
                score = (price - ma20) / ma20
                if score > best_score:
                    best_score = score
                    best = s
        except:
            continue

    return best

# ===== TRADE MANAGER =====
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

    # ===== PROFIT UPDATE =====
    send(f"📊 {symbol} Update: {price:.2f} | {profit:.2f}%")

    # ===== LOCK PROFIT =====
    if profit > 5 and not active_trade["locked"]:
        active_trade["locked"] = True
        send(f"🔒 LOCK PROFIT {symbol} +{profit:.2f}%")

    # ===== TRAILING STOP =====
    drop = ((active_trade["highest"] - price) / active_trade["highest"]) * 100
    if active_trade["locked"] and drop > 2:
        send(f"⚠️ EXIT TRAILING {symbol} +{profit:.2f}%")
        active_trade = None
        return

    # ===== STOP LOSS =====
    if price <= active_trade["stop"]:
        send(f"❌ STOP LOSS {symbol}")
        active_trade = None
        return

    # ===== TARGET =====
    if price >= active_trade["target"]:
        send(f"🎯 TARGET HIT {symbol} +{profit:.2f}%")
        active_trade = None

# ===== MAIN =====
def run():
    global active_trade, last_heartbeat

    send("🚀 V9 SINGLE TRADE BOT LIVE")

    while True:
        try:
            now = time.time()

            # heartbeat
            if now - last_heartbeat > 3600:
                send(f"💓 Alive {datetime.now(UTC).strftime('%H:%M:%S')}")
                last_heartbeat = now

            # ===== IF NO ACTIVE TRADE =====
            if not active_trade:
                stock = find_stock()

                if stock:
                    closes = get_data(stock)
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

Mode: SINGLE TRADE ACTIVE
""")

            else:
                manage_trade()

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print("ERROR:", e)
            time.sleep(5)

# ===== START =====
if __name__ == "__main__":
    run()
