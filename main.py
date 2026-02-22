import os
import telebot
import google.generativeai as genai

# Берем ключи из настроек Render
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

# Настраиваем ИИ (теперь с правильной моделью!)
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Запускаем бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        # Показываем пользователю, что бот "печатает"
        bot.send_chat_action(message.chat.id, 'typing')
        # Запрос к нейросети
        response = model.generate_content(message.text)
        # Отправка ответа
        bot.reply_to(message, response.text)
       except Exception as e:
        error_text = str(e)
        bot.reply_to(message, f"Ошибка от Google: {error_text}")
        print(f"Ошибка в логах: {error_text}")

print("Бот успешно запущен и ждет сообщений в Telegram!")
bot.infinity_polling()