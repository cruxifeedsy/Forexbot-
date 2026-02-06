import os
import requests
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio

# ---------------- CONFIG ----------------
API_KEY = 'J4JQXEF42DGJHWN1'  # Replace with your API key
BOT_TOKEN = os.getenv('8133705665:AAFhhc0_mx4Cw6Tq72MyP7l4MQEowxCJzzU')  # Or set your Telegram bot token here
CURRENCY_PAIRS = ['EUR/USD','USD/JPY','GBP/USD','AUD/USD','USD/CAD','USD/CHF','NZD/USD','EUR/GBP']
TIMEFRAMES = ['1min','2min','5min']
EXPIRATIONS = ['5s','10s','30s','1min','3min','5min']
AUTO_ALERTS = False

# ---------------- HELPER FUNCTIONS ----------------
async def fetch_price_data(from_symbol, to_symbol, interval='1min'):
    url = f'https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={from_symbol}&to_symbol={to_symbol}&interval={interval}&apikey={API_KEY}&outputsize=compact'
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if 'Time Series FX (' in str(data):
            key = list(data.keys())[1]
            df = pd.DataFrame(data[key]).T
            df = df.rename(columns={'1. open':'open','2. high':'high','3. low':'low','4. close':'close'})
            df = df.astype(float)
            df = df.sort_index()
            return df
        else:
            return None
    except Exception as e:
        print('Error fetching data:', e)
        return None

async def calculate_indicators(df):
    df['rsi'] = RSIIndicator(df['close'], window=14).rsi()
    macd = MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['sma'] = SMAIndicator(df['close'], window=20).sma_indicator()
    return df

async def check_strict_signal(df):
    # Strict signal: RSI <30 (buy) or >70 (sell), MACD crossover, price above/below SMA
    latest = df.iloc[-1]
    previous = df.iloc[-2]
    signal = None
    
    # BUY condition
    if latest['rsi'] < 30 and previous['macd'] < previous['macd_signal'] and latest['macd'] > latest['macd_signal'] and latest['close'] > latest['sma']:
        signal = 'BUY'
    # SELL condition
    elif latest['rsi'] > 70 and previous['macd'] > previous['macd_signal'] and latest['macd'] < latest['macd_signal'] and latest['close'] < latest['sma']:
        signal = 'SELL'
    return signal

# ---------------- TELEGRAM BOT ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton('Get Strong Signal Now', callback_data='manual_signal')],
        [InlineKeyboardButton('Start Auto Alerts', callback_data='start_auto')],
        [InlineKeyboardButton('Stop Auto Alerts', callback_data='stop_auto')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Welcome! Choose an option:', reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global AUTO_ALERTS
    query = update.callback_query
    await query.answer()

    if query.data == 'manual_signal':
        msg = 'Choose currency pair and timeframe:'
        await query.edit_message_text(msg)
        # For simplicity, just pick first pair and timeframe
        pair = CURRENCY_PAIRS[0].split('/')
        df = await fetch_price_data(pair[0], pair[1], TIMEFRAMES[0])
        if df is not None:
            df = await calculate_indicators(df)
            signal = await check_strict_signal(df)
            if signal:
                await query.message.reply_text(f'STRONG SIGNAL: {signal} for {CURRENCY_PAIRS[0]} | TF: {TIMEFRAMES[0]}')
            else:
                await query.message.reply_text('No strong signal at the moment.')
        else:
            await query.message.reply_text('Error fetching market data.')

    elif query.data == 'start_auto':
        if not AUTO_ALERTS:
            AUTO_ALERTS = True
            await query.message.reply_text('Auto alerts started.')
            asyncio.create_task(auto_alerts(context))
        else:
            await query.message.reply_text('Auto alerts already running.')

    elif query.data == 'stop_auto':
        if AUTO_ALERTS:
            AUTO_ALERTS = False
            await query.message.reply_text('Auto alerts stopped.')
        else:
            await query.message.reply_text('Auto alerts are not running.')

async def auto_alerts(context: ContextTypes.DEFAULT_TYPE):
    global AUTO_ALERTS
    while AUTO_ALERTS:
        for cp in CURRENCY_PAIRS:
            pair = cp.split('/')
            for tf in TIMEFRAMES:
                df = await fetch_price_data(pair[0], pair[1], tf)
                if df is not None:
                    df = await calculate_indicators(df)
                    signal = await check_strict_signal(df)
                    if signal:
                        await context.bot.send_message(chat_id=context.job.chat_id, text=f'AUTO STRONG SIGNAL: {signal} for {cp} | TF: {tf}')
        await asyncio.sleep(60)  # Check every 60 seconds

# ---------------- MAIN ----------------
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler('start', start))
app.add_handler(CallbackQueryHandler(button))

print('Bot is running...')
app.run_polling()