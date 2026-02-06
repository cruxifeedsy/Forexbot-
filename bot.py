import os
import pandas as pd
import yfinance as yf
import ta
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ====== ENVIRONMENT VARIABLES ======
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
ACCESS_CODES = os.environ.get("ACCESS_CODES", "123ABC").split(",")
OWNER_CONTACT = os.environ.get("OWNER_CONTACT", "@YourUsername")

# ====== DATA ======
authorized_users = []
PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]
EXPIRATION = ["5s", "15s", "1m", "2m", "3m", "5m", "10m"]

BUY_IMAGE = "buy.png"
SELL_IMAGE = "sell.png"

# ====== FAST MARKET DATA FETCH ======
async def fetch_data(pair):
    loop = asyncio.get_running_loop()
    df = await loop.run_in_executor(None, lambda: yf.download(
        tickers=f"{pair}=X",
        period="1h",      # last 1 hour
        interval="1m"     # 1-minute candles
    ))
    df.dropna(inplace=True)
    return df

# ====== SIGNAL CALCULATION ======
def analyze_signal(df):
    df['rsi'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
    macd = ta.trend.MACD(df['Close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['sma'] = df['Close'].rolling(window=20).mean()
    last = df.iloc[-1]

    # strength scores
    buy_score = max(0, 50 - last['rsi']) + max(0, last['macd'] - last['macd_signal'])*10 + (10 if last['Close'] > last['sma'] else 0)
    sell_score = max(0, last['rsi'] - 50) + max(0, last['macd_signal'] - last['macd'])*10 + (10 if last['Close'] < last['sma'] else 0)

    return "BUY" if buy_score >= sell_score else "SELL"

def calculate_probability(df, signal):
    last = df.iloc[-1]
    buy_score = max(0, 50 - last['rsi']) + max(0, last['macd'] - last['macd_signal'])*10 + (10 if last['Close'] > last['sma'] else 0)
    sell_score = max(0, last['rsi'] - 50) + max(0, last['macd_signal'] - last['macd'])*10 + (10 if last['Close'] < last['sma'] else 0)
    prob = buy_score + 50 if signal == "BUY" else sell_score + 50
    return min(int(prob), 95)

# ====== START COMMAND ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in authorized_users:
        await update.message.reply_text(
            f"🚫 You need an access code to use this bot.\n"
            f"Please chat with {OWNER_CONTACT} to get the access code."
        )
        return

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

    if data.startswith("pair_"):
        pair = data.split("_")[1]
        keyboard = [[InlineKeyboardButton(exp, callback_data=f"exp_{pair}_{exp}")] for exp in EXPIRATION]
        await query.edit_message_text(f"Select expiration for {pair}:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("exp_"):
        _, pair, exp = data.split("_")
        await query.edit_message_text("⏳ Generating signal...")
        await context.bot.send_message(chat_id=query.message.chat_id, text="Analyzing market...")

        # fetch data async
        df = await fetch_data(pair)
        signal = analyze_signal(df)
        probability = calculate_probability(df, signal)
        volatility = "Moderate"  # placeholder
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

    elif data == "back":
        await start(update, context)

# ====== RUN BOT ======
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    app.run_polling()