import os
import asyncio
import requests
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ---------------------- ENV VARIABLES ----------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
TWELVE_DATA_API_KEY = os.environ.get("TWELVE_DATA_API_KEY")

# ---------------------- SETTINGS ----------------------
CURRENCY_PAIRS = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "EURGBP"]
TIMEFRAMES = ["1min", "2min", "5min"]
EXPIRATION_TIMES = ["5s", "10s", "30s", "1m", "3m", "5m"]
AUTO_ALERTS = {}  # chat_id: True/False

# Buy/Sell images
BUY_IMAGE_URL = "https://i.ibb.co/TrjYzY1/buy.png"  # Replace with your professional buy image
SELL_IMAGE_URL = "https://i.ibb.co/wWZQhMf/sell.png" # Replace with your professional sell image

# ---------------------- HELPERS ----------------------
def fetch_market_data(pair: str, interval: str):
    url = f"https://api.twelvedata.com/time_series?symbol={pair}&interval={interval}&outputsize=100&apikey={TWELVE_DATA_API_KEY}"
    response = requests.get(url)
    data = response.json()
    if "values" not in data:
        raise ValueError("Error fetching market data.")
    df = pd.DataFrame(data["values"])
    df = df.astype(float)
    df = df.iloc[::-1]  # Oldest to newest
    return df

def calculate_indicators(df):
    df["RSI"] = RSIIndicator(df["close"]).rsi()
    macd = MACD(df["close"])
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["SMA"] = SMAIndicator(df["close"], window=14).sma_indicator()
    last_row = df.iloc[-1]
    signal = "Hold"
    if last_row["RSI"] < 30 and last_row["MACD"] > last_row["MACD_signal"] and last_row["close"] > last_row["SMA"]:
        signal = "Buy"
    elif last_row["RSI"] > 70 and last_row["MACD"] < last_row["MACD_signal"] and last_row["close"] < last_row["SMA"]:
        signal = "Sell"
    return signal, last_row

# ---------------------- BUTTONS ----------------------
def build_currency_buttons():
    buttons = [[InlineKeyboardButton(pair, callback_data=f"currency|{pair}")] for pair in CURRENCY_PAIRS]
    return InlineKeyboardMarkup(buttons)

def build_timeframe_buttons():
    buttons = [[InlineKeyboardButton(tf, callback_data=f"timeframe|{tf}")] for tf in TIMEFRAMES]
    return InlineKeyboardMarkup(buttons)

def build_expiration_buttons():
    buttons = [[InlineKeyboardButton(exp, callback_data=f"expiration|{exp}")] for exp in EXPIRATION_TIMES]
    return InlineKeyboardMarkup(buttons)

def build_auto_alert_buttons(chat_id):
    status = "ON" if AUTO_ALERTS.get(chat_id, False) else "OFF"
    buttons = [[InlineKeyboardButton(f"Auto Alert: {status}", callback_data="toggle_auto_alert")]]
    return InlineKeyboardMarkup(buttons)

# ---------------------- COMMAND HANDLERS ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! I am your professional Forex bot 🤖\n"
        "Choose a currency pair to start:",
        reply_markup=build_currency_buttons()
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data

    if data.startswith("currency"):
        _, pair = data.split("|")
        context.user_data["pair"] = pair
        await query.edit_message_text(
            f"Currency selected: {pair}\nNow choose timeframe:",
            reply_markup=build_timeframe_buttons()
        )
    elif data.startswith("timeframe"):
        _, tf = data.split("|")
        context.user_data["timeframe"] = tf
        await query.edit_message_text(
            f"Timeframe selected: {tf}\nNow choose expiration time:",
            reply_markup=build_expiration_buttons()
        )
    elif data.startswith("expiration"):
        _, exp = data.split("|")
        context.user_data["expiration"] = exp
        await query.edit_message_text(
            f"Expiration time selected: {exp}\nFetching signal...",
        )
        await send_signal(chat_id, context)
    elif data == "toggle_auto_alert":
        current = AUTO_ALERTS.get(chat_id, False)
        AUTO_ALERTS[chat_id] = not current
        await query.edit_message_reply_markup(reply_markup=build_auto_alert_buttons(chat_id))
        status = "ON" if AUTO_ALERTS[chat_id] else "OFF"
        await context.bot.send_message(chat_id, f"Auto alert turned {status} ✅")

# ---------------------- SIGNAL ----------------------
async def send_signal(chat_id, context: ContextTypes.DEFAULT_TYPE):
    pair = context.user_data.get("pair")
    tf = context.user_data.get("timeframe")
    exp = context.user_data.get("expiration")
    if not all([pair, tf, exp]):
        await context.bot.send_message(chat_id, "Please select currency, timeframe, and expiration first.")
        return
    try:
        df = fetch_market_data(pair, tf)
        signal, last_row = calculate_indicators(df)
        price = last_row["close"]
        msg = f"Signal for {pair} ({tf})\nPrice: {price}\nSignal: {signal}\nExpiration: {exp}\nGenerated by your professional bot 🤖"
        image_url = BUY_IMAGE_URL if signal == "Buy" else SELL_IMAGE_URL if signal == "Sell" else None
        if image_url:
            await context.bot.send_photo(chat_id, photo=image_url, caption=msg)
        else:
            await context.bot.send_message(chat_id, msg)
    except Exception as e:
        await context.bot.send_message(chat_id, f"Error fetching market data. Check logs.\nDetails: {e}")

# ---------------------- AUTO ALERT LOOP ----------------------
async def auto_alert_loop(application):
    while True:
        for chat_id, active in AUTO_ALERTS.items():
            if active:
                await send_signal(chat_id, application)
        await asyncio.sleep(30)  # checks every 30 seconds

# ---------------------- MAIN ----------------------
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Start auto alert loop in background
    app.job_queue.run_repeating(lambda ctx: asyncio.create_task(auto_alert_loop(app)), interval=30, first=5)

    print("Bot started successfully ✅")
    app.run_polling()