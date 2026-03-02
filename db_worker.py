import os
import re
import requests
import pymysql
from bs4 import BeautifulSoup
from telebot import TeleBot

# Настройки из Render
DB_PASSWORD = os.getenv('DB_PASSWORD', '807bba4c') 
ADMIN_ID = int(os.getenv('ADMIN_ID', 0)) 
BOT_TOKEN = os.getenv('BOT_TOKEN')

bot = TeleBot(BOT_TOKEN)

DB_CONFIG = {
    'host': 'mysql9.hostland.ru',
    'port': 3306,
    'user': 'host1324224',
    'password': DB_PASSWORD,
    'database': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def extract_price(element):
    """Ищет число перед 'рублей' или просто число в элементе"""
    if not element: return "0"
    text = element.get_text(separator=' ', strip=True).replace('\xa0', ' ')
    # Ищем число перед словом 'рублей'
    match = re.search(r'(\d[\d\s]*)\s*рублей', text)
    if match:
        return re.sub(r'\D', '', match.group(1))
    # Если слова 'рублей' нет (в таблицах), берем просто все цифры
    digits = re.sub(r'\D', '', text)
    return digits if digits else "0"

def run_parser():
    base_url = "https://vuoksa-virta.ru"
    all_data = []
    
    try:
        print("--- Старт парсинга ---")
        response = requests.get(base_url, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        menu = soup.find(id='menu')
        
        if not menu: return "Ошибка: id='menu' не найден."
        
        # Собираем ссылки, превращая их в полные URL
        links = set()
        for a in menu.find_all('a', href=True):
            href = a['href']
            full_url = href if href.startswith('http') else f"{base_url}/{href.lstrip('/')}"
            links.add(full_url)

        for url in links:
            print(f"Парсим страницу: {url}")
            page_res = requests.get(url, timeout=15)
            page_soup = BeautifulSoup(page_res.content, 'html.parser')

            # --- А) Обычные объекты H3 ---
            for h3 in page_soup.find_all('h3', id=True):
                if h3.find_parent('figure', id=['priceShip', 'priceSauna']): continue
                title = h3.get_text(strip=True)
                # Ищем цену в следующем элементе или в родителе
                price = extract_price(h3.find_next())
                all_data.append((url, title, price, title))

            # --- Б) ЛОДКИ (id=priceShip) ---
            ship_fig = page_soup.find('figure', id='priceShip')
            if ship_fig:
                for row in ship_fig.find_all('tr')[1:]:
                    tds = row.find_all('td')
                    if len(tds) >= 3:
                        tariff = tds[0].get_text(strip=True)
                        p_in = extract_price(tds[1])
                        p_out = extract_price(tds[2])
                        all_data.append((url, "Прокат лодки Пелла", p_in, f"прокат лодки Пелла тариф {tariff} для проживающих"))
                        all_data.append((url, "Прокат лодки Пелла", p_out, f"прокат лодки Пелла тариф {tariff} для непроживающих"))

            # --- В) БАНЯ (id=priceSauna) ---
            sauna_fig = page_soup.find('figure', id='priceSauna')
            if sauna_fig:
                for row in sauna_fig.find_all('tr')[1:]:
                    tds = row.find_all('td')
                    if len(tds) >= 2:
                        p_in = extract_price(tds[0])
                        p_out = extract_price(tds[1])
                        all_data.append((url, "Баня на дровах", p_in, "баня на дровах для проживающих"))
                        all_data.append((url, "Баня на дровах", p_out, "баня на дровах для непроживающих"))

        if not all_data: return "Данные не найдены на страницах."

        # Запись в БД
        connection = pymysql.connect(**DB_CONFIG)
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM `parsed_content`")
                sql = "INSERT INTO `parsed_content` (`url`, `title`, `price`, `content`) VALUES (%s, %s, %s, %s)"
                cursor.executemany(sql, all_data)
                connection.commit()
            return f"✅ Успех! В базе {len(all_data)} записей."
        finally:
            connection.close()

    except Exception as e:
        return f"❌ Ошибка: {str(e)}"

@bot.message_handler(commands=['update'])
def handle_update(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "🔄 Обновляю...")
        result = run_parser()
        bot.send_message(message.chat.id, result)
    else:
        bot.send_message(message.chat.id, "🔐 Нет доступа.")

if __name__ == "__main__":
    bot.infinity_polling()
