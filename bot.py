import os
import random
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext

# ====== ENVIRONMENT VARIABLES ======
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ACCESS_CODES = os.environ.get("ACCESS_CODES", "123ABC").split(",")  # comma-separated codes in Railway
OWNER_CONTACT = os.environ.get("OWNER_CONTACT", "@YourUsername")     # your Telegram contact for unauthorized users
NOTIFY_BEFORE = int(os.environ.get("NOTIFY_BEFORE", 60))             # optional pre-notification in seconds

# ====== DATA ======
authorized_users = []
PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]
EXPIRATION = ["5s", "15s", "1m", "2m", "3m", "5m", "10m"]

BUY_IMAGE = "buy.png"
SELL_IMAGE = "sell.png"

# ====== START COMMAND ======
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in authorized_users:
        update.message.reply_text(
            f"🚫 You need an access code to use this bot.\n"
            f"Please chat with {OWNER_CONTACT} to get the access code."
        )
        return

    # authorized users see the main menu
    keyboard = [[InlineKeyboardButton(pair, callback_data=f"pair_{pair}") for pair in PAIRS[i:i+2]] for i in range(0, len(PAIRS), 2)]
    update.message.reply_text("Select a currency pair:", reply_markup=InlineKeyboardMarkup(keyboard))

# ====== HANDLE ACCESS CODE ======
def handle_message(update: Update, context: CallbackContext):
    code = update.message.text.strip()
    user_id = update.effective_user.id

    if user_id in authorized_users:
        update.message.reply_text("✅ You are already authorized! Use /start to begin.")
        return

    if code in ACCESS_CODES:
        authorized_users.append(user_id)
        update.message.reply_text("✅ Access granted! Use /start to continue.")
    else:
        update.message.reply_text(
            f"❌ Invalid code.\n"
            f"Please contact {OWNER_CONTACT} to get a valid access code."
        )

# ====== BUTTON CALLBACK ======
def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data

    # Select currency pair → show expiration buttons
    if data.startswith("pair_"):
        pair = data.split("_")[1]
        keyboard = [[InlineKeyboardButton(exp, callback_data=f"exp_{pair}_{exp}")] for exp in EXPIRATION]
        query.edit_message_text(f"Select expiration for {pair}:", reply_markup=InlineKeyboardMarkup(keyboard))

    # Generate signal
    elif data.startswith("exp_"):
        _, pair, exp = data.split("_")
        query.edit_message_text("⏳ Generating signal...")
        time.sleep(2)  # simulate analysis

        # Placeholder signal (can later use RSI/MA/MACD)
        signal = random.choice(["BUY", "SELL"])
        probability = random.randint(70, 90)
        volatility = random.choice(["Low", "Moderate", "High"])
        img_path = BUY_IMAGE if signal == "BUY" else SELL_IMAGE

        context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=open(img_path, "rb"),
            caption=f"Signal: {signal}\nPair: {pair}\nExpiry: {exp}\nVolatility: {volatility}\nProbability: {probability}%"
        )

        keyboard = [
            [InlineKeyboardButton("🍀 Repeat", callback_data=f"exp_{pair}_{exp}")],
            [InlineKeyboardButton("↩️ Back", callback_data="back")]
        ]
        context.bot.send_message(chat_id=query.message.chat_id, text="Next action:", reply_markup=InlineKeyboardMarkup(keyboard))

    # Back to main menu
    elif data == "back":
        start(update, context)

# ====== RUN BOT ======
updater = Updater(BOT_TOKEN)
updater.dispatcher.add_handler(CommandHandler("start", start))
updater.dispatcher.add_handler(CallbackQueryHandler(button))
updater.dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot is running...")
updater.start_polling()
updater.idle()