import os
import time
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)


def create_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("📈 Случайный сигнал")
    btn2 = types.KeyboardButton("🎯 Сигнал по активу")
    btn3 = types.KeyboardButton("⚙️ Настройки")
    btn4 = types.KeyboardButton("📊 Моя статистика")
    btn5 = types.KeyboardButton("👥 Рефералы")
    btn6 = types.KeyboardButton("ℹ️ Помощь")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    return markup


@bot.message_handler(commands=["start"])
def start_command(message):
    text = (
        "🤖 Бот работает, бро!\n\n"
        "Жми кнопки ниже или напиши что-нибудь."
    )
    bot.send_message(message.chat.id, text, reply_markup=create_main_menu())


@bot.message_handler(func=lambda message: message.text == "📈 Случайный сигнал")
def random_signal_handler(message):
    signal_text = (
        "📉 СИГНАЛ ПО РЫНКУ 📉\n\n"
        "🎲 Случайный актив\n"
        "🔴 АКТИВ: BTC/USD\n"
        "🎯 ДЕЙСТВИЕ: ПОКУПКА (CALL)\n"
        "⏱ ЭКСПИРАЦИЯ: 1 мин\n"
        "📊 УВЕРЕННОСТЬ: 78%\n"
        "⚠️ РИСК: 🟡 СРЕДНИЙ\n\n"
        "🧠 АНАЛИЗ:\n"
        "• Структура: BULLISH\n"
        "• Цена выше EMA21\n"
        "• RSI подтверждает импульс\n"
        "• MACD выше нуля\n\n"
        "📈 АНАЛИТИЧЕСКИЙ ВЫВОД:\n"
        "1. Направление рассчитано по теханализу\n"
        "2. Таймфрейм анализа: 1 мин\n"
        "3. Слабые сигналы лучше пропускать"
    )
    bot.send_message(message.chat.id, signal_text, reply_markup=create_main_menu())


@bot.message_handler(func=lambda message: message.text == "🎯 Сигнал по активу")
def asset_signal_handler(message):
    bot.send_message(
        message.chat.id,
        "🎯 Напиши актив текстом, например:\nBTC/USD\nETH/USD\nEUR/USD",
        reply_markup=create_main_menu()
    )


@bot.message_handler(func=lambda message: message.text == "⚙️ Настройки")
def settings_handler(message):
    bot.send_message(
        message.chat.id,
        "⚙️ Раздел настроек пока тестовый.",
        reply_markup=create_main_menu()
    )


@bot.message_handler(func=lambda message: message.text == "📊 Моя статистика")
def stats_handler(message):
    bot.send_message(
        message.chat.id,
        "📊 Статистика пока пустая.",
        reply_markup=create_main_menu()
    )


@bot.message_handler(func=lambda message: message.text == "👥 Рефералы")
def refs_handler(message):
    bot.send_message(
        message.chat.id,
        "👥 Раздел рефералов пока тестовый.",
        reply_markup=create_main_menu()
    )


@bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
def help_handler(message):
    bot.send_message(
        message.chat.id,
        "ℹ️ Нажми /start, потом пользуйся кнопками.",
        reply_markup=create_main_menu()
    )


@bot.message_handler(func=lambda message: True)
def echo_handler(message):
    text = (message.text or "").strip().upper()

    if text in ["BTC/USD", "ETH/USD", "EUR/USD", "GBP/USD", "FIL/OTC"]:
        signal_text = (
            f"📉 СИГНАЛ ПО РЫНКУ 📉\n\n"
            f"🎯 Выбранный актив: {text}\n"
            f"🎯 ДЕЙСТВИЕ: ПРОДАЖА (PUT)\n"
            f"⏱ ЭКСПИРАЦИЯ: 1 мин\n"
            f"📊 УВЕРЕННОСТЬ: 74%\n"
            f"⚠️ РИСК: 🟡 СРЕДНИЙ\n\n"
            f"🧠 АНАЛИЗ:\n"
            f"• Структура: BEARISH\n"
            f"• Цена ниже EMA21\n"
            f"• RSI подтверждает импульс\n"
            f"• MACD слабеет"
        )
        bot.send_message(message.chat.id, signal_text, reply_markup=create_main_menu())
    else:
        bot.send_message(
            message.chat.id,
            f"Я получил сообщение: {message.text}",
            reply_markup=create_main_menu()
        )


if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(skip_pending=True)
