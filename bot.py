import yfinance as yf
import requests
import time
from datetime import datetime
import pytz

# ================= CONFIG =================
TELEGRAM_TOKEN = "8268157455:AAF807pO5yASxEZ-RKSowuIA4LlGRWkE1Vs"
CHAT_ID = "7216850185"

SCAN_INTERVAL = 120
uk = pytz.timezone('Europe/London')

WATCHLIST = [
    "AAPL","TSLA","NVDA","AMD","META","AMZN","PLTR",
    "SOFI","NIO","RIVN","LCID","F","UBER"
]

# ================= TELEGRAM =================
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram error:", e)

# ================= ANALYSIS =================
def analyze(symbol):
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="1d", interval="1m")

        if data.empty:
            return None

        price = round(data["Close"].iloc[-1], 2)
        open_price = round(data["Open"].iloc[0], 2)

        change = ((price - open_price) / open_price) * 100

        # 🔥 ONLY STRONG BULLISH STOCKS
        if change < 1.5:
            return None

        # breakout logic
        recent_high = round(data["High"].tail(10).max(), 2)

        # avoid already broken stocks
        if price >= recent_high:
            return None

        breakout = round(recent_high, 2)
        stop = round(price * 0.97, 2)

        return {
            "symbol": symbol,
            "price": price,
            "change": round(change, 2),
            "breakout": breakout,
            "stop": stop
        }

    except Exception as e:
        print("Error:", e)
        return None

# ================= MAIN =================
def run():
    print("🔥 SNIPER BREAKOUT BOT ACTIVE")
    send_telegram("🚀 BOT LIVE - BREAKOUT MODE")

    sent = set()

    while True:
        now = datetime.now(uk)

        # FULL US SESSION
        if 9 <= now.hour <= 21:
            for symbol in WATCHLIST:

                if symbol in sent:
                    continue

                result = analyze(symbol)

                if result:
                    msg = f"""🔥 BREAKOUT SETUP

{result['symbol']}
Price: ${result['price']}
Change: {result['change']}%

👉 BUY ONLY IF breaks: ${result['breakout']}
🛑 Stop: ${result['stop']}

❌ Skip if weak or rejected
"""
                    send_telegram(msg)
                    sent.add(symbol)
                    time.sleep(1)

        time.sleep(SCAN_INTERVAL)

run()
