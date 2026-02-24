import telebot
from telebot import types
import pymysql
import os
import re
import google.generativeai as genai
from main import parse_site # Импортируем ваш парсер

# --- НАСТРОЙКИ ---
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

# Настройка Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-pro')

# Настройка БД
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

# --- ФУНКЦИИ БАЗЫ ---
def get_from_db(query=""):
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            if query:
                sql = "SELECT * FROM parsed_content WHERE title LIKE %s OR content LIKE %s"
                cursor.execute(sql, (f'%{query}%', f'%{query}%'))
            else:
                sql = "SELECT * FROM parsed_content"
                cursor.execute(sql)
            return cursor.fetchall()
    finally:
        conn.close()

# --- ГЛАВНОЕ МЕНЮ (КНОПКИ) ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🏠 Проживание", "🚣 Лодки")
    markup.add("♨️ Сауна", "🚕 Трансфер")
    markup.add("📜 Весь прайс-лист")
    return markup

# --- КОМАНДЫ ---
@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Привет! Я гид базы отдыха «Вуокса-Вирта». Выберите раздел в меню или просто спросите меня о чем-нибудь.", reply_markup=main_menu())

@bot.message_handler(commands=['update'])
def update(m):
    if m.from_user.id == ADMIN_ID:
        msg = bot.send_message(m.chat.id, "⏳ Начинаю обновление базы данных с сайта...")
        try:
            parse_site() # Вызов функции парсинга из main.py
            bot.edit_message_text("✅ База данных успешно обновлена!", m.chat.id, msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Ошибка при обновлении: {e}", m.chat.id, msg.message_id)
    else:
        bot.reply_to(m, "⛔ У вас нет прав администратора для этой команды.")

# --- ОБРАБОТКА ТЕКСТА ---
@bot.message_handler(func=lambda m: True)
def handle_all(m):
    text = m.text.lower()
    
    # Ключевые слова для поиска в базе
    category_map = {
        "проживание": "дом", "лодки": "лодка", 
        "сауна": "сауна", "баня": "сауна", "трансфер": "трансфер"
    }
    
    search_word = ""
    for k, v in category_map.items():
        if k in text: search_word = v
    
    # 1. Сначала ищем в MySQL (если нажата кнопка или короткий запрос)
    db_results = []
    if "прайс" in text:
        db_results = get_from_db("")
    elif search_word or len(text) < 15:
        db_results = get_from_db(search_word if search_word else text)

    # 2. Если нашли в базе — выдаем точные цены
    if db_results:
        response = "📊 *Информация из нашего прайса:*\n\n"
        for r in db_results[:10]:
            p = f"{r['price']} руб." if r['price'] != "0" else "По запросу"
            response += f"📍 *{r['title']}*\n💰 Цена: {p}\n📞 {r['phone']}\n\n"
        bot.send_message(m.chat.id, response, parse_mode="Markdown")
        
    # 3. Если в базе нет или это сложный вопрос — идем к Gemini
    else:
        bot.send_chat_action(m.chat.id, 'typing')
        try:
            # Даем инструкции нейросети, как себя вести
            prompt = (
                f"Ты официальный помощник базы отдыха 'Вуокса-Вирта'. "
                f"Ответь вежливо на вопрос: {m.text}. "
                f"Если спрашивают цены, которых нет в прайсе, или условия бронирования, "
                f"советуй звонить администратору: +79219930209."
            )
            chat_response = model.generate_content(prompt)
            bot.reply_to(m, chat_response.text)
        except Exception as e:
            bot.reply_to(m, "Я задумался... Пожалуйста, попробуйте еще раз или позвоните нам.")

if __name__ == "__main__":
    print("Бот Вуокса-Вирта запущен...")
    bot.infinity_polling()
