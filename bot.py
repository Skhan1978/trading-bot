import requests
import time
from datetime import datetime
import pytz

# CONFIG
API_KEY = "wg6hAv7crwZdlFQcmoYwKdYqnK0cXaXD"
TELEGRAM_TOKEN = "8268157455:AAF807pO5yASxEZ-RKSowuIA4LlGRWkE1Vs"
CHAT_ID = "7216850185"

SCAN_INTERVAL = 180
uk = pytz.timezone('Europe/London')

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except:
        pass

def get_gainers():
    url = f"https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey={API_KEY}"
    return requests.get(url).json()

def analyze(stock):
    price = stock.get("price", 0)
    change = stock.get("changesPercentage", 0)
    volume = stock.get("volume", 0)

    # Ignore weak junk
    if volume < 300000:
        return None

    # Strong sniper
    if price < 5 and change >= 20:
        entry_low = round(price * 0.97, 2)
        entry_high = round(price * 1.02, 2)
        breakout = round(price * 1.05, 2)
        stop = round(price * 0.90, 2)

        return {
            "type": "SNIPER",
            "entry": f"${entry_low} - ${entry_high}",
            "breakout": f"${breakout}",
            "stop": f"${stop}"
        }

    # Watchlist
    elif change >= 10:
        return {"type": "WATCH"}

    return None

def run():
    print("🔥 SNIPER PRO BOT ACTIVE")
    send_telegram("🚀 SNIPER PRO BOT LIVE")

    sent = set()

    while True:
        now = datetime.now(uk)

        if 9 <= now.hour <= 14:
            try:
                stocks = get_gainers()

                for stock in stocks[:15]:
                    symbol = stock.get("symbol")

                    if symbol in sent:
                        continue

                    result = analyze(stock)

                    if result:
                        if result["type"] == "SNIPER":
                            msg = f"""🔥 SNIPER SETUP

{symbol}
Price: ${stock.get('price')}
Change: {stock.get('changesPercentage')}%
Volume: {stock.get('volume')}

🎯 Entry: {result['entry']}
🚀 Breakout: {result['breakout']}
🛑 Stop Loss: {result['stop']}
"""
                        else:
                            msg = f"""⚠️ WATCHLIST

{symbol}
Price: ${stock.get('price')}
Change: {stock.get('changesPercentage')}%
"""

                        send_telegram(msg)
                        sent.add(symbol)
                        time.sleep(1)

            except Exception as e:
                print("Error:", e)

        time.sleep(SCAN_INTERVAL)

run()
