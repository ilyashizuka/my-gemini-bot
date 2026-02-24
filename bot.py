import telebot
import pymysql
import os
import re
import requests
import google.generativeai as genai
from bs4 import BeautifulSoup

# --- КОНФИГ ---
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

# --- ФУНКЦИЯ ОЧИСТКИ ЦЕН ---
def clean_p(text):
    match = re.search(r'(\d[\d\s\xa0]*)', text)
    return re.sub(r'[^\d]', '', match.group(1)) if match else "0"

# --- ПОЛНЫЙ ПАРСЕР ---
def run_update():
    url = "https://vuoksa-virta.ru"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # 1. ПОЛНЫЙ СНОС БАЗЫ
            cur.execute("TRUNCATE TABLE `parsed_content` ")
            
            # 2. ЛОДКИ (Таблица priceShip)
            ship = soup.find('figure', id='priceShip')
            if ship:
                rows = ship.find_all('tr')[1:]
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        name = cols[0].get_text(strip=True).replace(':', '')
                        cur.execute("INSERT INTO parsed_content (url, title, price, phone, content) VALUES (%s,%s,%s,%s,%s)",
                                   (f"{url}#b_{name}_r", f"Лодка: {name} (Для проживающих)", clean_p(cols[1].text), "+79219930209", "Тариф для гостей базы"))
                        cur.execute("INSERT INTO parsed_content (url, title, price, phone, content) VALUES (%s,%s,%s,%s,%s)",
                                   (f"{url}#b_{name}_e", f"Лодка: {name} (Без проживания)", clean_p(cols[2].text), "+79219930209", "Тариф для внешних гостей"))

            # 3. САУНА (Таблица priceSauna)
            sauna = soup.find('figure', id='priceSauna')
            if sauna:
                cols = sauna.find_all('td')
                if len(cols) >= 2:
                    desc = "Минимальный заказ от 3-х часов. Время растопки - 3 часа."
                    cur.execute("INSERT INTO parsed_content (url, title, price, phone, content) VALUES (%s,%s,%s,%s,%s)",
                               (f"{url}#s_res", "Сауна (Для проживающих)", clean_p(cols[0].text), "+79219930209", desc))
                    cur.execute("INSERT INTO parsed_content (url, title, price, phone, content) VALUES (%s,%s,%s,%s,%s)",
                               (f"{url}#s_ext", "Сауна (Без проживания)", clean_p(cols[1].text), "+79219930209", desc))

            # 4. ДОМА (H3)
            for h3 in soup.find_all('h3'):
                title = re.sub(r'^[а-я]\s+', '', h3.get_text(strip=True), flags=re.IGNORECASE).strip(': ')
                if any(x in title.lower() for x in ['меню', 'навигация', 'лодки', 'сауна']): continue
                for sib in h3.find_next_siblings():
                    if sib.name in ['h3', 'figure']: break
                    txt = sib.get_text(strip=True)
                    m = re.search(r'(\d[\d\s\xa0]*)руб', txt)
                    if m:
                        p = clean_p(m.group(1))
                        if int(p) > 400:
                            f_t = f"{title} (Доп. место)" if "доп" in txt.lower() else title
                            cur.execute("INSERT INTO parsed_content (url, title, price, phone, content) VALUES (%s,%s,%s,%s,%s)",
                                       (f"{url}#{hash(f_t+p)}", f_t, p, "+79219930209", txt[:500]))
            conn.commit()
    finally:
        conn.close()

# --- ПОИСК ---
def search_in_db(query):
    q = query.lower().strip()
    words = [w[:5] for w in q.split() if len(w) > 3]
    if not words: return []
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            cond = " AND ".join(["LOWER(title) LIKE %s" for _ in words])
            params = [f'%{w}%' for w in words]
            cur.execute(f"SELECT * FROM parsed_content WHERE {cond} GROUP BY title LIMIT 10", params)
            return cur.fetchall()
    except: return []
    finally:
        if 'conn' in locals(): conn.close()

# --- ОБРАБОТЧИКИ ---
@bot.message_handler(commands=['update'])
def update_cmd(m):
    if str(m.from_user.id) == str(ADMIN_ID):
        msg = bot.send_message(m.chat.id, "🧹 **Сношу базу и загружаю Дома, Лодки и Сауну...**", parse_mode="Markdown")
        try:
            run_update()
            bot.edit_message_text("✅ **Готово! База полностью пересобрана.**", m.chat.id, msg.message_id, parse_mode="Markdown")
        except Exception as e:
            bot.edit_message_text(f"❌ Ошибка: {e}", m.chat.id, msg.message_id)

@bot.message_handler(func=lambda m: True)
def handle_msg(m):
    rows = search_in_db(m.text)
    if rows:
        for r in rows:
            bot.send_message(m.chat.id, f"📍 *{r['title']}*\n💰 Цена: {r['price']} руб.\n📞 {r['phone']}\n\n_{r['content']}_", parse_mode="Markdown")
        return

    if model:
        bot.send_chat_action(m.chat.id, 'typing')
        try:
            res = model.generate_content(f"Ты бот базы 'Вуокса-Вирта'. Ответь вежливо: {m.text}")
            bot.reply_to(m, res.text)
        except: bot.reply_to(m, "Информации нет. Звоните: +79219930209")

if __name__ == "__main__":
    bot.infinity_polling()
