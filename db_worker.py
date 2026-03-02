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
                # Поле content для домиков строго ПУСТОЕ
                all_data.append((f"{base_url}#{hid}", h3.get_text(strip=True), price, ""))

        # --- 2. ПРОКАТ ЛОДОК (8 записей) ---
        ship_fig = soup.find('figure', id='priceShip')
        if ship_fig:
            table = ship_fig.find('table')
            # Вытаскиваем заголовки из thead (второй и третий th)
            headers_cells = table.find('thead').find_all('th')
            col_in_name = headers_cells[1].get_text(strip=True).replace(':', '') # Для проживающих
            col_out_name = headers_cells[2].get_text(strip=True).replace(':', '') # Без проживания

            # Идем по строкам tbody
            rows = table.find('tbody').find_all('tr')
            for i, row in enumerate(rows):
                tds = row.find_all('td')
                if len(tds) >= 3:
                    # Текст из первой колонки (например, "Мираж тариф День:")
                    row_label = tds[0].get_text(strip=True).replace(':', '')
                    
                    price_in = re.sub(r'\D', '', tds[1].get_text())
                    price_out = re.sub(r'\D', '', tds[2].get_text())
                    
                    # Запись 1: Мираж тариф День Для проживающих
                    all_data.append((f"{base_url}#boat_in_{i}", "Прокат лодки", price_in, f"{row_label} {col_in_name}"))
                    # Запись 2: Мираж тариф День Без проживания
                    all_data.append((f"{base_url}#boat_out_{i}", "Прокат лодки", price_out, f"{row_label} {col_out_name}"))

        # --- 3. БАНЯ НА ДРОВАХ (2 записи) ---
        sauna_fig = soup.find('figure', id='priceSauna')
        if sauna_fig:
            table = sauna_fig.find('table')
            # У бани заголовки могут быть в первой строке tr, если нет thead
            head_row = table.find('tr')
            h_cells = head_row.find_all(['td', 'th'])
            b_in_name = h_cells[0].get_text(strip=True).replace(':', '')
            b_out_name = h_cells[1].get_text(strip=True).replace(':', '')

            # Берем последнюю строку с ценами
            data_row = table.find_all('tr')[-1]
            tds = data_row.find_all('td')
            if len(tds) >= 2:
                p_in = re.sub(r'\D', '', tds[0].get_text())
                p_out = re.sub(r'\D', '', tds[1].get_text())
                all_data.append((f"{base_url}#sauna_in", "Баня на дровах", p_in, b_in_name))
                all_data.append((f"{base_url}#sauna_out", "Баня на дровах", p_out, b_out_name))

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
