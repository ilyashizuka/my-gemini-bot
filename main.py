import os
import telebot
import google.generativeai as genai

# Ключи из Render
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

# Настройка новой модели 2.0
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('models/gemini-1.5-flash')

bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        # Запрос к нейросети
        response = model.generate_content(message.text)
        
        if response.text:
            bot.reply_to(message, response.text)
        else:
            bot.reply_to(message, "Нейросеть выдала пустой ответ.")
            
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")

print("Бот запущен на модели 2.0!")
bot.infinity_polling()
