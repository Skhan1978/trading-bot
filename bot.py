import requests
import time
import os
from datetime import datetime, UTC

# ===== CONFIG =====
TELEGRAM_TOKEN = os.getenv("8268157455:AAElh_Fi0znhxEhVkwbK1Y2fhRMoUA65TI4")
CHAT_ID = os.getenv("7216850185")
FMP_API_KEY = os.getenv("412cc787d78a4975804e17b245ca3c68")

CHECK_INTERVAL = 3600  # every hour
TOP_N = 3

sent_today = set()
last_reset_day = None

# ===== TELEGRAM =====
def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except:
        pass

# ===== RESET DAILY =====
def reset_daily():
    global sent_today, last_reset_day
    today = datetime.now(UTC).date()

    if last_reset_day != today:
        sent_today.clear()
        last_reset_day = today

# ===== GET MIDCAP STOCKS =====
def get_stocks():
    url = f"https://financialmodelingprep.com/api/v3/stock-screener?marketCapMoreThan=2000000000&marketCapLowerThan=20000000000&volumeMoreThan=500000&limit=300&apikey={FMP_API_KEY}"
    return [s["symbol"] for s in requests.get(url).json()]

# ===== GET PRICE DATA =====
def get_data(symbol):
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?apikey={FMP_API_KEY}"
    data = requests.get(url).json()
    hist = data.get("historical", [])[:120]

    closes = [c["close"] for c in hist][::-1]
    volumes = [c["volume"] for c in hist][::-1]

    return closes, volumes

# ===== FUNDAMENTALS =====
def fundamentals(symbol):
    try:
        url = f"https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={FMP_API_KEY}"
        d = requests.get(url).json()[0]

        return {
            "debt": d.get("debtToEquity", 0),
            "profit": d.get("profitMargins", 0),
            "sector": d.get("sector", "")
        }
    except:
        return None

# ===== HALAL FILTER =====
def halal(f):
    if not f: return False
    if "Financial" in f["sector"]: return False
    if f["debt"] > 1: return False
    if f["profit"] <= 0: return False
    return True

# ===== AI SCORING =====
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

        # STRONG TREND
        if price > ma20 > ma50:
            score += 25

        # PULLBACK ENTRY
        recent_high = max(closes[-20:])
        pullback = (recent_high - price) / recent_high
        if 0.03 < pullback < 0.08:
            score += 20

        # VOLUME
        avg_vol = sum(volumes[-20:]) / 20
        if volumes[-1] > avg_vol * 1.3:
            score += 15

        # FUNDAMENTALS
        if f["profit"] > 0.1:
            score += 15

        # MOMENTUM
        momentum = (price - closes[-10]) / closes[-10]
        if momentum > 0.03:
            score += 15

        # EXTRA BOOST (HIGH RR)
        rr = (price * 1.18 - price) / (price - price * 0.94)
        if rr > 2:
            score += 10

        confidence = min(score, 100)

        return {
            "symbol": symbol,
            "score": confidence,
            "price": price,
            "target": price * 1.18,   # HIGH PROFIT
            "stop": price * 0.94
        }

    except:
        return None

# ===== MAIN =====
def run():
    send("🚀 V8 TOP 3 HALAL SWING BOT LIVE")

    while True:
        try:
            reset_daily()

            stocks = get_stocks()
            ranked = []

            for s in stocks:
                data = score_stock(s)
                if data:
                    ranked.append(data)

            # SORT BEST FIRST
            ranked = sorted(ranked, key=lambda x: x["score"], reverse=True)

            top = ranked[:TOP_N]

            msg = "🏆 TOP 3 HIGH PROBABILITY SWING STOCKS\n\n"

            for i, s in enumerate(top, 1):
                msg += f"""{i}. {s['symbol']} | Confidence: {s['score']}%

Entry: {s['price']:.2f}
Target: {s['target']:.2f}
Stop: {s['stop']:.2f}

Risk/Reward: HIGH
-----------------------
"""

            send(msg)

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print("ERROR:", e)
            time.sleep(10)

# ===== START =====
if __name__ == "__main__":
    run()
