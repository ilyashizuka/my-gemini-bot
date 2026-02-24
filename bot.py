import telebot
import pymysql
import os
import re
import requests
import time
from bs4 import BeautifulSoup

# --- НАСТРОЙКИ ---
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0')) # Ваш ID от @userinfobot

# Настройки БД из вашего db_worker
DB_CONFIG = {
    'host': 'mysql9.hostland.ru',
    'port': 3306,
    'user': 'host1324224_botanik',
    'password': os.getenv('DB_PASSWORD', '807bba4c'),
    'database': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

bot = telebot.TeleBot(TOKEN)

# --- ЛОГИКА БАЗЫ ДАННЫХ ---
def save_to_db(url, title, price, phone, content):
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            sql = """INSERT INTO `parsed_content` (`url`, `title`, `price`, `phone`, `content`) 
                     VALUES (%s, %s, %s, %s, %s)
                     ON DUPLICATE KEY UPDATE `title`=%s, `price`=%s, `phone`=%s, `content`=%s"""
            cursor.execute(sql, (url, title, price, phone, content, title, price, phone, content))
            conn.commit()
    finally:
        conn.close()

def get_from_db(query=""):
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            if query:
                sql = "SELECT * FROM parsed_content WHERE title LIKE %s OR content LIKE %s"
                cursor.execute(sql, (f'%{query}%', f'%{query}%'))
            else:
                sql = "SELECT * FROM parsed_content"
                cursor.execute(sql)
            return cursor.fetchall()
    finally:
        conn.close()

# --- ЛОГИКА ПАРСЕРА ---
def run_parser():
    url = "https://vuoksa-virta.ru"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
    res = requests.get(url, headers=headers, timeout=20)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # Телефон
    p_tag = soup.find('a', href=re.compile(r'^tel:'))
    phone = p_tag['href'].replace('tel:', '').replace('"', '') if p_tag else "+79219930209"

    # Очистка перед обновлением
    conn = pymysql.connect(**DB_CONFIG)
    conn.cursor().execute("TRUNCATE TABLE parsed_content")
    conn.close()

    # 1. Парсим Дома (H3)
    for h3 in soup.find_all('h3'):
        title = h3.get_text(strip=True).strip(':')
        if any(x in title.lower() for x in ['меню', 'навигация', 'лодки']): continue
        for sib in h3.find_next_siblings():
            if sib.name in ['h3', 'figure']: break
            txt = sib.get_text(strip=True)
            m = re.search(r'(\d[\d\s\xa0]*)руб', txt)
            if m:
                val = re.sub(r'[^\d]', '', m.group(1))
                if int(val) > 400:
                    final_t = f"{title} (Доп. место)" if "доп" in txt.lower() else title
                    save_to_db(f"{url}#{hash(final_t+val)}", final_t, val, phone, txt[:500])

    # 2. Парсим Лодки (#priceShip)
    ship = soup.find('figure', id='priceShip')
    if ship:
        for row in ship.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) >= 3:
                name = cols[0].get_text(strip=True)
                save_to_db(f"{url}#b_{name}_r", f"Лодка: {name} (Живу)", re.sub(r'\D','',cols[1].text), phone, "Для проживающих")
                save_to_db(f"{url}#b_{name}_e", f"Лодка: {name} (Внеш)", re.sub(r'\D','',cols[2].text), phone, "Для внешних")

    # 3. Парсим Сауну (#priceSauna)
    sauna = soup.find('figure', id='priceSauna')
    if sauna:
        tds = sauna.find_all('td')
        if len(tds) >= 2:
            save_to_db(f"{url}#s_r", "Сауна (Живу)", re.sub(r'\D','',tds[0].text), phone, "Мин 3 часа")
            save_to_db(f"{url}#s_e", "Сауна (Внеш)", re.sub(r'\D','',tds[1].text), phone, "Мин 3 часа")

# --- КОМАНДЫ БОТА ---
@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "👋 Привет! Я бот базы «Вуокса-Вирта».\n\nНапиши название (дом, лодка, сауна) или используй /price.")

@bot.message_handler(commands=['update'])
def update(m):
    if m.from_user.id == ADMIN_ID:
        bot.send_message(m.chat.id, "⏳ Обновляю базу данных...")
        run_parser()
        bot.send_message(m.chat.id, "✅ База успешно обновлена!")
    else:
        bot.reply_to(m, "❌ Нет прав.")

@bot.message_handler(commands=['price'])
def price_all(m):
    data = get_from_db()
    if not data: return bot.send_message(m.chat.id, "База пуста.")
    res = "📜 *Актуальный прайс:*\n\n"
    for r in data:
        res += f"• {r['title']}: {r['price']} руб.\n"
    bot.send_message(m.chat.id, res, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def search(m):
    results = get_from_db(m.text.lower())
    if not results:
        bot.send_message(m.chat.id, "Ничего не нашел. Попробуй другое слово или /price.")
    else:
        for r in results:
            msg = f"🏨 *{r['title']}*\n💰 Цена: {r['price']} руб.\n📞 Тел: {r['phone']}\n\n_{r['content'][:200]}_"
            bot.send_message(m.chat.id, msg, parse_mode="Markdown")

if __name__ == "__main__":
    bot.infinity_polling()
