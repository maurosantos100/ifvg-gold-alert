import os
import time
import requests

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
TWELVEDATA_KEY = os.environ["TWELVEDATA_KEY"]

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

def get_candles():
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=1h&outputsize=10&apikey={TWELVEDATA_KEY}"
    r = requests.get(url)
    data = r.json()
    if "values" not in data:
        return []
    candles = data["values"]
    result = []
    for c in candles:
        result.append({
            "time": c["datetime"],
            "open": float(c["open"]),
            "high": float(c["high"]),
            "low": float(c["low"]),
            "close": float(c["close"])
        })
    return list(reversed(result))

def detect_ifvg(candles):
    alerts = []
    known = set()
    for i in range(2, len(candles)):
        c1 = candles[i-2]
        c3 = candles[i]
        # FVG bullish: low[c3] > high[c1]
        if c3["low"] > c1["high"]:
            top = c3["low"]
            bot = c1["high"]
            # mitigado si close actual < bottom
            if candles[-1]["close"] < bot:
                key = f"bull_{c1['time']}"
                if key not in known:
                    known.add(key)
                    alerts.append(f"IFVG BEARISH creado | XAUUSD H1\nTop: {top:.2f} | Bot: {bot:.2f}\nHora: {candles[-1]['time']}")
        # FVG bearish: high[c3] < low[c1]
        if c3["high"] < c1["low"]:
            top = c1["low"]
            bot = c3["high"]
            # mitigado si close actual > top
            if candles[-1]["close"] > top:
                key = f"bear_{c1['time']}"
                if key not in known:
                    known.add(key)
                    alerts.append(f"IFVG BULLISH creado | XAUUSD H1\nTop: {top:.2f} | Bot: {bot:.2f}\nHora: {candles[-1]['time']}")
    return alerts

sent = set()

while True:
    try:
        candles = get_candles()
        if candles:
            alerts = detect_ifvg(candles)
            for a in alerts:
                if a not in sent:
                    send_telegram(a)
                    sent.add(a)
                    print(f"Sent: {a}")
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(300)
