import time
import requests
from datetime import datetime, timedelta

TELEGRAM_TOKEN = "8308050985:AAFcTT2_ZP-h7Cie8UhRO71mKKrUkH8RAbQ"
TELEGRAM_CHAT_ID = "640214582"
TWELVEDATA_KEY = "a5f67c63e14e44f7830df81f38232f4e"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

def get_candles():
    url = (
        f"https://api.twelvedata.com/time_series"
        f"?symbol=XAU/USD&interval=1h&outputsize=50&apikey={TWELVEDATA_KEY}"
    )
    r = requests.get(url)
    data = r.json()
    if "values" not in data:
        return []
    result = []
    for c in data["values"]:
        dt = datetime.strptime(c["datetime"], "%Y-%m-%d %H:%M:%S")
        dt_ny = dt + timedelta(hours=3)  # Twelve Data usa UTC-7, NY es UTC-4
        result.append({
            "time":  dt_ny.strftime("%Y-%m-%d %H:%M") + " NY",
            "open":  float(c["open"]),
            "high":  float(c["high"]),
            "low":   float(c["low"]),
            "close": float(c["close"]),
        })
    return list(reversed(result))

def get_active_fvgs(candles):
    fvgs = []
    for i in range(2, len(candles) - 1):
        c1 = candles[i - 2]
        c3 = candles[i]

        # FVG bullish: low[c3] > high[c1]
        if c3["low"] > c1["high"]:
            top = c3["low"]
            bot = c1["high"]
            mitigated = False
            for j in range(i + 1, len(candles) - 1):
                # Mitigado solo si el CIERRE es por debajo del bottom (misma logica que check_ifvg)
                if candles[j]["close"] < bot:
                    mitigated = True
                    break
            if not mitigated:
                fvgs.append({"type": "bullish", "top": top, "bot": bot, "formed": c3["time"]})

        # FVG bearish: high[c3] < low[c1]
        if c3["high"] < c1["low"]:
            top = c1["low"]
            bot = c3["high"]
            mitigated = False
            for j in range(i + 1, len(candles) - 1):
                # Mitigado solo si el CIERRE es por encima del top (misma logica que check_ifvg)
                if candles[j]["close"] > top:
                    mitigated = True
                    break
            if not mitigated:
                fvgs.append({"type": "bearish", "top": top, "bot": bot, "formed": c3["time"]})

    return fvgs

def check_ifvg(fvgs, last_candle):
    alerts = []
    body_high = max(last_candle["open"], last_candle["close"])
    body_low  = min(last_candle["open"], last_candle["close"])

    for fvg in fvgs:
        if fvg["type"] == "bullish":
            # IFVG bearish: FVG bullish invalidado por cierre con cuerpo por debajo del bottom
            if last_candle["close"] < fvg["bot"] and body_low < fvg["bot"]:
                key = f"ifvg_bear_{fvg['formed']}"
                msg = (
                    f"IFVG BEARISH creado | XAUUSD H1\n"
                    f"FVG top: {fvg['top']:.2f} | Bot: {fvg['bot']:.2f}\n"
                    f"Invalidado en: {last_candle['time']}"
                )
                alerts.append((key, msg))

        elif fvg["type"] == "bearish":
            # IFVG bullish: FVG bearish invalidado por cierre con cuerpo por encima del top
            if last_candle["close"] > fvg["top"] and body_high > fvg["top"]:
                key = f"ifvg_bull_{fvg['formed']}"
                msg = (
                    f"IFVG BULLISH creado | XAUUSD H1\n"
                    f"FVG top: {fvg['top']:.2f} | Bot: {fvg['bot']:.2f}\n"
                    f"Invalidado en: {last_candle['time']}"
                )
                alerts.append((key, msg))

    return alerts

sent = set()

while True:
    try:
        candles = get_candles()
        if len(candles) >= 4:
            fvgs = get_active_fvgs(candles)
            last = candles[-2]  # vela cerrada, no la actual en curso
            alerts = check_ifvg(fvgs, last)
            for key, msg in alerts:
                if key not in sent:
                    send_telegram(msg)
                    sent.add(key)
                    print(f"Sent: {msg}")
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(300)
