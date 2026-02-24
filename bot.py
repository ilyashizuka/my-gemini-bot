import telebot
from telebot import types
import pymysql
import os
import re
import google.generativeai as genai

# --- КОНФИГ ---
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
DB_PASSWORD = os.getenv('DB_PASSWORD', '807bba4c')

# Настройка Gemini
if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-pro')
    except:
        model = None
else:
    model = None

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
            if query:
                sql = "SELECT * FROM parsed_content WHERE title LIKE %s OR content LIKE %s"
                cursor.execute(sql, (f'%{query}%', f'%{query}%'))
            else:
                sql = "SELECT * FROM parsed_content LIMIT 15"
            res = cursor.fetchall()
            conn.close()
            return res
    except Exception as e:
        print(f"ОШИБКА БАЗЫ: {e}")
        return []

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🏠 Проживание", "🚣 Лодки")
    markup.add("♨️ Сауна", "🚕 Трансфер")
    markup.add("📜 Весь прайс")
    return markup

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Привет! Я гид базы «Вуокса-Вирта». Нажмите кнопку или спросите меня о чем угодно.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle_all(m):
    text = m.text.lower()
    
    # Сначала проверяем базу (кнопки или ключевые слова)
    search_query = ""
    if "проживание" in text or "дом" in text: search_query = "дом"
    elif "лодки" in text or "лодк" in text: search_query = "лодка"
    elif "сауна" in text or "баня" in text: search_query = "сауна"
    elif "трансфер" in text: search_query = "трансфер"
    elif "прайс" in text: search_query = ""
    
    # Если это короткое сообщение или кнопка — ищем в MySQL
    if search_query or len(text) < 15:
        results = get_from_db(search_query if search_query else text)
        if results:
            response = "📊 *Информация из прайса:*\n\n"
            for r in results[:8]:
                p = f"{r['price']} руб." if r['price'] != "0" else "По запросу"
                response += f"📍 *{r['title']}*\n💰 Цена: {p}\n📞 {r['phone']}\n\n"
            bot.send_message(m.chat.id, response, parse_mode="Markdown")
            return

    # Если в базе не нашли или это сложный вопрос — идем к Gemini
    if model:
        bot.send_chat_action(m.chat.id, 'typing')
        try:
            prompt = f"Ты помощник базы 'Вуокса-Вирта'. Ответь вежливо: {m.text}. Телефон базы: +79219930209."
            chat_response = model.generate_content(prompt)
            bot.reply_to(m, chat_response.text)
        except Exception as e:
            print(f"ОШИБКА GEMINI: {e}")
            bot.reply_to(m, "Нейросеть временно недоступна. Пожалуйста, используйте кнопки меню.")
    else:
        bot.reply_to(m, "Для получения информации воспользуйтесь кнопками ниже.")

if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
