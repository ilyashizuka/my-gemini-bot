import telebot
import pymysql
import os
import re
import requests
import google.generativeai as genai
from bs4 import BeautifulSoup

# --- SETTINGS ---
TOKEN = os.getenv('BOT_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
ADMIN_ID = os.getenv('ADMIN_ID', '0')
DB_PASSWORD = os.getenv('DB_PASSWORD', '807bba4c')

# Gemini configuration
if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-pro')
    except:
        model = None
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

# --- PARSER (INSIDE BOT) ---
def run_update():
    url = "https://vuoksa-virta.ru"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    res = requests.get(url, headers=headers, timeout=20)
    soup = BeautifulSoup(res.text, 'html.parser')

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE `parsed_content` ")
            # Parse Houses (H3)
            for h3 in soup.find_all('h3'):
                title = h3.get_text(strip=True).strip(':')
                if any(x in title.lower() for x in ['menu', 'navigation']): continue
                for sib in h3.find_next_siblings():
                    if sib.name in ['h3', 'figure']: break
                    txt = sib.get_text(strip=True)
                    m = re.search(r'(\d[\d\s\xa0]*)руб', txt)
                    if m:
                        p = re.sub(r'\D', '', m.group(1))
                        f_title = f"{title} (Additional spot)" if "additional" in txt.lower() else title
                        cur.execute("INSERT INTO parsed_content (url, title, price, phone, content) VALUES (%s,%s,%s,%s,%s)",
                                   (f"{url}#{hash(f_title+p)}", f_title, p, "+79219930209", txt[:400]))
            # Boats
            ship = soup.find('figure', id='priceShip')
            if ship:
                for row in ship.find_all('tr')[1:]:
                    tds = row.find_all('td')
                    if len(tds) >= 2:
                        name = tds[0].get_text(strip=True)
                        val = re.sub(r'\D', '', tds[1].text)
                        cur.execute("INSERT INTO parsed_content (url, title, price, phone, content) VALUES (%s,%s,%s,%s,%s)",
                                   (f"{url}#b{hash(name)}", f"Boat: {name}", val, "+79219930209", "Rental"))
            conn.commit()
    finally:
        conn.close()

# --- COMMAND HANDLING (PRIORITY 1) ---

@bot.message_handler(commands=['update'])
def update_cmd(m):
    if str(m.from_user.id) == str(ADMIN_ID):
        bot.send_message(m.chat.id, "⌛ Updating the database from the source...")
        try:
            run_update()
            bot.send_message(m.chat.id, "✅ Done! The MySQL database is up to date.")
        except Exception as e:
            bot.send_message(m.chat.id, f"❌ Parser error: {e}")
    else:
        bot.reply_to(m, f"⛔ Access denied. Your ID: {m.from_user.id}. Enter it in ADMIN_ID on Render.")

@bot.message_handler(commands=['start'])
def start_cmd(m):
    bot.send_message(m.chat.id, "Hello! I am the 'Vuoksa-Virta' database bot. Ask for the price (e.g., 'boat' or 'house').")

# --- TEXT PROCESSING (PRIORITY 2) ---

@bot.message_handler(func=lambda m: True)
def handle_msg(m):
    text_query = m.text.lower().strip()
    
    # 1. Search in MySQL (Free)
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            sql = "SELECT * FROM parsed_content WHERE title LIKE %s OR content LIKE %s"
            cur.execute(sql, (f'%{text_query}%', f'%{text_query}%'))
            rows = cur.fetchall()
        conn.close()

        if rows:
            for r in rows[:3]:
                bot.send_message(m.chat.id, f"🏠 *{r['title']}*\n💰 Price: {r['price']} rub.\n📞 {r['phone']}", parse_mode="Markdown")
            return
    except Exception as e:
        print(f"Search error: {e}")

    # 2. If there is nothing in the database, go to Gemini
    if model:
        bot.send_chat_action(m.chat.id, 'typing')
        try:
            prompt = f"You are an assistant for the 'Vuoksa-Virta' database. Answer politely: {m.text}. Phone: +79219930209."
            res = model.generate_content(prompt)
            bot.reply_to(m, res.text)
        except Exception as e:
            if "429" in str(e):
                bot.reply_to(m, "⚠️ Neural network limit exceeded. Try again tomorrow or ask for the price (boat, house).")
            else:
                bot.reply_to(m, "An error occurred. Call: +79219930209")
    else:
        bot.reply_to(m, "There is no information in the price list. Call: +79219930209")

if __name__ == "__main__":
    bot.infinity_polling()
