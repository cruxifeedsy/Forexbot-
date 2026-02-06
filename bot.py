import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# === IMAGES ===
BUY_IMAGE = "buy.png"
SELL_IMAGE = "sell.png"

# === START COMMAND ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("EURUSD", callback_data="pair_EURUSD")]
    ]
    await update.message.reply_text(
        "Select a currency pair:", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# === BUTTON CALLBACK ===
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("pair_"):
        pair = data.split("_")[1]
        # Start countdown 5 -> 0
        msg = await query.edit_message_text("⏳ Analyzing market... 5")
        for i in range(4, -1, -1):
            await asyncio.sleep(1)
            try:
                await msg.edit_text(f"⏳ Analyzing market... {i}")
            except:
                pass

        # Simulate signal (random BUY/SELL)
        import random
        signal = random.choice(["BUY", "SELL"])
        img_path = BUY_IMAGE if signal == "BUY" else SELL_IMAGE

        # Send photo + caption
        try:
            with open(img_path, "rb") as img:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=img,
                    caption=f"Signal: {signal}\nPair: {pair}\nExpiry: 1m\nVolatility: Moderate\nProbability: 85%"
                )
        except FileNotFoundError:
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"⚠️ {img_path} not found!")

# === RUN BOT ===
if __name__ == "__main__":
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # replace with your actual bot token
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    print("Bot is running...")
    app.run_polling()