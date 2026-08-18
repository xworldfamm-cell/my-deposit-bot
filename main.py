import os
import random
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MACRODROID_SECRET_KEY = os.getenv("MACRODROID_SECRET_KEY")

telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
pending_deposits = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot Aktif! Gunakan /deposit <nominal> untuk buat tiket deposit.")

async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Contoh: `/deposit 50000`", parse_mode="Markdown")
        return

    try:
        base_amount = int(context.args[0])
        unique_code = random.randint(100, 999)
        final_amount = base_amount + unique_code

        user_id = update.effective_user.id
        pending_deposits[final_amount] = user_id

        await update.message.reply_text(
            f"Silakan transfer sebesar:\n*Rp {final_amount:,}*\n\n"
            f"Ke BCA/DANA: 1234567890",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("Masukkan angka nominal saja.")

telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(CommandHandler("deposit", deposit_command))

@asynccontextmanager
async def lifespan(app: FastAPI):
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()
    yield
    await telegram_app.updater.stop()
    await telegram_app.stop()
    await telegram_app.shutdown()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "Bot Online"}

@app.post("/webhook-deposit")
async def receive_macrodroid(request: Request):
    data = await request.json()
    
    if data.get("secret_key") != MACRODROID_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")

    raw_nominal = data.get("nominal")
    if not raw_nominal:
        raise HTTPException(status_code=400, detail="Nominal kosong")

    clean_nominal = int("".join(filter(str.isdigit, str(raw_nominal))))

    if clean_nominal in pending_deposits:
        user_id = pending_deposits.pop(clean_nominal)
        await telegram_app.bot.send_message(
            chat_id=user_id,
            text=f"Deposit sebesar *Rp {clean_nominal:,}* SUCCESS!",
            parse_mode="Markdown"
        )
        return {"status": "success"}
    
    return {"status": "ignored"}
