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
    """Ищет цену домика (цифру до 'рублей')"""
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
    all_data = [] 
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/145.0.0.0'}

    try:
        resp = requests.get(base_url, headers=headers, timeout=20)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.content, 'html.parser')

        # --- 1. ДОМИКИ (5 записей) ---
        house_ids = ['5-ka', 'homewithsauna', 'figwam', 'nomernadellingom', 'studia']
        for hid in house_ids:
            h3 = soup.find('h3', id=hid)
            if h3:
                price = get_house_price(h3)
                all_data.append((f"{base_url}#{hid}", h3.get_text(strip=True), price, ""))

        # --- 2. ПРОКАТ ЛОДОК (8 записей) ---
        for fig in soup.find_all('figure', id=re.compile(r'^priceShip')):
            # Определяем марку лодки (Мираж или Пелла)
            caption = fig.find('caption')
            ship_brand = "Мираж" if caption and "Мираж" in caption.get_text() else "Пелла"
            
            # Находим заголовки колонок (второй и третий td первой строки tr)
            rows = fig.find_all('tr')
            header_cells = rows[0].find_all('td')
            # Заголовки: "Для проживающих", "Без проживания"
            col_name_2 = header_cells[1].get_text(strip=True) if len(header_cells) > 1 else "Для проживающих"
            col_name_3 = header_cells[2].get_text(strip=True) if len(header_cells) > 2 else "Без проживания"

            # Тарифы (обычно строки 1 и 2 после заголовка)
            data_rows = rows[1:3] 
            for row in data_rows:
                tds = row.find_all('td')
                if len(tds) >= 3:
                    # Из первой колонки берем тариф (например, "тариф День")
                    raw_tariff = tds[0].get_text(strip=True)
                    # Склеиваем по твоей матрице: [Марка] [Тариф] [Заголовок столбца]
                    full_name_base = f"{ship_brand} {raw_tariff}"
                    
                    price_2 = re.sub(r'\D', '', tds[1].get_text()) # Цена во 2-м столбце
                    price_3 = re.sub(r'\D', '', tds[2].get_text()) # Цена в 3-м столбце
                    
                    # Запись 1: Для проживающих
                    all_data.append((f"{base_url}#{ship_brand}_{raw_tariff}_in", "Прокат лодки", price_2, f"{full_name_base} {col_name_2}"))
                    # Запись 2: Без проживания
                    all_data.append((f"{base_url}#{ship_brand}_{raw_tariff}_out", "Прокат лодки", price_3, f"{full_name_base} {col_name_3}"))

        # --- 3. БАНЯ НА ДРОВАХ (2 записи) ---
        sauna_fig = soup.find('figure', id='priceSauna')
        if sauna_fig:
            rows = sauna_fig.find_all('tr')
            header_cells = rows[0].find_all('td')
            col_name_1 = header_cells[0].get_text(strip=True) # Для проживающих
            col_name_2 = header_cells[1].get_text(strip=True) # Без проживания
            
            data_cells = rows[1].find_all('td')
            if len(data_cells) >= 2:
                p_in = re.sub(r'\D', '', data_cells[0].get_text())
                p_out = re.sub(r'\D', '', data_cells[1].get_text())
                
                all_data.append((f"{base_url}#sauna_in", "Баня на дровах", p_in, col_name_1))
                all_data.append((f"{base_url}#sauna_out", "Баня на дровах", p_out, col_name_2))

        # --- ЗАПИСЬ В БД ---
        if all_data:
            conn = pymysql.connect(**DB_CONFIG)
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM `parsed_content`")
                    sql = "INSERT INTO `parsed_content` (url, title, price, content) VALUES (%s, %s, %s, %s)"
                    cur.executemany(sql, all_data)
                    conn.commit()
                return f"✅ Успех! В базе ровно {len(all_data)} строк."
            finally:
                conn.close()
        return "⚠️ Данные не найдены."

    except Exception as e:
        return f"❌ Ошибка: {e}"
