from flask import Flask
import requests
import time
import threading
from sklearn.linear_model import LogisticRegression

app = Flask(__name__)

# ===== CONFIG =====
TELEGRAM_TOKEN = "8268157455:AAElh_Fi0znhxEhVkwbK1Y2fhRMoUA65TI4"
TELEGRAM_CHAT_ID = "7216850185"
NEWS_API_KEY = "412cc787d78a4975804e17b245ca3c68"

WATCHLIST = ["AMD","NVDA","PLTR","TSLA","ENPH","AAPL","MSFT"]
CHECK_INTERVAL = 180

active_trades = {}
last_signal_time = {}

# ===== TELEGRAM =====
def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        r = requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg
        }, timeout=5)
        print("Telegram:", r.text, flush=True)
    except Exception as e:
        print("Telegram ERROR:", e, flush=True)

# ===== DATA (FIXED WITH HEADERS) =====
def get_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=5m"

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(url, headers=headers, timeout=5)
        print(f"{symbol} status:", response.status_code, flush=True)

        data = response.json()

        if "chart" not in data or not data["chart"]["result"]:
            print(f"{symbol} invalid data", flush=True)
            return None, None

        result = data["chart"]["result"][0]

        closes = result["indicators"]["quote"][0]["close"]
        volumes = result["indicators"]["quote"][0]["volume"]

        return closes, volumes

    except Exception as e:
        print(f"Data error for {symbol}:", e, flush=True)
        return None, None

# ===== RSI =====
def rsi(closes, period=14):
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff,0))
        losses.append(abs(min(diff,0)))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100/(1+rs))

# ===== FEATURES =====
def extract_features(closes, volumes):
    price = closes[-1]
    rsi_val = rsi(closes)
    momentum = (price - closes[-5]) / closes[-5]
    trend = closes[-1] - closes[-20]

    avg_vol = sum(volumes[-20:]) / 20
    vol_spike = volumes[-1] / avg_vol if avg_vol else 1

    return [rsi_val, momentum, trend, vol_spike]

# ===== ML MODEL =====
model = LogisticRegression()

X_train = [
    [55,0.03,2,1.8],
    [60,0.05,3,2.0],
    [65,0.04,2.5,1.9],
    [45,-0.02,-2,0.8],
    [70,0.07,5,2.5],
    [50,0.01,1,1.2]
]

y_train = [1,1,1,0,1,0]
model.fit(X_train, y_train)

def predict_trade(features):
    return model.predict_proba([features])[0][1]

# ===== NEWS =====
def get_news(symbol):
    try:
        url = f"https://newsapi.org/v2/everything?q={symbol}&pageSize=1&apiKey={NEWS_API_KEY}"
        res = requests.get(url, timeout=5).json()

        articles = res.get("articles", [])
        if not articles:
            return "No news", False

        title = articles[0]["title"]
        bullish_words = ["beat","growth","upgrade","surge","strong"]

        bullish = any(w in title.lower() for w in bullish_words)

        return title, bullish
    except:
        return "No news", False

# ===== ENGINE =====
def run():
    print("🚀 BOT THREAD STARTED", flush=True)
    send("🔥 BOT THREAD STARTED")

    while True:
        print("Loop running...", flush=True)

        best = None
        best_score = 0
        best_news = "No catalyst"

        for symbol in WATCHLIST:
            print(f"Checking {symbol}", flush=True)

            closes, volumes = get_data(symbol)
            if not closes:
                continue

            features = extract_features(closes, volumes)
            confidence = predict_trade(features)

            print(f"{symbol} confidence: {confidence:.2f}", flush=True)

            news_title, bullish = get_news(symbol)
            if bullish:
                confidence += 0.05

            if confidence > best_score:
                best_score = confidence
                best = (symbol, closes[-1], confidence)
                best_news = news_title

        # ===== ALWAYS SEND TOP PICK =====
        if best:
            symbol, price, conf = best

            send(f"""🚀 TOP PICK
{symbol} @ {price}

Confidence: {conf:.2f}

📰 {best_news}
""")

        time.sleep(CHECK_INTERVAL)

# ===== START THREAD (IMPORTANT FOR GUNICORN) =====
threading.Thread(target=run).start()

# ===== ROUTE =====
@app.route("/")
def home():
    return "✅ Bot Running"
