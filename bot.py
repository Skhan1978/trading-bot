import requests
import time
from datetime import datetime

BOT_TOKEN = "8522684488:AAG3bBfl_amlYwzi27AOqeqAfIHXJBdRZL8"
CHAT_ID = "7216850185"

API_KEY = "demo"  # replace later with your key if needed

sent_signals = set()

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def is_market_time():
    hour = datetime.utcnow().hour
    return 11 <= hour <= 21  # premarket + market

def get_active_stocks():
    url = f"https://financialmodelingprep.com/api/v3/stock_market/actives?apikey={API_KEY}"
    try:
        return requests.get(url).json()
    except:
        return []

def get_rsi(symbol):
    try:
        url = f"https://financialmodelingprep.com/api/v3/technical_indicator/1day/{symbol}?type=rsi&period=14&apikey={API_KEY}"
        data = requests.get(url).json()
        return float(data[0]["rsi"])
    except:
        return None

def get_profile(symbol):
    try:
        url = f"https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={API_KEY}"
        data = requests.get(url).json()
        return data[0]
    except:
        return {}

def is_halal(profile):
    sector = profile.get("sector", "").lower()
    forbidden = ["financial", "bank", "insurance", "gambling", "alcohol"]
    return not any(word in sector for word in forbidden)

def sniper_scan():
    global sent_signals

    stocks = get_active_stocks()
    found = False

    for stock in stocks[:15]:  # limit for stability
        try:
            symbol = stock["symbol"]
            price = float(stock["price"])
            change = float(stock["changesPercentage"].replace('%',''))

            if not (5 <= price <= 50 and change > 5):
                continue

            if symbol in sent_signals:
                continue

            rsi = get_rsi(symbol)
            if rsi is None or not (50 <= rsi <= 65):
                continue

            profile = get_profile(symbol)
            if not is_halal(profile):
                continue

            found = True
            sent_signals.add(symbol)

            entry = round(price * 1.01, 2)
            target = round(price * 1.10, 2)
            stop = round(price * 0.96, 2)

            msg = f"""
🚀 ELITE SNIPER ALERT

Stock: {symbol}
Price: ${price}
Change: +{change}%

RSI: {round(rsi,1)}

Setup: Breakout / Pullback

Entry: ${entry}
Target: ${target}
Stop: ${stop}

Halal: ✅ PASS
Confidence: ⭐⭐⭐⭐⭐
"""

            send_telegram(msg)

        except:
            continue

    if not found:
        send_telegram("⚠️ No strong halal sniper setups right now.")

def main():
    send_telegram("✅ ELITE BOT LIVE (Halal Sniper Mode)")

    while True:
        if is_market_time():
            sniper_scan()
        time.sleep(1800)  # every 30 min

if __name__ == "__main__":
    main()
