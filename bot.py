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
    "SOFI",
    "QQQ",
    "SPY"
]

# =========================
# YFINANCE FIX
# =========================

yf.set_tz_cache_location("/tmp")

# =========================
# GLOBALS
# =========================

active_trade = None
BOT_RUNNING = False

# =========================
# SESSION
# =========================

session = requests.Session()

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

        print("Telegram Error:", e)

# =========================
# MARKET HOURS
# =========================

def market_open():

    now = datetime.datetime.utcnow()

    # Monday-Friday
    if now.weekday() >= 5:
        return False

    total = now.hour * 60 + now.minute

    market_start = 13 * 60 + 30
    market_end = 20 * 60

    return market_start <= total <= market_end

# =========================
# MARKET DATA
# =========================

def get_dataframe(symbol):

    try:

        ticker = yf.Ticker(symbol)

        df = ticker.history(
            period="5d",
            interval="5m",
            auto_adjust=True,
            prepost=False
        )

        if df.empty:
            return None

        return df.dropna()

    except Exception as e:

        print(f"DATA ERROR {symbol}: {e}")

        return None

# =========================
# RSI
# =========================

def calculate_rsi(closes, period=14):

    if len(closes) < period + 1:
        return 50

    gains = []
    losses = []

    for i in range(1, period + 1):

        change = closes[-i] - closes[-i - 1]

        if change > 0:
            gains.append(change)
        else:
            losses.append(abs(change))

    avg_gain = sum(gains) / period if gains else 0.01
    avg_loss = sum(losses) / period if losses else 0.01

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi

# =========================
# MARKET TREND FILTER
# =========================

def market_bullish():

    spy = get_dataframe("SPY")

    if spy is None:
        return False

    closes = spy["Close"].tolist()

    if len(closes) < 50:
        return False

    ma20 = sum(closes[-20:]) / 20
    ma50 = sum(closes[-50:]) / 50

    return ma20 > ma50

# =========================
# FIND BEST STOCK
# =========================

def find_stock():

    # Avoid trading in weak market
    if not market_bullish():

        print("Market trend bearish")

        return None

    best_stock = None
    best_score = -999

    for symbol in WATCHLIST:

        if symbol in ["SPY", "QQQ"]:
            continue

        df = get_dataframe(symbol)

        if df is None:
            continue

        try:

            closes = df["Close"].tolist()
            volumes = df["Volume"].tolist()

            if len(closes) < 50:
                continue

            price = closes[-1]

            ma20 = sum(closes[-20:]) / 20
            ma50 = sum(closes[-50:]) / 50

            rsi = calculate_rsi(closes)

            avg_volume = sum(volumes[-20:]) / 20
            current_volume = volumes[-1]

            recent_high = max(closes[-10:])

            # =========================
            # ENTRY CONDITIONS
            # =========================

            bullish_trend = price > ma20 > ma50

            healthy_rsi = 45 <= rsi <= 65

            volume_spike = current_volume > avg_volume * 1.3

            breakout = price >= recent_high * 0.998

            # avoid extended moves
            not_overextended = (
                (price - ma20) / ma20
            ) < 0.04

            if (
                bullish_trend
                and healthy_rsi
                and volume_spike
                and breakout
                and not_overextended
            ):

                score = (
                    ((price - ma20) / ma20)
                    + (current_volume / avg_volume)
                )

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

    df = get_dataframe(symbol)

    if df is None:
        return

    closes = df["Close"].tolist()

    price = closes[-1]

    # update highest
    if price > active_trade["highest"]:
        active_trade["highest"] = price

    profit = (
        (price - active_trade["entry"])
        / active_trade["entry"]
    ) * 100

    send(
        f"📊 {symbol}\n"
        f"Price: ${price:.2f}\n"
        f"Profit: {profit:.2f}%"
    )

    # =========================
    # PROFIT LOCK
    # =========================

    if profit >= 4 and not active_trade["locked"]:

        active_trade["locked"] = True

        send(
            f"🔒 PROFIT LOCKED\n"
            f"{symbol} +{profit:.2f}%"
        )

    # =========================
    # TRAILING STOP
    # =========================

    drop = (
        (active_trade["highest"] - price)
        / active_trade["highest"]
    ) * 100

    if active_trade["locked"] and drop >= 1.5:

        send(
            f"⚠️ EXIT SIGNAL\n"
            f"{symbol} +{profit:.2f}%"
        )

        active_trade = None
        return

    # =========================
    # HARD STOP LOSS
    # =========================

    if price <= active_trade["stop"]:

        send(
            f"❌ STOP LOSS HIT\n"
            f"{symbol} {profit:.2f}%"
        )

        active_trade = None
        return

    # =========================
    # TARGET HIT
    # =========================

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

    if BOT_RUNNING:

        print("Bot already running")
        return

    BOT_RUNNING = True

    active_trade = None

    send("🤖 Advanced Trading Bot Started")

    while True:

        try:

            # market closed
            if not market_open():

                print("Market Closed")

                time.sleep(300)
                continue

            # =========================
            # NEW TRADE
            # =========================

            if not active_trade:

                stock = find_stock()

                if not stock:

                    print("No quality setup found")

                    time.sleep(CHECK_INTERVAL)
                    continue

                df = get_dataframe(stock)

                if df is None:

                    time.sleep(CHECK_INTERVAL)
                    continue

                closes = df["Close"].tolist()

                price = closes[-1]

                active_trade = {
                    "symbol": stock,
                    "entry": price,
                    "target": round(price * 1.10, 2),
                    "stop": round(price * 0.97, 2),
                    "highest": price,
                    "locked": False
                }

                send(
                    f"🚀 HIGH QUALITY TRADE: {stock}\n\n"
                    f"Entry: ${price:.2f}\n"
                    f"Target: ${price * 1.10:.2f}\n"
                    f"Stop: ${price * 0.97:.2f}"
                )

            # =========================
            # MANAGE TRADE
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
# START
# =========================

if __name__ == "__main__":

    run()
