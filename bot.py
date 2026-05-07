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

CHECK_INTERVAL = 60

MAX_DAILY_LOSS = -3
MAX_TRADES_PER_DAY = 3
COOLDOWN_MINUTES = 90

WATCHLIST = [
    "NVDA",
    "MSFT",
    "META",
    "AMZN",
    "PLTR",
    "AMD",
    "TSLA"
]

yf.set_tz_cache_location("/tmp")

session = requests.Session()

active_trade = None
trade_history = []
last_trade_time = {}

daily_pnl = 0
daily_trade_count = 0

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

    except:
        pass

# =========================
# MARKET HOURS
# =========================

def market_open():

    now = datetime.datetime.utcnow()

    if now.weekday() >= 5:
        return False

    total = now.hour * 60 + now.minute

    return 13 * 60 + 30 <= total <= 20 * 60

# =========================
# DATA
# =========================

def get_df(symbol, interval="5m", period="5d"):

    try:

        df = yf.Ticker(symbol).history(
            period=period,
            interval=interval,
            auto_adjust=True
        )

        if df.empty:
            return None

        return df.dropna()

    except:
        return None

# =========================
# RSI
# =========================

def calculate_rsi(closes, period=14):

    if len(closes) < period + 1:
        return 50

    gains = []
    losses = []

    for i in range(1, len(closes)):

        diff = closes[i] - closes[i - 1]

        gains.append(max(diff, 0))
        losses.append(abs(min(diff, 0)))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):

        avg_gain = ((avg_gain * 13) + gains[i]) / 14
        avg_loss = ((avg_loss * 13) + losses[i]) / 14

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))

# =========================
# ATR
# =========================

def calculate_atr(df, period=14):

    highs = df["High"].tolist()
    lows = df["Low"].tolist()
    closes = df["Close"].tolist()

    trs = []

    for i in range(1, len(closes)):

        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )

        trs.append(tr)

    return sum(trs[-period:]) / period

# =========================
# MARKET FILTER
# =========================

def market_bullish():

    spy = get_df("SPY")

    if spy is None:
        return False

    closes = spy["Close"].tolist()

    if len(closes) < 50:
        return False

    ma20 = sum(closes[-20:]) / 20
    ma50 = sum(closes[-50:]) / 50

    rsi = calculate_rsi(closes)

    return (
        closes[-1] > ma20 > ma50
        and rsi > 55
    )

# =========================
# COOLDOWN
# =========================

def cooldown(symbol):

    if symbol not in last_trade_time:
        return False

    elapsed = (
        time.time() - last_trade_time[symbol]
    ) / 60

    return elapsed < COOLDOWN_MINUTES

# =========================
# FIND BEST STOCK
# =========================

def find_stock():

    best = None
    best_score = -999

    if not market_bullish():
        return None

    for symbol in WATCHLIST:

        if cooldown(symbol):
            continue

        df = get_df(symbol)

        if df is None:
            continue

        try:

            closes = df["Close"].tolist()
            volumes = df["Volume"].tolist()

            if len(closes) < 50:
                continue

            price = closes[-1]

            ema9 = sum(closes[-9:]) / 9
            ema20 = sum(closes[-20:]) / 20
            ma50 = sum(closes[-50:]) / 50

            rsi = calculate_rsi(closes)

            avg_volume = sum(volumes[-20:]) / 20
            current_volume = volumes[-1]

            relative_volume = current_volume / avg_volume

            recent_high = max(closes[-11:-1])

            atr = calculate_atr(df)

            trend = ema9 > ema20 > ma50
            strong_rsi = 55 <= rsi <= 68
            breakout = price > recent_high
            volume_ok = relative_volume > 1.3

            volatility_ok = (atr / price) < 0.025

            range_ok = (
                (max(closes[-5:]) - min(closes[-5:]))
                / price
            ) > 0.01

            # DAILY TREND CONFIRMATION
            daily = get_df(symbol, "1d", "3mo")

            if daily is None:
                continue

            daily_closes = daily["Close"].tolist()

            daily_ma20 = sum(daily_closes[-20:]) / 20

            daily_bull = (
                daily_closes[-1] > daily_ma20
            )

            if (
                trend
                and strong_rsi
                and breakout
                and volume_ok
                and volatility_ok
                and range_ok
                and daily_bull
            ):

                score = (
                    (relative_volume * 40)
                    + ((rsi - 50) * 2)
                    + (((price - ema20) / ema20) * 100)
                )

                if score > best_score:

                    best_score = score
                    best = symbol

        except:
            continue

    return best

