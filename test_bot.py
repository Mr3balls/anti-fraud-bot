import telebot
bot = telebot.TeleBot("8308100428:AAHoex9y8fK8eUqMWHC1KLlJZ81fnLlO0aY")

@bot.message_handler(commands=["start"])
def start(m):
    bot.reply_to(m, "Бот работает ✅")

bot.polling()
