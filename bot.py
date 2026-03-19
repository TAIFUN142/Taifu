import os
import telebot

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

bot.remove_webhook()
bot.delete_my_commands()

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "Бот работает, бро!")

bot.infinity_polling(skip_pending=True)
