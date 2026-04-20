import requests
import time
from datetime import datetime
import pytz

# ================= CONFIG =================
API_KEY = "wg6hAv7crwZdlFQcmoYwKdYqnK0cXaXD"
TELEGRAM_TOKEN = "8268157455:AAF807pO5yASxEZ-RKSowuIA4LlGRWkE1Vs"
CHAT_ID = "7216850185"


SCAN_INTERVAL = 180  # 3 minutes

# UK timezone

uk = pytz.timezone('Europe/London')

# ================= TELEGRAM =================

def send_telegram(message):

    try:

        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

        requests.post(url, data={"chat_id": CHAT_ID, "text": message})

    except Exception as e:

        print("Telegram Error:", e)

# ================= DATA =================

def get_gainers():

    url = f"https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey={API_KEY}"

    response = requests.get(url)

    return response.json()

# ================= LOGIC =================

def classify(stock):

    price = stock.get("price", 0)

    change = stock.get("changesPercentage", 0)

    volume = stock.get("volume", 0)

    # 🔥 SNIPER SIGNAL

    if price < 5 and change >= 20 and volume >= 500000:

        return "SNIPER"

    # ⚠️ WATCHLIST

    elif price < 10 and change >= 10 and volume >= 200000:

        return "WATCH"

    return None

# ================= MAIN LOOP =================

def run():

    print("🔥 SNIPER BOT ACTIVE")

    # ✅ TEST MESSAGE (CONFIRM TELEGRAM WORKS)

    send_telegram("✅ BOT IS LIVE")

    sent_symbols = set()

    while True:

        now = datetime.now(uk)

        hour = now.hour

        # UK time: 9 AM – 2:30 PM

        if 9 <= hour <= 14:

            try:

                stocks = get_gainers()

                for stock in stocks[:15]:

                    symbol = stock.get("symbol")

                    if symbol in sent_symbols:

                        continue

                    signal = classify(stock)

                    if signal:

                        msg = f"{'🔥 SNIPER SIGNAL' if signal=='SNIPER' else '⚠️ WATCHLIST'}\n"

                        msg += f"{symbol}\n"

                        msg += f"Price: ${stock.get('price')}\n"

                        msg += f"Change: {stock.get('changesPercentage')}%\n"

                        msg += f"Volume: {stock.get('volume')}"

                        send_telegram(msg)

                        sent_symbols.add(symbol)

                        time.sleep(1)

            except Exception as e:

                print("Error:", e)

        time.sleep(SCAN_INTERVAL)

# ================= START =================

run()
