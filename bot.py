import os
import time
from collections import defaultdict
from dotenv import load_dotenv
from telegram import Bot
import requests

# Memuat konfigurasi dari file .env
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("ERROR: Token atau Chat ID Telegram belum diset di file .env!")
    exit(1)

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# ==========================================
# 1. DAFTAR SMART WALLET YANG INGIN DIPANTAU
# ==========================================
SMART_WALLETS = [
    "3g4D4n67vUFSDUwW8NWvzkQSUqD4J5H8zW1sbKJrrczi",
    "E4Ka2GiyZNsDSsQHJssSgoBeKEcuiRdnZKumhnopRMee",
    "bTiNAiDWsAzuDvqf1vGcv3GuvgLxVvaj76KABoqkJa6",
    "D3zAG2Kb6dAWvfuJtxhMun9dT3VurJcFjRDJvVkApZ3d",
    "pwZpq97vcUqG5r79PMYJ2rPdJeVfuqdTaxmNvj5KYMR",
    "72NWWbchKdRJKvhG6U4f9363psUttkeEkE4yk15imy8u",
    "HSeCG7T2KCTuVAARGXZuxBNZg6pas1EdJdjn7Xyy1ENB",
    "BopgSXVHNqks8GNMp5UJ3g54mKP1Wgfs8j6DcRNSCoBb",
    "J8N8cW3ADBpuwNxRChmnxAfmbmdiyBZiAsp6UKNtKxuc",
    "7gdo83WqcXvown8aHUrgma716BEwGdjRA9CtdUThBy5U",
    "5yzVtM9eYzgRwQ3HkaJXpGqduhBv9c9VEq8JyUEDxjDh",
    "H44zceMf6tP8cH6NGcKov2nNjGWrtC7a1LEVRNBvcaPf",
    "4XMPyWFsYdNcCN4FG8geyytyTeUNacn4QundBzMqbGGT",
    "GoTobqA53i68PJqeT2KU2HvWzWzHvizj5i2faufUd3xz",
    "4N4mW6oEarkJSR52TwgTQVRjpkUM7tkf2qrNnkE1uaHm",
    "APSXgDne6B5m7QQobnp8tPQdkDTa19ec7pRoDvXYKQRu",
    "C32NsZNdQrrnJkNkHJUZCeP2XPgj5kPQgaXk5s1bssCb",
    "D9UiteKBjbVp8UYGRSKi4fJRsXYp8Csk7zcrnaCvq6LS",
    "GNoRVtc34FsAsjWLTNxvoRWHH8CnjdQkddgUvj8LJ3vu"
]

# Solana Public RPC Endpoint (Gratis)
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

# Memori sementara untuk filter
# Format: {token_address: [{'wallet': '...', 'time': timestamp}]}
recent_buys = defaultdict(list)

# Konfigurasi Filter
TIME_WINDOW = 300       # Rentang waktu dalam detik (5 menit)
MIN_UNIQUE_WALLETS = 3  # Minimal smart wallet unik yang harus beli barengan


def send_telegram_alert(token_address, wallets):
    """Fungsi untuk mengirim notifikasi ke Telegram"""
    message = (
        f"🚨 **ALERTS: SMART MONEY ACCUMULATION!** 🚨\n\n"
        f"Token: `{token_address}`\n"
        f"Terdeteksi **{len(wallets)} Smart Wallet** berbeda memborong token ini dalam 5 menit terakhir!\n\n"
        f"🔗 Cek di GMGN / DEX Screener:\n"
        f"https://gmgn.ai/sol/token/{token_address}"
    )
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown"
        )
        print(f"[ALERT TERKIRIM] Token: {token_address}")
    except Exception as e:
        print(f"Gagal kirim pesan Telegram: {e}")


def process_transaction(wallet, token_address):
    """Logika utama penyaringan transaksi"""
    current_time = time.time()

    # 1. Bersihkan data yang sudah kedaluwarsa (> 5 menit)
    for token in list(recent_buys.keys()):
        recent_buys[token] = [
            item for item in recent_buys[token]
            if current_time - item['time'] < TIME_WINDOW
        ]
        if not recent_buys[token]:
            del recent_buys[token]

    # 2. Catat pembelian baru
    recent_buys[token_address].append({'wallet': wallet, 'time': current_time})

    # 3. Hitung jumlah wallet UNIK yang beli token ini
    unique_buyers = set(item['wallet'] for item in recent_buys[token_address])

    print(f"Wallet {wallet[:6]}... beli token {token_address[:6]}... (Total unique: {len(unique_buyers)})")

    # 4. Terapkan Filter: Jika >= batas minimal, kirim alert!
    if len(unique_buyers) >= MIN_UNIQUE_WALLETS:
        send_telegram_alert(token_address, list(unique_buyers))
        # Reset list untuk token ini agar tidak spam alert terus-menerus
        recent_buys[token_address] = []


def get_signatures_for_address(wallet_address):
    """Mengambil riwayat transaksi terbaru dari RPC Solana"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [
            wallet_address,
            {"limit": 5} # Ambil 5 transaksi terakhir
        ]
    }
    try:
        response = requests.post(SOLANA_RPC_URL, json=payload, timeout=10)
        data = response.json()
        return data.get("result", [])
    except Exception as e:
        print(f"Error koneksi RPC untuk wallet {wallet_address[:6]}: {e}")
        return []


def check_onchain_activity():
    """Fungsi pengecekan berkala ke blockchain Solana"""
    print("--- Memeriksa aktivitas smart wallet di jaringan Solana ---")
    
    for wallet in SMART_WALLETS:
        signatures = get_signatures_for_address(wallet)
        
        for sig_info in signatures:
            # Placeholder untuk parsing transaksi ke depan
            pass
            
        # Jeda sebentar antar wallet agar tidak terkena rate-limit RPC publik
        time.sleep(1)


def main_loop():
    print("Bot Telegram Smart Money Tracker Berjalan (Mode Live RPC)...")
    while True:
        try:
            check_onchain_activity()
        except Exception as e:
            print(f"Terjadi kesalahan pada loop: {e}")
            
        # Cek ulang setiap 30 detik
        time.sleep(30)


if __name__ == "__main__":
    main_loop()