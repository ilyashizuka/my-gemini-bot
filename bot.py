import os
import sys
import telebot
import pymysql
import re
import requests
import google.generativeai as genai
from google.api_core import exceptions
from google.generativeai.types import HarmCategory, HarmBlockThreshold  # Вот это добавляем
from telebot import types
from google.api_core import exceptions
from google.generativeai.types import HarmCategory, HarmBlockThreshold

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
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Теперь эти настройки будут работать благодаря импорту выше
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    try:
        # Передаем настройки безопасности в запрос
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text if response.candidates else "Извините, я не могу ответить на этот вопрос."
    except Exception as e:
        print(f"Ошибка API: {e}")
        return None

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
    # Добавляем все три кнопки
    markup.add(types.InlineKeyboardButton("🚗 На машине", callback_data="btn_auto"))
    markup.add(types.InlineKeyboardButton("🚌 Автобус", callback_data="btn_bus"))
    markup.add(types.InlineKeyboardButton("🚆 Электричка", callback_data="btn_train")) # Вот она
    
    bot.send_message(m.chat.id, "Выберите способ передвижения:", reply_markup=markup)
    return

# Чтобы кнопки «ожили», добавьте этот обработчик:
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == "btn_auto":
        bot.send_message(call.message.chat.id, "Маршрут на авто: ...")
    elif call.data == "btn_bus":
        bot.send_message(call.message.chat.id, "Расписание автобусов: ...")
    elif call.data == "btn_train":
        bot.send_message(call.message.chat.id, "Расписание электричек: ...")
    
    # Обязательно уведомляем телеграм, что запрос обработан (убирает «часики»)
    bot.answer_callback_query(call.id)


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
