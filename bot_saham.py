import yfinance as yf
from groq import Groq
import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
import json
from datetime import datetime

# ================= CONFIG =================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

client = Groq(api_key=GROQ_API_KEY)

SCAN_LIST = [
    "BBCA.JK","BBRI.JK","TLKM.JK","ASII.JK","GOTO.JK",
    "ADRO.JK","AMRT.JK","ANTM.JK","BMRI.JK",
    "AAPL","NVDA","TSLA","MSFT","META","BTC-USD"
]

# ================= CHART =================
def create_chart(ticker, hist, support, resistance):
    try:
        plt.style.use('dark_background')
        plt.figure(figsize=(10,5))

        plt.plot(hist.index, hist['Close'], color='#00ff99', linewidth=2)
        plt.fill_between(hist.index, hist['Close'], alpha=0.1)

        plt.axhline(y=support, color='red', linestyle='--')
        plt.axhline(y=resistance, color='cyan', linestyle='--')

        plt.title(f"{ticker} Signal Scanner")
        plt.grid(alpha=0.2)

        plt.savefig("chart.png", bbox_inches='tight')
        plt.close()
        return True
    except Exception as e:
        print("Chart Error:", e)
        return False

# ================= AI ANALYSIS =================
def ai_analyze(ticker, price, change, vol_ratio):
    try:
        prompt = f"""
        Kamu adalah trader profesional.
        Analisa singkat saham {ticker}

        Harga sekarang: {price}
        Perubahan: {change:.2f}%
        Lonjakan Volume: {vol_ratio:.2f}x

        Berikan kesimpulan:
        - Bullish / Bearish / Sideways
        - Potensi entry
        - Risk level
        """

        chat = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":prompt}],
            temperature=0.3,
            max_tokens=300
        )

        return chat.choices[0].message.content
    except Exception as e:
        print("AI Error:", e)
        return "AI Analisa gagal."

# ================= DISCORD =================
def kirim_discord(data, analisa):
    try:
        color = 3066993 if data['change'] >= 0 else 15158332

        txt_market = (
            f"Price: {data['price']:.2f}\n"
            f"Change: {data['change']:.2f}%\n"
            f"Vol Spike: {data['vol_ratio']:.2f}x"
        )

        txt_sr = (
            f"Support: {data['support']:.2f}\n"
            f"Resistance: {data['resistance']:.2f}"
        )

        txt_news = "\n".join(data['news'])

        payload = {
            "embeds":[
                {
                    "title": f"🚀 SIGNAL SAHAM: {data['ticker']}",
                    "color": color,
                    "fields":[
                        {"name":"📊 Market","value":txt_market,"inline":True},
                        {"name":"📉 S/R","value":txt_sr,"inline":True},
                        {"name":"📰 News","value":txt_news,"inline":False},
                        {"name":"🤖 AI","value":analisa[:1000],"inline":False}
                    ],
                    "image":{"url":"attachment://chart.png"}
                }
            ]
        }

        with open("chart.png","rb") as f:
            files = {"file":("chart.png",f,"image/png")}

            requests.post(
                DISCORD_WEBHOOK,
                data={"payload_json":json.dumps(payload)},
                files=files,
                timeout=30
            )

        print("SEND DISCORD SUCCESS")

    except Exception as e:
        print("Discord Error:", e)

# ================= SCANNER =================
def scan_market():

    kandidat = []

    print("Scanning Market...")

    for ticker in SCAN_LIST:
        try:
            stock = yf.Ticker(ticker)

            df_h = stock.history(period="5d", interval="1h")
            df_d = stock.history(period="1mo", interval="1d")

            if df_h.empty or len(df_h) < 5:
                continue

            last_price = df_h['Close'].iloc[-1]
            prev_price = df_h['Close'].iloc[-2]

            change_pct = ((last_price - prev_price) / prev_price) * 100

            last_vol = df_h['Volume'].iloc[-1]
            avg_vol = df_h['Volume'].mean()

            vol_ratio = last_vol / avg_vol if avg_vol > 0 else 0

            support = df_d['Low'].min() if not df_d.empty else last_price*0.95
            resistance = df_d['High'].max() if not df_d.empty else last_price*1.05

            news_titles = []
            try:
                news_titles = [n.get('title','No Title') for n in stock.news[:2]]
            except:
                news_titles = ["News tidak tersedia"]

            if vol_ratio > 2 or abs(change_pct) > 3:
                kandidat.append({
                    "ticker": ticker,
                    "price": last_price,
                    "change": change_pct,
                    "vol_ratio": vol_ratio,
                    "support": support,
                    "resistance": resistance,
                    "hist": df_h.tail(30),
                    "news": news_titles
                })

        except Exception as e:
            print("Scan Error:", ticker, e)

    kandidat = sorted(kandidat, key=lambda x: x['vol_ratio'], reverse=True)

    return kandidat[:1]   # kirim TOP 1 saja biar tidak spam

# ================= MAIN =================
def main():

    hasil = scan_market()

    if not hasil:
        print("Tidak ada signal.")
        return

    for data in hasil:

        ok = create_chart(
            data['ticker'],
            data['hist'],
            data['support'],
            data['resistance']
        )

        if not ok:
            continue

        analisa = ai_analyze(
            data['ticker'],
            data['price'],
            data['change'],
            data['vol_ratio']
        )

        kirim_discord(data, analisa)

if __name__ == "__main__":
    main()
