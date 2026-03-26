import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os, requests, time, json, hashlib
from groq import Groq
from datetime import datetime

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

client = Groq(api_key=GROQ_API_KEY)

# ================= HUGE INDO + GLOBAL =================
SCAN_LIST = [
"BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK",
"TLKM.JK","EXCL.JK","ISAT.JK",
"ASII.JK","AUTO.JK","UNTR.JK",
"ADRO.JK","ITMG.JK","PTBA.JK","ANTM.JK","MDKA.JK",
"INCO.JK","TINS.JK",
"CPIN.JK","JPFA.JK",
"ICBP.JK","INDF.JK","MYOR.JK",
"ACES.JK","MAPI.JK","ERAA.JK",
"SMGR.JK","INTP.JK",
"AAPL","NVDA","TSLA","META","MSFT","BTC-USD"
]

# ================= SAFE DOWNLOAD =================
def safe_download(ticker):
    try:
        df = yf.download(ticker, period="1y", progress=False)

        if df is None or df.empty:
            return pd.DataFrame()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)

        df = df.dropna().astype(float)
        return df
    except:
        return pd.DataFrame()

# ================= INDICATOR =================
def indicator(df):

    if len(df) < 220:
        return pd.DataFrame()

    df["EMA20"] = df["Close"].ewm(span=20).mean()
    df["EMA50"] = df["Close"].ewm(span=50).mean()
    df["EMA200"] = df["Close"].ewm(span=200).mean()

    df["VOL_AVG"] = df["Volume"].rolling(20).mean()
    df["MOMENTUM"] = df["Close"].pct_change(10)

    df["TR"] = np.maximum(
        df["High"] - df["Low"],
        np.maximum(
            abs(df["High"] - df["Close"].shift()),
            abs(df["Low"] - df["Close"].shift())
        )
    )
    df["ATR"] = df["TR"].rolling(14).mean()

    return df.dropna()

# ================= STRUCTURE =================
def structure(df):

    hh = df["High"].tail(30).max()
    ll = df["Low"].tail(30).min()
    last = df.iloc[-1]["Close"]

    if last >= hh:
        return "BREAKOUT"
    if last <= ll:
        return "BREAKDOWN"
    return "RANGE"

# ================= SWING PLAN =================
def swing_plan(df):

    last = df.iloc[-1]

    entry = last["EMA20"]

    sl = entry - last["ATR"]*2
    tp = entry + last["ATR"]*4

    if entry <= sl:
        return None

    rr = (tp-entry)/(entry-sl)

    vol_spike = last["Volume"] > last["VOL_AVG"]*1.4

    trend = 0
    if last["EMA20"] > last["EMA50"]:
        trend += 1
    if last["EMA50"] > last["EMA200"]:
        trend += 1
    if last["MOMENTUM"] > 0:
        trend += 1

    return entry,tp,sl,rr,vol_spike,trend

# ================= STABLE BACKTEST =================
def backtest(df):

    df_bt = df.tail(250)

    wins = 0
    total = 0

    for i in range(60, len(df_bt)-25):

        if df_bt["EMA20"].iloc[i] > df_bt["EMA50"].iloc[i]:

            entry = df_bt["Close"].iloc[i]
            future = df_bt["Close"].iloc[i+25]

            total += 1

            if future > entry*1.06:
                wins += 1

    if total == 0:
        return 0

    return round((wins/total)*100,2)

# ================= FEAR GREED =================
def fear_greed():

    btc = safe_download("BTC-USD")

    if btc.empty:
        return "NEUTRAL"

    ret = btc["Close"].pct_change(5).iloc[-1]

    if ret > 0.08:
        return "EXTREME GREED"
    if ret > 0.03:
        return "GREED"
    if ret < -0.08:
        return "EXTREME FEAR"
    if ret < -0.03:
        return "FEAR"

    return "NEUTRAL"

# ================= GLOBAL TREND =================
def global_trend():

    spy = safe_download("^GSPC")

    if spy.empty:
        return "UNKNOWN"

    spy = indicator(spy)

    if spy.empty:
        return "UNKNOWN"

    if spy["Close"].iloc[-1] > spy["EMA50"].iloc[-1]:
        return "GLOBAL BULL"

    return "GLOBAL BEAR"

# ================= SIGNAL ID LOCK =================
def signal_id(data):

    raw = f"{data['ticker']}{round(data['entry'],2)}{round(data['tp'],2)}{round(data['sl'],2)}"
    return hashlib.md5(raw.encode()).hexdigest()[:8]

