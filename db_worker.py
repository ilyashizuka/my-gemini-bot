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

def get_house_data(h3_element):
    """Ищет цену домика (универсально для всех вариантов)"""
    current = h3_element.find_next_sibling()
    # Маркеры для поиска
    marker_long = "Стоимость (без учёта стоимости постельного белья):"
    marker_short = "Стоимость:"
    
    while current and current.name != 'h3':
        if current.name == 'p':
            text = current.get_text().replace('\xa0', ' ').strip()
            # Если нашли любой из маркеров стоимости
            if marker_short in text or marker_long in text:
                # Ищем число перед словом "рублей"
                match = re.search(r'Стоимость.*?\s*(\d[\d\s]*)\s*рублей', text)
                price = re.sub(r'\D', '', match.group(1)) if match else "0"
                return price, text
        current = current.find_next_sibling()
    return "0", h3_element.get_text(strip=True)

def run_parser():
    base_url = "https://vuoksa-virta.ru"
    all_data = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'}

    try:
        resp = requests.get(base_url, headers=headers, timeout=25)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        menu = soup.find(id='menu') or soup.find('nav')
        if not menu: return "Ошибка меню"

        links = set()
        for a in menu.find_all('a', href=True):
            href = a['href'].split('#')[0]
            if not href or href in ['/', 'index.html']: continue
            links.add(href if href.startswith('http') else f"{base_url}/{href.lstrip('/')}")
        
        links.add(base_url)

        for url in links:
            p_res = requests.get(url, headers=headers, timeout=15)
            p_res.encoding = 'utf-8'
            p_soup = BeautifulSoup(p_res.content, 'html.parser')

            # --- 1. ДОМИКИ ---
            for h3 in p_soup.find_all('h3', id=True):
                if h3['id'] in ['sauna', 'boat_rental', 'top', 'menu']: continue
                price, content = get_house_data(h3)
                all_data.append((f"{url}?#{h3['id']}", h3.get_text(strip=True), price, content))

            # --- 2. ЛОДКИ ---
            ship_fig = p_soup.find('figure', id='priceShip')
            if ship_fig:
                # Определяем название лодки (Мираж или Пелла) из заголовка таблицы
                caption = ship_fig.find('caption')
                ship_name = "Пелла" # По умолчанию
                if caption and "Мираж" in caption.get_text(): ship_name = "Мираж"
                
                rows = ship_fig.find_all('tr')[1:5]
                for i, row in enumerate(rows):
                    tds = row.find_all('td')
                    if len(tds) >= 3:
                        # Чистый тариф (День, Сутки и т.д.)
                        tariff = tds[0].get_text(strip=True).replace('тариф', '').replace('Тариф', '').strip()
                        p_in = re.sub(r'\D', '', tds[1].get_text())
                        p_out = re.sub(r'\D', '', tds[2].get_text())
                        
                        # Формат: Мираж День для проживающих
                        all_data.append((f"{url}#ship_in_{i}", "Прокат лодки", p_in, f"{ship_name} {tariff} для проживающих"))
                        all_data.append((f"{url}#ship_out_{i}", "Прокат лодки", p_out, f"{ship_name} {tariff} для непроживающих"))

            # --- 3. БАНЯ ---
            sauna_fig = p_soup.find('figure', id='priceSauna')
            if sauna_fig:
                rows = sauna_fig.find_all('tr')[1:]
                for i, row in enumerate(rows):
                    tds = row.find_all('td')
                    if len(tds) >= 2:
                        p_in = re.sub(r'\D', '', tds[0].get_text())
                        p_out = re.sub(r'\D', '', tds[1].get_text())
                        all_data.append((f"{url}#sauna_in_{i}", "Баня на дровах", p_in, "Баня на дровах для проживающих"))
                        all_data.append((f"{url}#sauna_out_{i}", "Баня на дровах", p_out, "Баня на дровах для непроживающих"))

        if all_data:
            conn = pymysql.connect(**DB_CONFIG)
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM `parsed_content`")
                    sql = "INSERT INTO `parsed_content` (url, title, price, content) VALUES (%s,%s,%s,%s)"
                    cur.executemany(sql, list(set(all_data)))
                    conn.commit()
                return f"✅ Успех! В базе {len(all_data)} строк."
            finally:
                conn.close()
        return "⚠️ Данные не найдены."
    except Exception as e:
        return f"❌ Ошибка: {e}"
