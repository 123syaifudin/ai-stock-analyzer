import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os, requests, time
from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

client = Groq(api_key=GROQ_API_KEY)

SCAN_LIST = [
    "BBCA.JK","BBRI.JK","TLKM.JK","ASII.JK",
    "ADRO.JK","ANTM.JK","BMRI.JK",
    "AAPL","NVDA","TSLA","META","MSFT","BTC-USD"
]

# ================= SAFE DOWNLOAD =================
def safe_download(ticker):
    try:
        df = yf.download(ticker, period="8mo", progress=False)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)

        df = df.dropna()
        df = df.astype(float)

        return df
    except:
        return pd.DataFrame()

# ================= INDICATOR =================
def indicator(df):

    df["EMA20"] = df["Close"].ewm(span=20).mean()
    df["EMA50"] = df["Close"].ewm(span=50).mean()
    df["EMA200"] = df["Close"].ewm(span=200).mean()

    df["VOL_AVG"] = df["Volume"].rolling(20).mean()

    return df.dropna()

# ================= MARKET STRUCTURE =================
def structure(df):

    high_break = df["High"].iloc[-1] > df["High"].tail(20).max()
    low_break = df["Low"].iloc[-1] < df["Low"].tail(20).min()

    if high_break:
        return "BULLISH STRUCTURE"
    if low_break:
        return "BEARISH STRUCTURE"

    return "RANGE"

# ================= SWING PLAN =================
def swing_plan(df):

    last = df.iloc[-1]

    entry = last["EMA20"]

    swing_low = df["Low"].tail(15).min()
    swing_high = df["High"].tail(40).max()

    sl = swing_low
    tp = swing_high

    rr = (tp-entry)/(entry-sl) if entry>sl else 0

    vol_spike = last["Volume"] > last["VOL_AVG"] * 1.5

    trend_score = 1 if last["EMA20"]>last["EMA50"] else 0
    trend_score += 1 if last["EMA50"]>last["EMA200"] else 0

    return entry,tp,sl,rr,vol_spike,trend_score

# ================= BACKTEST =================
def backtest(df):

    wins = 0
    total = 0

    for i in range(100, len(df)-30):

        if df["EMA20"].iloc[i] > df["EMA50"].iloc[i]:

            entry = df["Close"].iloc[i]
            future = df["Close"].iloc[i+30]

            total += 1

            if future > entry * 1.05:
                wins += 1

    if total == 0:
        return 0

    return round((wins/total)*100,2)

# ================= AI FILTER =================
def ai_filter(data):

    prompt = f"""
    Kamu analis hedge fund.
    Ticker {data['ticker']}
    RR {data['rr']}
    Winrate {data['winrate']}
    TrendScore {data['trend']}
    VolumeSpike {data['vol']}
    Structure {data['structure']}

    Putuskan:
    STRONG BUY / WATCHLIST / AVOID
    """

    try:
        chat = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":prompt}],
            max_tokens=10
        )
        return chat.choices[0].message.content
    except:
        return "WATCHLIST"

# ================= CHART =================
def make_chart(df, ticker):

    plt.figure(figsize=(8,4))
    plt.plot(df["Close"].tail(120))
    plt.plot(df["EMA20"].tail(120))
    plt.plot(df["EMA50"].tail(120))
    plt.title(ticker)

    filename = f"{ticker}.png"
    plt.savefig(filename)
    plt.close()

    return filename

# ================= SCAN =================
def scan():

    results = []

    for ticker in SCAN_LIST:

        df = safe_download(ticker)

        if df.empty:
            continue

        df = indicator(df)

        entry,tp,sl,rr,vol,trend = swing_plan(df)

        if rr < 1:
            continue

        winrate = backtest(df)
        struct = structure(df)

        score = rr*10 + trend*10 + (winrate/5)

        results.append({
            "ticker":ticker,
            "rr":rr,
            "entry":entry,
            "tp":tp,
            "sl":sl,
            "winrate":winrate,
            "trend":trend,
            "vol":vol,
            "structure":struct,
            "score":score,
            "df":df
        })

        time.sleep(1)

    results = sorted(results, key=lambda x:x["score"], reverse=True)

    return results[:3]

# ================= DISCORD =================
def send_discord(data):

    decision = ai_filter(data)

    chart = make_chart(data["df"], data["ticker"])

    files = {"file": open(chart,"rb")}

    payload = {
        "embeds":[
            {
                "title":f"🔥 MISTERX SWING SIGNAL {data['ticker']}",
                "description":f"AI Verdict: **{decision}**",
                "color":16753920,
                "fields":[
                    {"name":"RR","value":str(round(data["rr"],2))},
                    {"name":"Winrate","value":str(data["winrate"])+"%"},
                    {"name":"Structure","value":data["structure"]},
                    {"name":"Entry","value":str(round(data["entry"],2))},
                    {"name":"TP","value":str(round(data["tp"],2))},
                    {"name":"SL","value":str(round(data["sl"],2))}
                ],
                "image":{"url":f"attachment://{chart}"}
            }
        ]
    }

    requests.post(DISCORD_WEBHOOK, data={"payload_json":json.dumps(payload)}, files=files)

# ================= MAIN =================
def main():

    print("Scanning Swing Market...")

    hasil = scan()

    if not hasil:
        print("Tidak ada signal RR >= 1")
        return

    for h in hasil:
        send_discord(h)

    print("Signal terkirim.")

if __name__ == "__main__":
    main()
