limport os
import requests
import pandas as pd
import asyncio
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Environment variables
TWELVEDATA_KEY = os.environ.get('TWELVEDATA_KEY')
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

if not TWELVEDATA_KEY or not BOT_TOKEN:
    raise ValueError("Please set environment variables: TWELVEDATA_KEY and TELEGRAM_BOT_TOKEN")

CURRENCY_PAIRS = ['EUR/USD','USD/JPY','GBP/USD','AUD/USD','USD/CAD','USD/CHF','NZD/USD','EUR/GBP']
TIMEFRAMES = ['1min','5min','15min','30min','45min','1h','2h','4h','5h']
EXPIRATIONS = ['5s','10s','30s','1min','3min','5min']

async def fetch_price_data(pair, interval='1min'):
    from_symbol, to_symbol = pair.split('/')
    url = f'https://api.twelvedata.com/time_series?symbol={from_symbol}/{to_symbol}&interval={interval}&apikey={TWELVEDATA_KEY}&outputsize=100'
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        print('Twelve Data response keys:', data.keys())

        if 'values' in data:
            df = pd.DataFrame(data['values'])
            df = df.rename(columns={'open':'open','high':'high','low':'low','close':'close'})
            df = df[['open','high','low','close']].astype(float)
            df = df[::-1].reset_index(drop=True)
            return df
        elif 'message' in data:
            print('API message:', data['message'])
            return None
        else:
            print('Unexpected response:', data)
            return None
    except Exception as e:
        print('Error fetching data from Twelve Data:', e)
        return None

async def calculate_indicators(df):
    df['rsi'] = RSIIndicator(df['close'], window=14).rsi()
    macd = MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['sma'] = SMAIndicator(df['close'], window=20).sma_indicator()
    return df

async def get_signal(df):
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    signal = None
    if latest['rsi'] < 30 and prev['macd'] < prev['macd_signal'] and latest['macd'] > latest['macd_signal'] and latest['close'] > latest['sma']:
        signal = 'BUY'
    elif latest['rsi'] > 70 and prev['macd'] > prev['macd_signal'] and latest['macd'] < latest['macd_signal'] and latest['close'] < latest['sma']:
        signal = 'SELL'
    return signal

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Get Strong Signal Now", callback_data='strong_signal')],
        [InlineKeyboardButton("Start Auto Alert", callback_data='auto_alert')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Choose an option:', reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'strong_signal':
        pair = CURRENCY_PAIRS[0]  # Default, can be updated to allow selection
        interval = TIMEFRAMES[0]
        df = await fetch_price_data(pair, interval)
        if df is None:
            await query.edit_message_text(text='Error fetching market data. Check logs.')
            return
        df = await calculate_indicators(df)
        signal = await get_signal(df)
        await query.edit_message_text(text=f'Pair: {pair}\nTimeframe: {interval}\nSignal: {signal or "No strong signal"}')

    elif query.data == 'auto_alert':
        await query.edit_message_text(text='Auto alert feature coming soon.')

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button))
    print('Bot started...')
    app.run_polling()