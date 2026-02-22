import os
import telebot
import google.generativeai as genai

# 1. Получаем ключи из настроек Render
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

# 2. Настраиваем нейросеть Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 3. Запускаем бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        # Показываем в Телеграм статус "печатает..."
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Отправляем запрос нейросети
        response = model.generate_content(message.text)
        
        # Отправляем ответ пользователю
        bot.reply_to(message, response.text)
        
    except Exception as e:
        # Если что-то пошло не так, бот пришлет текст ошибки прямо в чат
        error_text = str(e)
        bot.reply_to(message, f"Ошибка от Google: {error_text}")
        print(f"Ошибка в логах: {error_text}")

# Сообщение в консоль Render, что всё запустилось
print("Бот успешно запущен и ждет сообщений в Telegram!")

# Запуск бесконечного цикла опроса Телеграм
bot.infinity_polling()
