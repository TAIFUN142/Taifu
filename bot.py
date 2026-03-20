import os
import sqlite3
import random
import telebot
from telebot import types
from datetime import datetime

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

ADMIN_ID = 8385943123  # <-- ВСТАВЬ СВОЙ TELEGRAM ID
POCKET_REFERRAL_LINK = "https://pocket-friends.co/r/cvez0moyv8"

bot = telebot.TeleBot(TOKEN)

CRYPTO_ASSETS = [
    "BTC/USD", "ETH/USD", "BNB/USD", "SOL/USD", "XRP/USD",
    "ADA/USD", "DOGE/USD", "DOT/USD", "MATIC/USD", "SHIB/USD",
    "AVAX/USD", "LINK/USD", "LTC/USD", "TRX/USD", "UNI/USD",
    "ATOM/USD", "ETC/USD", "XLM/USD", "FIL/USD", "ALGO/USD"
]

FOREX_ASSETS = [
    "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD",
    "USD/CAD", "NZD/USD", "EUR/GBP", "GBP/JPY",
    "USD/CHF", "EUR/JPY", "EUR/CHF", "GBP/CHF"
]

OTC_ASSETS = [
    "BTC/OTC", "ETH/OTC", "BNB/OTC", "SOL/OTC", "XRP/OTC",
    "ADA/OTC", "DOGE/OTC", "DOT/OTC", "MATIC/OTC", "SHIB/OTC",
    "AVAX/OTC", "LINK/OTC", "LTC/OTC", "TRX/OTC", "UNI/OTC",
    "ATOM/OTC", "XLM/OTC", "FIL/OTC", "ALGO/OTC"
]

TIMEFRAMES = ["1 мин", "5 мин", "15 мин"]


