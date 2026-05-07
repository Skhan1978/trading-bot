import os
import time
import gc
from datetime import datetime, UTC

import requests
import yfinance as yf

# =========================
# CONFIG
# =========================

TELEGRAM_TOKEN ="8268157455:AAElh_Fi0znhxEhVkwbK1Y2fhRMoUA65TI4"
CHAT_ID = "7216850185"

CHECK_INTERVAL = 300  # 5 minutes

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

# =========================
# STATE
# =========================

active_trade = None
last_heartbeat = 0

# =========================
# REQUEST SESSION
# =========================

session = requests.Session()

# =========================
# TELEGRAM
# =========================

def send(msg):

    try:
        # debug info
        print("TOKEN:", TELEGRAM_TOKEN, flush=True)
        print("CHAT_ID:", CHAT_ID, flush=True)

        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

        response = session.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": msg
            },
            timeout=10
        )

        print("TELEGRAM STATUS:", response.status_code, flush=True)
        print("TELEGRAM RESPONSE:", response.text, flush=True)

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

        # Fix newer yfinance versions
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
# STOCK SCANNER
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

            # bullish trend
            if price > ma20 > ma50:

                score = (price - ma20) / ma20

                if score > best_score:
                    best_score = score
                    best_stock = symbol

        except Exception as e:
            print(f"SCAN ERROR {symbol}: {e}", flush=True)

    # fallback
    if not best_stock:
        best_stock = "AAPL"

    print(f"Selected stock: {best_stock}", flush=True)

    return best_stock

# =========================
# TRADE MANAGEMENT
# =========================

def manage_trade():

    global active_trade

    symbol = active_trade["symbol"]

    closes = get_data(symbol)

    if not closes:
        return

    price = closes[-1]

    # highest price update
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
            f"⚠️ EXIT (Trailing) "
            f"{symbol} +{profit:.2f}%"
        )

        active_trade = None
        gc.collect()
        return

    # stop loss
    if price <= active_trade["stop"]:

        send(
            f"❌ STOP LOSS "
            f"{symbol} at ${price:.2f}"
        )

        active_trade = None
        gc.collect()
        return

    # target hit
    if price >= active_trade["target"]:

        send(
            f"🎯 TARGET HIT "
            f"{symbol} +{profit:.2f}%"
        )

        active_trade = None
        gc.collect()

# =========================
# MAIN LOOP
# =========================

def run():

    global active_trade
    global last_heartbeat

    send("🚀 BOT LIVE (Single Trade Manager)")

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

            # =========================
            # FIND NEW TRADE
            # =========================

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

            time.sleep(10)

# =========================
# START
# =========================

if __name__ == "__main__":
    run()
