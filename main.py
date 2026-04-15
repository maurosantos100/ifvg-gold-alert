import time
import requests
from datetime import datetime, timezone, timedelta

TELEGRAM_TOKEN = "8308050985:AAFcTT2_ZP-h7Cie8UhRO71mKKrUkH8RAbQ"
TELEGRAM_CHAT_ID = "640214582"
TWELVEDATA_KEY = "a5f67c63e14e44f7830df81f38232f4e"

NY_OFFSET = timedelta(hours=-4)

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

def get_candles():
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=1h&outputsize=10&apikey={TWELVEDATA_KEY}"
    r = requests.get(url)
    data = r.json()
    if "values" not in data:
        return []
    result = []
    for c in data["values"]:
        utc_time = datetime.strptime(c["datetime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        ny_time = utc_time + NY_OFFSET
        result.append({
            "time": ny_time.strftime("%Y-%m-%d %H:%M NY"),
            "high": float(c["high"]),
            "low": float(c["low"]),
            "close": float(c["close"])
        })
    return list(reversed(result))

def detect_ifvg(candles):
    alerts = []
    # Solo mirar las ultimas 3 velas para IFVGs recientes
    for i in range(max(2, len(candles)-3), len(candles)):
        c1 = candles[i-2]
        c3 = candles[i]
        if c3["low"] > c1["high"]:
            top = c3["low"]
            bot = c1["high"]
            if candles[-1]["close"] < bot:
                alerts.append(f"IFVG BEARISH creado | XAUUSD H1\nTop: {top:.2f} | Bot: {bot:.2f}\nVela: {c3['time']}")
        if c3["high"] < c1["low"]:
            top = c1["low"]
            bot = c3["high"]
            if candles[-1]["close"] > top:
                alerts.append(f"IFVG BULLISH creado | XAUUSD H1\nTop: {top:.2f} | Bot: {bot:.2f}\nVela: {c3['time']}")
    return alerts

sent = set()

while True:
    try:
        candles = get_candles()
        if candles:
            for a in detect_ifvg(candles):
                if a not in sent:
                    send_telegram(a)
                    sent.add(a)
                    print(f"Sent: {a}")
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(300)
