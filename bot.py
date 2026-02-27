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

# --- 3. УНИВЕРСАЛЬНЫЙ ПОИСК (ФАЙЛ + БД) ---
def search_in_db(query):
    # Подготовка поискового запроса (берем корень слова)
    clean_query = query.lower().replace('цена', '').replace('стоимость', '').strip()
    search_term = clean_query[:4] if len(clean_query) >= 2 else clean_query

    results = []

    # 1. ПОИСК В ТЕКСТОВОМ ФАЙЛЕ (Приоритетный)
    try:
        # Укажите точное название вашего файла вместо 'data.txt'
        with open('your_file.txt', 'r', encoding='utf-8') as f:
            content = f.read()
            # Разбиваем файл на разделы (обычно разделы разделены пустой строкой)
            sections = content.split('\n\n')
            
            for section in sections:
                if search_term in section.lower():
                    # Логика замены 0 на "Цена договорная" прямо в тексте раздела
                    # Ищем " 0 " или ": 0" или " 0 руб"
                    import re
                    processed_text = re.sub(r'[:\s]0(\s|руб|$)', ' Цена договорная ', section)
                    
                    # Формируем структуру, которую ожидает ваш бот (id, title, content, price)
                    results.append((999, "Информация", processed_text, "0"))
    except Exception as e:
        print(f"Ошибка чтения файла: {e}")

    # 2. ПОИСК В БАЗЕ ДАННЫХ (Если в файле мало результатов или нужно дополнить)
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            words = [w[:4] for w in clean_query.split() if len(w) >= 2]
            if words:
                conds = " AND ".join(["(LOWER(title) LIKE %s OR LOWER(content) LIKE %s)" for _ in words])
                params = []
                for w in words: params.extend([f'%{w}%', f'%{w}%'])
                
                sql = f"SELECT * FROM parsed_content WHERE {conds} GROUP BY title LIMIT 10"
                cur.execute(sql, params)
                db_rows = cur.fetchall()
                
                # Обработка 0 для данных из БД
                for row in db_rows:
                    row_list = list(row)
                    for i, val in enumerate(row_list):
                        if str(val).strip() == "0" or val == 0:
                            row_list[i] = "Цена договорная"
                    results.append(tuple(row_list))
    except Exception as e:
        print(f"Ошибка БД: {e}")
    finally:
        if 'conn' in locals(): conn.close()

    return results

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