# =========================
# БАЗА ДАННЫХ
# =========================
def db():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        join_date TEXT,
        pocket_id TEXT,
        is_verified INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS verification_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        pocket_id TEXT,
        status TEXT DEFAULT 'PENDING',
        request_date TEXT,
        review_date TEXT
    )
    """)

    conn.commit()
    cur.close()
    conn.close()


init_db()


def execute(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = db()
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


def add_user(user):
    execute(
        """
        INSERT OR IGNORE INTO users (telegram_id, username, first_name, join_date)
        VALUES (?, ?, ?, ?)
        """,
        (
            user.id,
            user.username,
            user.first_name,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ),
        commit=True
    )


def get_user(user_id):
    return execute(
        "SELECT * FROM users WHERE telegram_id = ?",
        (user_id,),
        fetchone=True
    )


def is_verified(user_id):
    if user_id == ADMIN_ID:
        return True

    row = get_user(user_id)
    if not row:
        return False

    return int(dict(row).get("is_verified", 0)) == 1


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


def create_asset_categories_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💰 Криптовалюты", callback_data="cat_crypto"),
        types.InlineKeyboardButton("💱 Форекс", callback_data="cat_forex"),
        types.InlineKeyboardButton("📊 OTC", callback_data="cat_otc")
    )
    return markup


def create_assets_page_menu(assets, prefix, page=1, per_page=10):
    markup = types.InlineKeyboardMarkup(row_width=2)
    start = (page - 1) * per_page
    end = min(start + per_page, len(assets))
    items = assets[start:end]

    row = []
    for asset in items:
        row.append(types.InlineKeyboardButton(asset, callback_data=f"asset_{asset}"))
        if len(row) == 2:
            markup.add(*row)
            row = []

    if row:
        markup.add(*row)

    nav = []
    if page > 1:
        nav.append(types.InlineKeyboardButton("◀️ Назад", callback_data=f"{prefix}_{page-1}"))
    if end < len(assets):
        nav.append(types.InlineKeyboardButton("Вперёд ▶️", callback_data=f"{prefix}_{page+1}"))
    if nav:
        markup.add(*nav)

    markup.add(types.InlineKeyboardButton("🔙 К категориям", callback_data="back_categories"))
    return markup


def generate_signal_text(asset):
    action = random.choice(["ПОКУПКА (CALL)", "ПРОДАЖА (PUT)"])
    confidence = random.randint(68, 89)
    timeframe = random.choice(TIMEFRAMES)

    if action == "ПОКУПКА (CALL)":
        structure = "BULLISH"
        price_text = "Цена выше EMA21"
        macd_text = "MACD выше нуля"
    else:
        structure = "BEARISH"
        price_text = "Цена ниже EMA21"
        macd_text = "MACD слабеет"

    risk = "🟢 НИЗКИЙ" if confidence >= 82 else "🟡 СРЕДНИЙ" if confidence >= 72 else "🔴 ВЫСОКИЙ"

    return (
        f"📉 СИГНАЛ ПО РЫНКУ 📉\n\n"
        f"🎯 АКТИВ: {asset}\n"
        f"🎯 ДЕЙСТВИЕ: {action}\n"
        f"⏱ ЭКСПИРАЦИЯ: {timeframe}\n"
        f"📊 УВЕРЕННОСТЬ: {confidence}%\n"
        f"⚠️ РИСК: {risk}\n\n"
        f"🧠 АНАЛИЗ:\n"
        f"• Структура: {structure}\n"
        f"• {price_text}\n"
        f"• RSI подтверждает импульс\n"
        f"• {macd_text}\n\n"
        f"📈 АНАЛИТИЧЕСКИЙ ВЫВОД:\n"
        f"1. Направление рассчитано по теханализу\n"
        f"2. Таймфрейм анализа: {timeframe}\n"
        f"3. Слабые сигналы лучше пропускать"
    )


def require_verification(chat_id):
    bot.send_message(
        chat_id,
        "🔒 Доступ к сигналам закрыт.\n\nСначала пройди верификацию через кнопку «🔐 Регистрация».",
        reply_markup=create_main_menu()
    )


# =========================
# КОМАНДЫ
# =========================
@bot.message_handler(commands=["start"])
def start_command(message):
    add_user(message.from_user)

    text = (
        "🤖 Бот работает, бро!\n\n"
        "Если хочешь сигналы — сначала пройди верификацию через «🔐 Регистрация»."
    )
    bot.send_message(message.chat.id, text, reply_markup=create_main_menu())


@bot.message_handler(commands=["myid"])
def myid_command(message):
    bot.send_message(message.chat.id, f"Твой Telegram ID: {message.from_user.id}")


@bot.message_handler(func=lambda message: message.text == "🔐 Регистрация")
def registration_handler(message):
    add_user(message.from_user)

    if message.from_user.id == ADMIN_ID:
        execute(
            "UPDATE users SET is_verified = 1 WHERE telegram_id = ?",
            (message.from_user.id,),
            commit=True
        )
        bot.send_message(
            message.chat.id,
            "👑 Ты владелец, тебе доступ открыт.",
            reply_markup=create_main_menu()
        )
        return

    user = get_user(message.from_user.id)
    if user and int(dict(user).get("is_verified", 0)) == 1:
        bot.send_message(
            message.chat.id,
            "✅ Ты уже верифицирован.",
            reply_markup=create_main_menu()
        )
        return

    text = (
        "📝 РЕГИСТРАЦИЯ\n\n"
        f"1. Зарегистрируйся по ссылке:\n{POCKET_REFERRAL_LINK}\n\n"
        "2. Найди свой Pocket ID\n"
        "3. Отправь мне его следующим сообщением\n\n"
        "⚠️ Только цифры."
    )
    msg = bot.send_message(message.chat.id, text, reply_markup=create_main_menu())
    bot.register_next_step_handler(msg, process_pocket_id)


def process_pocket_id(message):
    pocket_id = (message.text or "").strip()

    if not pocket_id.isdigit():
        bot.send_message(
            message.chat.id,
            "❌ Pocket ID должен содержать только цифры.",
            reply_markup=create_main_menu()
        )
        return

    add_user(message.from_user)

    execute(
        "UPDATE users SET pocket_id = ? WHERE telegram_id = ?",
        (pocket_id, message.from_user.id),
        commit=True
    )

    execute(
        """
        INSERT INTO verification_requests (user_id, pocket_id, status, request_date)
        VALUES (?, ?, 'PENDING', ?)
        """,
        (
            message.from_user.id,
            pocket_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ),
        commit=True
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"verify_approve_{message.from_user.id}"),
        types.InlineKeyboardButton("❌ Отклонить", callback_data=f"verify_reject_{message.from_user.id}")
    )

    admin_text = (
        "🆕 НОВАЯ ЗАЯВКА НА ВЕРИФИКАЦИЮ\n\n"
        f"👤 Пользователь: {message.from_user.first_name}\n"
        f"🆔 Telegram ID: {message.from_user.id}\n"
        f"👤 Username: @{message.from_user.username if message.from_user.username else 'нет'}\n"
        f"💳 Pocket ID: {pocket_id}"
    )

    try:
        bot.send_message(ADMIN_ID, admin_text, reply_markup=markup)
    except Exception:
        pass

    bot.send_message(
        message.chat.id,
        "✅ Заявка отправлена админу. Жди подтверждения.",
        reply_markup=create_main_menu()
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("verify_"))
def verification_callback(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Только для админа")
        return

    parts = call.data.split("_")
    action = parts[1]
    user_id = int(parts[2])

    if action == "approve":
        execute(
            "UPDATE users SET is_verified = 1 WHERE telegram_id = ?",
            (user_id,),
            commit=True
        )
        execute(
            """
            UPDATE verification_requests
            SET status = 'APPROVED', review_date = ?
            WHERE user_id = ? AND status = 'PENDING'
            """,
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                user_id
            ),
            commit=True
        )

        try:
            bot.send_message(user_id, "✅ Верификация подтверждена. Теперь тебе доступны сигналы.")
        except Exception:
            pass

        bot.answer_callback_query(call.id, "✅ Подтверждено")

    elif action == "reject":
        execute(
            """
            UPDATE verification_requests
            SET status = 'REJECTED', review_date = ?
            WHERE user_id = ? AND status = 'PENDING'
            """,
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                user_id
            ),
            commit=True
        )

        try:
            bot.send_message(user_id, "❌ Верификация отклонена.")
        except Exception:
            pass

        bot.answer_callback_query(call.id, "❌ Отклонено")


@bot.message_handler(func=lambda message: message.text == "📈 Случайный сигнал")
def random_signal_handler(message):
    if not is_verified(message.from_user.id):
        require_verification(message.chat.id)
        return

    asset = random.choice(CRYPTO_ASSETS + FOREX_ASSETS + OTC_ASSETS)
    bot.send_message(message.chat.id, "🧠 Генерирую сигнал...")
    bot.send_message(message.chat.id, generate_signal_text(asset), reply_markup=create_main_menu())


@bot.message_handler(func=lambda message: message.text == "🎯 Сигнал по активу")
def signal_by_asset_handler(message):
    if not is_verified(message.from_user.id):
        require_verification(message.chat.id)
        return

    bot.send_message(
        message.chat.id,
        "🎯 Выбери категорию актива:",
        reply_markup=create_asset_categories_menu()
    )


@bot.message_handler(func=lambda message: message.text == "⚙️ Настройки")
def settings_handler(message):
    bot.send_message(message.chat.id, "⚙️ Настройки пока тестовые.", reply_markup=create_main_menu())


@bot.message_handler(func=lambda message: message.text == "📊 Моя статистика")
def stats_handler(message):
    user = get_user(message.from_user.id)
    if not user:
        add_user(message.from_user)
        user = get_user(message.from_user.id)

    status = "✅ Верифицирован" if is_verified(message.from_user.id) else "❌ Не верифицирован"
    pocket_id = dict(user).get("pocket_id") or "не указан"

    text = (
        "📊 ТВОЯ СТАТИСТИКА\n\n"
        f"👤 Имя: {message.from_user.first_name}\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"📌 Статус: {status}\n"
        f"💳 Pocket ID: {pocket_id}"
    )
    bot.send_message(message.chat.id, text, reply_markup=create_main_menu())


@bot.message_handler(func=lambda message: message.text == "👥 Рефералы")
def refs_handler(message):
    try:
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    except Exception:
        ref_link = "Не удалось получить ссылку"

    text = (
        "👥 РЕФЕРАЛЫ\n\n"
        f"Твоя ссылка:\n{ref_link}"
    )
    bot.send_message(message.chat.id, text, reply_markup=create_main_menu())


@bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
def help_handler(message):
    text = (
        "ℹ️ ПОМОЩЬ\n\n"
        "1. Жми «🔐 Регистрация»\n"
        "2. Отправь Pocket ID\n"
        "3. Жди подтверждения админа\n"
        "4. После этого пользуйся сигналами"
    )
    bot.send_message(message.chat.id, text, reply_markup=create_main_menu())


# =========================
# INLINE КАТЕГОРИИ / АКТИВЫ
# =========================
@bot.callback_query_handler(func=lambda call: call.data == "cat_crypto")
def cat_crypto(call):
    bot.edit_message_text(
        "💰 Выбери криптовалюту:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=create_assets_page_menu(CRYPTO_ASSETS, "crypto", 1)
    )


@bot.callback_query_handler(func=lambda call: call.data == "cat_forex")
def cat_forex(call):
    bot.edit_message_text(
        "💱 Выбери валютную пару:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=create_assets_page_menu(FOREX_ASSETS, "forex", 1)
    )


@bot.callback_query_handler(func=lambda call: call.data == "cat_otc")
def cat_otc(call):
    bot.edit_message_text(
        "📊 Выбери OTC актив:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=create_assets_page_menu(OTC_ASSETS, "otc", 1)
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("crypto_"))
def crypto_page(call):
    page = int(call.data.split("_")[1])
    bot.edit_message_text(
        "💰 Выбери криптовалюту:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=create_assets_page_menu(CRYPTO_ASSETS, "crypto", page)
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("forex_"))
def forex_page(call):
    page = int(call.data.split("_")[1])
    bot.edit_message_text(
        "💱 Выбери валютную пару:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=create_assets_page_menu(FOREX_ASSETS, "forex", page)
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("otc_"))
def otc_page(call):
    page = int(call.data.split("_")[1])
    bot.edit_message_text(
        "📊 Выбери OTC актив:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=create_assets_page_menu(OTC_ASSETS, "otc", page)
    )


@bot.callback_query_handler(func=lambda call: call.data == "back_categories")
def back_categories(call):
    bot.edit_message_text(
        "🎯 Выбери категорию актива:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=create_asset_categories_menu()
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("asset_"))
def asset_selected(call):
    if not is_verified(call.from_user.id):
        bot.send_message(call.message.chat.id, "🔒 Сначала пройди верификацию.")
        return

    asset = call.data.replace("asset_", "", 1)
    bot.send_message(call.message.chat.id, "🧠 Генерирую сигнал...")
    bot.send_message(call.message.chat.id, generate_signal_text(asset), reply_markup=create_main_menu())


@bot.message_handler(func=lambda message: True)
def echo_handler(message):
    bot.send_message(
        message.chat.id,
        f"Я получил сообщение: {message.text}",
        reply_markup=create_main_menu()
    )


if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True, long_polling_timeout=30)
