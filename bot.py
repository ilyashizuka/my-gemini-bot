import telebot
from telebot import types
import pymysql
import os
import re
import google.generativeai as genai

# --- НАСТРОЙКИ ---
TOKEN = os.getenv('BOT_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
DB_PASSWORD = os.getenv('DB_PASSWORD', '807bba4c')

# Настройка Gemini
model = None
if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-pro')
    except: model = None

DB_CONFIG = {
    'host': 'mysql9.hostland.ru',
    'port': 3306,
    'user': 'host1324224_botanik',
    'password': DB_PASSWORD,
    'database': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

bot = telebot.TeleBot(TOKEN)

def get_from_db(query=""):
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            # Если запрос пустой - отдаем всё (для кнопки Прайс)
            if not query:
                sql = "SELECT * FROM parsed_content ORDER BY price DESC LIMIT 30"
                cursor.execute(sql)
            else:
                sql = "SELECT * FROM parsed_content WHERE title LIKE %s OR content LIKE %s"
                cursor.execute(sql, (f'%{query}%', f'%{query}%'))
            return cursor.fetchall()
    except Exception as e:
        print(f"ОШИБКА БАЗЫ: {e}")
        return []
    finally:
        if 'conn' in locals(): conn.close()

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # ВАЖНО: Текст здесь должен СОВПАДАТЬ с текстом в обработчике ниже
    markup.add("🏠 Проживание", "🚣 Лодки")
    markup.add("♨️ Сауна", "🚕 Трансфер")
    markup.add("📜 Весь прайс-лист")
    return markup

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Меню обновлено! Выберите раздел:", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle_all(m):
    text = m.text # Текст кнопки
    
    # 1. Логика распознавания КНОПОК (с учетом смайликов)
    search_term = None
    
    if "Проживание" in text:
        search_term = "дом" # ищем дома по ключевому слову в базе
    elif "Лодки" in text:
        search_term = "лодка"
    elif "Сауна" in text:
        search_term = "сауна"
    elif "Трансфер" in text:
        search_term = "трансфер"
    elif "Весь прайс-лист" in text:
        search_term = "" # пустая строка вернет всё через get_from_db
    
    # 2. Если нажата кнопка — ищем в базе
    if search_term is not None:
        results = get_from_db(search_term)
        if results:
            response = f"📊 *Результаты по разделу {text}:*\n\n"
            for r in results:
                p = f"{r['price']} руб." if r['price'] != "0" else "По запросу"
                response += f"📍 *{r['title']}*\n💰 Цена: {p}\n📞 {r['phone']}\n\n"
            bot.send_message(m.chat.id, response, parse_mode="Markdown")
            return

    # 3. Если это НЕ кнопка — отправляем в Gemini
    if model:
        bot.send_chat_action(m.chat.id, 'typing')
        try:
            prompt = f"Ты помощник базы 'Вуокса-Вирта'. Ответь вежливо на русском: {text}. Тел: +79219930209."
            chat_response = model.generate_content(prompt)
            bot.reply_to(m, chat_response.text)
        except:
            bot.reply_to(m, "Информация не найдена. Попробуйте нажать кнопку меню.")
    else:
        bot.reply_to(m, "Для получения цен нажмите на кнопки меню.")

if __name__ == "__main__":
    bot.infinity_polling()
