import os
import random
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext

# ===== ACCESS CODE =====
ACCESS_CODES = ["123ABC", "456DEF"]
authorized_users = []

# ===== CURRENCY PAIRS & EXPIRATION =====
PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]
EXPIRATION = ["5s", "15s", "1m", "2m", "3m", "5m", "10m"]

# ===== BOT TOKEN FROM ENVIRONMENT =====
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# ===== START COMMAND =====
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in authorized_users:
        update.message.reply_text("Enter your access code to unlock the bot:")
        return
    keyboard = [[InlineKeyboardButton(pair, callback_data=f"pair_{pair}") for pair in PAIRS[i:i+2]] for i in range(0, len(PAIRS), 2)]
    update.message.reply_text("Select a currency pair:", reply_markup=InlineKeyboardMarkup(keyboard))

# ===== HANDLE ACCESS CODE =====
def handle_message(update: Update, context: CallbackContext):
    code = update.message.text
    user_id = update.effective_user.id
    if code in ACCESS_CODES:
        authorized_users.append(user_id)
        update.message.reply_text("Access granted! Use /start to continue.")
    else:
        update.message.reply_text("Invalid code. Try again.")

# ===== BUTTON CALLBACK =====
def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data

    # Choose pair → show expiration
    if data.startswith("pair_"):
        pair = data.split("_")[1]
        keyboard = [[InlineKeyboardButton(exp, callback_data=f"exp_{pair}_{exp}")] for exp in EXPIRATION]
        query.edit_message_text(f"Select expiration for {pair}:", reply_markup=InlineKeyboardMarkup(keyboard))

    # Generate signal
    elif data.startswith("exp_"):
        _, pair, exp = data.split("_")
        query.edit_message_text("Generating signal... ⏳")
        time.sleep(2)  # simulate analysis
        signal = random.choice(["BUY", "SELL"])  # placeholder for real analysis
        probability = random.randint(70, 90)
        volatility = random.choice(["Low", "Moderate", "High"])
        img_path = "buy.png" if signal == "BUY" else "sell.png"

        context.bot.send_photo(chat_id=query.message.chat_id,
                               photo=open(img_path, "rb"),
                               caption=f"Signal: {signal}\nPair: {pair}\nExpiry: {exp}\nVolatility: {volatility}\nProbability: {probability}%")

        keyboard = [
            [InlineKeyboardButton("🍀 Repeat", callback_data=f"exp_{pair}_{exp}")],
            [InlineKeyboardButton("↩️ Back", callback_data="back")]
        ]
        context.bot.send_message(chat_id=query.message.chat_id, text="Next action:", reply_markup=InlineKeyboardMarkup(keyboard))

    # Back to main menu
    elif data == "back":
        start(update, context)

# ===== RUN BOT =====
updater = Updater(BOT_TOKEN)
updater.dispatcher.add_handler(CommandHandler("start", start))
updater.dispatcher.add_handler(CallbackQueryHandler(button))
updater.dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot is running...")
updater.start_polling()
updater.idle()