import os
import random
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ====== ENVIRONMENT VARIABLES ======
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ACCESS_CODES = os.environ.get("ACCESS_CODES", "123ABC").split(",")  # comma-separated codes
OWNER_CONTACT = os.environ.get("OWNER_CONTACT", "@YourUsername")
NOTIFY_BEFORE = int(os.environ.get("NOTIFY_BEFORE", 60))  # seconds before signal

# ====== DATA ======
authorized_users = []
PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]
EXPIRATION = ["5s", "15s", "1m", "2m", "3m", "5m", "10m"]

BUY_IMAGE = "buy.png"
SELL_IMAGE = "sell.png"

# ====== START COMMAND ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in authorized_users:
        await update.message.reply_text(
            f"🚫 You need an access code to use this bot.\n"
            f"Please chat with {OWNER_CONTACT} to get the access code."
        )
        return

    # authorized users see main menu
    keyboard = [[InlineKeyboardButton(pair, callback_data=f"pair_{pair}") for pair in PAIRS[i:i+2]] 
                for i in range(0, len(PAIRS), 2)]
    await update.message.reply_text("Select a currency pair:", reply_markup=InlineKeyboardMarkup(keyboard))

# ====== HANDLE ACCESS CODE ======
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    user_id = update.effective_user.id

    if user_id in authorized_users:
        await update.message.reply_text("✅ You are already authorized! Use /start to begin.")
        return

    if code in ACCESS_CODES:
        authorized_users.append(user_id)
        await update.message.reply_text("✅ Access granted! Use /start to continue.")
    else:
        await update.message.reply_text(
            f"❌ Invalid code.\n"
            f"Please contact {OWNER_CONTACT} to get a valid access code."
        )

# ====== BUTTON CALLBACK ======
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Select currency pair → show expiration buttons
    if data.startswith("pair_"):
        pair = data.split("_")[1]
        keyboard = [[InlineKeyboardButton(exp, callback_data=f"exp_{pair}_{exp}")] for exp in EXPIRATION]
        await query.edit_message_text(f"Select expiration for {pair}:", reply_markup=InlineKeyboardMarkup(keyboard))

    # Generate signal
    elif data.startswith("exp_"):
        _, pair, exp = data.split("_")
        await query.edit_message_text("⏳ Generating signal...")
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"Signal analysis in progress...")
        time.sleep(2)  # simulate calculation

        # Placeholder signal (can later integrate RSI/MA/MACD)
        signal = random.choice(["BUY", "SELL"])
        probability = random.randint(70, 90)
        volatility = random.choice(["Low", "Moderate", "High"])
        img_path = BUY_IMAGE if signal == "BUY" else SELL_IMAGE

        with open(img_path, "rb") as img:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=img,
                caption=f"Signal: {signal}\nPair: {pair}\nExpiry: {exp}\nVolatility: {volatility}\nProbability: {probability}%"
            )

        keyboard = [
            [InlineKeyboardButton("🍀 Repeat", callback_data=f"exp_{pair}_{exp}")],
            [InlineKeyboardButton("↩️ Back", callback_data="back")]
        ]
        await context.bot.send_message(chat_id=query.message.chat_id, text="Next action:", reply_markup=InlineKeyboardMarkup(keyboard))

    # Back to main menu
    elif data == "back":
        await start(update, context)

# ====== RUN BOT ======
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()