# ================= AI FILTER =================
def ai_filter(data):

    prompt = f"""
    Kamu hedge fund swing trader.
    RR {data['rr']}
    Winrate {data['winrate']}
    TrendScore {data['trend']}
    Structure {data['structure']}
    FearGreed {data['fear']}
    GlobalTrend {data['gtrend']}

    Jawab hanya:
    STRONG BUY / WATCHLIST / AVOID
    """

    try:
        chat = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":prompt}],
            temperature=0,
            max_tokens=10
        )
        return chat.choices[0].message.content.strip()
    except:
        return "WATCHLIST"

# ================= AI DESC =================
def ai_desc(data):

    prompt = f"""
    Berikan analisa singkat tindakan investor swing.
    RR {data['rr']}
    Winrate {data['winrate']}
    TrendScore {data['trend']}
    Structure {data['structure']}
    FearGreed {data['fear']}
    GlobalTrend {data['gtrend']}
    Maksimal 3 kalimat.
    """

    try:
        chat = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":prompt}],
            temperature=0.2,
            max_tokens=120
        )
        return chat.choices[0].message.content.strip()
    except:
        return "AI analisa tidak tersedia."

# ================= CHART =================
def chart(df,ticker):

    plt.figure(figsize=(10,4))
    plt.plot(df["Close"].tail(150))
    plt.plot(df["EMA20"].tail(150))
    plt.plot(df["EMA50"].tail(150))
    plt.title(ticker)

    file = f"{ticker}.png"
    plt.savefig(file)
    plt.close()

    return file

# ================= SCAN =================
def scan():

    fg = fear_greed()
    gt = global_trend()

    results = []

    for ticker in SCAN_LIST:

        df = safe_download(ticker)
        if df.empty:
            continue

        df = indicator(df)
        if df.empty:
            continue

        plan = swing_plan(df)
        if plan is None:
            continue

        entry,tp,sl,rr,vol,trend = plan
        if rr < 1:
            continue

        winrate = backtest(df)
        struct = structure(df)

        score = rr*20 + trend*15 + winrate/3 + (8 if vol else 0)

        data = {
            "ticker":ticker,
            "entry":entry,
            "tp":tp,
            "sl":sl,
            "rr":rr,
            "trend":trend,
            "vol":vol,
            "winrate":winrate,
            "structure":struct,
            "fear":fg,
            "gtrend":gt,
            "score":score,
            "df":df
        }

        data["sid"] = signal_id(data)

        results.append(data)

        time.sleep(0.4)

    results = sorted(results,key=lambda x:x["score"],reverse=True)

    return results[:5]

# ================= DISCORD =================
def send_dc(data):

    verdict = ai_filter(data)
    desc = ai_desc(data)
    img = chart(data["df"],data["ticker"])

    files = {"file":open(img,"rb")}

    payload = {
        "embeds":[
            {
                "title":f"🚀 MISTERX SIGNAL {data['ticker']} | ID {data['sid']}",
                "description":f"🤖 AI Verdict **{verdict}**",
                "color":5763719,
                "fields":[
                    {"name":"🌎 Global","value":data["gtrend"],"inline":True},
                    {"name":"😱 FearGreed","value":data["fear"],"inline":True},
                    {"name":"🏆 Winrate","value":str(data["winrate"])+"%","inline":True},

                    {"name":"📊 RR","value":str(round(data["rr"],2)),"inline":True},
                    {"name":"🧱 Structure","value":data["structure"],"inline":True},
                    {"name":"⚡ Trend","value":str(data["trend"]),"inline":True},

                    {"name":"💰 Entry","value":str(round(data["entry"],2)),"inline":True},
                    {"name":"✅ TP","value":str(round(data["tp"],2)),"inline":True},
                    {"name":"🛑 SL","value":str(round(data["sl"],2)),"inline":True},

                    {"name":"🧠 AI Analisa","value":desc,"inline":False},
                    {"name":"⚠️ Disclaimer","value":"Signal AI MisterX bukan saran investasi.","inline":False}
                ],
                "image":{"url":f"attachment://{img}"}
            }
        ]
    }

    requests.post(DISCORD_WEBHOOK,
        data={"payload_json":json.dumps(payload)},
        files=files,
        timeout=30
    )

    files["file"].close()
    os.remove(img)

# ================= MAIN =================
def main():

    print("Scanning Swing Market Fund Mode...")

    hasil = scan()

    if not hasil:
        print("Tidak ada signal.")
        return

    for h in hasil:
        send_dc(h)

    print("Signal terkirim.")

if __name__ == "__main__":
    main()
