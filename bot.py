import yfinance as yf
import requests
import time
from datetime import datetime
import pytz

# TELEGRAM
TELEGRAM_TOKEN = "8268157455:AAF807pO5yASxEZ-RKSowuIA4LlGRWkE1Vs"
CHAT_ID = "7216850185"

uk = pytz.timezone('Europe/London')

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ================= STOCK LIST =================
WATCHLIST = [
    "AAPL","TSLA","NVDA","AMD","META","AMZN","PLTR",
    "SOFI","NIO","RIVN","LCID","F","T","UBER"
]

# ================= LOGIC =================
def analyze(symbol):
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="1d", interval="1m")

        if data.empty:
            return None

        price = round(data["Close"].iloc[-1], 2)
        open_price = round(data["Open"].iloc[0], 2)

        change = ((price - open_price) / open_price) * 100

        # Only send movers
        if abs(change) < 1:
            return None

        entry_low = round(price * 0.99, 2)
        entry_high = round(price * 1.01, 2)
        breakout = round(price * 1.02, 2)
        stop = round(price * 0.97, 2)

        return {
            "symbol": symbol,
            "price": price,
            "change": round(change, 2),
            "entry": f"${entry_low}-{entry_high}",
            "breakout": breakout,
            "stop": stop
        }

    except Exception as e:
        print("Error:", e)
        return None

# ================= MAIN =================
def run():
    print("🔥 REAL MARKET BOT ACTIVE")
    send_telegram("🚀 BOT LIVE - STABLE MODE")

    sent = set()

    while True:
        now = datetime.now(uk)

        if 9 <= now.hour <= 21:
            for symbol in WATCHLIST:
                if symbol in sent:
                    continue

                result = analyze(symbol)

                if result:
                    msg = f"""🔥 TRADE SIGNAL

{result['symbol']}
Price: ${result['price']}
Change: {result['change']}%

🎯 Entry: {result['entry']}
🚀 Breakout: ${result['breakout']}
🛑 Stop: ${result['stop']}
"""
                    send_telegram(msg)
                    sent.add(symbol)
                    time.sleep(1)

        time.sleep(120)

run()
