import yfinance as yf
from groq import Groq
import os
import requests
import pandas as pd
import matplotlib.pyplot as plt

# Konfigurasi
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# Daftar Scan (Bisa ditambah sesuai keinginan)
SCAN_LIST = [
    # Indonesia (LQ45 & Popular)
    "BBCA.JK", "BBRI.JK", "TLKM.JK", "ASII.JK", "GOTO.JK", "ADRO.JK", "AMRT.JK", "ANTM.JK", "BMRI.JK",
    # US & Crypto
    "AAPL", "NVDA", "TSLA", "MSFT", "META", "BTC-USD", "ETH-USD"
]

def create_chart(ticker, hist):
    plt.figure(figsize=(10, 5))
    plt.plot(hist.index, hist['Close'], label='Price', color='#00ff00', linewidth=2)
    plt.fill_between(hist.index, hist['Close'], color='#00ff00', alpha=0.1)
    plt.title(f"Price Action: {ticker}")
    plt.grid(True, alpha=0.2)
    plt.savefig('chart.png')
    plt.close()

def scanner_potensial():
    found = []
    print(f"Memulai Scanning {len(SCAN_LIST)} saham...")
    
    # Ambil data sekaligus untuk efisiensi
    data = yf.download(SCAN_LIST, period="5d", interval="1h", group_by='ticker')
    
    for ticker in SCAN_LIST:
        try:
            df = data[ticker].dropna()
            if len(df) < 5: continue
            
            # LOGIKA SCANNER: Volume naik 1.5x rata-rata ATAU Harga naik > 2%
            last_vol = df['Volume'].iloc[-1]
            avg_vol = df['Volume'].mean()
            price_change = ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
            
            if last_vol > (avg_vol * 1.5) or abs(price_change) > 2.0:
                found.append({
                    "ticker": ticker,
                    "price": df['Close'].iloc[-1],
                    "change": price_change,
                    "vol_spike": last_vol / avg_vol,
                    "hist": df.tail(10)
                })
        except: continue
    
    # Urutkan berdasarkan volume spike tertinggi (Top 3 saja agar tidak spam)
    found = sorted(found, key=lambda x: x['vol_spike'], reverse=True)[:3]
    return found

def kirim_discord_pro(ticker, analisa, price, change):
    # Warna: Hijau jika naik, Merah jika turun
    color = 3066993 if change > 0 else 15158332
    
    payload = {
        "embeds": [{
            "title": f"🚀 SIGNAL POTENSIAL: {ticker}",
            "color": color,
            "fields": [
                {"name": "Current Price", "value": f"
http://googleusercontent.com/immersive_entry_chip/0
http://googleusercontent.com/immersive_entry_chip/1

---

### 💡 Mengapa Sistem Baru Ini "Gahar"?
1.  **Smart Filtering:** Bot tidak akan "berisik". Jika tidak ada saham yang menarik (volume sepi/harga flat), bot tidak akan mengirim apa-apa ke Discord.
2.  **Discord Embeds:** Tampilan di Discord tidak lagi teks biasa, tapi kotak berwarna (Hijau/Merah) dengan kolom-kolom rapi.
3.  **Visual Chart:** Kamu bisa langsung melihat tren harga lewat gambar yang dikirim bot tanpa harus buka TradingView.
4.  **Full Free:** Matplotlib gratis, Groq gratis, GitHub Actions gratis.

**Langkah Terakhir:**
1. Update kedua file di atas di GitHub kamu.
2. Tunggu 1 jam, atau klik **Run Workflow** secara manual untuk tes.

Apakah kamu ingin saya tambahkan **Pesan Suara (TTS)** atau notifikasi khusus jika ada saham yang "Super Breakout"?
