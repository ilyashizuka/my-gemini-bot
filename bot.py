import os
import sys
import telebot
import pymysql
import re
import requests
import google.generativeai as genai
from telebot import types
from google.api_core import exceptions

# Настройка логов для Render
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# --- НАСТРОЙКИ ---
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID', '0')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_CONFIG = {
    'host': 'mysql9.hostland.ru', 
    'user': 'host1324224', 
    'password': DB_PASSWORD,
    'database': 'host1324224_botanik', 
    'charset': 'utf8mb4', 
    'cursorclass': pymysql.cursors.DictCursor
}

# КЛЮЧИ GEMINI
GEMINI_KEYS = list(set(filter(None, [os.getenv(f'GEMINI_KEY_{i}') for i in range(1, 4)] + [os.getenv('GEMINI_API_KEY')])))
bot = telebot.TeleBot(TOKEN, threaded=False)

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def get_gemini_response(prompt):
    for key in GEMINI_KEYS:
        try:
            genai.configure(api_key=key, transport='rest')
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            if response and response.text: return response.text
        except Exception: continue
    return "Извините, сейчас я не могу ответить. Попробуйте позже."

def search_in_db(query):
    clean_query = query.lower().replace('цена', '').replace('стоимость', '').strip()
    if len(clean_query) < 2: return []

    # 1. ПОИСК В ФАЙЛЕ (Приоритет: Скидки, Бронирование)
    try:
        if os.path.exists('knowledge.txt'):
            with open('knowledge.txt', 'r', encoding='utf-8') as f:
                sections = f.read().split('===')
                for section in sections:
                    if clean_query[:4] in section.lower():
                        # УСЛОВИЕ: Цена 0 = Цена договорная
                        res_text = re.sub(r'[:\s]0(\s|руб|$)', ' Цена договорная ', section.strip())
                        return [{'title': 'Информация', 'content': res_text, 'price': 'Цена договорная'}]
    except Exception as e: print(f"Ошибка файла: {e}")

    # 2. ПОИСК В БД (Если в файле нет)
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            search_val = f"%{clean_query[:4]}%"
            sql = "SELECT title, content, price FROM parsed_content WHERE LOWER(title) LIKE %s OR LOWER(content) LIKE %s LIMIT 3"
            cur.execute(sql, (search_val, search_val))
            rows = cur.fetchall()
            for r in rows:
                if str(r['price']).strip() in ["0", "0.0", "None"]:
                    r['price'] = "Цена договорная"
                else:
                    r['price'] = f"{r['price']} руб."
            return rows
    except Exception as e: print(f"Ошибка БД: {e}"); return []
    finally:
        if 'conn' in locals(): conn.close()

# --- ОБРАБОТЧИКИ ---

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Бот базы «Вуокса-Вирта» на связи! Спросите про маршрут, цены или скидки.")

@bot.message_handler(func=lambda m: True)
def handle_msg(m):
    text = m.text.lower()
    
    # МАРШРУТ
    if any(kw in text for kw in ['маршрут', 'доехать', 'добраться']):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🚗 На машине", callback_data="btn_auto"))
        markup.add(types.InlineKeyboardButton("🚌 Автобус", callback_data="btn_bus"))
        bot.send_message(m.chat.id, "Выберите способ передвижения:", reply_markup=markup)
        return

    # ПОИСК (СКИДКИ, ЦЕНЫ, БРОНЬ)
    if any(kw in text for kw in ['цена', 'стоимость', 'скидк', 'брони', 'слип', 'лодка']):
        rows = search_in_db(text)
        if rows:
            for r in rows:
                p = r['price']
                price_line = f"💰 *{p}*" if "договорная" in str(p) else f"💰 Цена: {p}"
                bot.send_message(m.chat.id, f"🏠 *{r['title']}*\n{price_line}\n\n{r['content']}", parse_mode="Markdown")
            return

        # 3. GEMINI (Если ничего не нашли в файле и БД)
    # Отправляем только голый запрос пользователя, чтобы сберечь лимиты ключей
    if m.chat.type == 'private' or (bot.get_me().username and bot.get_me().username in text):
        bot.send_chat_action(m.chat.id, 'typing')
        
        # Формируем минимальный промпт БЕЗ подгрузки файла
        simple_prompt = f"Ты помощник базы отдыха 'Вуокса-Вирта'. Кратко ответь на вопрос: {m.text}"
        
        ans = get_gemini_response(simple_prompt)
        if ans:
            bot.reply_to(m, ans)

@bot.callback_query_handler(func=lambda call: call.data.startswith('btn_'))
def route_callback(call):
    # Здесь используется поиск в файле для деталей маршрута
    res = search_in_db(call.data.split('_')[1])
    if res:
        bot.send_message(call.message.chat.id, res[0]['content'], parse_mode="Markdown")
    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    print("✅ БОТ ГОТОВ")
    bot.remove_webhook()
    bot.infinity_polling()
