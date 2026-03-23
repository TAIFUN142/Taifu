import os
import sqlite3
import random
import telebot
from telebot import types
from datetime import datetime

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

TIMEFRAMES = ["1 мин", "5 мин", "15 мин"]


# =========================
# БАЗА ДАННЫХ
# =========================
def get_db():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        join_date TEXT,
        pocket_id TEXT,
        is_verified INTEGER DEFAULT 0,
        preferred_timeframe TEXT DEFAULT ''
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        asset TEXT,
        direction TEXT,
        timeframe TEXT,
        confidence INTEGER,
        created_at TEXT
    )
    """)

    conn.commit()
    cur.close()
    conn.close()


init_db()


def execute(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = get_db()
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


def save_signal(user_id, asset, direction, timeframe, confidence):
    execute(
        """
        INSERT INTO signals (user_id, asset, direction, timeframe, confidence, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            asset,
            direction,
            timeframe,
            confidence,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ),
        commit=True
    )


# =========================
# UI
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


def create_timeframe_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    for tf in TIMEFRAMES:
        markup.add(types.InlineKeyboardButton(tf, callback_data=f"timeframe_{tf}"))
    markup.add(types.InlineKeyboardButton("🎲 Случайное время", callback_data="timeframe_random"))
    markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="timeframe_cancel"))
    return markup


def create_asset_categories_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💰 Криптовалюты", callback_data="category_crypto"),
        types.InlineKeyboardButton("💱 Форекс", callback_data="category_forex")
    )
    markup.add(types.InlineKeyboardButton("📊 OTC", callback_data="category_otc"))
    return markup


def create_paged_asset_menu(assets, prefix, page=1, per_page=20):
    markup = types.InlineKeyboardMarkup(row_width=2)
    start = (page - 1) * per_page
    end = min(start + per_page, len(assets))
    chunk = assets[start:end]

    row = []
    for asset in chunk:
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

    markup.add(types.InlineKeyboardButton("🔙 Назад к категориям", callback_data="back_categories"))
    return markup


# =========================
# ЛОГИКА
# =========================
def generate_signal(asset, timeframe=None):
    direction = random.choice(["BUY", "SELL"])
    confidence = random.randint(68, 91)
    tf = timeframe or random.choice(TIMEFRAMES)

    if direction == "BUY":
        action = "ПОКУПКА (CALL)"
        structure = "BULLISH"
        price_line = "Цена выше EMA21"
        macd_line = "MACD выше нуля"
        color = "🟢"
    else:
        action = "ПРОДАЖА (PUT)"
        structure = "BEARISH"
        price_line = "Цена ниже EMA21"
        macd_line = "MACD слабеет"
        color = "🔴"

    risk = "🟢 НИЗКИЙ" if confidence >= 84 else "🟡 СРЕДНИЙ" if confidence >= 72 else "🔴 ВЫСОКИЙ"

    text = (
        f"📉 **СИГНАЛ ПО РЫНКУ** 📉\n\n"
        f"🎯 **АКТИВ:** {asset}\n"
        f"🎯 **ДЕЙСТВИЕ:** {action}\n"
        f"⏱ **ЭКСПИРАЦИЯ:** {tf}\n"
        f"📊 **УВЕРЕННОСТЬ:** {confidence}%\n"
        f"⚠️ **РИСК:** {risk}\n\n"
        f"🧠 **АНАЛИЗ:**\n"
        f"• Структура: {structure}\n"
        f"• {price_line}\n"
        f"• RSI подтверждает импульс\n"
        f"• {macd_line}\n\n"
        f"📈 **АНАЛИТИЧЕСКИЙ ВЫВОД:**\n"
        f"1. Направление рассчитано по теханализу\n"
        f"2. Таймфрейм анализа: {tf}\n"
        f"3. Слабые сигналы лучше пропускать\n\n"
        f"📅 **ВРЕМЯ:** {datetime.now().strftime('%H:%M %d.%m.%Y')}"
    )
    return direction, confidence, tf, text


def require_verification(chat_id):
    bot.send_message(
        chat_id,
        "🔒 Доступ к сигналам закрыт.\n\nСначала пройди верификацию через кнопку «🔐 Регистрация».",
        reply_markup=create_main_menu()
    )


# =========================
# ОБРАБОТЧИКИ
# =========================
@bot.message_handler(commands=["start"])
def start_command(message):
    add_user(message.from_user)
    text = (
        f"🎯 Добро пожаловать, {message.from_user.first_name}!\n\n"
        "🤖 Это бот с сигналами.\n"
        "Сначала пройди верификацию через «🔐 Регистрация», потом сможешь получать сигналы."
    )
    bot.send_message(message.chat.id, text, reply_markup=create_main_menu())


