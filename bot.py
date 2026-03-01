import os
import telebot
from gemini_handler import get_ai_answer

# Достаем токен из секретов Render
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    # Просто запрашиваем ответ у модуля Gemini
    response = get_ai_answer(message.text)
    bot.send_message(message.chat.id, response)

if __name__ == "__main__":
    print("Бот успешно запущен на Render...")
    bot.polling(none_stop=True)
