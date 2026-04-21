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

    # 1H data
    data = stock.history(period="5d", interval="1h")

    if data.empty:
        return None

    price = round(data["Close"].iloc[-1], 2)

    # EMAs
    ema20 = data["Close"].ewm(span=20).mean().iloc[-1]
    ema50 = data["Close"].ewm(span=50).mean().iloc[-1]

    # ================= TREND FILTER =================
    if not (price > ema20 > ema50):
        return None

    # ================= PULLBACK CONDITION =================
    # Price must be near EMA20 (not far away)
    if abs(price - ema20) / price > 0.015:
        return None

    # ================= ENTRY =================
    entry_low = round(ema20 * 0.995, 2)
    entry_high = round(ema20 * 1.005, 2)

    # ================= TARGET =================
    target = round(price * 1.05, 2)

    # ================= STOP =================
    stop = round(ema50 * 0.98, 2)

    return {
        "symbol": symbol,
        "price": price,
        "entry": f"{entry_low}-{entry_high}",
        "target": target,
        "stop": stop
    }

def run():
    send("🚀 SWING EMA BOT ACTIVE")

    sent = set()

    while True:
        for s in WATCHLIST:

            result = analyze(s)

            if result and s not in sent:

                msg = f"""📊 SWING BUY (EMA SETUP)

{result['symbol']}
Price: ${result['price']}

✅ BUY near EMA20: ${result['entry']}
🎯 TARGET (2–3 days): ${result['target']}
🛑 STOP: ${result['stop']}

📌 Rule:
- Only buy on pullback
- Do NOT chase green candles
"""

                send(msg)
                sent.add(s)
                time.sleep(2)

        time.sleep(900)

run()
