import requests
import time
import os

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
sent_signals = set()
last_heartbeat = 0

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
        res = requests.get(url, headers=headers, timeout=10)

        if res.status_code != 200:
            return None, None

        data = res.json()

        if not data.get("chart") or not data["chart"]["result"]:
            return None, None

        result = data["chart"]["result"][0]

        closes = result["indicators"]["quote"][0]["close"]
        volumes = result["indicators"]["quote"][0]["volume"]

        closes = [c for c in closes if c is not None]
        volumes = [v for v in volumes if v is not None]

        return closes, volumes

    except Exception as e:
        print(f"DATA ERROR {symbol}: {e}", flush=True)
        return None, None

# ===== ANALYZE (V2 LOGIC) =====
def analyze(symbol):
    closes_5m, volumes = get_data(symbol)

    if not closes_5m or len(closes_5m) < 50:
        return None

    price = closes_5m[-1]

    # ===== 5M TREND =====
    ma20 = sum(closes_5m[-20:]) / 20
    ma50 = sum(closes_5m[-50:]) / 50

    # ===== RSI =====
    gains, losses = [], []
    for i in range(1, len(closes_5m)):
        diff = closes_5m[i] - closes_5m[i-1]
        gains.append(max(diff,0))
        losses.append(abs(min(diff,0)))

    avg_gain = sum(gains[-14:]) / 14
    avg_loss = sum(losses[-14:]) / 14 if sum(losses[-14:]) != 0 else 1
    rs = avg_gain / avg_loss
    rsi_val = 100 - (100/(1+rs))

    # ===== MOMENTUM =====
    momentum = (price - closes_5m[-10]) / closes_5m[-10]

    # ===== VOLUME =====
    avg_vol = sum(volumes[-20:]) / 20
    vol_ok = volumes[-1] > avg_vol * 1.0

    # ===== BREAKOUT =====
    recent_high = max(closes_5m[-20:])
    breakout = price > recent_high * 1.002

    # ===== 15M CONFIRMATION =====
    closes_15m = closes_5m[::3]
    if len(closes_15m) < 20:
        return None

    ma15 = sum(closes_15m[-20:]) / 20
    trend_15m = closes_15m[-1] > ma15

    # ===== FILTERS =====
    if not breakout:
        return None

    if not trend_15m:
        return None

    if rsi_val < 52 or rsi_val > 65:
        return None

    if momentum < 0.01:
        return None

    if not vol_ok:
        return None

    if ma20 < ma50:
        return None

    # ===== SCORE =====
    score = 0
    if breakout: score += 2
    if trend_15m: score += 2
    if momentum > 0.015: score += 1
    if vol_ok: score += 1
    if 55 <= rsi_val <= 62: score += 1

    confidence = round(score / 7, 2)

    if confidence < 0.6:
        return None

    entry_low = price
    entry_high = price * 1.003
    stop = price * 0.97
    target = price * 1.06

    return {
        "symbol": symbol,
        "entry_low": entry_low,
        "entry_high": entry_high,
        "stop": stop,
        "target": target,
        "rsi": rsi_val,
        "confidence": confidence
    }

# ===== ENTRY =====
def check_entries():
    for symbol, setup in list(pending_setups.items()):

        closes, _ = get_data(symbol)
        if not closes:
            continue

        price = closes[-1]

        if setup["entry_low"] <= price <= setup["entry_high"]:

            signal_id = f"{symbol}_{round(price, 2)}"

            if signal_id in sent_signals:
                continue

            if symbol in last_sent and time.time() - last_sent[symbol] < COOLDOWN:
                continue

            tag = "🔥 A+ BREAKOUT" if setup["confidence"] >= 0.7 else "⚡ BREAKOUT"

            send(f"""🚀 {tag} {symbol} @ {price:.2f}

Breakout Confirmed!
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
    global last_heartbeat

    print("BOT STARTED", flush=True)
    send("✅ V2 Bot is live (Breakout Mode)")

    while True:
        try:
            now = time.time()

            # HEARTBEAT
            if now - last_heartbeat > 1800:
                send("💓 Bot alive (V2 running)")
                last_heartbeat = now

            manage_trades()

            for s in WATCHLIST:
                setup = analyze(s)

                if setup:
                    if s in last_sent and time.time() - last_sent[s] < COOLDOWN:
                        continue

                    existing = pending_setups.get(s)

                    if existing:
                        old_price = (existing["entry_low"] + existing["entry_high"]) / 2
                        new_price = (setup["entry_low"] + setup["entry_high"]) / 2

                        if abs(new_price - old_price) / old_price < 0.003:
                            continue

                    pending_setups[s] = setup

            check_entries()

            print("Loop running...", flush=True)
            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print("CRASH:", e, flush=True)
            time.sleep(5)

# ===== START =====
if __name__ == "__main__":
    run()
