import requests
import time
from datetime import datetime
import pytz

# TELEGRAM CONFIG
TELEGRAM_TOKEN = "8268157455:AAF807pO5yASxEZ-RKSowuIA4LlGRWkE1Vs"
CHAT_ID = "7216850185"

SCAN_INTERVAL = 120
uk = pytz.timezone('Europe/London')

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except Exception as e:
        print("Telegram error:", e)

# ================= DATA (Yahoo Finance) =================
def get_stocks():
    url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
    params = {
        "scrIds": "day_gainers",
        "count": 25
    }

    try:
        res = requests.get(url, params=params).json()
        quotes = res["finance"]["result"][0]["quotes"]
        return quotes
    except Exception as e:
        print("Yahoo error:", e)
        return []

# ================= LOGIC =================
def analyze(stock):
    symbol = stock.get("symbol")
    price = stock.get("regularMarketPrice", 0)
    change = stock.get("regularMarketChangePercent", 0)
    volume = stock.get("regularMarketVolume", 0)

    if not price or not change:
        return None

    # filter real movers
    if change < 5 or volume < 200000:
        return None

    entry_low = round(price * 0.98, 2)
    entry_high = round(price * 1.02, 2)
    breakout = round(price * 1.05, 2)
    stop = round(price * 0.93, 2)

    return {
        "symbol": symbol,
        "price": price,
        "change": round(change, 2),
        "volume": volume,
        "entry": f"${entry_low} - ${entry_high}",
        "breakout": f"${breakout}",
        "stop": f"${stop}"
    }

# ================= MAIN =================
def run():
    print("🔥 LIVE YAHOO BOT")
    send_telegram("🚀 BOT LIVE - REAL DATA MODE")

    sent = set()

    while True:
        now = datetime.now(uk)

        # FULL US SESSION
        if 9 <= now.hour <= 21:
            try:
                stocks = get_stocks()

                for stock in stocks:
                    result = analyze(stock)

                    if result and result["symbol"] not in sent:
                        msg = f"""🔥 TODAY TRADE

{result['symbol']}
Price: ${result['price']}
Change: {result['change']}%
Volume: {result['volume']}

🎯 Entry: {result['entry']}
🚀 Breakout: {result['breakout']}
🛑 Stop: {result['stop']}
"""

                        send_telegram(msg)
                        sent.add(result["symbol"])
                        time.sleep(1)

            except Exception as e:
                print("Error:", e)

        time.sleep(SCAN_INTERVAL)

run()
