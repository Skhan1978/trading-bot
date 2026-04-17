import requests
import time
from datetime import datetime, UTC

# 🔐 ADD YOUR DETAILS
BOT_TOKEN = "PASTE_YOUR_TOKEN_HERE"
CHAT_ID = "PASTE_YOUR_CHAT_ID_HERE"

API_KEY = "demo"  # you can upgrade later

sent_signals = set()

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def is_market_time():
    hour = datetime.now(UTC).hour
    return 11 <= hour <= 21  # premarket + market

def get_active_stocks():
    url = f"https://financialmodelingprep.com/api/v3/stock_market/actives?apikey={API_KEY}"
    try:
        res = requests.get(url)
        data = res.json()

        # ✅ FIX: ensure it's a list
        if isinstance(data, list):
            return data
        else:
            return []
    except:
        return []

def get_rsi(symbol):
    try:
        url = f"https://financialmodelingprep.com/api/v3/technical_indicator/1day/{symbol}?type=rsi&period=14&apikey={API_KEY}"
        data = requests.get(url).json()
        if isinstance(data, list) and len(data) > 0:
            return float(data[0]["rsi"])
    except:
        return None

def get_profile(symbol):
    try:
        url = f"https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={API_KEY}"
        data = requests.get(url).json()
        if isinstance(data, list) and len(data) > 0:
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

    # ✅ SAFETY CHECK (prevents crash)
    if not stocks:
        send_telegram("⚠️ Market data unavailable (API issue)")
        return

    found = False

    for stock in stocks[:10]:  # limit for stability
        try:
            symbol = stock.get("symbol")
            price = float(stock.get("price", 0))
            change = float(stock.get("changesPercentage", "0").replace('%',''))

            # 🎯 BASIC FILTER
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

            sent_signals.add(symbol)
            found = True

            entry = round(price * 1.01, 2)
            target = round(price * 1.10, 2)
            stop = round(price * 0.96, 2)

            msg = f"""
🚀 ELITE SNIPER ALERT

Stock: {symbol}
Price: ${price}
Change: +{change}%

RSI: {round(rsi,1)}

Entry: ${entry}
Target: ${target}
Stop: ${stop}

Halal: ✅ PASS
"""

            send_telegram(msg)

        except:
            continue

    if not found:
        send_telegram("⚠️ No strong halal sniper setups right now.")

def main():
    send_telegram("✅ ELITE BOT RUNNING")

    while True:
        if is_market_time():
            sniper_scan()
        time.sleep(1800)  # every 30 minutes

if __name__ == "__main__":
    main()
