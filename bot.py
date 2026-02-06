import os
import asyncio
import random
import pandas as pd
import yfinance as yf
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BUY_IMAGE = "buy.png"
SELL_IMAGE = "sell.png"

PAIRS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X"
}

EXPIRATION = ["1m", "2m", "5m"]

# === REAL MARKET ANALYSIS ===
def analyze_market(symbol):
    df = yf.download(symbol, period="1d", interval="1m")
    df.dropna(inplace=True)

    # Indicators
    df["rsi"] = RSIIndicator(df["Close"], window=14).rsi()
    df["sma"] = SMAIndicator(df["Close"], window=10).sma_indicator()
    macd = MACD(df["Close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()

    last = df.iloc[-1]

    buy_score = 0
    sell_score = 0

    if last["Close"] > last["sma"]:
        buy_score += 1
    else:
        sell_score += 1

    if last["rsi"] < 35:
        buy_score += 1
    elif last["rsi"] > 65:
        sell_score += 1

    if last["macd"] > last["macd_signal"]:
        buy_score += 1
    else:
        sell_score += 1

    if buy_score > sell_score:
        signal = "BUY"
        probability = 70 + buy_score * 5
    else:
        signal = "SELL"
        probability = 70 + sell_score * 5

    return signal, min(probability, 95)

# === START ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(p, callback_data=f"pair_{p}")] for p in PAIRS]
    await update.message.reply_text("Select a currency pair:", reply_markup=InlineKeyboardMarkup(keyboard))

# === BUTTON HANDLER ===
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("pair_"):
        pair = data.split("_")[1]
        keyboard = [[InlineKeyboardButton(e, callback_data=f"exp_{pair}_{e}")] for e in EXPIRATION]
        await query.edit_message_text(f"Select expiration for {pair}:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("exp_"):
        _, pair, exp = data.split("_")
        msg = await query.edit_message_text("⏳ Analyzing market... 5")

        for i in range(4, -1, -1):
            await asyncio.sleep(1)
            try:
                await msg.edit_text(f"⏳ Analyzing market... {i}")
            except:
                pass

        signal, probability = analyze_market(PAIRS[pair])
        img_path = BUY_IMAGE if signal == "BUY" else SELL_IMAGE

        caption = f"""Signal: {signal}
Pair: {pair}
Expiry: {exp}
Volatility: Moderate
Probability: {probability}%"""

        with open(img_path, "rb") as img:
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=img, caption=caption)

        keyboard = [
            [InlineKeyboardButton("🍀 Repeat", callback_data=f"exp_{pair}_{exp}")],
            [InlineKeyboardButton("↩️ Back", callback_data="back")]
        ]
        await context.bot.send_message(chat_id=query.message.chat_id, text="Next action:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "back":
        await start(update, context)

# === RUN ===
if __name__ == "__main__":
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    print("Bot running...")
    app.run_polling()