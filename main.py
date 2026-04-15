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
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=1h&outputsize=50&apikey={TWELVEDATA_KEY}"
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
            "close": float(c["close"]),
            "open": float(c["open"])
        })
    return list(reversed(result))

def detect_ifvg(candles):
    alerts = []
    last = candles[-1]

    # Buscar todos los FVGs activos en el historico
    # Un FVG se considera activo si NO fue mitigado antes de la ultima vela
    for i in range(2, len(candles) - 1):
        c1 = candles[i-2]
        c2 = candles[i-1]
        c3 = candles[i]

        # FVG bullish: low[c3] > high[c1]
        if c3["low"] > c1["high"]:
            fvg_top = c3["low"]
            fvg_bot = c1["high"]

            # Chequear si ya fue mitigado antes de la ultima vela
            already_mitigated = False
            for j in range(i+1, len(candles)-1):
                if candles[j]["close"] < fvg_bot:
                    already_mitigated = True
                    break

            # La ultima vela cierra con cuerpo por debajo del bottom -> IFVG bearish
            if not already_mitigated:
                body_close = last["close"]
                body_open = last["open"]
                body_bottom = min(body_close, body_open)
                if body_close < fvg_bot and body_bottom < fvg_bot:
                    key = f"bull_ifvg_{c1['time']}_{c3['time']}"
                    alerts.append((key, f"IFVG BEARISH creado | XAUUSD H1\nFVG top: {fvg_top:.2f} | Bot: {fvg_bot:.2f}\nMitigado en vela: {last['time']}"))

        # FVG bearish: high[c3] < low[c1]
        if c3["high"] < c1["low"]:
            fvg_top = c1["low"]
            fvg_bot = c3["high"]

            # Chequear si ya fue mitigado antes de la ultima vela
            already_mitigated = False
            for j in range(i+1, len(candles)-1):
                if candles[j]["close"] > fvg_top:
                    already_mitigated = True
                    break

            # La ultima vela cierra con cuerpo por encima del top -> IFVG bullish
            if not already_mitigated:
                body_close = last["close"]
                body_open = last["open"]
                body_top = max(body_close, body_open)
                if body_close > fvg_top and body_top > fvg_top:
                    key = f"bear_ifvg_{c1['time']}_{c3['time']}"
                    alerts.append((key, f"IFVG BULLISH creado | XAUUSD H1\nFVG top: {fvg_top:.2f} | Bot: {fvg_bot:.2f}\nMitigado en vela: {last['time']}"))

    return alerts

sent = set()

while True:
    try:
        candles = get_candles()
        if candles:
            for key, msg in detect_ifvg(candles):
                if key not in sent:
                    send_telegram(msg)
                    sent.add(key)
                    print(f"Sent: {msg}")
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(300)
