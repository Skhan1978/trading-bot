import requests
import time

# ===== CONFIG =====
TELEGRAM_TOKEN = "8268157455:AAElh_Fi0znhxEhVkwbK1Y2fhRMoUA65TI4"
CHAT_ID = "7216850185"

WATCHLIST = ["AAPL","NVDA","MSFT","AMD","TSLA","META","GOOGL","AMZN"]
CHECK_INTERVAL = 180

trades = []

# ===== TELEGRAM =====
def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except:
        pass

# ===== DATA =====
def get_data_full(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=5m"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5).json()

        result = res["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        volumes = result["indicators"]["quote"][0]["volume"]

        # CLEAN
        closes = [c for c in closes if c is not None]
        volumes = [v for v in volumes if v is not None]

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

    if len(gains) < period:
        return 50

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100/(1+rs))

# ===== MARKET =====
def market_condition():
    closes, _ = get_data_full("SPY")

    if not closes or len(closes) < 50:
        return "neutral"

    ma20 = sum(closes[-20:]) / 20
    ma50 = sum(closes[-50:]) / 50

    if ma20 > ma50:
        return "strong"
    elif ma20 > ma50 * 0.995:
        return "neutral"
    else:
        return "weak"

# ===== ANALYSIS =====
def analyze(symbol):
    closes, volumes = get_data_full(symbol)

    if not closes or not volumes or len(closes) < 50:
        return None

    price = closes[-1]

    ma20 = sum(closes[-20:]) / 20
    ma50 = sum(closes[-50:]) / 50
    rsi_val = rsi(closes)
    momentum = (price - closes[-10]) / closes[-10]

    # ===== VOLUME =====
    avg_vol = sum(volumes[-20:]) / 20
    vol_ok = volumes[-1] > avg_vol

    # ===== BREAKOUT FILTER =====
    recent_high = max(closes[-20:])
    too_high = price > recent_high * 0.995

    # ===== ENTRY TIMING =====
    if not (closes[-1] > closes[-2]):
        return None

    # ===== FILTER =====
    if rsi_val > 65 or rsi_val < 48:
        return None

    # ===== SCORING =====
    score = 0
    if price > ma20: score += 1
    if ma20 > ma50: score += 1
    if 52 <= rsi_val <= 60: score += 2
    if momentum > 0: score += 1
    if vol_ok: score += 1
    if not too_high: score += 1

    confidence = round(score / 7, 2)

    if confidence < 0.6:
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

# ===== TRACKING =====
def check_trades():
    for trade in trades:
        if trade["status"] != "open":
            continue

        closes, _ = get_data_full(trade["symbol"])
        if not closes:
            continue

        price = closes[-1]

        if price >= trade["target"]:
            trade["status"] = "win"
            send(f"✅ WIN: {trade['symbol']}")

        elif price <= trade["stop"]:
            trade["status"] = "loss"
            send(f"❌ LOSS: {trade['symbol']}")

# ===== MAIN LOOP =====
def run():
    send("🚀 FINAL BOT LIVE")

    while True:
        try:
            check_trades()

            market = market_condition()

            if market == "weak":
                send("⚠️ Weak market → A+ only")

            setups = []

            for s in WATCHLIST:
                setup = analyze(s)
                if setup:
                    setups.append(setup)

            setups = sorted(setups, key=lambda x: x["confidence"], reverse=True)[:3]

            if not setups:
                send("⚠️ No setups")

            for setup in setups:

                if setup["confidence"] >= 0.8:
                    tag = "🔥 A+"

                elif setup["confidence"] >= 0.6:
                    if market == "weak":
                        continue
                    tag = "⚡ B"

                else:
                    continue

                send(f"""{tag} {setup['symbol']} @ {setup['price']:.2f}

Entry: {setup['entry_low']:.2f}-{setup['entry_high']:.2f}
Target: {setup['target']:.2f}
Stop: {setup['stop']:.2f}
RSI: {setup['rsi']:.1f}
""")

                trades.append({
                    "symbol": setup["symbol"],
                    "stop": setup["stop"],
                    "target": setup["target"],
                    "status": "open"
                })

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print("ERROR:", e)
            time.sleep(10)

# ===== START =====
if __name__ == "__main__":
    run()
