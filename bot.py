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

COOLDOWN = 3600  # 1 hour

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

    if len(gains) < period:
        return 50

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100/(1+rs))

# ===== ANALYZE =====
def analyze(symbol):
    closes = get_data(symbol)

    if not closes or len(closes) < 50:
        return None

    price = closes[-1]

    ma20 = sum(closes[-20:]) / 20
    ma50 = sum(closes[-50:]) / 50
    rsi_val = rsi(closes)
    momentum = (price - closes[-10]) / closes[-10]

    # Balanced filter
    if price > ma20 and ma20 > ma50 and 50 <= rsi_val <= 65 and momentum > 0:
        confidence = 0.75
    elif price > ma20 and momentum > 0:
        confidence = 0.6
    else:
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

        closes = get_data(symbol)
        if not closes:
            continue

        price = closes[-1]

        if setup["entry_low"] <= price <= setup["entry_high"]:

            if symbol in last_sent:
                if time.time() - last_sent[symbol] < COOLDOWN:
                    continue

            tag = "🔥 A ENTRY" if setup["confidence"] >= 0.7 else "⚡ B ENTRY"

            send(f"""🚨 {tag} {symbol} @ {price:.2f}

Entry Zone Hit!
Target: {setup['target']:.2f}
Stop: {setup['stop']:.2f}
RSI: {setup['rsi']:.1f}
""")

            last_sent[symbol] = time.time()

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

        closes = get_data(trade["symbol"])
        if not closes:
            continue

        price = closes[-1]

        # update highest
        if price > trade["highest"]:
            trade["highest"] = price

        profit = ((price - trade["entry"]) / trade["entry"]) * 100

        # 💰 PARTIAL PROFIT
        if profit >= 3 and not trade["partial_taken"]:
            trade["partial_taken"] = True
            send(f"💰 TAKE PARTIAL: {trade['symbol']} +{profit:.2f}%")

        # 🔒 LOCK PROFIT
        if profit >= 3 and not trade["locked"]:
            trade["locked"] = True
            send(f"🔒 LOCK PROFIT: {trade['symbol']} +{profit:.2f}%")

        # 📉 TRAILING EXIT
        drop = ((trade["highest"] - price) / trade["highest"]) * 100

        if trade["locked"] and drop >= 2:
            trade["status"] = "win"
            send(f"⚠️ EXIT (Trailing): {trade['symbol']} secured {profit:.2f}%")
            continue

        # ❌ STOP LOSS
        if price <= trade["stop"]:
            trade["status"] = "loss"
            send(f"❌ STOP HIT: {trade['symbol']}")

        # 🎯 TARGET HIT
        elif price >= trade["target"]:
            trade["status"] = "win"
            send(f"🎯 TARGET HIT: {trade['symbol']}")

# ===== MAIN LOOP =====
def run():
    send("🚀 BOT LIVE (FULL SYSTEM)")

    while True:
        try:
            check_trades()

            # find setups
            for s in WATCHLIST:
                setup = analyze(s)
                if setup:
                    pending_setups[s] = setup

            # trigger entries
            check_entry_triggers()

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print("ERROR:", e)
            time.sleep(10)

# ===== START =====
if __name__ == "__main__":
    run()
