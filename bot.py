import requests
import time

# ===== CONFIG =====
TELEGRAM_TOKEN = "8268157455:AAElh_Fi0znhxEhVkwbK1Y2fhRMoUA65TI4"
CHAT_ID = "7216850185"

WATCHLIST = ["AAPL","NVDA","MSFT","AMD","TSLA","META","GOOGL","AMZN"]
CHECK_INTERVAL = 180

# ===== STATE =====
trades = []
last_sent = {}
pending_setups = {}
triggered_symbols = set()

COOLDOWN = 3600  # 1 hour
RESET_TIME = 3600 * 6  # reset every 6 hours
last_reset = time.time()

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
        closes = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]
        volumes = [v for v in result["indicators"]["quote"][0]["volume"] if v is not None]

        return closes, volumes
    except:
        return None, None

# ===== ANALYZE =====
def analyze(symbol):
    closes, volumes = get_data_full(symbol)

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
        "price": price,
        "entry_low": entry_low,
        "entry_high": entry_high,
        "stop": stop,
        "target": target,
        "rsi": rsi_val,
        "confidence": confidence
    }

# ===== ENTRY TRIGGER =====
def check_entry_triggers():
    for symbol, setup in list(pending_setups.items()):

        closes, _ = get_data_full(symbol)
        if not closes:
            continue

        price = closes[-1]

        if setup["entry_low"] <= price <= setup["entry_high"]:

            if symbol in last_sent and time.time() - last_sent[symbol] < COOLDOWN:
                continue

            tag = "🔥 A ENTRY" if setup["confidence"] >= 0.7 else "⚡ B ENTRY"

            send(f"""🚨 {tag} {symbol} @ {price:.2f}

Entry Zone Hit!
Target: {setup['target']:.2f}
Stop: {setup['stop']:.2f}
RSI: {setup['rsi']:.1f}
""")

            last_sent[symbol] = time.time()
            triggered_symbols.add(symbol)

            trades.append({
                "symbol": symbol,
                "entry": price,
                "stop": setup["stop"],
                "target": setup["target"],
                "status": "open",
                "highest": price,
                "locked": False,
                "partial_taken": False
            })

            del pending_setups[symbol]

# ===== TRADE MANAGEMENT =====
def check_trades():
    for trade in trades:
        if trade["status"] != "open":
            continue

        closes, _ = get_data_full(trade["symbol"])
        if not closes:
            continue

        price = closes[-1]

        if price > trade["highest"]:
            trade["highest"] = price

        profit = ((price - trade["entry"]) / trade["entry"]) * 100

        if profit >= 3 and not trade["partial_taken"]:
            trade["partial_taken"] = True
            send(f"💰 TAKE PARTIAL: {trade['symbol']} +{profit:.2f}%")

        if profit >= 3 and not trade["locked"]:
            trade["locked"] = True
            send(f"🔒 LOCK PROFIT: {trade['symbol']} +{profit:.2f}%")

        drop = ((trade["highest"] - price) / trade["highest"]) * 100

        if trade["locked"] and drop >= 2:
            trade["status"] = "win"
            send(f"⚠️ EXIT (Trailing): {trade['symbol']} secured {profit:.2f}%")
            continue

        if price <= trade["stop"]:
            trade["status"] = "loss"
            send(f"❌ STOP HIT: {trade['symbol']}")

        elif price >= trade["target"]:
            trade["status"] = "win"
            send(f"🎯 TARGET HIT: {trade['symbol']}")

# ===== MAIN LOOP =====
def run():
    global last_reset

    send("🚀 BOT LIVE (SMART FINAL VERSION)")

    while True:
        try:
            check_trades()

            # reset duplicates every few hours
            if time.time() - last_reset > RESET_TIME:
                triggered_symbols.clear()
                last_reset = time.time()

            for s in WATCHLIST:
                setup = analyze(s)
                if setup and s not in triggered_symbols:
                    pending_setups[s] = setup

            check_entry_triggers()

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print("ERROR:", e)
            time.sleep(10)

# ===== START =====
if __name__ == "__main__":
    run()
