import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Token & Secret Key diambil dari Variable Environment (Railway)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MACRODROID_SECRET_KEY = os.getenv("MACRODROID_SECRET_KEY")

# Inisialisasi Bot Telegram
telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Database Sederhana dalam Memory (Untuk Produksi disarankan PostgreSQL/SQLite)
# Format: { nominal_unik: user_id }
pending_deposits = {}

# --- COMMAND BOT TELEGRAM ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Selamat datang! Gunakan command /deposit <jumlah> untuk membuat tiket deposit.\n\n"
        "Contoh: /deposit 50000"
    )

async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Harap masukkan jumlah deposit. Contoh: `/deposit 50000`", parse_mode="Markdown")
        return

    try:
        base_amount = int(context.args[0])
        # Tambahkan kode unik acak 3 digit agar nominal spesifik (misal: 50.142)
        import random
        unique_code = random.randint(100, 999)
        final_amount = base_amount + unique_code

        user_id = update.effective_user.id
        pending_deposits[final_amount] = user_id

        await update.message.reply_text(
            f" Silakan transfer tepat sebesar:\n"
            f" *Rp {final_amount:,}*\n\n"
            f" Ke Rekening/E-Wallet: *BCA/DANA 1234567890*\n"
            f" Selesaikan pembayaran dalam 15 menit.",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("Nominal harus berupa angka saja.")

telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(CommandHandler("deposit", deposit_command))

# --- LIFESPAN MANAGER (UNTUK MENJALANKAN BOT TELEGRAM DALAM FASTAPI) ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start bot saat server menyala
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()
    yield
    # Stop bot saat server mati
    await telegram_app.updater.stop()
    await telegram_app.stop()
    await telegram_app.shutdown()

app = FastAPI(lifespan=lifespan)

# --- WEBHOOK ENDPOINT UNTUK MACRODROID ---

@app.post("/webhook-deposit")
async def receive_macrodroid(request: Request):
    data = await request.json()
    
    # Validasi Keamanan
    secret = data.get("secret_key")
    if secret != MACRODROID_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized request")

    raw_nominal = data.get("nominal")
    if not raw_nominal:
        raise HTTPException(status_code=400, detail="Nominal missing")

    # Bersihkan nominal dari karakter non-angka (misal "Rp 50.142" -> 50142)
    clean_nominal = int("".join(filter(str.isdigit, str(raw_nominal))))

    # Cek apakah nominal sesuai tiket pending
    if clean_nominal in pending_deposits:
        user_id = pending_deposits.pop(clean_nominal)
        
        # Kirim Notifikasi ke User via Telegram
        await telegram_app.bot.send_message(
            chat_id=user_id,
            text=f" Deposit Sebesar *Rp {clean_nominal:,}* BERHASIL DITERIMA!",
            parse_mode="Markdown"
        )
        return {"status": "success", "message": "Deposit diproses"}
    else:
        return {"status": "ignored", "message": "Nominal tidak cocok dengan tiket deposit manapun"}
