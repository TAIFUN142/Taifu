import os
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

bot.remove_webhook()

@bot.message_handler(commands=['start'])
def start_message(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("📈 Случайный сигнал")
    btn2 = types.KeyboardButton("🎯 Сигнал по активу")
    btn3 = types.KeyboardButton("⚙️ Настройки")
    btn4 = types.KeyboardButton("📊 Моя статистика")
    btn5 = types.KeyboardButton("👥 Рефералы")
    btn6 = types.KeyboardButton("ℹ️ Помощь")
    btn7 = types.KeyboardButton("🔐 Регистрация")

    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5, btn6)
    markup.add(btn7)

    bot.send_message(message.chat.id, "Бот работает, бро!", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def buttons(message):
    if message.text == "📈 Случайный сигнал":
        bot.send_message(message.chat.id, "Случайный сигнал: BUY")
    elif message.text == "🎯 Сигнал по активу":
        bot.send_message(message.chat.id, "Напиши название актива, бро.")
    elif message.text == "⚙️ Настройки":
        bot.send_message(message.chat.id, "Раздел настроек.")
    elif message.text == "📊 Моя статистика":
        bot.send_message(message.chat.id, "Твоя статистика пока пустая.")
    elif message.text == "👥 Рефералы":
        bot.send_message(message.chat.id, "Раздел рефералов.")
    elif message.text == "ℹ️ Помощь":
        bot.send_message(message.chat.id, "Раздел помощи.")
    elif message.text == "🔐 Регистрация":
        bot.send_message(message.chat.id, "Раздел регистрации.")
    else:
        bot.send_message(message.chat.id, "Я получил сообщение: " + message.text)

bot.infinity_polling(skip_pending=True)