# =========================
# MANAGE TRADE
# =========================

def manage_trade():

    global active_trade
    global daily_pnl

    symbol = active_trade["symbol"]

    df = get_df(symbol)

    if df is None:
        return

    price = df["Close"].tolist()[-1]

    if price > active_trade["highest"]:
        active_trade["highest"] = price

    profit = (
        (price - active_trade["entry"])
        / active_trade["entry"]
    ) * 100

    send(
        f"📊 {symbol}\n"
        f"Price: ${price:.2f}\n"
        f"PnL: {profit:.2f}%"
    )

    # BREAKEVEN

    if profit >= 2 and not active_trade["breakeven"]:

        active_trade["breakeven"] = True
        active_trade["stop"] = active_trade["entry"]

        send(f"🛡 Breakeven Enabled {symbol}")

    # PARTIAL PROFIT

    if profit >= 3 and not active_trade["partial"]:

        active_trade["partial"] = True

        send(f"💰 Partial Profit Taken {symbol}")

    # TRAILING STOP

    drop = (
        (active_trade["highest"] - price)
        / active_trade["highest"]
    ) * 100

    if profit > 2 and drop >= 1.2:

        send(f"⚠️ TRAILING EXIT {symbol} {profit:.2f}%")

        daily_pnl += profit

        last_trade_time[symbol] = time.time()

        active_trade = None

        return

    # STOP LOSS

    if price <= active_trade["stop"]:

        send(f"❌ STOP HIT {symbol} {profit:.2f}%")

        daily_pnl += profit

        last_trade_time[symbol] = time.time()

        active_trade = None

# =========================
# MAIN LOOP
# =========================

def run():

    global active_trade
    global daily_trade_count

    send("🤖 Stable Trading Bot Started")

    while True:

        try:

            if not market_open():

                time.sleep(300)
                continue

            if daily_trade_count >= MAX_TRADES_PER_DAY:

                time.sleep(600)
                continue

            if daily_pnl <= MAX_DAILY_LOSS:

                send("🛑 DAILY LOSS LIMIT HIT")

                time.sleep(1800)
                continue

            if not active_trade:

                stock = find_stock()

                if stock:

                    df = get_df(stock)

                    closes = df["Close"].tolist()

                    price = closes[-1]

                    atr = calculate_atr(df)

                    stop = round(
                        max(
                            price - (atr * 1.5),
                            price * 0.975
                        ),
                        2
                    )

                    target = round(
                        price + (atr * 3),
                        2
                    )

                    active_trade = {
                        "symbol": stock,
                        "entry": price,
                        "target": target,
                        "stop": stop,
                        "highest": price,
                        "breakeven": False,
                        "partial": False
                    }

                    daily_trade_count += 1

                    send(
                        f"🚀 HIGH PROBABILITY TRADE\n\n"
                        f"{stock}\n"
                        f"Entry: ${price:.2f}\n"
                        f"Target: ${target:.2f}\n"
                        f"Stop: ${stop:.2f}"
                    )

            else:

                manage_trade()

            gc.collect()

            time.sleep(CHECK_INTERVAL)

        except Exception as e:

            print(e)

            time.sleep(60)

if __name__ == "__main__":

    run()
