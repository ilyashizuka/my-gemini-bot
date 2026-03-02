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

def extract_house_price(soup_element):
    """Ищет цену домика по конкретной фразе"""
    full_text = soup_element.get_text(separator=' ', strip=True).replace('\xa0', ' ')
    # Ищем число между фразой про белье и словом рублей
    pattern = r'Стоимость\s*\(без\s*учёта\s*стоимости\s*постельного\s*белья\):\s*(\d[\d\s]*)\s*рублей'
    match = re.search(pattern, full_text)
    if match:
        return re.sub(r'\D', '', match.group(1))
    return "0"

def extract_simple_price(element):
    """Для таблиц: просто берет цифры из ячейки"""
    if not element: return "0"
    text = element.get_text(strip=True).replace('\xa0', ' ')
    digits = re.sub(r'\D', '', text)
    return digits if digits else "0"

def run_parser():
    base_url = "https://vuoksa-virta.ru"
    all_data = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0'}
    
    # Список якорей, которые НЕ НУЖНО вносить в базу
    exclude_anchors = ['sauna', 'boat_rental']

    try:
        resp = requests.get(base_url, headers=headers, timeout=20)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.content, 'html.parser')
        menu = soup.find(id='menu') or soup.find('nav')
        if not menu: return "Ошибка меню"
        
        links = set()
        for a in menu.find_all('a', href=True):
            href = a['href'].split('#')[0]
            if not href or href in ['/', 'index.html']: continue
            links.add(href if href.startswith('http') else f"{base_url}/{href.lstrip('/')}")

        for url in links:
            p_res = requests.get(url, headers=headers, timeout=15)
            p_res.encoding = 'utf-8'
            p_soup = BeautifulSoup(p_res.content, 'html.parser')

            # --- 1. Домики (H3 с ID) ---
            for h3 in p_soup.find_all('h3', id=True):
                anchor = h3['id']
                if anchor in exclude_anchors: continue
                
                title = h3.get_text(strip=True)
                # Ищем цену в родительском блоке секции домика
                parent_section = h3.find_parent('section') or h3.parent
                price = extract_house_price(parent_section)
                
                all_data.append((f"{url}?#{anchor}", title, price, title))

            # --- 2. Таблица ЛОДКИ (priceShip) ---
            ship_fig = p_soup.find('figure', id='priceShip')
            if ship_fig:
                # Пропускаем заголовок, берем строки со 2-й по 5-ю (индексы 1-4)
                rows = ship_fig.find_all('tr')[1:5]
                for i, row in enumerate(rows):
                    tds = row.find_all('td')
                    if len(tds) >= 3:
                        tariff = tds[0].get_text(strip=True).replace('тариф ', '').replace('Тариф ', '')
                        p_in = extract_simple_price(tds[1])
                        p_out = extract_simple_price(tds[2])
                        
                        all_data.append((f"{url}#ship_in_{i}", "Прокат лодки Пелла", p_in, f"прокат лодки Пелла тариф {tariff} для проживающих"))
                        all_data.append((f"{url}#ship_out_{i}", "Прокат лодки Пелла", p_out, f"прокат лодки Пелла тариф {tariff} для непроживающих"))

            # --- 3. Таблица БАНЯ (priceSauna) ---
            sauna_fig = p_soup.find('figure', id='priceSauna')
            if sauna_fig:
                rows = sauna_fig.find_all('tr')[1:]
                for i, row in enumerate(rows):
                    tds = row.find_all('td')
                    if len(tds) >= 2:
                        p_in = extract_simple_price(tds[0])
                        p_out = extract_simple_price(tds[1])
                        all_data.append((f"{url}#sauna_in_{i}", "Баня на дровах", p_in, "баня на дровах для проживающих"))
                        all_data.append((f"{url}#sauna_out_{i}", "Баня на дровах", p_out, "баня на дровах для непроживающих"))

        if all_data:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                cur.execute("DELETE FROM `parsed_content`")
                cur.executemany("INSERT INTO `parsed_content` (url, title, price, content) VALUES (%s, %s, %s, %s)", all_data)
                conn.commit()
            return f"✅ Успех! Обновлено строк: {len(all_data)}"
        return "Данные не найдены."
    except Exception as e:
        return f"Критическая ошибка: {e}"
