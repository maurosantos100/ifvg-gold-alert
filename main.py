import time
import requests
from datetime import datetime

TELEGRAM_TOKEN = "8308050985:AAFcTT2_ZP-h7Cie8UhRO71mKKrUkH8RAbQ"
TELEGRAM_CHAT_ID = "640214582"
TWELVEDATA_KEY = "a5f67c63e14e44f7830df81f38232f4e"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

def get_candles():
    url = (
        f"https://api.twelvedata.com/time_series"
        f"?symbol=XAU/USD&interval=1h&outputsize=200&apikey={TWELVEDATA_KEY}"
    )
    r = requests.get(url)
    data = r.json()
    if "values" not in data:
        return []
    result = []
    for c in data["values"]:
        result.append({
            "time":  c["datetime"],
            "open":  float(c["open"]),
            "high":  float(c["high"]),
            "low":   float(c["low"]),
            "close": float(c["close"]),
        })
    return list(reversed(result))

def get_fvgs(candles):
    fvgs = []
    for i in range(2, len(candles)):
        c1 = candles[i - 2]
        c3 = candles[i]
        if c3["low"] > c1["high"]:
            fvgs.append({"type": "bullish", "top": c3["low"], "bot": c1["high"],
                         "bar": i, "formed": c3["time"]})
        if c3["high"] < c1["low"]:
            fvgs.append({"type": "bearish", "top": c1["low"], "bot": c3["high"],
                         "bar": i, "formed": c3["time"]})
    return fvgs

def find_ifvg_events(fvgs, candles):
    events = []
    for fvg in fvgs:
        for j in range(fvg["bar"] + 1, len(candles)):
            c = candles[j]
            body_high = max(c["open"], c["close"])
            body_low  = min(c["open"], c["close"])
            if fvg["type"] == "bullish":
                if c["close"] < fvg["bot"] and body_low < fvg["bot"]:
                    key = f"ifvg_bear_{fvg['formed']}"
                    msg = (f"IFVG BEARISH creado | XAUUSD H1\n"
                           f"FVG top: {fvg['top']:.2f} | Bot: {fvg['bot']:.2f}\n"
                           f"Invalidado en: {c['time']}")
                    events.append((key, msg, j))
                    break
            elif fvg["type"] == "bearish":
                if c["close"] > fvg["top"] and body_high > fvg["top"]:
                    key = f"ifvg_bull_{fvg['formed']}"
                    msg = (f"IFVG BULLISH creado | XAUUSD H1\n"
                           f"FVG top: {fvg['top']:.2f} | Bot: {fvg['bot']:.2f}\n"
                           f"Invalidado en: {c['time']}")
                    events.append((key, msg, j))
                    break
    return events

def segundos_hasta_proximo_chequeo():
    """Calcula segundos hasta el proximo :02, :17, :32 o :47 de la hora actual."""
    ahora = datetime.utcnow()
    minuto = ahora.minute
    segundo = ahora.second
    minutos_chequeo = [2, 17, 32, 47]
    for m in minutos_chequeo:
        if minuto < m or (minuto == m and segundo == 0):
            espera = (m - minuto) * 60 - segundo
            return max(espera, 1)
    # si pasamos el :47, esperar hasta el :02 de la proxima hora
    espera = (60 - minuto + 2) * 60 - segundo
    return max(espera, 1)

sent = set()

while True:
    try:
        candles = get_candles()
        if len(candles) >= 4:
            fvgs = get_fvgs(candles)
            last_bar = len(candles) - 2
            events = find_ifvg_events(fvgs, candles)
            for key, msg, bar_idx in events:
                if bar_idx >= last_bar - 1 and key not in sent:
                    send_telegram(msg)
                    sent.add(key)
                    print(f"Sent: {msg}")
                elif key not in sent:
                    sent.add(key)
                    print(f"Skipped (pasado): {key}")
    except Exception as e:
        print(f"Error: {e}")

    espera = segundos_hasta_proximo_chequeo()
    print(f"Proximo chequeo en {espera}s")
    time.sleep(espera)
