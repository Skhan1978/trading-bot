import requests
import time
import os
from datetime import datetime, UTC

# ===== CONFIG =====
TELEGRAM_TOKEN = os.getenv("8268157455:AAElh_Fi0znhxEhVkwbK1Y2fhRMoUA65TI4")
CHAT_ID = os.getenv("7216850185")
FMP_API_KEY = os.getenv("412cc787d78a4975804e17b245ca3c68")

CHECK_INTERVAL = 3600
TOP_N = 10

sent_today = set()
last_reset_day = None

# ===== TELEGRAM =====
def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except:
        pass

# ===== RESET =====
def reset_daily():
    global sent_today, last_reset_day
    today = datetime.now(UTC).date()

    if last_reset_day != today:
        sent_today.clear()
        last_reset_day = today

# ===== GET STOCKS =====
def get_midcaps():
    url = f"https://financialmodelingprep.com/api/v3/stock-screener?marketCapMoreThan=2000000000&marketCapLowerThan=20000000000&volumeMoreThan=500000&limit=300&apikey={FMP_API_KEY}"
    return [s["symbol"] for s in requests.get(url).json()]

# ===== DATA =====
def get_data(symbol):
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?apikey={FMP_API_KEY}"
    data = requests.get(url).json()
    hist = data.get("historical", [])[:120]

    closes = [c["close"] for c in hist][::-1]
    volumes = [c["volume"] for c in hist][::-1]

    return closes, volumes

# ===== FUNDAMENTALS =====
def fundamentals(symbol):
    url = f"https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={FMP_API_KEY}"
    d = requests.get(url).json()[0]

    return {
        "debt": d.get("debtToEquity", 0),
        "profit": d.get("profitMargins", 0),
        "sector": d.get("sector", "")
    }

# ===== NEWS =====
def has_news(symbol):
    url = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={symbol}&limit=2&apikey={FMP_API_KEY}"
    return len(requests.get(url).json()) > 0

# ===== HALAL =====
def halal(f):
    if not f: return False
    if "Financial" in f["sector"]: return False
    if f["debt"] > 1: return False
    if f["profit"] <= 0: return False
    return True

# ===== AI SCORE =====
def score_stock(symbol):
    try:
        closes, volumes = get_data(symbol)
        f = fundamentals(symbol)

        if not closes or len(closes) < 50 or not halal(f):
            return None

        price = closes[-1]

        ma20 = sum(closes[-20:]) / 20
        ma50 = sum(closes[-50:]) / 50

        score = 0

        # Trend
        if price > ma20 > ma50:
            score += 25

        # Pullback
        recent_high = max(closes[-20:])
        pullback = (recent_high - price) / recent_high
        if 0.03 < pullback < 0.08:
            score += 20

        # Volume
        avg_vol = sum(volumes[-20:]) / 20
        if volumes[-1] > avg_vol * 1.3:
            score += 15

        # Fundamentals
        if f["profit"] > 0.1:
            score += 15

        # News catalyst
        if has_news(symbol):
            score += 10

        # Momentum
        momentum = (price - closes[-10]) / closes[-10]
        if momentum > 0.03:
            score += 15

        return {
            "symbol": symbol,
            "score": score,
            "price": price,
            "target": price * 1.12,
            "stop": price * 0.95
        }

    except:
        return None

# ===== BACKTEST =====
def quick_backtest(closes):
    wins = 0
    trades = 0

    for i in range(20, len(closes)-5):
        entry = closes[i]
        future = closes[i+1:i+6]

        if max(future) > entry * 1.05:
            wins += 1
        trades += 1

    if trades == 0:
        return 0

    return round((wins/trades)*100, 1)

# ===== MAIN =====
def run():
    send("🧠 V7 AI HALAL SCANNER LIVE")

    while True:
        try:
            reset_daily()

            stocks = get_midcaps()
            ranked = []

            for s in stocks:
                data = score_stock(s)
                if data:
                    closes, _ = get_data(s)
                    data["winrate"] = quick_backtest(closes)
                    ranked.append(data)

            # SORT BY SCORE
            ranked = sorted(ranked, key=lambda x: x["score"], reverse=True)

            top = ranked[:TOP_N]

            msg = "📊 TOP 10 HALAL SWING STOCKS (AI RANKED)\n\n"

            for i, s in enumerate(top, 1):
                msg += f"""{i}. {s['symbol']} | Score: {s['score']}/100
Price: {s['price']:.2f}
Target: {s['target']:.2f}
Stop: {s['stop']:.2f}
Backtest Winrate: {s['winrate']}%

"""

            send(msg)

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print("ERROR:", e)
            time.sleep(10)

# ===== START =====
if __name__ == "__main__":
    run()
