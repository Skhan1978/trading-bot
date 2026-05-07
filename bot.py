import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time
import requests
from datetime import datetime, timedelta

# =========================
# SETTINGS
# =========================

SYMBOL = "PLTR"

TELEGRAM_BOT_TOKEN = "8268157455:AAElh_Fi0znhxEhVkwbK1Y2fhRMoUA65TI4"

TELEGRAM_CHAT_ID = "7216850185"

STOP_LOSS = -1.0
TAKE_PROFIT = 2.5

TRAILING_TRIGGER = 1.0
TRAILING_STOP = 0.5

MAX_TRADES_PER_DAY = 2
COOLDOWN_MINUTES = 15

CHECK_INTERVAL = 60

# =========================
# STATE VARIABLES
# =========================

in_position = False
entry_price = 0
highest_profit = 0

daily_trades = 0
last_trade_time = None

# =========================
# TELEGRAM
# =========================

def send_telegram(msg):

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg
    }

    try:
        requests.post(url, data=payload)
    except:
        pass

# =========================
# MARKET DATA
# =========================

def get_data():

    df = yf.download(
        tickers=SYMBOL,
        period="2d",
        interval="1m",
        auto_adjust=True,
        progress=False
    )

    df.dropna(inplace=True)

    return df

# =========================
# INDICATORS
# =========================

def calculate_indicators(df):

    df['EMA9'] = ta.ema(df['Close'], length=9)

    df['EMA20'] = ta.ema(df['Close'], length=20)

    macd = ta.macd(df['Close'])

    df['MACD_HIST'] = macd['MACDh_12_26_9']

    df['RSI'] = ta.rsi(df['Close'], length=14)

    df['VWAP'] = ta.vwap(
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        volume=df['Volume']
    )

    df['VOL_AVG'] = df['Volume'].rolling(20).mean()

    return df

# =========================
# BUY SIGNAL
# =========================

def buy_signal(df):

    latest = df.iloc[-1]

    price = latest['Close']

    trend_bullish = (
        price > latest['VWAP'] and
        latest['EMA9'] > latest['EMA20']
    )

    momentum_good = (
        latest['RSI'] > 40 and
        latest['MACD_HIST'] > 0
    )

    volume_spike = (
        latest['Volume'] >
        latest['VOL_AVG'] * 1.5
    )

    last3_red = (
        df['Close'].iloc[-1] < df['Open'].iloc[-1] and
        df['Close'].iloc[-2] < df['Open'].iloc[-2] and
        df['Close'].iloc[-3] < df['Open'].iloc[-3]
    )

    return (
        trend_bullish and
        momentum_good and
        volume_spike and
        not last3_red
    )

# =========================
# START BOT
# =========================

send_telegram("🤖 Stable Trading Bot Started")

while True:

    try:

        now = datetime.now()

        if now.hour == 0 and now.minute == 0:
            daily_trades = 0

        cooldown_active = False

        if last_trade_time:

            if datetime.now() < (
                last_trade_time +
                timedelta(minutes=COOLDOWN_MINUTES)
            ):
                cooldown_active = True

        df = get_data()

        if len(df) < 30:
            time.sleep(CHECK_INTERVAL)
            continue

        df = calculate_indicators(df)

        current_price = df['Close'].iloc[-1]

        # =====================
        # BUY
        # =====================

        if (
            not in_position and
            not cooldown_active and
            daily_trades < MAX_TRADES_PER_DAY
        ):

            if buy_signal(df):

                in_position = True
                entry_price = current_price
                highest_profit = 0

                daily_trades += 1
                last_trade_time = datetime.now()

                send_telegram(
                    f"🟢 BUY {SYMBOL}\n"
                    f"Price: ${current_price:.2f}"
                )

        # =====================
        # SELL MANAGEMENT
        # =====================

        elif in_position:

            profit_percent = (
                (current_price - entry_price)
                / entry_price
            ) * 100

            highest_profit = max(
                highest_profit,
                profit_percent
            )

            # STOP LOSS
            if profit_percent <= STOP_LOSS:

                send_telegram(
                    f"🔴 STOP LOSS HIT\n"
                    f"{SYMBOL}\n"
                    f"Price: ${current_price:.2f}\n"
                    f"Profit: {profit_percent:.2f}%"
                )

                in_position = False

            # TAKE PROFIT
            elif profit_percent >= TAKE_PROFIT:

                send_telegram(
                    f"💰 TAKE PROFIT HIT\n"
                    f"{SYMBOL}\n"
                    f"Price: ${current_price:.2f}\n"
                    f"Profit: {profit_percent:.2f}%"
                )

                in_position = False

            # TRAILING STOP
            elif (
                highest_profit >= TRAILING_TRIGGER and
                profit_percent <
                (highest_profit - TRAILING_STOP)
            ):

                send_telegram(
                    f"📉 TRAILING STOP HIT\n"
                    f"{SYMBOL}\n"
                    f"Price: ${current_price:.2f}\n"
                    f"Profit: {profit_percent:.2f}%"
                )

                in_position = False

            # LIVE UPDATE
            else:

                send_telegram(
                    f"📊 {SYMBOL}\n"
                    f"Price: ${current_price:.2f}\n"
                    f"Profit: {profit_percent:.2f}%"
                )

        time.sleep(CHECK_INTERVAL)

    except Exception as e:

        send_telegram(f"⚠️ ERROR: {str(e)}")

        time.sleep(60)
