import requests
import time
from datetime import datetime
import pytz
from bs4 import BeautifulSoup

# TELEGRAM
TELEGRAM_TOKEN = "8268157455:AAF807pO5yASxEZ-RKSowuIA4LlGRWkE1Vs"
CHAT_ID = "7216850185"

uk = pytz.timezone('Europe/London')

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ================= DATA (NASDAQ SCRAPER) =================
def get_stocks():
    url = "https://www.nasdaq.com/market-activity/stocks/screener"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")

        stocks = []

        rows = soup.find_all("tr")[1:15]

        for row in rows:
            cols = row.find_all("td")

            if len(cols) < 4:
                continue

            symbol = cols[1].text.strip()
            price = cols[2].text.strip().replace("$", "")

            try:
                price = float(price)
            except:
                continue

            stocks.append({
                "symbol": symbol,
                "price": price
            })

        return stocks

    except Exception as e:
        print("Scrape error:", e)
        return []

# ================= LOGIC =================
def analyze(stock):
    price = stock["price"]

    entry_low = round(price * 0.98, 2)
    entry_high = round(price * 1.02, 2)
    breakout = round(price * 1.05, 2)
    stop = round(price * 0.94, 2)

    return {
        "symbol": stock["symbol"],
        "price": price,
        "entry": f"${entry_low}-{entry_high}",
        "breakout": breakout,
        "stop": stop
    }

# ================= MAIN =================
def run():
    print("🔥 SCRAPER BOT ACTIVE")
    send_telegram("🚀 BOT LIVE - GUARANTEED DATA MODE")

    sent = set()

    while True:
        now = datetime.now(uk)

        if 9 <= now.hour <= 21:
            stocks = get_stocks()

            if not stocks:
                send_telegram("⚠️ Still no data — scraping issue")
            else:
                for s in stocks:
                    if s["symbol"] in sent:
                        continue

                    result = analyze(s)

                    msg = f"""🔥 LIVE TRADE

{result['symbol']}
Price: ${result['price']}

🎯 Entry: {result['entry']}
🚀 Breakout: ${result['breakout']}
🛑 Stop: ${result['stop']}
"""

                    send_telegram(msg)
                    sent.add(s["symbol"])
                    time.sleep(1)

        time.sleep(300)

run()