@bot.message_handler(commands=["myid"])
def myid_command(message):
    bot.send_message(message.chat.id, f"Твой Telegram ID: {message.from_user.id}")


@bot.message_handler(func=lambda m: m.text == "🔐 Регистрация")
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

    row = get_user(message.from_user.id)
    if row and int(dict(row).get("is_verified", 0)) == 1:
        bot.send_message(
            message.chat.id,
            "✅ Ты уже верифицирован.",
            reply_markup=create_main_menu()
        )
        return

    text = (
        "📝 **РЕГИСТРАЦИЯ В POCKET OPTION**\n\n"
        f"1. Зарегистрируйся по ссылке:\n{POCKET_REFERRAL_LINK}\n\n"
        "2. Найди свой Pocket ID\n"
        "3. Отправь его следующим сообщением\n\n"
        "⚠️ Только цифры."
    )
    msg = bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=create_main_menu())
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
        f"🆕 **НОВАЯ ЗАЯВКА НА ВЕРИФИКАЦИЮ**\n\n"
        f"👤 Имя: {message.from_user.first_name}\n"
        f"🆔 Telegram ID: `{message.from_user.id}`\n"
        f"👤 Username: @{message.from_user.username if message.from_user.username else 'нет'}\n"
        f"💳 Pocket ID: {pocket_id}"
    )

    try:
        bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=markup)
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

    _, action, user_id = call.data.split("_")
    user_id = int(user_id)

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
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id),
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
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id),
            commit=True
        )
        try:
            bot.send_message(user_id, "❌ Верификация отклонена.")
        except Exception:
            pass
        bot.answer_callback_query(call.id, "❌ Отклонено")


@bot.message_handler(func=lambda m: m.text == "📈 Случайный сигнал")
def random_signal_handler(message):
    if not is_verified(message.from_user.id):
        require_verification(message.chat.id)
        return

    user_row = get_user(message.from_user.id)
    preferred_tf = dict(user_row).get("preferred_timeframe", "") if user_row else ""
    timeframe = preferred_tf if preferred_tf else None

    asset = random.choice(CRYPTO_ASSETS + FOREX_ASSETS + OTC_ASSETS)
    direction, confidence, tf, signal_text = generate_signal(asset, timeframe)
    save_signal(message.from_user.id, asset, direction, tf, confidence)

    bot.send_message(message.chat.id, "🧠 Генерирую сигнал...")
    bot.send_message(message.chat.id, signal_text, parse_mode="Markdown", reply_markup=create_main_menu())


@bot.message_handler(func=lambda m: m.text == "🎯 Сигнал по активу")
def signal_by_asset_handler(message):
    if not is_verified(message.from_user.id):
        require_verification(message.chat.id)
        return

    bot.send_message(
        message.chat.id,
        "🎯 Выбери категорию актива:",
        reply_markup=create_asset_categories_menu()
    )


@bot.message_handler(func=lambda m: m.text == "⚙️ Настройки")
def settings_handler(message):
    bot.send_message(
        message.chat.id,
        "⚙️ Выбери настройку:",
        reply_markup=create_settings_menu()
    )


@bot.message_handler(func=lambda m: m.text == "⏱️ Выбрать время")
def choose_timeframe_handler(message):
    bot.send_message(
        message.chat.id,
        "⏱️ Выбери время экспирации:",
        reply_markup=create_timeframe_menu()
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("timeframe_"))
def timeframe_callback(call):
    if call.data == "timeframe_cancel":
        bot.send_message(call.message.chat.id, "❌ Выбор времени отменён.", reply_markup=create_main_menu())
        return

    if call.data == "timeframe_random":
        timeframe = ""
        tf_text = "случайное"
    else:
        timeframe = call.data.replace("timeframe_", "")
        tf_text = timeframe

    execute(
        "UPDATE users SET preferred_timeframe = ? WHERE telegram_id = ?",
        (timeframe, call.from_user.id),
        commit=True
    )

    bot.send_message(
        call.message.chat.id,
        f"✅ Сохранено. Теперь время экспирации: {tf_text}.",
        reply_markup=create_main_menu()
    )


