import os
import requests
import pandas as pd
import numpy as np
import asyncio

from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ---------------- CONFIG USING ENV VARIABLES ----------------
API_KEY = os.environ.get('ALPHA_VANTAGE_KEY')
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

if not BOT_TOKEN or not API_KEY:
    raise ValueError("Please set the environment variables TELEGRAM_BOT_TOKEN and ALPHA_VANTAGE_KEY")

CURRENCY_PAIRS = ['EUR/USD','USD/JPY','GBP/USD','AUD/USD','USD/CAD','USD/CHF','NZD/USD','EUR/GBP']
TIMEFRAMES = ['1min','5min','15min','30min','60min']  # Valid Alpha Vantage intervals
EXPIRATIONS = ['5s','10s','30s','1min','3min','5min']
AUTO_ALERTS = False
USER_SELECTION = {}

# ---------------- HELPER FUNCTIONS ----------------
async def fetch_price_data(from_symbol, to_symbol, interval='1min'):
    url = f'https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol={from_symbol}&to_symbol={to_symbol}&interval={interval}&apikey={API_KEY}&outputsize=compact'
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        print('Alpha Vantage response keys:', data.keys())  # Debug log

        # Find the correct key for time series
        ts_key = None
        for key in data.keys():
            if 'Time Series FX' in key:
                ts_key = key
                break

        if ts_key:
            df = pd.DataFrame(data[ts_key]).T
            df = df.rename(columns={'1. open':'open','2. high':'high','3. low':'low','4. close':'close'})
            df = df.astype(float)
            df = df.sort_index()
            return df
        else:
            print('Error: Time series key not found in response:', data)
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
    latest = df.iloc[-1]
    previous = df.iloc[-2]
    signal = None
    if latest['rsi'] < 30 and previous['macd'] < previous['macd_signal'] and latest['macd'] > latest['macd_signal'] and latest['close'] > latest['sma']:
        signal = 'BUY'
    elif latest['rsi'] > 70 and previous['macd'] > previous['macd_signal'] and latest['macd'] < latest['macd_signal'] and latest['close'] < latest['sma']:
        signal = 'SELL'
    return signal

# ---------------- TELEGRAM BOT ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton('Get Strong Signal Now', callback_data='manual_signal')],
                [InlineKeyboardButton('Start Auto Alerts', callback_data='start_auto')],
                [InlineKeyboardButton('Stop Auto Alerts', callback_data='stop_auto')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Welcome! Choose an option:', reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global AUTO_ALERTS
    query = update.callback_query
    await query.answer()

    if query.data == 'manual_signal':
        keyboard = [[InlineKeyboardButton(cp, callback_data=f'select_pair|{cp}')] for cp in CURRENCY_PAIRS]
        await query.edit_message_text('Select currency pair:', reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith('select_pair'):
        _, cp = query.data.split('|')
        USER_SELECTION[query.from_user.id] = {'pair': cp}
        keyboard = [[InlineKeyboardButton(tf, callback_data=f'select_tf|{tf}')] for tf in TIMEFRAMES]
        await query.edit_message_text(f'Pair selected: {cp}. Now select timeframe:', reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith('select_tf'):
        _, tf = query.data.split('|')
        USER_SELECTION[query.from_user.id]['tf'] = tf
        keyboard = [[InlineKeyboardButton(exp, callback_data=f'select_exp|{exp}')] for exp in EXPIRATIONS]
        await query.edit_message_text(f'Timeframe selected: {tf}. Now select expiration time:', reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith('select_exp'):
        _, exp = query.data.split('|')
        USER_SELECTION[query.from_user.id]['exp'] = exp
        user_choice = USER_SELECTION[query.from_user.id]
        pair_split = user_choice['pair'].split('/')
        df = await fetch_price_data(pair_split[0], pair_split[1], user_choice['tf'])
        if df is not None:
            df = await calculate_indicators(df)
            signal = await check_strict_signal(df)
            if signal:
                await query.edit_message_text(f'STRONG SIGNAL: {signal} for {user_choice["pair"]} | TF: {user_choice["tf"]} | EXP: {user_choice["exp"]}')
                img_file = 'buy.png' if signal == 'BUY' else 'sell.png'
                await context.bot.send_photo(chat_id=query.message.chat_id, photo=open(img_file, 'rb'))
            else:
                await query.edit_message_text('No strong signal at the moment.')
        else:
            await query.edit_message_text('Error fetching market data. Check logs for details.')

    elif query.data == 'start_auto':
        if not AUTO_ALERTS:
            AUTO_ALERTS = True
            await query.message.reply_text('Auto alerts started.')
            asyncio.create_task(auto_alerts(context, query.message.chat_id))
        else:
            await query.message.reply_text('Auto alerts already running.')

    elif query.data == 'stop_auto':
        if AUTO_ALERTS:
            AUTO_ALERTS = False
            await query.message.reply_text('Auto alerts stopped.')
        else:
            await query.message.reply_text('Auto alerts are not running.')

async def auto_alerts(context: ContextTypes.DEFAULT_TYPE, chat_id):
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
                        msg = f'AUTO STRONG SIGNAL: {signal} for {cp} | TF: {tf}'
                        await context.bot.send_message(chat_id=chat_id, text=msg)
                        img_file = 'buy.png' if signal == 'BUY' else 'sell.png'
                        await context.bot.send_photo(chat_id=chat_id, photo=open(img_file, 'rb'))
        await asyncio.sleep(60)

# ---------------- MAIN ----------------
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler('start', start))
app.add_handler(CallbackQueryHandler(button))

print('Bot is running...')
app.run_polling()