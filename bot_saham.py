import yfinance as yf
from groq import Groq
import os
import requests
import pandas as pd

# Konfigurasi API
# Pastikan GROQ_API_KEY dan DISCORD_WEBHOOK sudah ada di GitHub Secrets
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

def get_data_saham(ticker):
    stock = yf.Ticker(ticker)
    # Ambil data 1 bulan terakhir
    hist = stock.history(period="1mo")
    
    # FIX: Cara ambil berita terbaru yang lebih aman
    news_list = []
    try:
        raw_news = stock.news
        if raw_news:
            # Mengambil maksimal 3 judul berita
            news_list = [n.get('title', 'No Title') for n in raw_news[:3]]
    except:
        news_list = ["Tidak ada berita terbaru."]
        
    return hist, news_list

def analisa_ai(ticker, hist, news):
    # Ringkas data agar hemat token
    data_summary = hist.tail(10)[['Close', 'Volume']].to_string()
    
    # FIX: Menggunakan model terbaru 'llama-3.3-70b-versatile' atau 'llama3-8b-8192'
    # llama-3.3-70b-versatile adalah model flagship Groq saat ini
    prompt = f"""
    Sistem: Anda adalah Pakar Saham & Ahli Bandarmologi Indonesia.
    Tugas: Analisa saham {ticker} berdasarkan data 10 hari terakhir:
    {data_summary}
    Berita Terkait: {news}

    Instruksi Khusus:
    1. Analisa Volume (VPA): Jika volume naik drastis saat harga sideways/naik, tandai sebagai BIG ACCUMULATION.
    2. Sentimen: Positif/Negatif/Netral dari berita.
    3. Trading Plan: Berikan angka ENTRY, TP (Take Profit), dan SL (Stop Loss) yang presisi.
    4. Jangka Waktu: Tentukan (Scalping/Swing/Inves).

    Balas dengan format Markdown yang rapi untuk Discord.
    """
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile", # Update model terbaru
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content

def main():
    # Daftar saham (Indo pakai .JK, Luar tanpa akhiran)
    watchlist = ["BBCA.JK", "GOTO.JK", "TLKM.JK", "NVDA", "AAPL", "BTC-USD"]
    
    for ticker in watchlist:
        try:
            print(f"Menganalisa {ticker}...")
            hist, news = get_data_saham(ticker)
            
            if hist.empty:
                print(f"Data {ticker} kosong, skip.")
                continue
                
            hasil = analisa_ai(ticker, hist, news)
            
            # Kirim ke Discord
            msg = {"content": f"## 📈 ANALISA SAHAM: {ticker}\n{hasil}"}
            requests.post(DISCORD_WEBHOOK, json=msg)
            print(f"Berhasil mengirim analisa {ticker} ke Discord.")
            
        except Exception as e:
            print(f"Gagal analisa {ticker}: {str(e)}")

if __name__ == "__main__":
    main()
