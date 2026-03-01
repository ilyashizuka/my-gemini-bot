import os
import telebot
# Импортируем функцию из второго файла
from gemini_handler import get_ai_answer 

# Берем токен из секретов Render
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    print("Ошибка: TELEGRAM_BOT_TOKEN не найден!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    # ШАГ 1: Просто пробрасываем текст в Gemini и ждем ответ
    # Функция сама переберет 3 ключа внутри себя
    ai_response = get_ai_answer(message.text)
    
    # Отправляем результат пользователю
    bot.send_message(message.chat.id, ai_response)

if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)
