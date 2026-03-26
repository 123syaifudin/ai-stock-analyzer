import yfinance as yf
from groq import Groq
import os
import requests
import pandas as pd

# Konfigurasi API
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

def get_data_saham(ticker):
    stock = yf.Ticker(ticker)
    # Ambil data 1 bulan terakhir untuk melihat tren
    hist = stock.history(period="1mo")
    # Ambil berita terbaru
    news = [n['title'] for n in stock.news[:3]]
    return hist, news

def analisa_ai(ticker, hist, news):
    # Ringkas data agar hemat token
    data_summary = hist.tail(10)[['Close', 'Volume']].to_string()
    
    prompt = f"""
    Sistem: Anda adalah Pakar Saham & Ahli Bandarmologi Indonesia.
    Tugas: Analisa saham {ticker} berdasarkan data 10 hari terakhir:
    {data_summary}
    Berita: {news}

    Instruksi Khusus:
    1. Cek Volume: Jika volume naik drastis saat harga sideways/naik, tandai sebagai BIG ACCUMULATION.
    2. Tentukan Sentiment: Positif/Negatif dari berita.
    3. Trading Plan: Berikan angka ENTRY, TP (Take Profit), dan SL (Stop Loss).
    4. Timeframe: Tentukan Jangka waktu (Scalping/Swing/Inves).

    Balas dengan format Markdown yang keren untuk Discord.
    """
    
    completion = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content

def main():
    # Daftar saham yang ingin di-scan (Indo pakai .JK)
    watchlist = ["BBCA.JK", "GOTO.JK", "TLKM.JK", "NVDA", "AAPL", "BTC-USD"]
    
    for ticker in watchlist:
        try:
            print(f"Menganalisa {ticker}...")
            hist, news = get_data_saham(ticker)
            hasil = analisa_ai(ticker, hist, news)
            
            # Kirim ke Discord
            msg = {"content": f"## 📈 LAPORAN ANALISA: {ticker}\n{hasil}"}
            requests.post(DISCORD_WEBHOOK, json=msg)
        except Exception as e:
            print(f"Gagal analisa {ticker}: {e}")

if __name__ == "__main__":
    main()
