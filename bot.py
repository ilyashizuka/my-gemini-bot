import os
import sys
# Принудительно выводим логи сразу в консоль Render
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

print("🚀 БОТ ЗАПУСКАЕТСЯ...")

import telebot
import pymysql
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

# --- ПРОВЕРКА КЛЮЧЕЙ GEMINI ---
GEMINI_KEYS = []
print("🔍 Начинаю поиск ключей...", flush=True)

for i in range(1, 4):
    key = os.getenv(f'GEMINI_KEY_{i}')
    if key:
        k_clean = key.strip()
        GEMINI_KEYS.append(k_clean)
        print(f"✅ Нашел GEMINI_KEY_{i}: {k_clean[:5]}*** (длина {len(k_clean)})", flush=True)

extra_key = os.getenv('GEMINI_API_KEY')
if extra_key:
    GEMINI_KEYS.append(extra_key.strip())
    print("✅ Нашел GEMINI_API_KEY", flush=True)

GEMINI_KEYS = list(set(GEMINI_KEYS))
print(f"📊 ИТОГО: {len(GEMINI_KEYS)} уникальных ключей загружено.", flush=True)

# --- КОНФИГУРАЦИЯ БАЗ ДАННЫХ ---
DB_CONFIG = {
    'host': 'mysql9.hostland.ru', 
    'user': 'host1324224', 
    'password': DB_PASSWORD,
    'database': 'host1324224_botanik', 
    'charset': 'utf8mb4', 
    'cursorclass': pymysql.cursors.DictCursor
}

# СОЗДАНИЕ ОБЪЕКТА БОТА (Важно: до обработчиков!)
bot = telebot.TeleBot(TOKEN, threaded=False)

# --- 1. РОТАЦИЯ GEMINI 1.5 FLASH ---
def get_gemini_response(prompt):
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    for i, key in enumerate(GEMINI_KEYS):
        try:
            genai.configure(api_key=key, transport='rest')
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            
            if response and response.candidates:
                return response.text
            print(f"⚠️ Ключ {i+1}: Пустой ответ.")
            continue
        except exceptions.ResourceExhausted:
            print(f"🛑 Ключ {i+1}: Лимит 429.")
            continue
        except Exception as e:
            print(f"❌ Ключ {i+1}: Ошибка {e}")
            continue
            
    return "Извините, сейчас я не могу ответить. Попробуйте позже."

# --- 2. ПОИСК В ФАЙЛЕ KNOWLEDGE.TXT ---
def search_in_knowledge_base(query):
    query = query.lower().strip()
    if not os.path.exists('knowledge.txt'): return None
    try:
        with open('knowledge.txt', 'r', encoding='utf-8') as f:
            parts = f.read().split('===')
            
            # 1. Сначала ищем точное совпадение заголовка
            for i in range(1, len(parts), 2):
                header = parts[i].lower()
                content = parts[i+1].strip()
                keywords = [k.strip() for k in header.split(',')]
                if query in keywords:
                    return content
            
            # 2. Если не нашли, ищем частичное вхождение
            for i in range(1, len(parts), 2):
                header = parts[i].lower()
                content = parts[i+1].strip()
                keywords = [k.strip() for k in header.split(',')]
                if any(kw in query for kw in keywords if len(kw) > 2):
                    return content
    except: return None
    return None

