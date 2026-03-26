import yfinance as yf
from groq import Groq
import os, requests, time
import pandas as pd
import numpy as np

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

client = Groq(api_key=GROQ_API_KEY)

SCAN_LIST = [
    "BBCA.JK","BBRI.JK","TLKM.JK","ASII.JK",
    "ADRO.JK","ANTM.JK","BMRI.JK",
    "AAPL","NVDA","TSLA","META","MSFT","BTC-USD"
]

# ================= SAFE DOWNLOADER =================
def safe_download(ticker, period="6mo", retry=3):

    for i in range(retry):
        try:
            df = yf.download(ticker, period=period, progress=False)

            if df is None or df.empty:
                time.sleep(1)
                continue

            # FIX MULTI INDEX
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)

            df = df.dropna()
            df = df.astype(float)

            return df

        except:
            time.sleep(1)

    return pd.DataFrame()

# ================= MARKET TREND =================
def market_trend():

    sp = safe_download("^GSPC","1mo")
    btc = safe_download("BTC-USD","1mo")

    if sp.empty or btc.empty:
        return "UNKNOWN"

    sp_close = sp["Close"]
    btc_close = btc["Close"]

    sp_trend = "BULL" if sp_close.iloc[-1] > sp_close.mean() else "BEAR"
    btc_trend = "BULL" if btc_close.iloc[-1] > btc_close.mean() else "BEAR"

    return f"SP500 {sp_trend} | BTC {btc_trend}"

# ================= FEAR GREED =================
def fear_greed():

    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=10)
        data = r.json()
        value = data["data"][0]["value"]
        status = data["data"][0]["value_classification"]

        return f"{value} ({status})"

    except:
        return "50 (Neutral)"

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

            if future > entry * 1.03:
                wins += 1

    if total == 0:
        return 0

    return round((wins/total)*100,2)

# ================= TRADING PLAN =================
def trading_plan(df):

    last = df.iloc[-1]

    entry = last["EMA20"]
    sl = last["EMA50"] * 0.99
    tp = df["High"].tail(30).max()

    rr = (tp-entry)/(entry-sl) if entry>sl else 1

    profit = ((tp-entry)/entry)*100
    loss = ((entry-sl)/entry)*100

    return entry,tp,sl,rr,profit,loss

# ================= AI TWEET =================
def tweet_ai(ticker, signal, rr):

    prompt = f"""
    Buat tweet trading branding MisterX.
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
        return "Stay smart with MisterX trading insight."

# ================= SCANNER =================
def scan():

    results = []

    for ticker in SCAN_LIST:

        df = safe_download(ticker)

        if df.empty:
            continue

        df = indicator(df)

        winrate = backtest(df)

        entry,tp,sl,rr,profit,loss = trading_plan(df)

        last = df.iloc[-1]

        signal = "BULLISH" if last["EMA20"] > last["EMA50"] else "BEARISH"

        confidence = 50 + winrate/2

        results.append({
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

        time.sleep(1)

    results = sorted(results, key=lambda x:x["confidence"], reverse=True)

    return results[:3]

# ================= DISCORD =================
def send_discord(data, trend, fear):

    tweet = tweet_ai(data["ticker"], data["signal"], data["rr"])

    payload = {
        "embeds":[
            {
                "title":f"🚀 MISTERX SMART SIGNAL {data['ticker']}",
                "color":65280,
                "fields":[
                    {"name":"📊 Signal","value":data["signal"],"inline":True},
                    {"name":"🎯 Confidence","value":str(round(data["confidence"],1)),"inline":True},
                    {"name":"🏆 Winrate","value":str(data["winrate"])+"%","inline":True},

                    {"name":"💰 Entry","value":str(round(data["entry"],2)),"inline":True},
                    {"name":"✅ TP","value":str(round(data["tp"],2)),"inline":True},
                    {"name":"🛑 SL","value":str(round(data["sl"],2)),"inline":True},

                    {"name":"⚖️ Risk Reward","value":str(round(data["rr"],2)),"inline":True},
                    {"name":"📈 Profit Potensi","value":str(round(data["profit"],2))+"%","inline":True},
                    {"name":"📉 Risk Potensi","value":str(round(data["loss"],2))+"%","inline":True},

                    {"name":"🌎 Market Trend","value":trend,"inline":False},
                    {"name":"😱 Fear Greed","value":fear,"inline":False},

                    {"name":"🐦 MisterX Tweet Idea","value":tweet[:400],"inline":False}
                ]
            }
        ]
    }

    requests.post(DISCORD_WEBHOOK, json=payload)

# ================= MAIN =================
def main():

    print("Scanning Market...")

    trend = market_trend()
    fear = fear_greed()

    hasil = scan()

    if not hasil:
        print("Tidak ada signal.")
        return

    for h in hasil:
        send_discord(h, trend, fear)

    print("Signal terkirim ke Discord.")

if __name__ == "__main__":
    main()
