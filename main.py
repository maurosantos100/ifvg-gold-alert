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
        dt_ny = dt - timedelta(hours=10)
        result.append({
            "time":  dt_ny.strftime("%Y-%m-%d %H:%M") + " NY",
            "open":  float(c["open"]),
            "high":  float(c["high"]),
            "low":   float(c["low"]),
            "close": float(c["close"]),
        })
    return list(reversed(result))

def get_fvgs(candles):
    """Detecta todos los FVGs en el historial, sin importar si fueron tocados antes."""
    fvgs = []
    for i in range(2, len(candles)):
        c1 = candles[i - 2]
        c3 = candles[i]

        # FVG bullish: low[c3] > high[c1]
        if c3["low"] > c1["high"]:
            fvgs.append({
                "type": "bullish",
                "top":  c3["low"],
                "bot":  c1["high"],
                "bar":  i,
                "formed": c3["time"],
            })

        # FVG bearish: high[c3] < low[c1]
        if c3["high"] < c1["low"]:
            fvgs.append({
                "type": "bearish",
                "top":  c1["low"],
                "bot":  c3["high"],
                "bar":  i,
                "formed": c3["time"],
            })

    return fvgs

def find_ifvg_events(fvgs, candles):
    """
    Para cada FVG, busca la primera vela posterior que cierra con cuerpo del otro lado.
    Eso es el momento exacto de creacion del IFVG.
    Devuelve una lista de eventos (key, msg, bar_index) ordenados por barra.
    """
    events = []
    for fvg in fvgs:
        for j in range(fvg["bar"] + 1, len(candles)):
            c = candles[j]
            body_high = max(c["open"], c["close"])
            body_low  = min(c["open"], c["close"])

            if fvg["type"] == "bullish":
                # IFVG bearish: cierre con cuerpo por debajo del bottom
                if c["close"] < fvg["bot"] and body_low < fvg["bot"]:
                    key = f"ifvg_bear_{fvg['formed']}"
                    msg = (
                        f"IFVG BEARISH creado | XAUUSD H1\n"
                        f"FVG top: {fvg['top']:.2f} | Bot: {fvg['bot']:.2f}\n"
                        f"Invalidado en: {c['time']}"
                    )
                    events.append((key, msg, j))
                    break  # primera vela que lo invalida, no seguir

            elif fvg["type"] == "bearish":
                # IFVG bullish: cierre con cuerpo por encima del top
                if c["close"] > fvg["top"] and body_high > fvg["top"]:
                    key = f"ifvg_bull_{fvg['formed']}"
                    msg = (
                        f"IFVG BULLISH creado | XAUUSD H1\n"
                        f"FVG top: {fvg['top']:.2f} | Bot: {fvg['bot']:.2f}\n"
                        f"Invalidado en: {c['time']}"
                    )
                    events.append((key, msg, j))
                    break  # primera vela que lo invalida, no seguir

    return events

sent = set()

while True:
    try:
        candles = get_candles()
        if len(candles) >= 4:
            fvgs = get_fvgs(candles)
            last_bar = len(candles) - 2  # indice de la ultima vela cerrada

            print(f"Candles: {len(candles)} | FVGs detectados: {len(fvgs)}")
            print(f"Ultima vela cerrada: {candles[last_bar]['time']} close:{candles[last_bar]['close']:.2f}")

            events = find_ifvg_events(fvgs, candles)

            for key, msg, bar_idx in events:
                # Solo alertar si el evento ocurrio en la ultima vela cerrada
                if bar_idx == last_bar and key not in sent:
                    send_telegram(msg)
                    sent.add(key)
                    print(f"Sent: {msg}")
                elif key not in sent:
                    # Evento pasado — marcarlo como ya visto para no spamear
                    sent.add(key)
                    print(f"Skipped (pasado): {key}")

    except Exception as e:
        print(f"Error: {e}")
    time.sleep(300)
