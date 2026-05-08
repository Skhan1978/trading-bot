print("🚀 BOT STARTING...")

import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
import warnings
import pytz

from datetime import datetime, timedelta

warnings.filterwarnings("ignore")

# =====================================
# SETTINGS
# =====================================

SYMBOL = "PLTR"

TELEGRAM_BOT_TOKEN = "8268157455:AAElh_Fi0znhxEhVkwbK1Y2fhRMoUA65TI4"
TELEGRAM_CHAT_ID = "7216850185"

STOP_LOSS = -1.5
TAKE_PROFIT = 4.0

TRAILING_TRIGGER = 2.0
TRAILING_STOP = 1.0

MAX_TRADES_PER_DAY = 5

COOLDOWN_MINUTES = 15

CHECK_INTERVAL = 300  # 5 minutes

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

    try:

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }

        response = requests.post(
            url,
            data=payload,
            timeout=15
        )

        print("Telegram sent:", response.status_code)

    except Exception as e:

        print("Telegram Error:", e)

# =====================================
# MARKET HOURS
# =====================================

def market_open():

    eastern = pytz.timezone('US/Eastern')

    now = datetime.now(eastern)

    if now.weekday() >= 5:
        return False

    current = now.hour * 60 + now.minute

    market_start = 9 * 60 + 35
    market_end = 15 * 60 + 55

    return market_start <= current <= market_end

# =====================================
# DATA
# =====================================

def get_data():

    try:

        df = yf.download(
            tickers=SYMBOL,
            period="5d",
            interval="5m",
            auto_adjust=True,
            progress=False,
            threads=False
        )

        if df.empty:
            return None

        df.dropna(inplace=True)

        return df

    except Exception as e:

        print("DATA ERROR:", e)

        return None

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

    df['EMA9'] = df['Close'].ewm(span=9).mean()

    df['EMA20'] = df['Close'].ewm(span=20).mean()

    ema12 = df['Close'].ewm(span=12).mean()

    ema26 = df['Close'].ewm(span=26).mean()

    df['MACD'] = ema12 - ema26

    signal = df['MACD'].ewm(span=9).mean()

    df['MACD_HIST'] = df['MACD'] - signal

    df['RSI'] = calculate_rsi(df['Close'])

    typical_price = (
        df['High']
        + df['Low']
        + df['Close']
    ) / 3

    cumulative_tp_vol = (
        typical_price * df['Volume']
    ).cumsum()

    cumulative_vol = df['Volume'].cumsum()

    df['VWAP'] = cumulative_tp_vol / cumulative_vol

    df['VOL_AVG'] = (
        df['Volume']
        .rolling(20)
        .mean()
    )

    return df

# =====================================
# BUY SIGNAL
# =====================================

def buy_signal(df):

    latest = df.iloc[-1]

    price = latest['Close']

    bullish_trend = (

        price > latest['VWAP']

        and latest['EMA9'] > latest['EMA20']
    )

    momentum_good = (

        latest['MACD_HIST'] > 0

        and latest['RSI'] > 52

        and latest['RSI'] < 75
    )

    volume_good = (

        latest['Volume']
        > latest['VOL_AVG'] * 1.05
    )

    strong_candle = (

        latest['Close']
        > latest['Open']
    )

    return (

        bullish_trend

        and momentum_good

        and volume_good

        and strong_candle
    )

# =====================================
# STARTUP ALERT
# =====================================

send_telegram(f"🚀 {SYMBOL} BOT LIVE")

# =====================================
# MAIN LOOP
# =====================================

while True:

    try:

        now = datetime.now()

        # =====================================
        # MARKET HOURS
        # =====================================

        if not market_open():

            print("Market closed")

            time.sleep(300)

            continue

        # =====================================
        # RESET TRADES DAILY
        # =====================================

        if now.hour == 0 and now.minute == 0:

            daily_trades = 0

        # =====================================
        # COOLDOWN
        # =====================================

        cooldown_active = False

        if last_trade_time:

            if datetime.now() < (

                last_trade_time
                + timedelta(minutes=COOLDOWN_MINUTES)
            ):

                cooldown_active = True

        # =====================================
        # GET DATA
        # =====================================

        df = get_data()

        if df is None or len(df) < 30:

            print("Waiting for data")

            time.sleep(CHECK_INTERVAL)

            continue

        df = calculate_indicators(df)

        current_price = float(df['Close'].iloc[-1])

        latest = df.iloc[-1]

        print(
            f"{SYMBOL} | "
            f"Price: {current_price:.2f} | "
            f"RSI: {latest['RSI']:.1f}"
        )

        # =====================================
        # BUY ENTRY
        # =====================================

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

                send_telegram(

                    f"🟢 BUY SIGNAL\n\n"

                    f"Stock: {SYMBOL}\n"

                    f"Entry: ${current_price:.2f}\n"

                    f"RSI: {latest['RSI']:.1f}\n"

                    f"Volume Surge Detected\n"

                    f"Momentum Bullish"
                )

        # =====================================
        # POSITION MANAGEMENT
        # =====================================

        elif in_position:

            profit_percent = (

                (current_price - entry_price)
                / entry_price
            ) * 100

            highest_profit = max(
                highest_profit,
                profit_percent
            )

            print(f"PnL: {profit_percent:.2f}%")

            # STOP LOSS
            if profit_percent <= STOP_LOSS:

                send_telegram(

                    f"🔴 STOP LOSS\n\n"

                    f"{SYMBOL}\n"

                    f"Exit: ${current_price:.2f}\n"

                    f"PnL: {profit_percent:.2f}%"
                )

                in_position = False

            # TAKE PROFIT
            elif profit_percent >= TAKE_PROFIT:

                send_telegram(

                    f"💰 TAKE PROFIT\n\n"

                    f"{SYMBOL}\n"

                    f"Exit: ${current_price:.2f}\n"

                    f"PnL: {profit_percent:.2f}%"
                )

                in_position = False

            # TRAILING STOP
            elif (

                highest_profit >= TRAILING_TRIGGER

                and profit_percent
                < (highest_profit - TRAILING_STOP)
            ):

                send_telegram(

                    f"📉 TRAILING STOP\n\n"

                    f"{SYMBOL}\n"

                    f"Exit: ${current_price:.2f}\n"

                    f"PnL: {profit_percent:.2f}%"
                )

                in_position = False

            # POSITION UPDATE
            elif (

                now.minute % 15 == 0

                and now.minute != last_update_minute
            ):

                last_update_minute = now.minute

                send_telegram(

                    f"📊 OPEN POSITION\n\n"

                    f"{SYMBOL}\n"

                    f"Price: ${current_price:.2f}\n"

                    f"PnL: {profit_percent:.2f}%\n"

                    f"Highest: {highest_profit:.2f}%"
                )

        # =====================================
        # WAIT
        # =====================================

        time.sleep(CHECK_INTERVAL)

    except Exception as e:

        print("MAIN LOOP ERROR:", e)

        send_telegram(

            f"⚠️ BOT ERROR\n\n{str(e)}"
        )

        time.sleep(60)
