import os
import telebot
from gemini_handler import get_ai_answer

# Используются указанные названия переменных
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')

if not BOT_TOKEN:
    print("Ошибка: TELEGRAM_BOT_TOKEN не найден в переменных Render!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    # Этап 1: Получаем ответ от Gemini
    response = get_ai_answer(message.text)
    bot.send_message(message.chat.id, response)

if __name__ == "__main__":
    print(f"Бот запущен. Админ ID: {ADMIN_ID}")
    bot.polling(none_stop=True)

