import requests
import time

BOT_TOKEN = "8522684488:AAHrUC1qBwUYK7x3-GMYVsSqONslUnH5WL8"
CHAT_ID = "7216850185"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=data)

def sniper_scan():
    watchlist = [
        {"symbol": "PLTR", "price": 22.4, "rsi": 56},
        {"symbol": "SOFI", "price": 8.9, "rsi": 58},
    ]

    for stock in watchlist:
        if 50 <= stock["rsi"] <= 65:
            msg = f"""
🚀 SNIPER ALERT

Stock: {stock['symbol']}
Price: ${stock['price']}
RSI: {stock['rsi']}

Setup: Breakout / Pullback
Target: +8% to +12%
Stop: -4%

Halal: ✅
"""
            send_telegram(msg)

while True:
    sniper_scan()
    time.sleep(3600)
