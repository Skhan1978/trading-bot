import requests
import time

# ===== CONFIG =====
TELEGRAM_TOKEN = "8268157455:AAElh_Fi0znhxEhVkwbK1Y2fhRMoUA65TI4"
CHAT_ID = "7216850185"

WATCHLIST = ["AAPL","NVDA","MSFT","AMD","TSLA","META","GOOGL","AMZN"]
CHECK_INTERVAL = 180
COOLDOWN = 3600  # 1 hour

# ===== STATE =====
trades = []
pending_setups = {}
last_sent = {}
sent_signals = set()  # ✅ prevents duplicate alerts

# ===== TELEGRAM =====
def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except:
        pass

# ===== DATA =====
def get_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=5m"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5).json()

        result = res["chart"]["result"][0]
        closes = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]
        volumes = [v for v in result["indicators"]["quote"][0]["volume"] if v is not None]

        return closes, volumes
    except:
        return None, None

# ===== ANALYZE =====
def analyze(symbol):
    closes, volumes = get_data(symbol)

    if not closes or not volumes or len(closes) < 50:
        return None

    price = closes[-1]

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
    rsi_val = 100 - (100/(1+rs))

    momentum = (price - closes[-10]) / closes[-10]

    avg_vol = sum(volumes[-20:]) / 20
    vol_ok = volumes[-1] > avg_vol * 0.8

    recent_high = max(closes[-20:])
    not_chasing = price < recent_high * 0.98

    # FILTERS
    if rsi_val > 68 or rsi_val < 48:
        return None

    if not (closes[-1] > closes[-2]):
        return None

    score = 0
    if price > ma20: score += 1
    if ma20 > ma50: score += 1
    if 52 <= rsi_val <= 60: score += 2
    if momentum > 0: score += 1
    if vol_ok: score += 1
    if not_chasing: score += 1

    confidence = round(score / 7, 2)

    if confidence < 0.55:
        return None

    entry_low = price * 0.995
    entry_high = price * 1.005
    stop = entry_low * 0.97
    target = entry_high * 1.05

    return {
        "symbol": symbol,
        "entry_low": entry_low,
        "entry_high": entry_high,
        "stop": stop,
        "target": target,
        "rsi": rsi_val,
        "confidence": confidence
    }

# ===== ENTRY TRIGGER =====
def check_entries():
    for symbol, setup in list(pending_setups.items()):

        closes, _ = get_data(symbol)
        if not closes:
            continue

        price = closes[-1]

        # ENTRY CONDITION
        if setup["entry_low"] <= price <= setup["entry_high"]:

            # ✅ UNIQUE SIGNAL ID
            signal_id = f"{symbol}_{round(price, 2)}"

            # 🚫 BLOCK DUPLICATES FOREVER (until restart)
            if signal_id in sent_signals:
                continue

            # 🚫 COOLDOWN BLOCK
            if symbol in last_sent and time.time() - last_sent[symbol] < COOLDOWN:
                continue

            tag = "🔥 A ENTRY" if setup["confidence"] >= 0.7 else "⚡ B ENTRY"

            send(f"""🚨 {tag} {symbol} @ {price:.2f}

Entry Zone Hit!
Target: {setup['target']:.2f}
Stop: {setup['stop']:.2f}
RSI: {setup['rsi']:.1f}
Confidence: {setup['confidence']}
""")

            # ✅ SAVE STATE
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

        # PARTIAL
        if profit >= 3 and not trade["partial"]:
            trade["partial"] = True
            send(f"💰 TAKE PARTIAL: {trade['symbol']} +{profit:.2f}%")

        # LOCK
        if profit >= 3 and not trade["locked"]:
            trade["locked"] = True
            send(f"🔒 LOCK PROFIT: {trade['symbol']} +{profit:.2f}%")

        # TRAILING EXIT
        drop = ((trade["highest"] - price) / trade["highest"]) * 100
        if trade["locked"] and drop >= 2:
            trade["status"] = "win"
            send(f"⚠️ EXIT (Trailing): {trade['symbol']} secured {profit:.2f}%")
            continue

        # STOP
        if price <= trade["stop"]:
            trade["status"] = "loss"
            send(f"❌ STOP HIT: {trade['symbol']}")

        # TARGET
        elif price >= trade["target"]:
            trade["status"] = "win"
            send(f"🎯 TARGET HIT: {trade['symbol']}")

# ===== MAIN LOOP =====
def run():
    print("BOT STARTED")

    while True:
        try:
            manage_trades()

            for s in WATCHLIST:
                setup = analyze(s)

                if setup:
                    # 🚫 COOLDOWN BLOCK
                    if s in last_sent and time.time() - last_sent[s] < COOLDOWN:
                        continue

                    # ✅ SMART SETUP FILTER
                    existing = pending_setups.get(s)

                    if existing:
                        old_price = (existing["entry_low"] + existing["entry_high"]) / 2
                        new_price = (setup["entry_low"] + setup["entry_high"]) / 2

                        # Only update if meaningful change (>0.3%)
                        if abs(new_price - old_price) / old_price < 0.003:
                            continue

                    pending_setups[s] = setup

            check_entries()

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print("ERROR:", e)
            time.sleep(10)

# ===== START =====
if __name__ == "__main__":
    run()
