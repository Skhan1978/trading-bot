print("BOT STARTING...")

import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time

from datetime import datetime, timedelta

# =====================================
# SETTINGS
# =====================================

SYMBOL = "PLTR"

TELEGRAM_BOT_TOKEN = "8268157455:AAElh_Fi0znhxEhVkwbK1Y2fhRMoUA65TI4"
TELEGRAM_CHAT_ID = "7216850185"

STOP_LOSS = -1.2
TAKE_PROFIT = 3.0

TRAILING_TRIGGER = 1.5
TRAILING_STOP = 0.7

MAX_TRADES_PER_DAY = 3

COOLDOWN_MINUTES = 20

CHECK_INTERVAL = 60

# =====================================
# STATE VARIABLES
# =====================================

in_position = False
entry_price = 0
highest_profit = 0

daily_trades = 0
last_trade_time = None
last_update_minute = -1

# =====================================
# TELEGRAM
# =====================================

def send_telegram(message):

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }

    try:
        requests.post(url, data=payload)

    except Exception as e:
        print(e)

# =====================================
# GET DATA
# =====================================

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

# =====================================
# RSI
# =====================================

def calculate_rsi(series, period=14):

    delta = series.diff()

    gain = delta.where(delta > 0, 0)

    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(period).mean()

    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi

# =====================================
# INDICATORS
# =====================================

def calculate_indicators(df):

    # EMA
    df['EMA9'] = df['Close'].ewm(span=9).mean()
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()

    # MACD
    ema12 = df['Close'].ewm(span=12).mean()
    ema26 = df['Close'].ewm(span=26).mean()

    df['MACD'] = ema12 - ema26

    signal = df['MACD'].ewm(span=9).mean()

    df['MACD_HIST'] = df['MACD'] - signal

    # RSI
    df['RSI'] = calculate_rsi(df['Close'])

    # VWAP
    typical_price = (
        df['High'] +
        df['Low'] +
        df['Close']
    ) / 3

    cumulative_tp_vol = (
        typical_price * df['Volume']
    ).cumsum()

    cumulative_vol = df['Volume'].cumsum()

    df['VWAP'] = cumulative_tp_vol / cumulative_vol

    # Volume average
    df['VOL_AVG'] = df['Volume'].rolling(20).mean()

    return df

# =====================================
# MARKET HOURS FILTER
# =====================================

def market_open():

    now = datetime.now()

    hour = now.hour
    minute = now.minute

    current = hour * 60 + minute

    market_start = 9 * 60 + 35
    market_end = 15 * 60 + 45

    return market_start <= current <= market_end

# =====================================
# BUY SIGNAL
# =====================================

def buy_signal(df):

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    price = latest['Close']

    # Strong trend confirmation
    bullish_trend = (
        price > latest['VWAP']
        and latest['EMA9'] > latest['EMA20']
        and latest['EMA20'] > latest['EMA50']
    )

    # Momentum confirmation
    momentum_good = (
        45 < latest['RSI'] < 70
        and latest['MACD_HIST'] > 0
    )

    # Volume confirmation
    volume_good = (
        latest['Volume']
        > latest['VOL_AVG'] * 1.3
    )

    # Pullback continuation setup
    bullish_recovery = (
        previous['Close'] < previous['EMA9']
        and latest['Close'] > latest['EMA9']
    )

    # Avoid weak candles
    strong_candle = (
        latest['Close'] > latest['Open']
    )

    return (
        bullish_trend
        and momentum_good
        and volume_good
        and bullish_recovery
        and strong_candle
    )

# =====================================
# START BOT
# =====================================

send_telegram(f"🤖 {SYMBOL} Trading Bot Started")

while True:

    try:

        now = datetime.now()

        # Only trade during market hours
        if not market_open():

            time.sleep(60)

            continue

        # Reset daily trades
        if now.hour == 0 and now.minute == 0:

            daily_trades = 0

        cooldown_active = False

        # Cooldown
        if last_trade_time:

            if datetime.now() < (
                last_trade_time
                + timedelta(minutes=COOLDOWN_MINUTES)
            ):

                cooldown_active = True

        # Get Data
        df = get_data()

        if len(df) < 60:

            time.sleep(CHECK_INTERVAL)

            continue

        # Indicators
        df = calculate_indicators(df)

        current_price = df['Close'].iloc[-1]

        # =================================
        # BUY
        # =================================

        if (
            not in_position
            and not cooldown_active
            and daily_trades < MAX_TRADES_PER_DAY
        ):

            if buy_signal(df):

                in_position = True

                entry_price = current_price

                highest_profit = 0

                daily_trades += 1

                last_trade_time = datetime.now()

                latest = df.iloc[-1]

                send_telegram(
                    f"🟢 BUY SIGNAL\n\n"
                    f"Stock: {SYMBOL}\n"
                    f"Entry: ${current_price:.2f}\n"
                    f"RSI: {latest['RSI']:.1f}\n"
                    f"Volume Spike Confirmed\n"
                    f"Trend: Bullish"
                )

        # =================================
        # POSITION MANAGEMENT
        # =================================

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
                    f"🔴 STOP LOSS HIT\n\n"
                    f"{SYMBOL}\n"
                    f"Exit: ${current_price:.2f}\n"
                    f"PnL: {profit_percent:.2f}%"
                )

                in_position = False

            # TAKE PROFIT
            elif profit_percent >= TAKE_PROFIT:

                send_telegram(
                    f"💰 TAKE PROFIT HIT\n\n"
                    f"{SYMBOL}\n"
                    f"Exit: ${current_price:.2f}\n"
                    f"PnL: {profit_percent:.2f}%"
                )

                in_position = False

            # TRAILING STOP
            elif (
                highest_profit >= TRAILING_TRIGGER
                and profit_percent <
                (highest_profit - TRAILING_STOP)
            ):

                send_telegram(
                    f"📉 TRAILING STOP HIT\n\n"
                    f"{SYMBOL}\n"
                    f"Exit: ${current_price:.2f}\n"
                    f"PnL: {profit_percent:.2f}%"
                )

                in_position = False

            # Update every 15 minutes only
            elif now.minute % 15 == 0 and now.minute != last_update_minute:

                last_update_minute = now.minute

                send_telegram(
                    f"📊 OPEN POSITION\n\n"
                    f"{SYMBOL}\n"
                    f"Price: ${current_price:.2f}\n"
                    f"PnL: {profit_percent:.2f}%\n"
                    f"Highest: {highest_profit:.2f}%"
                )

        time.sleep(CHECK_INTERVAL)

    except Exception as e:

        send_telegram(f"⚠️ ERROR: {str(e)}")

        time.sleep(60)
