import warnings
warnings.filterwarnings("ignore")

import json
import os
import time
import gc
from datetime import datetime, UTC

import requests
import yfinance as yf

# =========================
# YFINANCE CACHE FIX
# =========================

yf.set_tz_cache_location("/tmp")

# =========================
# CONFIG
# =========================

TELEGRAM_TOKEN = "8268157455:AAElh_Fi0znhxEhVkwbK1Y2fhRMoUA65TI4"
CHAT_ID = "7216850185"

CHECK_INTERVAL = 900  # 15 minutes

WATCHLIST = [
    "AAPL",
    "NVDA",
    "MSFT",
    "AMD",
    "TSLA",
    "META",
    "AMZN",
    "GOOGL",
    "PLTR",
    "SOFI"
]

STATE_FILE = "state.json"

# =========================
# REQUEST SESSION
# =========================

session = requests.Session()

# =========================
# LOAD STATE
# =========================

def load_state():

    if os.path.exists(STATE_FILE):

        try:

            with open(STATE_FILE, "r") as f:
                return json.load(f)

        except:
            pass

    return {
        "startup_sent": False,
        "active_trade": None,
        "last_heartbeat": 0
    }

# =========================
# SAVE STATE
# =========================

def save_state():

    with open(STATE_FILE, "w") as f:

        json.dump(
            {
                "startup_sent": startup_sent,
                "active_trade": active_trade,
                "last_heartbeat": last_heartbeat
            },
            f
        )

# =========================
# GLOBAL STATE
# =========================

state = load_state()

startup_sent = state["startup_sent"]
active_trade = state["active_trade"]
last_heartbeat = state["last_heartbeat"]

# =========================
# TELEGRAM
# =========================

def send(msg):

    try:

        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

        session.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": msg
            },
            timeout=10
        )

    except Exception as e:

        print(f"Telegram error: {e}", flush=True)

# =========================
# MARKET DATA
# =========================

def get_data(symbol):

    try:

        df = yf.download(
            tickers=symbol,
            period="5d",
            interval="5m",
            progress=False,
            threads=False,
            auto_adjust=True
        )

        if df.empty:
            return None

        closes = df["Close"]

        # yfinance fix
        if hasattr(closes, "columns"):
            closes = closes.iloc[:, 0]

        closes = closes.dropna().values.tolist()

        del df
        gc.collect()

        return closes

    except Exception as e:

        print(f"DATA ERROR {symbol}: {e}", flush=True)
        return None

# =========================
# FIND BEST STOCK
# =========================

def find_stock():

    best_stock = None
    best_score = -999

    for symbol in WATCHLIST:

        closes = get_data(symbol)

        if not closes or len(closes) < 50:
            continue

        try:

            price = closes[-1]

            ma20 = sum(closes[-20:]) / 20
            ma50 = sum(closes[-50:]) / 50

            if price > ma20 > ma50:

                score = (price - ma20) / ma20

                if score > best_score:

                    best_score = score
                    best_stock = symbol

        except:
            pass

    if not best_stock:
        best_stock = "AAPL"

    return best_stock

# =========================
# MANAGE ACTIVE TRADE
# =========================

def manage_trade():

    global active_trade

    symbol = active_trade["symbol"]

    closes = get_data(symbol)

    if not closes:
        return

    price = closes[-1]

    # highest price
    if price > active_trade["highest"]:
        active_trade["highest"] = price

    # profit %
    profit = (
        (price - active_trade["entry"])
        / active_trade["entry"]
    ) * 100

    send(f"📊 {symbol} | ${price:.2f} | {profit:.2f}%")

    # lock profits
    if profit > 5 and not active_trade["locked"]:

        active_trade["locked"] = True

        send(
            f"🔒 LOCK PROFIT "
            f"{symbol} +{profit:.2f}%"
        )

    # trailing stop
    drop = (
        (active_trade["highest"] - price)
        / active_trade["highest"]
    ) * 100

    if active_trade["locked"] and drop > 2:

        send(
            f"⚠️ EXIT "
            f"{symbol} +{profit:.2f}%"
        )

        active_trade = None
        save_state()
        return

    # stop loss
    if price <= active_trade["stop"]:

        send(f"❌ STOP LOSS {symbol}")

        active_trade = None
        save_state()
        return

    # target hit
    if price >= active_trade["target"]:

        send(
            f"🎯 TARGET HIT "
            f"{symbol} +{profit:.2f}%"
        )

        active_trade = None
        save_state()

# =========================
# MAIN LOOP
# =========================

def run():

    global startup_sent
    global last_heartbeat
    global active_trade

    # send startup once
    if not startup_sent:

        send("🚀 BOT LIVE (Single Trade Manager)")

        startup_sent = True
        save_state()

    while True:

        try:

            now = time.time()

            # heartbeat every hour
            if now - last_heartbeat > 3600:

                send(
                    f"💓 Alive "
                    f"{datetime.now(UTC).strftime('%H:%M:%S UTC')}"
                )

                last_heartbeat = now
                save_state()

            # no active trade
            if not active_trade:

                stock = find_stock()

                closes = get_data(stock)

                if not closes:

                    time.sleep(CHECK_INTERVAL)
                    continue

                price = closes[-1]

                active_trade = {
                    "symbol": stock,
                    "entry": price,
                    "target": round(price * 1.12, 2),
                    "stop": round(price * 0.95, 2),
                    "highest": price,
                    "locked": False
                }

                save_state()

                send(
                    f"🚀 NEW TRADE: {stock}\n\n"
                    f"Entry: ${price:.2f}\n"
                    f"Target: ${price * 1.12:.2f}\n"
                    f"Stop: ${price * 0.95:.2f}\n\n"
                    f"Mode: Single Trade Active"
                )

            else:

                manage_trade()

            gc.collect()

            time.sleep(CHECK_INTERVAL)

        except Exception as e:

            print(f"MAIN ERROR: {e}", flush=True)

            gc.collect()

            time.sleep(30)

# =========================
# START
# =========================

if __name__ == "__main__":
    run()
