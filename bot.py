import os
import sqlite3
import random
import traceback
from datetime import datetime

import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

ADMIN_ID = 8385943123
POCKET_REFERRAL_LINK = "https://pocket-friends.co/r/cvez0moyv8"

bot = telebot.TeleBot(TOKEN)

CRYPTO_ASSETS = [
    "BTC/USD", "ETH/USD", "BNB/USD", "SOL/USD", "XRP/USD",
    "ADA/USD", "DOGE/USD", "DOT/USD", "MATIC/USD", "SHIB/USD",
    "AVAX/USD", "LINK/USD", "LTC/USD", "TRX/USD", "UNI/USD",
    "ATOM/USD", "ETC/USD", "XLM/USD", "FIL/USD", "ALGO/USD",
    "VET/USD", "MANA/USD", "SAND/USD", "THETA/USD", "XTZ/USD",
    "EOS/USD", "AAVE/USD", "CAKE/USD", "KLAY/USD", "NEAR/USD",
    "QNT/USD", "CHZ/USD", "FLOW/USD", "GALA/USD", "AXS/USD",
    "APE/USD", "GRT/USD", "CRV/USD", "SNX/USD", "COMP/USD"
]

FOREX_ASSETS = [
    "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD",
    "USD/CAD", "NZD/USD", "EUR/GBP", "GBP/JPY",
    "USD/CHF", "EUR/JPY", "EUR/CHF", "GBP/CHF",
    "AUD/JPY", "CAD/JPY", "NZD/JPY", "EUR/AUD",
    "EUR/CAD", "GBP/AUD", "GBP/CAD", "AUD/CAD",
    "AUD/NZD", "USD/SGD", "USD/HKD", "USD/CNH",
    "USD/MXN", "USD/ZAR", "USD/TRY", "USD/INR"
]

COMMODITIES_ASSETS = [
    "XAU/USD", "XAG/USD", "XPT/USD", "XPD/USD",
    "OIL/USD", "NATURAL GAS", "COPPER", "ALUMINUM",
    "WHEAT", "CORN", "SOYBEAN", "SUGAR",
    "COFFEE", "COCOA", "COTTON", "LUMBER"
]

INDICES_ASSETS = [
    "S&P 500", "NASDAQ", "DOW JONES", "DAX 30",
    "FTSE 100", "NIKKEI 225", "CAC 40", "HSI",
    "ASX 200", "IBEX 35", "SMI", "TSX",
    "STOXX 50", "RUSSELL 2000", "SHANGHAI COMP"
]

OTC_ASSETS = [
    "BTC/OTC", "ETH/OTC", "BNB/OTC", "SOL/OTC", "XRP/OTC",
    "ADA/OTC", "DOGE/OTC", "DOT/OTC", "MATIC/OTC", "SHIB/OTC",
    "AVAX/OTC", "LINK/OTC", "LTC/OTC", "TRX/OTC", "UNI/OTC",
    "ATOM/OTC", "XLM/OTC", "FIL/OTC", "ALGO/OTC", "VET/OTC",
    "EOS/OTC", "AAVE/OTC", "XTZ/OTC", "MANA/OTC", "SAND/OTC",
    "GALA/OTC", "APE/OTC", "AXS/OTC", "THETA/OTC", "NEAR/OTC",
    "QNT/OTC", "CHZ/OTC", "FLOW/OTC", "GRT/OTC", "CRV/OTC",
    "SNX/OTC", "COMP/OTC", "CAKE/OTC", "KLAY/OTC", "ETC/OTC"
]

ALL_ASSETS = CRYPTO_ASSETS + FOREX_ASSETS + COMMODITIES_ASSETS + INDICES_ASSETS + OTC_ASSETS
TIMEFRAMES = ["1 мин", "5 мин", "15 мин", "30 мин", "1 час"]

