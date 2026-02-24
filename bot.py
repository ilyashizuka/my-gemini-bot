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
    try:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-pro')
    except: model = None
else: model = None

# Настройка Базы
DB_CONFIG = {
    'host': 'mysql9.hostland.ru',
    'user': 'host1324224',
    'password': DB_PASSWORD,
    'database': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# ИНИЦИАЛИЗАЦИЯ (threaded=False важен для групп)
bot = telebot.TeleBot(TOKEN, threaded=False)

# --- УМНЫЙ ПОИСК В БАЗЕ ---
def search_in_db(query):
    stop_words = ['цена', 'стоимость', 'сколько', 'стоит', 'есть', 'базе', 'на']
    q = query.lower().replace('?', '').strip()
    words = [w[:4] for w in q.split() if len(w) >= 3 and w not in stop_words]
    
    if not words: return []

    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            # Ищем совпадения по всем корням слов (AND)
            conditions = " AND ".join(["(LOWER(title) LIKE %s OR LOWER(content) LIKE %s)" for _ in words])
            params = []
            for w in words:
                params.extend([f'%{w}%', f'%{w}%'])
            
            sql = f"SELECT * FROM parsed_content WHERE {conditions} GROUP BY title LIMIT 5"
            cur.execute(sql, params)
            return cur.fetchall()
    except: return []
    finally:
        if 'conn' in locals(): conn.close()

# --- ПАРСЕР (ВНУТРИ) ---
def run_update():
    url = "https://vuoksa-virta.ru"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
    soup = BeautifulSoup(res.text, 'html.parser')
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE `parsed_content` ")
            # Собираем H3 (Дома)
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
    finally: conn.close()

# --- ОБРАБОТЧИКИ ---

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Бот базы «Вуокса-Вирта» готов! Просто напишите название дома или услуги (например, 'лодка' или 'Пятёрочка'), и я пришлю цену.")

@bot.message_handler(commands=['update'])
def update_cmd(m):
    if str(m.from_user.id) == str(ADMIN_ID):
        bot.send_message(m.chat.id, "🧹 Обновляю базу данных...")
        try:
            run_update()
            bot.send_message(m.chat.id, "✅ База успешно обновлена!")
        except Exception as e:
            bot.send_message(m.chat.id, f"❌ Ошибка: {e}")
    else:
        bot.reply_to(m, "У вас нет прав для этой команды.")

@bot.message_handler(func=lambda m: True)
def handle_msg(m):
    text = m.text.lower()
    
    # 1. Поиск в Базе (Бесплатно и точно)
    rows = search_in_db(text)
    if rows:
        for r in rows:
            msg = f"🏠 *{r['title']}*\n💰 Цена: {r['price']} руб.\n📞 {r['phone']}\n\n_{r['content'][:250]}_"
            bot.send_message(m.chat.id, msg, parse_mode="Markdown")
        return

    # 2. Если в базе нет — Gemini (только для личных чатов или при упоминании в группе)
    # В группе бот не будет отвечать нейросетью на каждое сообщение, чтобы не спамить.
    is_private = m.chat.type == 'private'
    is_mentioned = bot.get_me().username in text
    
    if model and (is_private or is_mentioned):
        bot.send_chat_action(m.chat.id, 'typing')
        try:
            prompt = f"Ты помощник базы 'Вуокса-Вирта'. Ответь кратко на вопрос: {m.text}. Телефон: +79219930209."
            res = model.generate_content(prompt)
            bot.reply_to(m, res.text)
        except: pass

if __name__ == "__main__":
    print("Бот Вуокса-Вирта запущен (режим без кнопок)...")
    bot.infinity_polling()
