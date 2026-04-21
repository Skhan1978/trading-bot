import requests
import time
from datetime import datetime
import pytz

# CONFIG
API_KEY = "wg6hAv7crwZdlFQcmoYwKdYqnK0cXaXD"
TELEGRAM_TOKEN = "8268157455:AAF807pO5yASxEZ-RKSowuIA4LlGRWkE1Vs"
CHAT_ID = "7216850185"

SCAN_INTERVAL = 120  # faster scans (2 min)
uk = pytz.timezone('Europe/London')

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except Exception as e:
        print("Telegram error:", e)

def get_stocks():
    gainers_url = f"https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey={API_KEY}"
    active_url = f"https://financialmodelingprep.com/api/v3/stock_market/actives?apikey={API_KEY}"

    gainers = requests.get(gainers_url).json()
    active = requests.get(active_url).json()

    return gainers[:10] + active[:10]

def analyze(stock):
    price = stock.get("price", 0)
    change = stock.get("changesPercentage", 0)
    volume = stock.get("volume", 0)

    if volume < 100000:
        return None

    # SNIPER (more flexible)
    if change >= 10:
        entry_low = round(price * 0.98, 2)
        entry_high = round(price * 1.03, 2)
        breakout = round(price * 1.05, 2)
        stop = round(price * 0.93, 2)

        return {
            "type": "SNIPER",
            "entry": f"${entry_low} - ${entry_high}",
            "breakout": f"${breakout}",
            "stop": f"${stop}"
        }

    return None

def run():
    print("🔥 LIVE TRADING BOT")
    send_telegram("🚀 BOT LIVE - READY FOR TODAY")

    sent = set()

    while True:
        now = datetime.now(uk)

        # FULL US SESSION
        if 9 <= now.hour <= 21:
            try:
                stocks = get_stocks()

                for stock in stocks:
                    symbol = stock.get("symbol")

                    if symbol in sent:
                        continue

                    result = analyze(stock)

                    if result:
                        msg = f"""🔥 TODAY TRADE SETUP

{symbol}
Price: ${stock.get('price')}
Change: {stock.get('changesPercentage')}%
Volume: {stock.get('volume')}

🎯 Entry: {result['entry']}
🚀 Breakout: {result['breakout']}
🛑 Stop: {result['stop']}
"""

                        send_telegram(msg)
                        sent.add(symbol)
                        time.sleep(1)

            except Exception as e:
                print("Error:", e)

        time.sleep(SCAN_INTERVAL)

run()
