import os
import telebot
import google.generativeai as genai

# 1. Ключи из Render
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

# 2. Настройка Google AI
genai.configure(api_key=GOOGLE_API_KEY)

# Пробуем найти рабочую модель при старте
try:
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    # Пытаемся выбрать 1.5-flash, если нет - берем первую доступную
    model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
    print(f"Использую модель: {model_name}")
    model = genai.GenerativeModel(model_name)
except Exception as e:
    print(f"Ошибка при поиске моделей: {e}")
    model = genai.GenerativeModel('gemini-1.5-flash')

# 3. Бот
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        response = model.generate_content(message.text)
        
        if response.text:
            bot.reply_to(message, response.text)
        else:
            bot.reply_to(message, "Нейросеть выдала пустой ответ.")
            
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")

print("Бот запущен и готов!")
bot.infinity_polling()
