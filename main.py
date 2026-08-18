import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Bot deposit kamu sudah aktif dan merespons /start!")

def main():
    # Inisialisasi Bot dengan Polling bawaan
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    
    print("Bot sedang berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
