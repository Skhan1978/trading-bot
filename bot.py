import requests
import time
from datetime import datetime
import pytz

API_KEY = "wg6hAv7crwZdlFQcmoYwKdYqnK0cXaXD"
TELEGRAM_TOKEN = "8268157455:AAF807pO5yASxEZ-RKSowuIA4LlGRWkE1Vs"
CHAT_ID = "7216850185"

uk = pytz.timezone('Europe/London')

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except Exception as e:
        print(e)

def get_data():
    url1 = f"https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey={API_KEY}"
    url2 = f"https://financialmodelingprep.com/api/v3/stock_market/actives?apikey={API_KEY}"

    g = requests.get(url1).json()
    a = requests.get(url2).json()

    return (g[:5] if isinstance(g, list) else []) + (a[:5] if isinstance(a, list) else [])

def run():
    print("🔥 FORCE SIGNAL BOT RUNNING")
    send_telegram("🚀 BOT LIVE - GUARANTEED SIGNAL MODE")

    while True:
        try:
            stocks = get_data()

            if not stocks:
                send_telegram("⚠️ No data from API — check API key")
            else:
                for s in stocks:
                    symbol = s.get("symbol")
                    price = s.get("price")
                    change = s.get("changesPercentage")
                    volume = s.get("volume")

                    msg = f"""📊 MARKET ALERT

{symbol}
Price: ${price}
Change: {change}%
Volume: {volume}
"""

                    send_telegram(msg)
                    time.sleep(1)

        except Exception as e:
            send_telegram(f"Error: {e}")

        time.sleep(300)  # every 5 minutes

run()
