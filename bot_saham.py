import yfinance as yf
from groq import Groq
import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
import json
import numpy as np

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

client = Groq(api_key=GROQ_API_KEY)

SCAN_LIST = [
    "BBCA.JK","BBRI.JK","TLKM.JK","ASII.JK",
    "ADRO.JK","ANTM.JK","BMRI.JK",
    "AAPL","NVDA","TSLA","META","MSFT","BTC-USD"
]

# ================= SAFE DOWNLOAD =================
def get_data(ticker):

    df = yf.download(
        ticker,
        period="3mo",
        interval="1d",
        auto_adjust=True,
        progress=False
    )

    if df is None or df.empty:
        return None

    # FIX MULTI INDEX
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    return df

# ================= INDICATOR =================
def add_indicator(df):

    df["EMA20"] = df["Close"].ewm(span=20).mean()
    df["EMA50"] = df["Close"].ewm(span=50).mean()

    delta = df["Close"].diff()

    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()

    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    return df.dropna()

# ================= CHART =================
def make_chart(ticker, df):

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

# ================= SCANNER =================
def scan():

    kandidat = []

    print("Scanning Market V4...")

    for ticker in SCAN_LIST:

        try:
            df = get_data(ticker)

            if df is None or len(df) < 50:
                print("No Data:", ticker)
                continue

            df = add_indicator(df)

            last = df.iloc[-1]

            price = last["Close"].item()
            ema20 = last["EMA20"].item()
            ema50 = last["EMA50"].item()
            rsi = last["RSI"].item()

            volume = last["Volume"].item()
            avg_vol = df["Volume"].tail(20).mean()

            vol_ratio = volume / avg_vol if avg_vol > 0 else 1

            high20 = df["High"].tail(20).max()

            signal = "SIDEWAYS"
            confidence = 10

            if ema20 > ema50:
                signal = "BULLISH"
                confidence += 25

            if ema20 < ema50:
                signal = "BEARISH"
                confidence += 25

            if rsi < 30:
                signal = "OVERSOLD"
                confidence += 20

            if rsi > 70:
                signal = "OVERBOUGHT"
                confidence += 20

            if vol_ratio > 1.3:
                confidence += 15

            if price >= high20:
                signal = "BREAKOUT"
                confidence += 40

            kandidat.append({
                "ticker":ticker,
                "price":price,
                "signal":signal,
                "confidence":confidence,
                "df":df.tail(60)
            })

            print("OK:", ticker, signal, confidence)

        except Exception as e:
            print("ERROR:", ticker, e)

    if not kandidat:
        return []

    kandidat = sorted(kandidat, key=lambda x: x["confidence"], reverse=True)

    return kandidat[:3]

# ================= AI =================
def ai_analysis(ticker, price, signal, conf):

    prompt = f"""
    Analisa trading saham {ticker}
    Harga {price}
    Signal {signal}
    Confidence {conf}
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

# ================= DISCORD =================
def send_discord(data, analisa):

    make_chart(data["ticker"], data["df"])

    payload = {
        "embeds":[
            {
                "title":f"SMART SIGNAL {data['ticker']}",
                "color":3447003,
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
        print("Market benar-benar sepi.")
        return

    for h in hasil:

        analisa = ai_analysis(
            h["ticker"],
            h["price"],
            h["signal"],
            h["confidence"]
        )

        send_discord(h, analisa)

if __name__ == "__main__":
    main()
