import yfinance as yf
from groq import Groq
import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
import json
from datetime import datetime

# --- KONFIGURASI ---
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# Daftar saham (Bisa ditambah/kurang sesukamu)
SCAN_LIST = [
    "BBCA.JK", "BBRI.JK", "TLKM.JK", "ASII.JK", "GOTO.JK", "ADRO.JK", "AMRT.JK", "ANTM.JK", "BMRI.JK",
    "AAPL", "NVDA", "TSLA", "MSFT", "META", "BTC-USD", "ETH-USD"
]

def create_chart(ticker, hist, support, resistance):
    """Membuat grafik dengan garis Support & Resistance"""
    try:
        plt.style.use('dark_background')
        plt.figure(figsize=(10, 5))
        
        # Plot Harga
        plt.plot(hist.index, hist['Close'], color='#00ff00', linewidth=2, label='Price')
        plt.fill_between(hist.index, hist['Close'], color='#00ff00', alpha=0.1)
        
        # Plot S/R
        plt.axhline(y=support, color='red', linestyle='--', alpha=0.5, label=f'Support ({support:.0f})')
        plt.axhline(y=resistance, color='cyan', linestyle='--', alpha=0.5, label=f'Resistance ({resistance:.0f})')
        
        plt.title(f"Scanner Signal: {ticker}", fontsize=14, color='white')
        plt.legend()
        plt.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.2)
        plt.savefig('chart.png', bbox_inches='tight')
        plt.close()
        return True
    except Exception as e:
        print(f"Gagal buat chart: {e}")
        return False

def scan_market():
    potensial = []
    print(f"Scanning {len(SCAN_LIST)} stocks...")

    for ticker in SCAN_LIST:
        try:
            stock = yf.Ticker(ticker)
            # Ambil data 1 jam untuk deteksi spike, dan 1 hari untuk S/R
            df_hourly = stock.history(period="5d", interval="1h")
            df_daily = stock.history(period="1mo", interval="1d")
            
            if df_hourly.empty or len(df_hourly) < 10: continue

            # Hitung Support & Resistance (1 Bulan Terakhir)
            current_support = df_daily['Low'].min()
            current_resistance = df_daily['High'].max()

            # Logika Anomali
            last_close = df_hourly['Close'].iloc[-1]
            change_pct = ((last_close - df_hourly['Close'].iloc[-2]) / df_hourly['Close'].iloc[-2]) * 100
            
            last_vol = df_hourly['Volume'].iloc[-1]
            avg_vol = df_hourly['Volume'].mean()
            vol_ratio = last_vol / avg_vol if avg_vol > 0 else 0

            # Filter: Volume Spike > 2x ATAU Perubahan Harga > 3%
            if vol_ratio > 2.0 or abs(change_pct) > 3.0:
                potensial.append({
                    "ticker": ticker,
                    "price": last_close,
                    "change": change_pct,
                    "vol_ratio": vol_ratio,
                    "support": current_support,
                    "resistance": current_resistance,
                    "hist": df_hourly.tail(20),
                    "news": [n.get('title') for n in stock.news[:2]] if stock.news else ["No news"]
                })
        except: continue
            
    return sorted(potensial, key=lambda x: x['vol_ratio'], reverse=True)[:3]

def kirim_discord(data, analisa):
    color = 3066993 if data['change'] >= 0 else 15158332
    
    payload = {
        "embeds": [{
            "title": f"🚀 ALERT POTENSIAL: {data['ticker']}",
            "color": color,
            "fields": [
                {
                    "name": "📊 Data Teknis", 
                    "value": f"
http://googleusercontent.com/immersive_entry_chip/0
http://googleusercontent.com/immersive_entry_chip/1

---

### 💡 Apa yang Baru?

* **Logic Support & Resistance:** Bot sekarang melihat data harian (`1mo`) untuk menentukan titik terendah (Support) dan tertinggi (Resistance) selama sebulan terakhir.
* **Visual Chart:** Grafik sekarang menyertakan garis putus-putus merah (Support) dan cyan (Resistance). Jadi kamu bisa lihat posisi harga sekarang ada di mana terhadap "benteng" harganya.
* **Target Lebih Masuk Akal:** AI Groq sekarang dipaksa memberikan **TP di area Resistance** dan **SL di bawah Support**, bukan cuma pakai angka persentase buta.
* **Format Rapi:** Penambahan kolom khusus "Support & Resistance" di Discord agar mata kamu bisa langsung tertuju ke angka krusial.

---

### Langkah Terakhir
1.  **Update kode** di GitHub repository kamu.
2.  Karena kita pakai data harian dan per jam, pastikan **GitHub Actions** kamu berjalan saat bursa sedang aktif atau minimal sehari sekali.
3.  Jangan lupa cek **GitHub Secrets** apakah `GROQ_API_KEY` dan `DISCORD_WEBHOOK` masih terpasang.

Apakah kamu ingin saya tambahkan **filter saham khusus** (misal: hanya mau scan saham yang harganya di atas Rp 100,- agar tidak terjebak saham "gocap")?
