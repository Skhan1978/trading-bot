import requests
import time
import os
import datetime

# ===== CONFIG =====
TELEGRAM_TOKEN = os.getenv("8268157455:AAElh_Fi0znhxEhVkwbK1Y2fhRMoUA65TI4")
CHAT_ID = os.getenv(" 7216850185")
FMP_API_KEY = os.getenv("412cc787d78a4975804e17b245ca3c68")

WATCHLIST = ["AAPL","NVDA","MSFT","AMD","TSLA","META","GOOGL","AMZN"]

CHECK_INTERVAL = 180
COOLDOWN = 3600
MAX_TRADES = 5

# ===== STATE =====
trades = []
pending_setups = {}
last_sent = {}
sent_signals = set()
sent_messages = {}
last_heartbeat = 0

# ===== TELEGRAM (ANTI-SPAM) =====
def send(msg):
    global sent_messages
    now = time.time()

    if msg in sent_messages:
        if now - sent_messages[msg] < 1800:
            return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=5)
        sent_messages[msg] = now
    except:
        pass

# ===== MARKET HOURS =====
def market_open():
    now = datetime.datetime.utcnow()
    return now.weekday() < 5 and 13 <= now.hour <= 20

# ===== DATA =====
def get_data(symbol):
    try:
        url = f"https://financialmodelingprep.com/api/v3/historical-chart/5min/{symbol}?apikey={FMP_API_KEY}"
        data = requests.get(url).json()

        closes = [c["close"] for c in data[:100]]
        volumes = [c["volume"] for c in data[:100]]

        closes.reverse()
        volumes.reverse()

        return closes, volumes
    except:
        return None, None

# ===== GAP =====
def gap_percent(closes):
    return (closes[-1] - closes[-2]) / closes[-2] * 100

# ===== NEWS =====
def has_news(symbol):
    try:
        url = f"https://financialmodelingprep.com/api/v3/stock_news?tickers={symbol}&limit=3&apikey={FMP_API_KEY}"
        data = requests.get(url).json()
        return len(data) > 0
    except:
        return False

# ===== ANALYZE =====
def analyze(symbol):
    closes, volumes = get_data(symbol)

    if not closes or len(closes) < 50:
        return None

    price = closes[-1]

    # MA
    ma20 = sum(closes[-20:]) / 20
    ma50 = sum(closes[-50:]) / 50

    # RSI
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff,0))
        losses.append(abs(min(diff,0)))

    avg_gain = sum(gains[-14:]) / 14
    avg_loss = sum(losses[-14:]) / 14 if sum(losses[-14:]) != 0 else 1
    rs = avg_gain / avg_loss
    rsi = 100 - (100/(1+rs))

    # Momentum
    momentum = (price - closes[-10]) / closes[-10]

    # GAP
    gap = gap_percent(closes)
    if gap < 1.5:
        return None

    # Volume Spike
    avg_vol = sum(volumes[-20:]) / 20
    if volumes[-1] < avg_vol * 1.5:
        return None

    # Breakout
    recent_high = max(closes[-20:])
    if price <= recent_high * 1.002:
        return None

    # Trend
    if ma20 < ma50:
        return None

    # RSI Filter
    if rsi < 52 or rsi > 65:
        return None

    # Momentum Filter
    if momentum < 0.01:
        return None

    # News
    if not has_news(symbol):
        return None

    # Score
    score = 0
    if gap > 2: score += 2
    if momentum > 0.015: score += 1
    if 55 <= rsi <= 62: score += 1
    score += 3  # breakout + volume + trend baseline

    confidence = round(score / 7, 2)
    if confidence < 0.6:
        return None

    return {
        "symbol": symbol,
        "entry_low": recent_high,
        "entry_high": recent_high * 1.002,
        "stop": min(closes[-10:]),
        "target": price * 1.06,
        "rsi": rsi,
        "confidence": confidence
    }

# ===== ENTRY =====
def check_entries():
    open_trades = [t for t in trades if t["status"] == "open"]
    if len(open_trades) >= MAX_TRADES:
        return

    for symbol, setup in list(pending_setups.items()):
        closes, _ = get_data(symbol)
        if not closes:
            continue

        price = closes[-1]

        if setup["entry_low"] <= price <= setup["entry_high"]:
            signal_id = f"{symbol}_{int(time.time()/300)}"

            if signal_id in sent_signals:
                continue

            if symbol in last_sent and time.time() - last_sent[symbol] < COOLDOWN:
                continue

            tag = "🔥 A+ GAP BREAKOUT" if setup["confidence"] >= 0.7 else "⚡ GAP BREAKOUT"

            send(f"""🚀 {tag} {symbol} @ {price:.2f}

Gap + Volume + News Confirmed
Target: {setup['target']:.2f}
Stop: {setup['stop']:.2f}
RSI: {setup['rsi']:.1f}
Confidence: {setup['confidence']}
""")

            last_sent[symbol] = time.time()
            sent_signals.add(signal_id)

            trades.append({
                "symbol": symbol,
                "entry": price,
                "stop": setup["stop"],
                "target": setup["target"],
                "highest": price,
                "locked": False,
                "partial": False,
                "status": "open"
            })

            del pending_setups[symbol]

# ===== TRADE MANAGEMENT =====
def manage_trades():
    for trade in trades:
        if trade["status"] != "open":
            continue

        closes, _ = get_data(trade["symbol"])
        if not closes:
            continue

        price = closes[-1]

        if price > trade["highest"]:
            trade["highest"] = price

        profit = ((price - trade["entry"]) / trade["entry"]) * 100

        if profit >= 3 and not trade["partial"]:
            trade["partial"] = True
            send(f"💰 PARTIAL: {trade['symbol']} +{profit:.2f}%")

        if profit >= 3 and not trade["locked"]:
            trade["locked"] = True

        drop = ((trade["highest"] - price) / trade["highest"]) * 100

        if trade["locked"] and drop >= 2:
            trade["status"] = "win"
            send(f"⚠️ TRAILING EXIT: {trade['symbol']} +{profit:.2f}%")
            continue

        if price <= trade["stop"]:
            trade["status"] = "loss"
            send(f"❌ STOP HIT: {trade['symbol']}")

        elif price >= trade["target"]:
            trade["status"] = "win"
            send(f"🎯 TARGET HIT: {trade['symbol']}")

# ===== MAIN =====
def run():
    global last_heartbeat

    send("✅ V4 Bot Live (Gap + Volume + News)")

    while True:
        try:
            if not market_open():
                time.sleep(300)
                continue

            now = time.time()

            # CLEAN HEARTBEAT (1 hour, unique)
            if now - last_heartbeat > 3600:
                send(f"💓 Bot alive | {datetime.datetime.utcnow().strftime('%H:%M:%S')} UTC")
                last_heartbeat = now

            manage_trades()

            for symbol in WATCHLIST:
                setup = analyze(symbol)
                if setup:
                    pending_setups[symbol] = setup

            check_entries()

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print("ERROR:", e)
            time.sleep(5)

# ===== START =====
if __name__ == "__main__":
    run()
