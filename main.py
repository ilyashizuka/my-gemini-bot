import os
import telebot
import google.generativeai as genai

# Ключи
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

# Настройка
genai.configure(api_key=GOOGLE_API_KEY)
# Используем самую стабильную версию имени модели
model = genai.GenerativeModel('gemini-1.5-flash')

bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        # Прямой вызов генерации
        response = model.generate_content(message.text)
        bot.reply_to(message, response.text if response.text else "Пустой ответ")
    except Exception as e:
        # Если снова 404, бот пришлет это
        bot.reply_to(message, f"Ошибка: {str(e)}")

print("Бот запущен!")
bot.infinity_polling()