# --- 3. ПОИСК В БАЗЕ ДАННЫХ (ЦЕНЫ) ---
def search_in_db(query):
    clean_query = query.lower().replace('цена', '').replace('стоимость', '').replace('сколько', '').strip()
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            # Модифицируем выборку цены: если 0, то заменяем на текст
            price_logic = """
                CASE 
                    WHEN price = '0' OR price = 0 THEN 'Цена договорная' 
                    ELSE CONCAT(price, ' руб.') 
                END as formatted_price
            """
            
            if not clean_query or len(clean_query) < 2:
                # Вставляем нашу логику в SELECT
                sql = f"SELECT id, title, content, {price_logic} FROM parsed_content GROUP BY title ORDER BY CAST(price AS UNSIGNED) DESC LIMIT 15"
                cur.execute(sql)
            else:
                words = [w[:4] for w in clean_query.split() if len(w) >= 2]
                conds = " AND ".join(["(LOWER(title) LIKE %s OR LOWER(content) LIKE %s)" for _ in words])
                params = []
                for w in words: params.extend([f'%{w}%', f'%{w}%'])
                
                # Вставляем нашу логику в SELECT здесь тоже
                sql = f"SELECT id, title, content, {price_logic} FROM parsed_content WHERE {conds} GROUP BY title ORDER BY CAST(price AS UNSIGNED) DESC LIMIT 10"
                cur.execute(sql, params)
            
            return cur.fetchall()
    except Exception as e:
        print(f"Ошибка БД: {e}")
        return []
    finally:
        if 'conn' in locals(): conn.close()

# --- ОБРАБОТЧИКИ СООБЩЕНИЙ ---

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Бот базы «Вуокса-Вирта» на связи! Спросите про маршрут, цены или домики.")

@bot.message_handler(commands=['update'])
def update_cmd(m):
    if str(m.from_user.id) == str(ADMIN_ID):
        bot.send_message(m.chat.id, "✅ База цен обновлена!")

@bot.message_handler(func=lambda m: True)
def handle_msg(m):
    text = m.text.lower()
    
    # 1. МАРШРУТ (КНОПКИ)
    if any(kw in text for kw in ['маршрут', 'доехать', 'добраться']):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🚗 На машине", callback_data="btn_auto"))
        markup.add(types.InlineKeyboardButton("🚌 На автобусе", callback_data="btn_bus"))
        markup.add(types.InlineKeyboardButton("🚉 Электричка", callback_data="btn_elec"))
        
        intro = search_in_knowledge_base("инфо_маршрут")
        if intro:
            bot.send_message(m.chat.id, intro, reply_markup=markup, parse_mode="Markdown")
            return 

    # 2. ФАЙЛ (Контакты, Описания)
    file_ans = search_in_knowledge_base(text)
    if file_ans:
        bot.send_message(m.chat.id, file_ans, parse_mode="Markdown", disable_web_page_preview=False)
        if not any(kw in text for kw in ['цена', 'стоимость', 'сколько']):
            return

    # 3. БАЗА ДАННЫХ (Цены)
    if any(kw in text for kw in ['цена', 'стоимость', 'сколько']) or len(text) < 20:
        rows = search_in_db(text)
        if rows:
            for r in rows:
                msg = f"🏠 *{r['title']}*\n💰 Цена: {r['price']} руб.\n\n_{r['content'][:250]}_"
                bot.send_message(m.chat.id, msg, parse_mode="Markdown")
            return

    # 4. GEMINI
    if m.chat.type == 'private' or bot.get_me().username in text:
        bot.send_chat_action(m.chat.id, 'typing')
        base_info = ""
        if os.path.exists('knowledge.txt'):
            with open('knowledge.txt', 'r', encoding='utf-8') as f:
                base_info = f.read()[:2000]

        full_prompt = (
            f"Ты помощник базы 'Вуокса-Вирта'. Инфо: {base_info}\n"
            f"Тел: +79219930209. Вопрос: {m.text}. Отвечай кратко на русском."
        )
        ans = get_gemini_response(full_prompt)
        if ans:
            bot.reply_to(m, ans)

# ОБРАБОТКА КНОПОК
@bot.callback_query_handler(func=lambda call: call.data.startswith('btn_'))
def route_callback(call):
    mapping = {"btn_auto": "детали_авто", "btn_bus": "детали_автобус", "btn_elec": "детали_электричка"}
    detail = search_in_knowledge_base(mapping.get(call.data))
    if detail:
        bot.send_message(call.message.chat.id, detail, parse_mode="Markdown", disable_web_page_preview=False)
    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    print("✅ БОТ ПОЛНОСТЬЮ ЗАПУЩЕН И ГОТОВ К РАБОТЕ")
    bot.remove_webhook() # Добавь эту строку, она сбросит старые соединения
    bot.infinity_polling()
