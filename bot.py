import telebot
import pymysql
import os
import re
import requests
import google.generativeai as genai
from bs4 import BeautifulSoup
from google.api_core import exceptions
from telebot import types

# --- НАСТРОЙКИ ---
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID', '0')
DB_PASSWORD = os.getenv('DB_PASSWORD', '807bba4c')

GEMINI_KEYS = [os.getenv(f'GEMINI_KEY_{i}') for i in range(1, 4)] + [os.getenv('GEMINI_API_KEY')]
GEMINI_KEYS = [k for k in GEMINI_KEYS if k]

DB_CONFIG = {
    'host': 'mysql9.hostland.ru', 'user': 'host1324224', 'password': DB_PASSWORD,
    'database': 'host1324224_botanik', 'charset': 'utf8mb4', 'cursorclass': pymysql.cursors.DictCursor
}

bot = telebot.TeleBot(TOKEN, threaded=False)

# --- ЛОГИКА GEMINI ---
def get_gemini_response(prompt):
    for key in GEMINI_KEYS:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-pro')
            return model.generate_content(prompt).text
        except exceptions.ResourceExhausted: continue
        except: continue
    return None

# --- ПОИСК В ФАЙЛЕ ---
def search_in_knowledge_base(query):
    query = query.lower()
    if not os.path.exists('knowledge.txt'): return None
    try:
        with open('knowledge.txt', 'r', encoding='utf-8') as f:
            parts = f.read().split('===')
            for i in range(1, len(parts), 2):
                if any(kw.strip() in query for kw in parts[i].lower().split(',') if len(kw.strip()) > 2):
                    return parts[i+1].strip()
    except: return None
    return None

# --- ПОИСК В БД ---
def search_in_db(query):
    # Если запрос "цена" или пустой, ищем просто популярные дома
    clean_query = query.replace('цена', '').strip()
    words = [w[:4] for w in (clean_query if clean_query else "дом").split() if len(w) >= 3]
    if not words: return []
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            conds = " AND ".join(["(LOWER(title) LIKE %s OR LOWER(content) LIKE %s)" for _ in words])
            params = []
            for w in words: params.extend([f'%{w}%', f'%{w}%'])
            cur.execute(f"SELECT * FROM parsed_content WHERE {conds} GROUP BY title LIMIT 5", params)
            return cur.fetchall()
    except: return []
    finally:
        if 'conn' in locals(): conn.close()

# --- ОБРАБОТЧИКИ ---

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Бот базы «Вуокса-Вирта» готов! Спросите про цену, маршрут или контакты.")

@bot.message_handler(func=lambda m: True)
def handle_msg(m):
    text = m.text.lower()
    
    # 1. Кнопки маршрута
    if any(kw in text for kw in ['маршрут', 'доехать', 'как добраться', 'как добраться']):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🚗 На машине", callback_data="route_auto"))
        markup.add(types.InlineKeyboardButton("🚂 На поезде", callback_data="route_train"))
        markup.add(types.InlineKeyboardButton("🚉 Электричка", callback_data="route_elec"))
        intro = search_in_knowledge_base("маршрут")
        bot.send_message(m.chat.id, intro, reply_markup=markup, parse_mode="Markdown")
        return

    # 2. Файл (Контакты, Wi-Fi, Правила)
    file_ans = search_in_knowledge_base(text)
    if file_ans:
        bot.send_message(m.chat.id, file_ans, parse_mode="Markdown", disable_web_page_preview=False)
        return

    # 3. База данных (Цены)
    rows = search_in_db(text)
    if rows:
        for r in rows:
            msg = f"🏠 *{r['title']}*\n💰 Цена: {r['price']} руб.\n📞 {r['phone']}\n\n_{r['content'][:250]}_"
            bot.send_message(m.chat.id, msg, parse_mode="Markdown")
        return

    # 4. Gemini
    if m.chat.type == 'private' or bot.get_me().username in text:
        bot.send_chat_action(m.chat.id, 'typing')
        ans = get_gemini_response(f"Ты помощник базы 'Вуокса-Вирта'. Ответь кратко: {m.text}. Тел: +79219930209.")
        if ans: bot.reply_to(m, ans)

@bot.callback_query_handler(func=lambda call: call.data.startswith('route_'))
def route_click(call):
    mapping = {"route_auto": "маршрут_авто", "route_train": "маршрут_поезд", "route_elec": "маршрут_электричка"}
    msg = search_in_knowledge_base(mapping.get(call.data))
    if msg: bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    bot.infinity_polling()