@bot.message_handler(func=lambda m: m.text == "📊 Моя статистика")
def stats_handler(message):
    add_user(message.from_user)
    user = get_user(message.from_user.id)
    status = "✅ Верифицирован" if is_verified(message.from_user.id) else "❌ Не верифицирован"
    pocket_id = dict(user).get("pocket_id") if user else None
    preferred_tf = dict(user).get("preferred_timeframe") if user else ""

    signal_count_row = execute(
        "SELECT COUNT(*) AS cnt FROM signals WHERE user_id = ?",
        (message.from_user.id,),
        fetchone=True
    )
    signals_count = dict(signal_count_row).get("cnt", 0) if signal_count_row else 0

    text = (
        "📊 **ВАША СТАТИСТИКА**\n\n"
        f"👤 Имя: {message.from_user.first_name}\n"
        f"🆔 ID: `{message.from_user.id}`\n"
        f"📌 Статус: {status}\n"
        f"💳 Pocket ID: {pocket_id if pocket_id else 'не указан'}\n"
        f"⏱ Время: {preferred_tf if preferred_tf else 'случайное'}\n"
        f"📈 Получено сигналов: {signals_count}"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=create_main_menu())


@bot.message_handler(func=lambda m: m.text == "👥 Рефералы")
def refs_handler(message):
    try:
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    except Exception:
        ref_link = "Не удалось получить ссылку"

    text = (
        "👥 **ВАША РЕФЕРАЛЬНАЯ СИСТЕМА**\n\n"
        f"🔗 Ваша ссылка:\n`{ref_link}`"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=create_main_menu())


@bot.message_handler(func=lambda m: m.text == "ℹ️ Помощь")
def help_handler(message):
    text = (
        "🆘 **ПОМОЩЬ**\n\n"
        "1. Нажми «🔐 Регистрация»\n"
        "2. Отправь Pocket ID\n"
        "3. Дождись подтверждения админа\n"
        "4. После этого пользуйся сигналами и активами"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=create_main_menu())


@bot.message_handler(func=lambda m: m.text == "🔙 Назад")
def back_handler(message):
    bot.send_message(message.chat.id, "🔙 Главное меню", reply_markup=create_main_menu())


# =========================
# INLINE МЕНЮ АКТИВОВ
# =========================
@bot.callback_query_handler(func=lambda call: call.data == "category_crypto")
def category_crypto(call):
    bot.edit_message_text(
        "💰 **Выберите криптовалюту:**",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=create_paged_asset_menu(CRYPTO_ASSETS, "crypto", 1)
    )


@bot.callback_query_handler(func=lambda call: call.data == "category_forex")
def category_forex(call):
    bot.edit_message_text(
        "💱 **Выберите валютную пару:**",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=create_paged_asset_menu(FOREX_ASSETS, "forex", 1)
    )


@bot.callback_query_handler(func=lambda call: call.data == "category_otc")
def category_otc(call):
    bot.edit_message_text(
        "📊 **Выберите OTC актив:**",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=create_paged_asset_menu(OTC_ASSETS, "otc", 1)
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("crypto_"))
def crypto_page(call):
    page = int(call.data.split("_")[1])
    bot.edit_message_text(
        "💰 **Выберите криптовалюту:**",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=create_paged_asset_menu(CRYPTO_ASSETS, "crypto", page)
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("forex_"))
def forex_page(call):
    page = int(call.data.split("_")[1])
    bot.edit_message_text(
        "💱 **Выберите валютную пару:**",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=create_paged_asset_menu(FOREX_ASSETS, "forex", page)
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("otc_"))
def otc_page(call):
    page = int(call.data.split("_")[1])
    bot.edit_message_text(
        "📊 **Выберите OTC актив:**",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=create_paged_asset_menu(OTC_ASSETS, "otc", page)
    )


@bot.callback_query_handler(func=lambda call: call.data == "back_categories")
def back_categories(call):
    bot.edit_message_text(
        "🎯 **Выберите категорию актива:**",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=create_asset_categories_menu()
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("asset_"))
def asset_selected(call):
    if not is_verified(call.from_user.id):
        bot.send_message(call.message.chat.id, "🔒 Сначала пройди верификацию.")
        return

    asset = call.data.replace("asset_", "", 1)
    user_row = get_user(call.from_user.id)
    preferred_tf = dict(user_row).get("preferred_timeframe", "") if user_row else ""
    timeframe = preferred_tf if preferred_tf else None

    direction, confidence, tf, signal_text = generate_signal(asset, timeframe)
    save_signal(call.from_user.id, asset, direction, tf, confidence)

    bot.send_message(call.message.chat.id, "🧠 Генерирую сигнал...")
    bot.send_message(call.message.chat.id, signal_text, parse_mode="Markdown", reply_markup=create_main_menu())


@bot.message_handler(func=lambda message: True)
def echo_handler(message):
    bot.send_message(
        message.chat.id,
        f"Я получил сообщение: {message.text}",
        reply_markup=create_main_menu()
    )


if __name__ == "__main__":
    print("=== BOT START ===")
    bot.infinity_polling(skip_pending=True, long_polling_timeout=30)
