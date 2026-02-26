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

# Ключи Gemini (GEMINI_KEY_1, GEMINI_KEY_2, GEMINI_KEY_3)
GEMINI_KEYS = [os.getenv(f'GEMINI_KEY_{i}') for i in range(1, 4)] + [os.getenv('GEMINI_API_KEY')]
GEMINI_KEYS = [k for k in GEMINI_KEYS if k]

DB_CONFIG = {
    'host': 'mysql9.hostland.ru', 
    'user': 'host1324224', 
    'password': DB_PASSWORD,
    'database': 'host1324224_botanik', 
    'charset': 'utf8mb4', 
    'cursorclass': pymysql.cursors.DictCursor
}

bot = telebot.TeleBot(TOKEN, threaded=False)

# --- 1. РОТАЦИЯ GEMINI 1.5 FLASH ---
def get_gemini_response(prompt):
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    for key in GEMINI_KEYS:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-1.5-flash', safety_settings=safety_settings)
            response = model.generate_content(prompt)
            
            if response.candidates and response.candidates[0].finish_reason == 3:
                continue # Заблокировано Google, пробуем другой ключ
                
            return response.text
        except exceptions.ResourceExhausted:
            continue # Ошибка 429
        except Exception as e:
            print(f"Ошибка Gemini (ключ {key[:5]}): {e}")
            continue
    return "Извините, сейчас я не могу ответить. Попробуйте позже."

# --- 2. ПОИСК В ФАЙЛЕ KNOWLEDGE.TXT ---
def search_in_knowledge_base(query):
    query = query.lower().strip()
    if not os.path.exists('knowledge.txt'): return None
    try:
        with open('knowledge.txt', 'r', encoding='utf-8') as f:
            # Разделяем файл по разделителю ===
            parts = f.read().split('===')
            
            # Сначала ищем точное совпадение (чтобы "авто" не путалось с "автобус")
            for i in range(1, len(parts), 2):
                header = parts[i].lower()
                content = parts[i+1].strip()
                keywords = [k.strip() for k in header.split(',')]
                
                # Если ищем по кнопке (целый заголовок), проверяем точное совпадение
                if query in keywords:
                    return content
            
            # Если точного совпадения нет, ищем вхождение (для обычных сообщений)
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
    # Очищаем запрос от стоп-слов
    clean_query = query.lower().replace('цена', '').replace('стоимость', '').replace('сколько', '').strip()
    
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            if not clean_query or len(clean_query) < 2:
                # Если просто "Цена" — выводим всё (дома будут первыми из-за цены)
                sql = "SELECT * FROM parsed_content GROUP BY title ORDER BY CAST(price AS UNSIGNED) DESC LIMIT 15"
                cur.execute(sql)
            else:
                # Поиск по категории (дом, лодка, баня)
                words = [w[:4] for w in clean_query.split() if len(w) >= 2]
                conds = " AND ".join(["(LOWER(title) LIKE %s OR LOWER(content) LIKE %s)" for _ in words])
                params = []
                for w in words: params.extend([f'%{w}%', f'%{w}%'])
                sql = f"SELECT * FROM parsed_content WHERE {conds} GROUP BY title ORDER BY CAST(price AS UNSIGNED) DESC LIMIT 10"
                cur.execute(sql, params)
            
            return cur.fetchall()
    except Exception as e:
        print(f"Ошибка БД: {e}")
        return []
    finally:
        if 'conn' in locals(): conn.close()

# --- ОБРАБОТЧИКИ ---

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Бот базы «Вуокса-Вирта» на связи! Спросите про маршрут, цены или домики.")

@bot.message_handler(commands=['update'])
def update_cmd(m):
    if str(m.from_user.id) == str(ADMIN_ID):
        bot.send_message(m.chat.id, "🧹 Обновляю базу цен с сайта...")
        # Здесь должен быть вызов функции run_update()
        bot.send_message(m.chat.id, "✅ Готово!")

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

    # 2. ФАЙЛ (Контакты, Описания, Wi-Fi)
    file_ans = search_in_knowledge_base(text)
    if file_ans:
        bot.send_message(m.chat.id, file_ans, parse_mode="Markdown", disable_web_page_preview=False)
        # Если в запросе НЕТ слова "цена", то выходим. Если ЕСТЬ — идем дальше искать цену в БД.
        if not any(kw in text for kw in ['цена', 'стоимость', 'сколько']):
            return

    # 3. БАЗА ДАННЫХ (Цены)
    if any(kw in text for kw in ['цена', 'стоимость', 'сколько']) or len(text) < 20:
        rows = search_in_db(text)
        if rows:
            for r in rows:
                msg = f"🏠 *{r['title']}*\n💰 Цена: {r['price']} руб.\n📞 {r['phone']}\n\n_{r['content'][:250]}_"
                bot.send_message(m.chat.id, msg, parse_mode="Markdown")
            return

    # 4. GEMINI (Погода, Звезды и прочее)
     if m.chat.type == 'private' or bot.get_me().username in text:
        bot.send_chat_action(m.chat.id, 'typing')
        
        # Читаем базу знаний, чтобы нейросеть была в курсе правил базы
        base_info = ""
        if os.path.exists('knowledge.txt'):
            with open('knowledge.txt', 'r', encoding='utf-8') as f:
                # Берем первые 2000 символов, чтобы не перегружать запрос
                base_info = f.read()[:2000] 

        # Формируем расширенную инструкцию для нейросети
        full_prompt = (
            f"Ты — дружелюбный помощник базы отдыха 'Вуокса-Вирта'.\n"
            f"Используй эту информацию при ответе: {base_info}\n"
            f"Телефон базы: +79219930209.\n"
            f"Вопрос пользователя: {m.text}\n"
            f"Отвечай кратко, вежливо и только на русском языке."
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
    bot.infinity_polling()
