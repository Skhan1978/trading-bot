import warnings
warnings.filterwarnings("ignore")

import time
import gc
import datetime
import requests
import yfinance as yf

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

# =========================
# FIX YFINANCE CACHE
# =========================

yf.set_tz_cache_location("/tmp")

# =========================
# GLOBAL STATE
# =========================

active_trade = None
BOT_RUNNING = False

# =========================
# REQUEST SESSION
# =========================

session = requests.Session()

# =========================
# TELEGRAM
# =========================

def send(msg):

    try:

        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

        response = session.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": msg
            },
            timeout=10
        )

        if response.status_code != 200:
            print("Telegram Error:", response.text)

    except Exception as e:

        print("Telegram Send Error:", e)

# =========================
# MARKET HOURS
# =========================

def market_open():

    now = datetime.datetime.utcnow()

    # Monday-Friday only
    if now.weekday() >= 5:
        return False

    total_minutes = now.hour * 60 + now.minute

    # US market hours
    market_start = 13 * 60 + 30
    market_end = 20 * 60

    return market_start <= total_minutes <= market_end

# =========================
# GET MARKET DATA
# =========================

def get_data(symbol):

    try:

        ticker = yf.Ticker(symbol)

        df = ticker.history(
            period="2d",
            interval="1m",
            auto_adjust=True,
            prepost=True
        )

        if df.empty:
            return None

        closes = df["Close"].dropna().tolist()

        del df
        gc.collect()

        return closes

    except Exception as e:

        print(f"DATA ERROR {symbol}: {e}")

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

            # Bullish setup
            if price > ma20 > ma50:

                score = (price - ma20) / ma20

                if score > best_score:

                    best_score = score
                    best_stock = symbol

        except Exception as e:

            print(f"SCAN ERROR {symbol}: {e}")

    return best_stock

# =========================
# MANAGE TRADE
# =========================

def manage_trade():

    global active_trade

    symbol = active_trade["symbol"]

    closes = get_data(symbol)

    if not closes:
        return

    price = closes[-1]

    # Update highest price
    if price > active_trade["highest"]:
        active_trade["highest"] = price

    # Profit %
    profit = (
        (price - active_trade["entry"])
        / active_trade["entry"]
    ) * 100

    send(
        f"📊 {symbol}\n"
        f"Price: ${price:.2f}\n"
        f"Profit: {profit:.2f}%"
    )

    # Lock profits
    if profit >= 5 and not active_trade["locked"]:

        active_trade["locked"] = True

        send(
            f"🔒 LOCK PROFIT\n"
            f"{symbol} +{profit:.2f}%"
        )

    # Trailing stop
    drop = (
        (active_trade["highest"] - price)
        / active_trade["highest"]
    ) * 100

    if active_trade["locked"] and drop >= 2:

        send(
            f"⚠️ EXIT SIGNAL\n"
            f"{symbol} +{profit:.2f}%"
        )

        active_trade = None
        return

    # Stop loss
    if price <= active_trade["stop"]:

        send(
            f"❌ STOP LOSS HIT\n"
            f"{symbol} {profit:.2f}%"
        )

        active_trade = None
        return

    # Target hit
    if price >= active_trade["target"]:

        send(
            f"🎯 TARGET HIT\n"
            f"{symbol} +{profit:.2f}%"
        )

        active_trade = None

# =========================
# MAIN LOOP
# =========================

def run():

    global active_trade
    global BOT_RUNNING

    # Prevent duplicate loops
    if BOT_RUNNING:

        print("Bot already running")
        return

    BOT_RUNNING = True

    # Reset stale trades
    active_trade = None

    send("🤖 Trading Bot Started")

    while True:

        try:

            # Skip if market closed
            if not market_open():

                print("Market Closed")

                time.sleep(300)
                continue

            # =========================
            # FIND NEW TRADE
            # =========================

            if not active_trade:

                stock = find_stock()

                if not stock:

                    print("No valid stock found")

                    time.sleep(CHECK_INTERVAL)
                    continue

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
                    f"Stop: ${price * 0.95:.2f}"
                )

            # =========================
            # MANAGE CURRENT TRADE
            # =========================

            else:

                manage_trade()

            gc.collect()

            time.sleep(CHECK_INTERVAL)

        except Exception as e:

            print("MAIN ERROR:", e)

            gc.collect()

            time.sleep(60)

# =========================
# START BOT
# =========================

if __name__ == "__main__":

    run()