# =========================
# БАЗА
# =========================
def get_db_connection():
    conn = sqlite3.connect("pocket_bot.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        username TEXT,
        first_name TEXT,
        join_date TEXT,
        pocket_id TEXT,
        is_verified INTEGER DEFAULT 0,
        referrer_id INTEGER DEFAULT 0,
        balance REAL DEFAULT 0,
        signals_count INTEGER DEFAULT 0,
        last_signal_date TEXT,
        preferred_timeframe TEXT DEFAULT ''
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER,
        registration_date TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        signal_date TEXT,
        asset TEXT,
        direction TEXT,
        timeframe TEXT,
        confidence INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS verification_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        pocket_id TEXT,
        request_date TEXT,
        status TEXT DEFAULT 'PENDING',
        verification_date TEXT,
        admin_id INTEGER
    )
    """)

    conn.commit()
    cur.close()
    conn.close()


init_db()


def execute_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        if commit:
            conn.commit()

        if fetchone:
            return cur.fetchone()
        if fetchall:
            return cur.fetchall()
        return None
    finally:
        cur.close()
        conn.close()


def add_user(telegram_id, username, first_name, join_date):
    execute_query(
        """INSERT OR IGNORE INTO users (telegram_id, username, first_name, join_date)
           VALUES (?, ?, ?, ?)""",
        (telegram_id, username, first_name, join_date),
        commit=True
    )


def get_user(telegram_id):
    return execute_query(
        "SELECT * FROM users WHERE telegram_id = ?",
        (telegram_id,),
        fetchone=True
    )


def check_user_access(user_id, username, first_name):
    if user_id == ADMIN_ID:
        execute_query(
            """INSERT OR IGNORE INTO users
               (telegram_id, username, first_name, join_date, is_verified)
               VALUES (?, ?, ?, ?, 1)""",
            (user_id, username, first_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            commit=True
        )
        execute_query(
            "UPDATE users SET is_verified = 1 WHERE telegram_id = ?",
            (user_id,),
            commit=True
        )
        return True, "owner"

    user_data = get_user(user_id)
    if not user_data:
        return False, "not_registered"

    if dict(user_data).get("is_verified", 0) == 1:
        return True, "verified"

    return False, "not_verified"


# =========================
# МЕНЮ
# =========================
def create_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📈 Случайный сигнал"),
        types.KeyboardButton("🎯 Сигнал по активу"),
        types.KeyboardButton("⚙️ Настройки"),
        types.KeyboardButton("📊 Моя статистика"),
        types.KeyboardButton("👥 Рефералы"),
        types.KeyboardButton("ℹ️ Помощь"),
        types.KeyboardButton("🔐 Регистрация")
    )
    return markup


def create_settings_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("⏱️ Выбрать время"),
        types.KeyboardButton("🔙 Назад")
    )
    return markup


def create_assets_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 Криптовалюты (40+)", callback_data="category_crypto"),
        types.InlineKeyboardButton("💱 Форекс (28+)", callback_data="category_forex")
    )
    markup.add(
        types.InlineKeyboardButton("🛢️ Сырье (16+)", callback_data="category_commodities"),
        types.InlineKeyboardButton("📊 Индексы (15+)", callback_data="category_indices")
    )
    markup.add(
        types.InlineKeyboardButton("📊 Крипто OTC (40+)", callback_data="category_otc")
    )
    return markup


def create_timeframe_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    for tf in TIMEFRAMES:
        markup.add(types.InlineKeyboardButton(tf, callback_data=f"timeframe_{tf}"))
    markup.add(
        types.InlineKeyboardButton("🎲 Случайное время", callback_data="timeframe_random"),
        types.InlineKeyboardButton("❌ Отмена", callback_data="timeframe_cancel")
    )
    return markup


def create_paged_menu(items, prefix, page=1, per_page=20):
    markup = types.InlineKeyboardMarkup(row_width=2)
    start = (page - 1) * per_page
    end = min(start + per_page, len(items))
    current = items[start:end]

    for i in range(0, len(current), 2):
        if i + 1 < len(current):
            markup.add(
                types.InlineKeyboardButton(current[i], callback_data=f"asset_{current[i]}"),
                types.InlineKeyboardButton(current[i + 1], callback_data=f"asset_{current[i + 1]}")
            )
        else:
            markup.add(types.InlineKeyboardButton(current[i], callback_data=f"asset_{current[i]}"))

    nav = []
    if page > 1:
        nav.append(types.InlineKeyboardButton("◀️ Назад", callback_data=f"{prefix}_page_{page-1}"))
    if end < len(items):
        nav.append(types.InlineKeyboardButton("Вперёд ▶️", callback_data=f"{prefix}_page_{page+1}"))
    if nav:
        markup.add(*nav)

    markup.add(types.InlineKeyboardButton("🔙 Назад к категориям", callback_data="back_to_categories"))
    return markup


# =========================
# СИГНАЛЫ
# =========================
def fake_analyze(asset, timeframe=None):
    if timeframe is None:
        timeframe = random.choice(TIMEFRAMES)

    direction = random.choice(["BUY", "SELL"])
    confidence = random.randint(68, 91)

    if direction == "BUY":
        action = "ПОКУПКА (CALL)"
        emoji = "📈"
        color = "🟢"
        pattern = "BULLISH"
        price
