import os
import telebot
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread

# --- БЛОК ДЛЯ ПОДДЕРЖКИ ЖИЗНИ (WAKE UP) ---
app = Flask('')

@app.route('/')
def home():
    return "I am alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- ФУНКЦИЯ ПАРСИНГА САЙТА ---
def get_site_info():
    try:
        url = "https://vuoksa-virta.ru"
        # Запрашиваем страницу (тайм-аут 10 сек)
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8' # Указываем кодировку для корректного русского текста
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Удаляем лишний мусор: скрипты и стили
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
            
        # Извлекаем текст
        text = soup.get_text(separator=' ')
        # Очищаем от лишних пробелов и пустых строк
        lines = (line.strip() for line in text.splitlines())
        clean_text = ' '.join(chunk for chunk in lines if chunk)
        
        # Берем первые 4000 символов, чтобы не превысить лимит контекста
        return clean_text[:4000]
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return "Информация о компании временно недоступна."

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
        
        # Получаем свежие данные с сайта
        context = get_site_info()
        
        # Формируем инструкцию для нейросети
        prompt = (
            f"Ты — официальный помощник базы отдыха 'Вуокса-Вирта'.\n"
            f"Используй следующую информацию с сайта для ответа: {context}\n\n"
            f"Вопрос клиента: {message.text}\n"
            f"Отвечай вежливо и кратко на основе предоставленных данных."
        )
        
        # Запрос к Gemini
        response = model.generate_content(prompt)
        
        if response.text:
            bot.send_message(message.chat.id, response.text)
        else:
            bot.send_message(message.chat.id, "К сожалению, я не смог найти ответ на этот вопрос.")
            
    except Exception as e:
        error_text = str(e)
        bot.send_message(message.chat.id, f"Произошла ошибка: {error_text}")
        print(f"Ошибка в боте: {error_text}")

# ЗАПУСК
if __name__ == "__main__":
    print("Запускаю веб-сервер Flask...")
    keep_alive()
    
    print("Бот Вуокса-Вирта запущен!")
    bot.infinity_polling()
