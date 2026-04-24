from flask import Flask, request
import requests
import os

app = Flask(__name__)

# ===== CONFIG (SET IN RENDER ENV VARIABLES) =====
TELEGRAM_TOKEN = os.environ.get("8268157455:AAF807pO5yASxEZ-RKSowuIA4LlGRWkE1Vs")
TELEGRAM_CHAT_ID = os.environ.get("7216850185")

# ===== SEND TELEGRAM =====
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    })

# ===== TEST ROUTE =====
@app.route("/")
def home():
    return "✅ Bot is running"

# ===== WEBHOOK ROUTE =====
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    symbol = data.get("symbol", "N/A")
    price = data.get("price", "N/A")
    action = data.get("action", "N/A")

    message = f"📊 {symbol}\n💰 Price: {price}\n⚡ {action}"

    send_telegram(message)

    return {"status": "ok"}

# ===== RUN =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
