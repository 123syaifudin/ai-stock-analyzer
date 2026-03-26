import yfinance as yf
from groq import Groq
import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
import json
import numpy as np

# ================= CONFIG =================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

client = Groq(api_key=GROQ_API_KEY)

SCAN_LIST = [
    "BBCA.JK","BBRI.JK","TLKM.JK","ASII.JK","GOTO.JK",
    "ADRO.JK","ANTM.JK","BMRI.JK",
    "AAPL","NVDA","TSLA","META","MSFT","BTC-USD"
]

# ================= INDICATOR =================
def add_indicator(df):

    df["EMA20"] = df["Close"].ewm(span=20).mean()
    df["EMA50"] = df["Close"].ewm(span=50).mean()

    delta = df["Close"].diff()

    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()

    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    return df

# ================= CHART =================
def create_chart(ticker, df):

    plt.style.use("dark_background")
    plt.figure(figsize=(10,5))

    plt.plot(df.index, df["Close"], label="Price")
    plt.plot(df.index, df["EMA20"], label="EMA20")
    plt.plot(df.index, df["EMA50"], label="EMA50")

    plt.legend()
    plt.title(ticker)
    plt.grid(alpha=0.2)

    plt.savefig("chart.png", bbox_inches="tight")
    plt.close()

# ================= AI =================
def ai_analyze(ticker, price, signal, confidence):

    prompt = f"""
    Kamu adalah analis saham.

    Saham: {ticker}
    Harga: {price}
    Signal: {signal}
    Confidence: {confidence}

    Buat analisa singkat trading.
    """

    try:
        chat = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":prompt}],
            temperature=0.4,
            max_tokens=200
        )
        return chat.choices[0].message.content
    except:
        return "AI gagal."

# ================= SCANNER =================
def scan():

    kandidat = []

    print("Scanning Market Smart V2...")

    for ticker in SCAN_LIST:

        try:
            df = yf.download(ticker, period="3mo", interval="1d", progress=False)

            if df.empty:
                continue

            df = add_indicator(df)

            last = df.iloc[-1]

            price = last["Close"]
            rsi = last["RSI"]

            ema20 = last["EMA20"]
            ema50 = last["EMA50"]

            volume = last["Volume"]
            avg_vol = df["Volume"].tail(20).mean()

            vol_spike = volume / avg_vol if avg_vol > 0 else 0

            breakout = price >= df["High"].tail(20).max()

            signal = "SIDEWAYS"
            confidence = 0

            if ema20 > ema50:
                signal = "BULLISH"
                confidence += 30

            if ema20 < ema50:
                signal = "BEARISH"
                confidence += 30

            if rsi < 30:
                signal = "OVERSOLD"
                confidence += 25

            if rsi > 70:
                signal = "OVERBOUGHT"
                confidence += 25

            if vol_spike > 1.5:
                confidence += 20

            if breakout:
                signal = "BREAKOUT"
                confidence += 40

            kandidat.append({
                "ticker":ticker,
                "price":price,
                "signal":signal,
                "confidence":confidence,
                "df":df.tail(60)
            })

        except Exception as e:
            print("Error:",ticker,e)

    kandidat = sorted(kandidat, key=lambda x: x["confidence"], reverse=True)

    if not kandidat:
        return []

    return kandidat[:3]

# ================= DISCORD =================
def send_discord(data, analisa):

    create_chart(data["ticker"], data["df"])

    payload = {
        "embeds":[
            {
                "title": f"SMART SIGNAL {data['ticker']}",
                "color": 3447003,
                "fields":[
                    {"name":"Signal","value":data["signal"]},
                    {"name":"Confidence","value":str(data["confidence"])},
                    {"name":"Price","value":str(round(data["price"],2))},
                    {"name":"AI","value":analisa[:900]}
                ],
                "image":{"url":"attachment://chart.png"}
            }
        ]
    }

    with open("chart.png","rb") as f:
        requests.post(
            DISCORD_WEBHOOK,
            data={"payload_json":json.dumps(payload)},
            files={"file":f}
        )

# ================= MAIN =================
def main():

    hasil = scan()

    if not hasil:
        print("Market Sepi.")
        return

    for h in hasil:

        analisa = ai_analyze(
            h["ticker"],
            h["price"],
            h["signal"],
            h["confidence"]
        )

        send_discord(h, analisa)

if __name__ == "__main__":
    main()
