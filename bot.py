from flask import Flask
import requests
import time
import threading

app = Flask(__name__)

# ===== CONFIG =====
TELEGRAM_TOKEN = "8268157455:AAElh_Fi0znhxEhVkwbK1Y2fhRMoUA65TI4"
TELEGRAM_CHAT_ID = "7216850185"

WATCHLIST = ["AAPL","NVDA","MSFT","AMD","TSLA","META","GOOGL","AMZN"]
CHECK_INTERVAL = 180

# ===== TELEGRAM =====
def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
    except:
        pass

# ===== DATA =====
def get_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=5m"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers).json()

        result = res["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]

        return closes
    except:
        return None

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

# ===== MARKET FILTER =====
def market_is_bullish():
    closes = get_data("SPY")
    if not closes or len(closes) < 50:
        return False

    ma20 = sum(closes[-20:]) / 20
    ma50 = sum(closes[-50:]) / 50

    return ma20 > ma50

# ===== ANALYSIS =====
def analyze(symbol):
    closes = get_data(symbol)
    if not closes or len(closes) < 50:
        return None

    price = closes[-1]

    ma20 = sum(closes[-20:]) / 20
    ma50 = sum(closes[-50:]) / 50
    rsi_val = rsi(closes)
    momentum = (price - closes[-10]) / closes[-10]
    recent_high = max(closes[-20:])

    # ===== HARD FILTER (REMOVE BAD TRADES) =====
    if rsi_val > 65 or rsi_val < 48:
        return None

    # ===== SCORING =====
    score = 0

    if price > ma20: score += 1
    if ma20 > ma50: score += 1
    if 52 <= rsi_val <= 60: score += 2   # weighted higher
    if momentum > 0: score += 1
    if price < recent_high * 0.98: score += 1

    confidence = round(score / 6, 2)

    if confidence < 0.65:
        return None

    entry_low = price * 0.995
    entry_high = price * 1.005
    stop = entry_low * 0.97
    target = entry_high * 1.05

    return {
        "symbol": symbol,
        "price": price,
        "entry_low": entry_low,
        "entry_high": entry_high,
        "stop": stop,
        "target": target,
        "rsi": rsi_val,
        "confidence": confidence
    }

# ===== SCAN =====
def scan_market():
    setups = []

    for symbol in WATCHLIST:
        setup = analyze(symbol)
        if setup:
            setups.append(setup)

    return setups

# ===== ENGINE =====
def run():
    send("📈 SWING BOT (HIGH-QUALITY MODE) STARTED")

    while True:

        if not market_is_bullish():
            send("⛔ Market weak (SPY bearish) — no trades")
            time.sleep(CHECK_INTERVAL)
            continue

        setups = scan_market()

        setups = sorted(setups, key=lambda x: x["confidence"], reverse=True)
        top_setups = setups[:3]

        if not top_setups:
            send("⚠️ No high-quality setups right now")
        else:
            for setup in top_setups:

                if setup["confidence"] >= 0.8:
                    tag = "🔥 A+ SETUP"
                else:
                    tag = "⚡ B SETUP"

                send(f"""{tag}
{setup['symbol']} @ {setup['price']:.2f}

Confidence: {setup['confidence']}

✅ Entry: {setup['entry_low']:.2f} – {setup['entry_high']:.2f}
🎯 Target: {setup['target']:.2f}
🛑 Stop: {setup['stop']:.2f}

RSI: {setup['rsi']:.1f}
⏳ Hold: 2–3 days
""")

        time.sleep(CHECK_INTERVAL)

# ===== START THREAD =====
threading.Thread(target=run).start()

@app.route("/")
def home():
    return "✅ Swing Bot Running"
