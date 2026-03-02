import os
import re
import requests
import pymysql
import telebot
import google.generativeai as genai
from google.generativeai.types import RequestOptions
from bs4 import BeautifulSoup

# --- 1. НАСТРОЙКИ ИЗ СЕКРЕТОВ РЕНДЕРА ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))
DB_PASSWORD = os.environ.get('DB_PASSWORD', '807bba4c')

DB_CONFIG = {
    'host': 'mysql9.hostland.ru',
    'port': 3306,
    'user': 'host1324224',
    'password': DB_PASSWORD,
    'database': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

bot = telebot.TeleBot(BOT_TOKEN)

# --- 2. ЛОГИКА GEMINI (ТВОЙ КОД С ПЕРЕБОРОМ КЛЮЧЕЙ) ---
def get_ai_answer(prompt):
    key_names = ['GEMINI_KEY_1', 'GEMINI_KEY_2', 'GEMINI_KEY_3']
    models_to_try = ['gemini-2.0-flash', 'gemini-1.5-flash']

    for name in key_names:
        raw_key = os.environ.get(name)
        if not raw_key: continue
            
        try:
            key = raw_key.strip().replace('"', '').replace("'", "")
            genai.configure(api_key=key)
            
            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(
                        prompt,
                        request_options=RequestOptions(api_version='v1')
                    )
                    if response and response.text:
                        return response.text
                except Exception:
                    continue 
        except Exception:
            continue
    return "❌ Все ключи выдали ошибку. Проверь лимиты или регион."

# --- 3. ЛОГИКА ПАРСЕРА (ДЛЯ БАЗЫ ДАННЫХ) ---
def extract_price(element):
    if not element: return "0"
    text = element.get_text(separator=' ', strip=True).replace('\xa0', ' ')
    match = re.search(r'(\d[\d\s]*)\s*рублей', text)
    if match:
        return re.sub(r'\D', '', match.group(1))
    digits = re.sub(r'\D', '', text)
    return digits if digits else "0"

def run_parser():
    base_url = "https://vuoksa-virta.ru"
    all_data = []
    try:
        resp = requests.get(base_url, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        menu = soup.find(id='menu')
        if not menu: return "Ошибка: меню не найдено."
        
        links = set()
        for a in menu.find_all('a', href=True):
            href = a['href']
            links.add(href if href.startswith('http') else f"{base_url}/{href.lstrip('/')}")

        for url in links:
            p_soup = BeautifulSoup(requests.get(url, timeout=15).content, 'html.parser')

            # Обычные H3
            for h3 in p_soup.find_all('h3', id=True):
                if h3.find_parent('figure', id=['priceShip', 'priceSauna']): continue
                all_data.append((url, h3.get_text(strip=True), extract_price(h3.find_next()), h3.get_text(strip=True)))

            # Лодки
            ship = p_soup.find('figure', id='priceShip')
            if ship:
                for row in ship.find_all('tr')[1:]:
                    tds = row.find_all('td')
                    if len(tds) >= 3:
                        t = tds[0].get_text(strip=True)
                        all_data.append((url, "Прокат лодки Пелла", extract_price(tds[1]), f"прокат лодки Пелла тариф {t} для проживающих"))
                        all_data.append((url, "Прокат лодки Пелла", extract_price(tds[2]), f"прокат лодки Пелла тариф {t} для непроживающих"))

            # Баня
            sauna = p_soup.find('figure', id='priceSauna')
            if sauna:
                for row in sauna.find_all('tr')[1:]:
                    tds = row.find_all('td')
                    if len(tds) >= 2:
                        all_data.append((url, "Баня на дровах", extract_price(tds[0]), "баня на дровах для проживающих"))
                        all_data.append((url, "Баня на дровах", extract_price(tds[1]), "баня на дровах для непроживающих"))

        if all_data:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                cur.execute("DELETE FROM `parsed_content`")
                cur.executemany("INSERT INTO `parsed_content` (`url`,`title`,`price`,`content`) VALUES (%s,%s,%s,%s)", all_data)
                conn.commit()
            conn.close()
            return f"✅ База обновлена! Записей: {len(all_data)}"
        return "Данные не найдены."
    except Exception as e:
        return f"❌ Ошибка: {e}"

# --- 4. ОБРАБОТЧИК СООБЩЕНИЙ ---
@bot.message_handler(func=lambda m: True)
def main_handler(message):
    # Команда обновления (только админ)
    if message.text == '/update':
        if message.from_user.id == ADMIN_ID:
            bot.reply_to(message, "⏳ Обновляю базу...")
            bot.send_message(message.chat.id, run_parser())
        else:
            bot.reply_to(message, "🔐 Доступ закрыт.")
        return

    # Вызов ИИ через /** (для всех или только админа - на твой вкус)
    if message.text and message.text.startswith('/**'):
        query = message.text[3:].strip()
        if not query:
            bot.reply_to(message, "Введите вопрос после /**")
            return
        
        bot.send_chat_action(message.chat.id, 'typing')
        answer = get_ai_answer(query)
        bot.reply_to(message, answer)

# Запуск
if __name__ == "__main__":
    bot.infinity_polling()
