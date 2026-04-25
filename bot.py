from flask import Flask
import requests
import time
import threading
import os
from sklearn.linear_model import LogisticRegression

app = Flask(__name__)

# ===== CONFIG =====
TELEGRAM_TOKEN = os.environ.get("8268157455:AAF807pO5yASxEZ-RKSowuIA4LlGRWkE1Vs")
TELEGRAM_CHAT_ID = os.environ.get("7216850185")
NEWS_API_KEY = os.environ.get("412cc787d78a4975804e17b245ca3c68")

WATCHLIST = ["AMD","NVDA","PLTR","TSLA","ENPH","AAPL","MSFT"]
CHECK_INTERVAL = 180
MAX_TRADES = 3

active_trades = {}
trade_log = []
last_signal_time = {}

# ===== TELEGRAM =====
def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=5)
    except:
        pass

# ===== DATA =====
def get_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=5m"
        data = requests.get(url, timeout=5).json()["chart"]["result"][0]

        closes = data["indicators"]["quote"][0]["close"]
        volumes = data["indicators"]["quote"][0]["volume"]

        return closes, volumes
    except:
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

# ===== MARKET FILTER =====
def market_is_good():
    closes, _ = get_data("SPY")
    if not closes:
        return False

    short = sum(closes[-10:]) / 10
    long = sum(closes[-30:]) / 30

    return short > long

# ===== TRADE =====
class Trade:
    def __init__(self, entry):
        self.entry = entry
        self.highest = entry
        self.locked = False

    def update(self, price, symbol):
        if price > self.highest:
            self.highest = price

        profit = ((price - self.entry) / self.entry) * 100

        if profit >= 3 and not self.locked:
            self.locked = True
            return f"🔒 LOCK PROFIT\n{symbol} +{profit:.2f}%"

        drop = ((self.highest - price) / self.highest) * 100

        if self.locked and drop >= 2:
            trade_log.append({
                "symbol": symbol,
                "entry": self.entry,
                "exit": price,
                "profit": profit
            })

            del active_trades[symbol]

            return f"⚠️ EXIT NOW\n{symbol} secured {profit:.2f}%"

        return None

# ===== ENGINE =====
def run():
    print("🚀 INSTITUTIONAL BOT RUNNING")

    while True:

        best = None
        best_score = 0
        best_news = "No catalyst"

        for symbol in WATCHLIST:

            closes, volumes = get_data(symbol)
            if not closes:
                continue

            features = extract_features(closes, volumes)
            confidence = predict_trade(features)

            news_title, bullish = get_news(symbol)
            if bullish:
                confidence += 0.05

            if confidence > best_score:
                best_score = confidence
                best = (symbol, closes[-1], confidence)
                best_news = news_title

        # ENTRY
        if best and best_score > 0.6 and market_is_good() and len(active_trades) < MAX_TRADES:
            symbol, price, conf = best

            if symbol not in last_signal_time or time.time() - last_signal_time[symbol] > 3600:

                active_trades[symbol] = Trade(price)
                last_signal_time[symbol] = time.time()

                send(f"""🚀 AI TRADE
{symbol} @ {price}

Confidence: {conf:.2f}

📰 {best_news}

🎯 Target: 6–10%
🛑 Stop: -3%
""")

        # MANAGE
        for symbol in list(active_trades.keys()):
            closes, _ = get_data(symbol)
            if not closes:
                continue

            price = closes[-1]
            alert = active_trades[symbol].update(price, symbol)

            if alert:
                send(alert)

        time.sleep(CHECK_INTERVAL)

# ===== DASHBOARD =====
@app.route("/")
def home():
    return "✅ Bot Running"

@app.route("/dashboard")
def dashboard():
    html = "<h1>📊 Active Trades</h1>"
    for s, t in active_trades.items():
        html += f"<p>{s} | Entry: {t.entry:.2f} | High: {t.highest:.2f}</p>"
    return html

@app.route("/performance")
def performance():
    if not trade_log:
        return "No trades yet"

    wins = [t for t in trade_log if t["profit"] > 0]
    win_rate = (len(wins)/len(trade_log))*100

    return f"""
    <h1>Performance</h1>
    <p>Trades: {len(trade_log)}</p>
    <p>Win Rate: {win_rate:.1f}%</p>
    """

# ===== START =====
threading.Thread(target=run, daemon=True).start()
