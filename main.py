import os
import telebot
import google.generativeai as genai

# 1. Получаем ключи из настроек Render
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

# 2. Настраиваем нейросеть Gemini (исправленный путь)
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('models/gemini-1.5-flash')

# 3. Запускаем бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        # Статус "печатает..." в Телеграм
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Запрос к нейросети
        response = model.generate_content(message.text)
        
        # Проверка на пустой ответ (цензура Google)
        if response.text:
            bot.reply_to(message, response.text)
        else:
            bot.reply_to(message, "Нейросеть промолчала (возможно, сработали фильтры безопасности).")
        
    except Exception as e:
        # Вывод технической ошибки в чат для отладки
        error_text = str(e)
        bot.reply_to(message, f"Ошибка от Google: {error_text}")
        print(f"Ошибка в логах: {error_text}")

# Сообщение в консоль Render
print("Бот запущен и готов к работе!")

# Бесконечный цикл работы
bot.infinity_polling()
