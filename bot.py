import yfinance as yf
import requests
import time

TELEGRAM_TOKEN = "8268157455:AAF807pO5yASxEZ-RKSowuIA4LlGRWkE1Vs"
CHAT_ID = "7216850185"

WATCHLIST = ["AAPL","TSLA","AMD","NVDA","META","AMZN"]

def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def analyze(symbol):
    stock = yf.Ticker(symbol)

    data_1h = stock.history(period="5d", interval="1h")

    if data_1h.empty:
        return None

    price = round(data_1h["Close"].iloc[-1], 2)

    # Moving average
    ma = data_1h["Close"].rolling(20).mean().iloc[-1]

    # Trend check
    if price < ma:
        return None

    # Pullback condition
    recent_high = data_1h["High"].tail(20).max()

    if price > recent_high * 0.98:
        return None  # avoid top entries

    entry_low = round(price * 0.99, 2)
    entry_high = round(price * 1.01, 2)

    target = round(price * 1.05, 2)
    stop = round(price * 0.96, 2)

    return {
        "symbol": symbol,
        "price": price,
        "entry": f"{entry_low}-{entry_high}",
        "target": target,
        "stop": stop
    }

def run():
    send("🚀 SWING BOT ACTIVE (HALAL MODE)")

    while True:
        for s in WATCHLIST:
            result = analyze(s)

            if result:
                msg = f"""📊 SWING BUY SIGNAL

{result['symbol']}
Price: ${result['price']}

✅ BUY: ${result['entry']}
🎯 TARGET: ${result['target']}
🛑 STOP: ${result['stop']}
"""
                send(msg)
                time.sleep(2)

        time.sleep(900)

run()
