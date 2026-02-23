import os
import telebot
import google.generativeai as genai
from flask import Flask
from threading import Thread

# --- БЛОК ДЛЯ ПОДДЕРЖКИ ЖИЗНИ (WAKE UP) ---
app = Flask('')

@app.route('/')
def home():
    return "I am alive!"

def run():
    # Render использует порт 8080 по умолчанию для веб-сервисов
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ------------------------------------------

# 1. Загрузка ключей
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

# 2. Настройка Google AI
genai.configure(api_key=GOOGLE_API_KEY)

# Авто-подбор рабочей модели
try:
    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    selected_model = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in models else models[0]
    model = genai.GenerativeModel(selected_model)
    print(f"Выбрана модель: {selected_model}")
except Exception as e:
    print(f"Ошибка при поиске моделей: {e}")
    model = genai.GenerativeModel('models/gemini-1.5-flash')

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

# ЗАПУСК СЕРВЕРА И БОТА
if __name__ == "__main__":
    print("Запускаю веб-сервер для поддержки жизни...")
    keep_alive()  # Запускаем Flask в отдельном потоке
    
    print("Бот запущен!")
    print("Я ЖИВОЙ И СЛУШАЮ ТЕЛЕГРАМ!")
    bot.infinity_polling()
