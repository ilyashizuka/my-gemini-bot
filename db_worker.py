import os
import re
import requests
import pymysql
from bs4 import BeautifulSoup

DB_CONFIG = {
    'host': 'mysql9.hostland.ru',
    'port': 3306,
    'user': 'host1324224',
    'password': os.environ.get('DB_PASSWORD'),
    'database': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_house_price(h3_element):
    """Ищет цену домика (7000 для Пятерки и т.д.)"""
    current = h3_element.find_next_sibling()
    while current and current.name != 'h3':
        if current.name == 'p':
            text = current.get_text().replace('\xa0', ' ').strip()
            if "Стоимость" in text:
                match = re.search(r'Стоимость.*?\s*(\d[\d\s]*)\s*рублей', text)
                if match: return re.sub(r'\D', '', match.group(1))
        current = current.find_next_sibling()
    return "0"

def run_parser():
    base_url = "https://vuoksa-virta.ru"
    all_data = [] # Список кортежей (url, title, price, content)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/140.0.0.0'}

    try:
        resp = requests.get(base_url, headers=headers, timeout=20)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.content, 'html.parser')

        # --- 1. ДОМИКИ (5 штук) ---
        house_anchors = ['5-ka', 'homewithsauna', 'figwam', 'nomernadellingom', 'studia']
        for anchor in house_anchors:
            h3 = soup.find('h3', id=anchor)
            if h3:
                price = get_house_price(h3)
                all_data.append((f"{base_url}#{anchor}", h3.get_text(strip=True), price, ""))

        # --- 2. ЛОДКИ (8 записей: Мираж и Пелла по 4 записи каждая) ---
        # Ищем все таблицы (figure), у которых id начинается на priceShip
        for fig in soup.find_all('figure', id=re.compile(r'^priceShip')):
            caption = fig.find('caption')
            # Определяем имя лодки из заголовка таблицы
            ship_name = "Мираж" if caption and "Мираж" in caption.get_text() else "Пелла"
            
            # Берем первые две строки с данными (День и Сутки)
            rows = fig.find_all('tr')[1:3] 
            for row in rows:
                tds = row.find_all('td')
                if len(tds) >= 3:
                    tariff = tds[0].get_text(strip=True).replace('тариф', '').strip()
                    price_in = re.sub(r'\D', '', tds[1].get_text())
                    price_out = re.sub(r'\D', '', tds[2].get_text())
                    
                    # Запись для Своих
                    all_data.append((
                        f"{base_url}#{ship_name}_{tariff}_svoi", 
                        "Прокат лодки", 
                        price_in, 
                        f"{ship_name} {tariff} свои"
                    ))
                    # Запись для Пришлых
                    all_data.append((
                        f"{base_url}#{ship_name}_{tariff}_prishlie", 
                        "Прокат лодки", 
                        price_out, 
                        f"{ship_name} {tariff} пришлые"
                    ))

        # --- 3. БАНЯ (2 записи) ---
        sauna_fig = soup.find('figure', id='priceSauna')
        if sauna_fig:
            row = sauna_fig.find_all('tr')[1] # Первая строка цен
            tds = row.find_all('td')
            if len(tds) >= 2:
                p_in = re.sub(r'\D', '', tds[0].get_text())
                p_out = re.sub(r'\D', '', tds[1].get_text())
                all_data.append((f"{base_url}#sauna_svoi", "Баня на дровах", p_in, "свои"))
                all_data.append((f"{base_url}#sauna_prishlie", "Баня на дровах", p_out, "пришлые"))

        # --- ЗАПИСЬ В БД ---
        if all_data:
            conn = pymysql.connect(**DB_CONFIG)
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM `parsed_content`")
                    sql = "INSERT INTO `parsed_content` (url, title, price, content) VALUES (%s, %s, %s, %s)"
                    cur.executemany(sql, all_data)
                    conn.commit()
                return f"✅ Успешно! В базе ровно {len(all_data)} строк."
            finally:
                conn.close()
        return "⚠️ Данные не найдены."

    except Exception as e:
        return f"❌ Ошибка парсера 2026: {e}"
