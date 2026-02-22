import os
import telebot
import google.generativeai as genai

# 1. Загрузка ключей
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

# 2. Настройка Google AI
genai.configure(api_key=GOOGLE_API_KEY)

# Авто-подбор рабочей модели (чтобы не было 404)
try:
    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    # Выбираем 1.5-flash или любую первую доступную
    selected_model = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in models else models[0]
    model = genai.GenerativeModel(selected_model)
    print(f"Выбрана модель: {selected_model}")
except Exception as e:
    print(f"Ошибка при поиске моделей: {e}")
    model = genai.GenerativeModel('gemini-1.5-flash')

# 3. Настройка бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        response = model.generate_content(message.text)
        if response.text:
            bot.reply_to(message, response.text)
        else:
            bot.reply_to(message, "ИИ промолчал (фильтры безопасности).")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")

print("Бот запущен!")
bot.infinity_polling()
