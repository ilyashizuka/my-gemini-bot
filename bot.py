import telebot
import pymysql
import os
import re
import requests
import google.generativeai as genai
from bs4 import BeautifulSoup

# --- НАСТРОЙКИ ИЗ RENDER ---
TOKEN = os.getenv('BOT_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
DB_PASSWORD = os.getenv('DB_PASSWORD', '807bba4c')

# Настройка нейросети
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-pro')

DB_CONFIG = {
    'host': 'mysql9.hostland.ru',
    'user': 'host1324224',
    'password': DB_PASSWORD,
    'database': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

bot = telebot.TeleBot(TOKEN)

# --- ПАРСЕР (ВНУТРИ БОТА) ---
def run_update():
    url = "https://vuoksa-virta.ru"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    res = requests.get(url, headers=headers, timeout=20)
    soup = BeautifulSoup(res.text, 'html.parser')

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE parsed_content")
            # Парсим Дома (H3)
            for h3 in soup.find_all('h3'):
                title = h3.get_text(strip=True).strip(':')
                if any(x in title.lower() for x in ['меню', 'навигация']): continue
                for sib in h3.find_next_siblings():
                    if sib.name in ['h3', 'figure']: break
                    txt = sib.get_text(strip=True)
                    m = re.search(r'(\d[\d\s\xa0]*)руб', txt)
                    if m:
                        p = re.sub(r'\D', '', m.group(1))
                        f_title = f"{title} (Доп. место)" if "доп" in txt.lower() else title
                        cur.execute("INSERT INTO parsed_content (url, title, price, phone, content) VALUES (%s,%s,%s,%s,%s)",
                                   (f"{url}#{hash(f_title+p)}", f_title, p, "+79219930209", txt[:300]))

            # Парсим Лодки (Таблица #priceShip)
            ship = soup.find('figure', id='priceShip')
            if ship:
                for row in ship.find_all('tr')[1:]:
                    tds = row.find_all('td')
                    if len(tds) >= 2:
                        name = tds[0].get_text(strip=True)
                        cur.execute("INSERT INTO parsed_content (url, title, price, phone, content) VALUES (%s,%s,%s,%s,%s)",
                                   (f"{url}#b{hash(name)}", f"Лодка: {name}", re.sub(r'\D','',tds[1].text), "+79219930209", "Прокат"))
            conn.commit()
    finally:
        conn.close()

# --- ОБРАБОТКА СООБЩЕНИЙ ---
@bot.message_handler(commands=['update'])
def update_cmd(m):
    if m.from_user.id == ADMIN_ID:
        bot.send_message(m.chat.id, "⌛ Начинаю обновление базы данных...")
        try:
            run_update()
            bot.send_message(m.chat.id, "✅ База данных успешно обновлена!")
        except Exception as e:
            bot.send_message(m.chat.id, f"❌ Ошибка: {e}")
    else:
        bot.reply_to(m, "⛔ У вас нет прав.")

@bot.message_handler(func=lambda m: True)
def handle_msg(m):
    # 1. Поиск в базе данных
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM parsed_content WHERE title LIKE %s", (f'%{m.text}%',))
            rows = cur.fetchall()
        conn.close()

        if rows:
            for r in rows[:3]:
                msg = f"📍 *{r['title']}*\n💰 Цена: {r['price']} руб.\n📞 {r['phone']}"
                bot.send_message(m.chat.id, msg, parse_mode="Markdown")
            return
    except Exception as e:
        print(f"Ошибка БД: {e}")

    # 2. Если в базе нет — идем к Gemini
    bot.send_chat_action(m.chat.id, 'typing')
    try:
        prompt = f"Ты помощник базы отдыха 'Вуокса-Вирта'. Ответь вежливо на русском: {m.text}. Если не знаешь цену, скажи позвонить +79219930209."
        response = model.generate_content(prompt)
        bot.reply_to(m, response.text)
    except:
        bot.reply_to(m, "Информации в прайсе нет. Для консультации звоните: +79219930209")

if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
