import telebot
import pymysql
import os
import re
import requests
import google.generativeai as genai
from bs4 import BeautifulSoup

# --- НАСТРОЙКИ ---
TOKEN = os.getenv('BOT_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
ADMIN_ID = os.getenv('ADMIN_ID', '0')
DB_PASSWORD = os.getenv('DB_PASSWORD', '807bba4c')

# Настройка Gemini
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-pro')
else: model = None

DB_CONFIG = {
    'host': 'mysql9.hostland.ru',
    'user': 'host1324224',
    'password': DB_PASSWORD,
    'database': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

bot = telebot.TeleBot(TOKEN)

# --- УЛУЧШЕННЫЙ ПАРСЕР ---
def run_update():
    url = "https://vuoksa-virta.ru"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # 1. СНОСИМ ВСЁ
            cur.execute("TRUNCATE TABLE `parsed_content` ")
            
            # 2. ПАРСИМ ЛОДКИ (ТАБЛИЦА)
            ship_table = soup.find('figure', id='priceShip')
            if ship_table:
                rows = ship_table.find_all('tr')[1:] # Пропускаем шапку
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        name = cols[0].get_text(strip=True).replace(':', '')
                        price_res = re.sub(r'\D', '', cols[1].text) # Для проживающих
                        price_ext = re.sub(r'\D', '', cols[2].text) # Без проживания
                        
                        # Сохраняем два варианта цены для каждой лодки
                        cur.execute("INSERT INTO parsed_content (url, title, price, phone, content) VALUES (%s,%s,%s,%s,%s)",
                                   (f"{url}#b_{name}_res", f"Лодка: {name} (Для проживающих)", price_res, "+79219930209", "Тариф для гостей базы"))
                        cur.execute("INSERT INTO parsed_content (url, title, price, phone, content) VALUES (%s,%s,%s,%s,%s)",
                                   (f"{url}#b_{name}_ext", f"Лодка: {name} (Без проживания)", price_ext, "+79219930209", "Тариф для внешних гостей"))

            # 3. ПАРСИМ ДОМА (H3)
            for h3 in soup.find_all('h3'):
                title = re.sub(r'^[а-я]\s+', '', h3.get_text(strip=True), flags=re.IGNORECASE).strip(': ')
                if any(x in title.lower() for x in ['меню', 'навигация', 'лодки']): continue
                
                for sib in h3.find_next_siblings():
                    if sib.name in ['h3', 'figure']: break
                    txt = sib.get_text(strip=True)
                    m = re.search(r'(\d[\d\s\xa0]*)руб', txt)
                    if m:
                        p = re.sub(r'\D', '', m.group(1))
                        f_t = f"{title} (Доп. место)" if "доп" in txt.lower() else title
                        cur.execute("INSERT INTO parsed_content (url, title, price, phone, content) VALUES (%s,%s,%s,%s,%s)",
                                   (f"{url}#{hash(f_t)}", f_t, p, "+79219930209", txt[:500]))
            conn.commit()
    finally:
        conn.close()

# --- УМНЫЙ ПОИСК ---
def search_in_db(query_text):
    query_text = query_text.lower().replace('?', '').strip()
    words = [w[:5] for w in query_text.split() if len(w) > 3]
    if not words: return []
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            # Группировка по title, чтобы не было дублей
            conditions = " AND ".join(["LOWER(title) LIKE %s" for _ in words])
            params = [f'%{w}%' for w in words]
            sql = f"SELECT * FROM parsed_content WHERE {conditions} GROUP BY title LIMIT 10"
            cur.execute(sql, params)
            return cur.fetchall()
    except: return []
    finally: conn.close()

# --- ОБРАБОТЧИКИ ---
@bot.message_handler(commands=['update'])
def update_cmd(m):
    if str(m.from_user.id) == str(ADMIN_ID):
        bot.send_message(m.chat.id, "🧹 **Сношу базу и загружаю лодки и дома...**", parse_mode="Markdown")
        run_update()
        bot.send_message(m.chat.id, "✅ **База обновлена! Теперь цены на лодки разделены.**", parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_msg(m):
    rows = search_in_db(m.text)
    if rows:
        for r in rows:
            p_text = f"{r['price']} руб." if r['price'] != "0" else "По запросу"
            msg = f"🚣 *{r['title']}*\n💰 Цена: {p_text}\n📞 {r['phone']}\n\n_{r['content']}_"
            bot.send_message(m.chat.id, msg, parse_mode="Markdown")
        return

    if model:
        bot.send_chat_action(m.chat.id, 'typing')
        try:
            res = model.generate_content(f"Ответь кратко про базу 'Вуокса-Вирта': {m.text}")
            bot.reply_to(m, res.text)
        except: bot.reply_to(m, "Звоните администратору: +79219930209")

if __name__ == "__main__":
    bot.infinity_polling()
