import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import pandas as pd
import random

# === IMAGES ===
BUY_IMAGE = "buy.png"
SELL_IMAGE = "sell.png"

# === SIMULATED MARKET DATA ===
# We'll generate fake candle data for demo
def get_market_data():
    # Generate last 10 candles
    data = []
    price = 1.1000
    for _ in range(10):
        change = random.uniform(-0.001, 0.001)
        close = price + change
        high = max(price, close) + random.uniform(0, 0.0005)
        low = min(price, close) - random.uniform(0, 0.0005)
        data.append({"close": close, "high": high, "low": low})
        price = close
    df = pd.DataFrame(data)
    return df

# === SIGNAL LOGIC (different method) ===
def analyze_signal(df):
    # Calculate 3-candle moving average
    df['ma3'] = df['close'].rolling(3).mean()
    # Simple RSI-like signal
    df['change'] = df['close'].diff()
    up = df['change'].apply(lambda x: x if x>0 else 0)
    down = df['change'].apply(lambda x: -x if x<0 else 0)
    avg_up = up.rolling(5).mean().iloc[-1]
    avg_down = down.rolling(5).mean().iloc[-1]
    rsi = 100 - 100/(1 + (avg_up/(avg_down+0.0001)))

    last = df.iloc[-1]
    if last['close'] > last['ma3'] and rsi < 70:
        return "BUY"
    else:
        return "SELL"

def calculate_probability(signal):
    # Just for display, random high probability
    return random.randint(70, 95)

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
        msg = await query.edit_message_text("⏳ Analyzing market... 5")

        # Countdown 5 → 0
        for i in range(4, -1, -1):
            await asyncio.sleep(1)
            try:
                await msg.edit_text(f"⏳ Analyzing market... {i}")
            except:
                pass

        # Generate fake market data and analyze
        df = get_market_data()
        signal = analyze_signal(df)
        probability = calculate_probability(signal)
        volatility = "Moderate"
        img_path = BUY_IMAGE if signal == "BUY" else SELL_IMAGE

        # Send photo + caption
        try:
            with open(img_path, "rb") as img:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=img,
                    caption=f"Signal: {signal}\nPair: {pair}\nExpiry: 1m\nVolatility: {volatility}\nProbability: {probability}%"
                )
        except FileNotFoundError:
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"⚠️ {img_path} not found!")

        # Repeat / Back buttons
        keyboard = [
            [InlineKeyboardButton("🍀 Repeat", callback_data=f"pair_{pair}")],
            [InlineKeyboardButton("↩️ Back", callback_data="back")]
        ]
        await context.bot.send_message(chat_id=query.message.chat_id, text="Next action:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "back":
        await start(update, context)

# === RUN BOT ===
if __name__ == "__main__":
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace with your real bot token
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    print("Bot is running...")
    app.run_polling()