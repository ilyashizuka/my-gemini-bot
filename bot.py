import telebot
import pymysql
import os
import re
import requests
import google.generativeai as genai
from bs4 import BeautifulSoup

# --- НАСТРОЙКИ (Берем из Render) ---
TOKEN = os.getenv('BOT_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
ADMIN_ID = os.getenv('ADMIN_ID', '0')
DB_PASSWORD = os.getenv('DB_PASSWORD', '807bba4c')

# Настройка Gemini
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-pro')
else:
    model = None

DB_CONFIG = {
    'host': 'mysql9.hostland.ru',
    'user': 'host1324224',
    'password': DB_PASSWORD,
    'database': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

bot = telebot.TeleBot(TOKEN)

# --- УМНЫЙ ПОИСК В БАЗЕ (РЕШАЕТ ПРОБЛЕМУ РЕГИСТРА И ПАДЕЖЕЙ) ---
def search_in_db(query_text):
    # Очищаем запрос: в нижний регистр, убираем знаки препинания
    query_text = query_text.lower().replace('?', '').strip()
    # Берем основы слов длиннее 3 символов (например, "студии" -> "студи")
    words = [w[:5] for w in query_text.split() if len(w) > 3]
    if not words: words = [query_text]

    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            # Строим запрос: ищем вхождение любого из корней слов
            conditions = []
            params = []
            for w in words:
                conditions.append("(LOWER(title) LIKE %s OR LOWER(content) LIKE %s)")
                params.extend([f'%{w}%', f'%{w}%'])
            
            sql = f"SELECT * FROM parsed_content WHERE {' OR '.join(conditions)} LIMIT 5"
            cur.execute(sql, params)
            rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return []

# --- ОБНОВЛЕННЫЙ ПАРСЕР (УБИРАЕТ ЛИШНИЕ БУКВЫ) ---
def run_update():
    url = "https://vuoksa-virta.ru"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers, timeout=20)
    soup = BeautifulSoup(res.text, 'html.parser')
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE `parsed_content` ")
            # Собираем Дома (H3)
            for h3 in soup.find_all('h3'):
                # lstrip('а ') уберет одиночную "а" в начале, если она прилипла при парсинге
                title = h3.get_text(strip=True).lstrip('а ').strip(':')
                if any(x in title.lower() for x in ['меню', 'навигация']): continue
                
                for sib in h3.find_next_siblings():
                    if sib.name in ['h3', 'figure']: break
                    txt = sib.get_text(strip=True)
                    m = re.search(r'(\d[\d\s\xa0]*)руб', txt)
                    if m:
                        p = re.sub(r'\D', '', m.group(1))
                        f_t = f"{title} (Доп. место)" if "доп" in txt.lower() else title
                        cur.execute("INSERT INTO parsed_content (url, title, price, phone, content) VALUES (%s,%s,%s,%s,%s)",
                                   (f"{url}#{hash(f_t+p)}", f_t, p, "+79219930209", txt[:500]))
            conn.commit()
    finally:
        conn.close()

# --- ОБРАБОТЧИКИ СООБЩЕНИЙ ---
@bot.message_handler(commands=['update'])
def update_cmd(m):
    if str(m.from_user.id) == str(ADMIN_ID):
        bot.send_message(m.chat.id, "⏳ Обновляю базу...")
        try:
            run_update()
            bot.send_message(m.chat.id, "✅ База данных обновлена!")
        except Exception as e:
            bot.send_message(m.chat.id, f"❌ Ошибка: {e}")
    else:
        bot.reply_to(m, f"Нет прав. Ваш ID: {m.from_user.id}")

@bot.message_handler(func=lambda m: True)
def handle_msg(m):
    # 1. ПРИОРИТЕТ: Ищем в базе данных (игнорируя регистр)
    rows = search_in_db(m.text)
    
    if rows:
        # Если в базе есть совпадения — Gemini не вызываем!
        for r in rows:
            price_text = f"{r['price']} руб." if r['price'] != "0" else "По запросу"
            msg = f"🏠 *{r['title']}*\n💰 Цена: {price_text}\n📞 {r['phone']}\n\n_{r['content'][:300]}_"
            bot.send_message(m.chat.id, msg, parse_mode="Markdown")
        return

    # 2. Если в базе пусто — идем к Gemini
    if model:
        bot.send_chat_action(m.chat.id, 'typing')
        try:
            prompt = f"Ты помощник базы 'Вуокса-Вирта'. Ответь кратко: {m.text}. Телефон: +79219930209."
            res = model.generate_content(prompt)
            bot.reply_to(m, res.text)
        except:
            bot.reply_to(m, "В прайсе не найдено. Звоните: +79219930209")
    else:
        bot.reply_to(m, "Информация не найдена. Тел: +79219930209")

if __name__ == "__main__":
    bot.infinity_polling()
