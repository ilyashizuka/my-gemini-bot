import telebot
from telebot import types
import pymysql
import os
import re
import requests
from bs4 import BeautifulSoup

# --- КОНФИГ ---
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
DB_CONFIG = {
    'host': 'mysql9.hostland.ru',
    'port': 3306,
    'user': 'host1324224_botanik',
    'password': os.getenv('DB_PASSWORD', '807bba4c'),
    'database': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

bot = telebot.TeleBot(TOKEN)

# --- БАЗА ДАННЫХ ---
def get_from_db(category=None):
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            if category == "homes":
                sql = "SELECT * FROM parsed_content WHERE price > 400 AND title NOT LIKE '%Лодка%' AND title NOT LIKE '%Сауна%'"
            elif category == "boats":
                sql = "SELECT * FROM parsed_content WHERE title LIKE '%Лодка%'"
            elif category == "sauna":
                sql = "SELECT * FROM parsed_content WHERE title LIKE '%Сауна%'"
            else:
                sql = "SELECT * FROM parsed_content"
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        conn.close()

# --- КЛАВИАТУРА ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🏠 Дома / Проживание", "🚣 Прокат лодок")
    markup.add("♨️ Сауна / Баня", "🚕 Трансфер")
    markup.add("📜 Весь прайс-лист")
    return markup

# --- КОМАНДЫ ---
@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Привет! Я бот базы «Вуокса-Вирта». Выберите интересующий раздел:", reply_markup=main_menu())

@bot.message_handler(commands=['update'])
def update(m):
    if m.from_user.id == ADMIN_ID:
        bot.send_message(m.chat.id, "⏳ Обновляю базу... Подождите.")
        # Здесь должен быть ваш вызов функции парсинга run_parser()
        bot.send_message(m.chat.id, "✅ База обновлена!")
    else:
        bot.reply_to(m, "❌ Нет прав.")

# --- ОБРАБОТКА КНОПОК И ТЕКСТА ---
@bot.message_handler(func=lambda m: True)
def handle_all(m):
    text = m.text.lower()
    results = []
    
    if "дома" in text or "проживание" in text:
        results = get_from_db("homes")
    elif "лодок" in text or "лодка" in text:
        results = get_from_db("boats")
    elif "сауна" in text or "баня" in text:
        results = get_from_db("sauna")
    elif "трансфер" in text:
        results = [r for r in get_from_db() if "трансфер" in r['title'].lower()]
    elif "прайс" in text:
        results = get_from_db()
    else:
        # Обычный поиск по слову
        results = [r for r in get_from_db() if text in r['title'].lower()]

    if not results:
        bot.send_message(m.chat.id, "Ничего не найдено. Попробуйте нажать на кнопку меню.")
    else:
        response = ""
        for r in results[:10]:
            p = f"{r['price']} руб." if r['price'] != "0" else "По запросу"
            response += f"📍 *{r['title']}*\n💰 Цена: {p}\n📞 {r['phone']}\n\n"
        
        bot.send_message(m.chat.id, response, parse_mode="Markdown")

if __name__ == "__main__":
    bot.infinity_polling()
