import telebot
import pymysql
import os
import re
import requests
import google.generativeai as genai
from bs4 import BeautifulSoup
from google.api_core import exceptions

# --- НАСТРОЙКИ ---
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID', '0')
DB_PASSWORD = os.getenv('DB_PASSWORD', '807bba4c')

# Список ключей Gemini для ротации (из переменных окружения)
GEMINI_KEYS = [
    os.getenv('GEMINI_KEY_1'),
    os.getenv('GEMINI_KEY_2'),
    os.getenv('GEMINI_KEY_3'),
    os.getenv('GEMINI_API_KEY')
]
GEMINI_KEYS = [k for k in GEMINI_KEYS if k] # Очистка от пустых

# Настройка Базы Данных
DB_CONFIG = {
    'host': 'mysql9.hostland.ru',
    'user': 'host1324224',
    'password': DB_PASSWORD,
    'database': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

bot = telebot.TeleBot(TOKEN, threaded=False)

# --- 1. РОТАЦИЯ КЛЮЧЕЙ GEMINI (ОШИБКА 429) ---
def get_gemini_response(prompt):
    for key in GEMINI_KEYS:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            return response.text
        except exceptions.ResourceExhausted:
            continue # Пробуем следующий ключ при 429
        except Exception as e:
            print(f"Ошибка Gemini: {e}")
            continue
    return None

# --- 2. ПОИСК В ТЕКСТОВОМ ФАЙЛЕ (KNOWLEDGE.TXT) ---
def search_in_knowledge_base(query):
    query = query.lower()
    file_path = 'knowledge.txt'
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            parts = content.split('===')
            for i in range(1, len(parts), 2):
                keywords_header = parts[i].lower()
                answer_text = parts[i+1].strip()
                kw_list = [k.strip() for k in keywords_header.split(',')]
                if any(kw in query for kw in kw_list if len(kw) > 2):
                    return answer_text
    except Exception as e:
        print(f"Ошибка чтения файла знаний: {e}")
    return None

# --- 3. ПОИСК В БАЗЕ ДАННЫХ MYSQL ---
def search_in_db(query):
    stop_words = ['цена', 'стоимость', 'сколько', 'стоит', 'есть', 'базе', 'на']
    q = query.lower().replace('?', '').strip()
    words = [w[:4] for w in q.split() if len(w) >= 3 and w not in stop_words]
    if not words: return []
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cur:
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

# --- 4. ПАРСЕР САЙТА ---
def run_update():
    url = "https://vuoksa-virta.ru"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
    soup = BeautifulSoup(res.text, 'html.parser')
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE `parsed_content` ")
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

# --- ОБРАБОТЧИКИ КОМАНД ---

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Бот базы «Вуокса-Вирта» готов! Спросите про цены, маршрут или контакты.")

@bot.message_handler(commands=['update'])
def update_cmd(m):
    if str(m.from_user.id) == str(ADMIN_ID):
        bot.send_message(m.chat.id, "🧹 Обновляю базу данных из сайта...")
        try:
            run_update()
            bot.send_message(m.chat.id, "✅ База успешно обновлена!")
        except Exception as e:
            bot.send_message(m.chat.id, f"❌ Ошибка: {e}")

# --- ГЛАВНЫЙ ОБРАБОТЧИК ТЕКСТА ---

@bot.message_handler(func=lambda m: True)
def handle_msg(m):
    text = m.text.lower()
    
    # ПРИОРИТЕТ 1: Текстовый файл знаний (Маршрут, Контакты)
    file_answer = search_in_knowledge_base(text)
    if file_answer:
        bot.send_message(m.chat.id, file_answer, parse_mode="Markdown", disable_web_page_preview=False)
        return

    # ПРИОРИТЕТ 2: База данных (Цены на дома/лодки)
    rows = search_in_db(text)
    if rows:
        for r in rows:
            msg = f"🏠 *{r['title']}*\n💰 Цена: {r['price']} руб.\n📞 {r['phone']}\n\n_{r['content'][:250]}_"
            bot.send_message(m.chat.id, msg, parse_mode="Markdown")
        return

    # ПРИОРИТЕТ 3: Gemini (если ничего не нашли)
    is_private = m.chat.type == 'private'
    is_mentioned = bot.get_me().username in text
    
    if (is_private or is_mentioned):
        bot.send_chat_action(m.chat.id, 'typing')
        prompt = f"Ты помощник базы 'Вуокса-Вирта'. Ответь кратко на вопрос: {m.text}. Телефон: +79219930209."
        answer = get_gemini_response(prompt)
        if answer:
            bot.reply_to(m, answer)

if __name__ == "__main__":
    print(f"Бот запущен. Ключей Gemini: {len(GEMINI_KEYS)}")
    bot.infinity_polling()
