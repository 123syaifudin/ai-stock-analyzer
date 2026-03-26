import yfinance as yf
from groq import Groq
import os, requests, json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

client = Groq(api_key=GROQ_API_KEY)

SCAN_LIST = [
    "BBCA.JK","BBRI.JK","TLKM.JK","ASII.JK",
    "ADRO.JK","ANTM.JK","BMRI.JK",
    "AAPL","NVDA","TSLA","META","MSFT","BTC-USD"
]

# ================= MARKET TREND =================
def market_trend():

    sp = yf.download("^GSPC", period="1mo", progress=False)
    btc = yf.download("BTC-USD", period="1mo", progress=False)

    sp_trend = "BULL" if sp["Close"].iloc[-1] > sp["Close"].mean() else "BEAR"
    btc_trend = "BULL" if btc["Close"].iloc[-1] > btc["Close"].mean() else "BEAR"

    return sp_trend, btc_trend

# ================= FEAR GREED =================
def fear_greed():
    try:
        r = requests.get("https://api.alternative.me/fng/")
        data = r.json()
        return data["data"][0]["value"], data["data"][0]["value_classification"]
    except:
        return "50","Neutral"

# ================= INDICATOR =================
def indicator(df):

    df["EMA20"] = df["Close"].ewm(span=20).mean()
    df["EMA50"] = df["Close"].ewm(span=50).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()

    rs = gain / loss
    df["RSI"] = 100 - (100/(1+rs))

    return df.dropna()

# ================= BACKTEST =================
def backtest(df):

    wins = 0
    total = 0

    for i in range(60, len(df)-20):

        if df["EMA20"].iloc[i] > df["EMA50"].iloc[i] and df["EMA20"].iloc[i-1] <= df["EMA50"].iloc[i-1]:

            entry = df["Close"].iloc[i]
            future = df["Close"].iloc[i+20]

            total += 1

            if future > entry*1.03:
                wins += 1

    if total == 0:
        return 0

    return round((wins/total)*100,2)

# ================= ENTRY TP SL =================
def trading_plan(df):

    last = df.iloc[-1]

    price = last["Close"]
    ema20 = last["EMA20"]
    ema50 = last["EMA50"]

    entry = ema20
    sl = ema50 * 0.99
    tp = df["High"].tail(30).max()

    rr = (tp-entry)/(entry-sl) if entry>sl else 1

    profit = ((tp-entry)/entry)*100
    loss = ((entry-sl)/entry)*100

    return entry, tp, sl, rr, profit, loss

# ================= AI TWEET =================
def tweet_ai(ticker, signal, rr):

    prompt = f"""
    Buat tweet trading menarik branding MisterX.
    Saham {ticker}
    Signal {signal}
    Risk Reward {rr}
    """

    try:
        chat = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":prompt}],
            max_tokens=120
        )
        return chat.choices[0].message.content
    except:
        return "Tweet gagal."

# ================= SCAN =================
def scan():

    hasil = []

    for ticker in SCAN_LIST:

        try:
            df = yf.download(ticker, period="6mo", progress=False)

            if df.empty:
                continue

            df = indicator(df)

            winrate = backtest(df)

            entry,tp,sl,rr,profit,loss = trading_plan(df)

            last = df.iloc[-1]

            signal = "BULLISH" if last["EMA20"]>last["EMA50"] else "BEARISH"

            confidence = 50 + winrate/2

            hasil.append({
                "ticker":ticker,
                "price":last["Close"],
                "signal":signal,
                "confidence":confidence,
                "entry":entry,
                "tp":tp,
                "sl":sl,
                "rr":rr,
                "profit":profit,
                "loss":loss,
                "winrate":winrate
            })

        except:
            pass

    return sorted(hasil, key=lambda x:x["confidence"], reverse=True)[:3]

# ================= DISCORD =================
def send(data, trend, fear):

    tweet = tweet_ai(data["ticker"], data["signal"], data["rr"])

    payload = {
        "embeds":[
            {
                "title":f"🚀 MISTERX SMART SIGNAL {data['ticker']}",
                "color":15844367,
                "fields":[
                    {"name":"Signal","value":data["signal"]},
                    {"name":"Confidence","value":str(round(data["confidence"],1))},
                    {"name":"Entry","value":str(round(data["entry"],2))},
                    {"name":"TP","value":str(round(data["tp"],2))},
                    {"name":"SL","value":str(round(data["sl"],2))},
                    {"name":"RR","value":str(round(data["rr"],2))},
                    {"name":"Winrate","value":str(data["winrate"])+"%"},
                    {"name":"Market Trend","value":str(trend)},
                    {"name":"Fear Greed","value":str(fear)},
                    {"name":"Tweet Idea","value":tweet[:500]}
                ]
            }
        ]
    }

    requests.post(DISCORD_WEBHOOK, json=payload)

# ================= MAIN =================
def main():

    trend = market_trend()
    fear = fear_greed()

    hasil = scan()

    for h in hasil:
        send(h, trend, fear)

if __name__ == "__main__":
    main()
