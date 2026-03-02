import os
import re
import requests
import pymysql
from bs4 import BeautifulSoup

DB_CONFIG = {
    'host': 'mysql9.hostland.ru',
    'port': 3306,
    'user': 'host1324224',
    'password': os.environ.get('DB_PASSWORD', '807bba4c'),
    'database': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def extract_price(element):
    if not element: return "0"
    text = element.get_text(separator=' ', strip=True).replace('\xa0', ' ')
    match = re.search(r'(\d[\d\s]*)\s*рублей', text)
    if match: return re.sub(r'\D', '', match.group(1))
    digits = re.sub(r'\D', '', text)
    return digits if digits else "0"

def run_parser():
    base_url = "https://vuoksa-virta.ru"
    all_data = []
    try:
        soup = BeautifulSoup(requests.get(base_url, timeout=15).content, 'html.parser')
        menu = soup.find(id='menu')
        if not menu: return "Ошибка меню"
        
        links = { (l if l.startswith('http') else f"{base_url}/{l.lstrip('/')}") for l in [a['href'] for a in menu.find_all('a', href=True)] }

        for url in links:
            p_soup = BeautifulSoup(requests.get(url, timeout=15).content, 'html.parser')
            # Парсинг H3
            for h3 in p_soup.find_all('h3', id=True):
                if h3.find_parent('figure', id=['priceShip', 'priceSauna']): continue
                all_data.append((url, h3.get_text(strip=True), extract_price(h3.find_next()), h3.get_text(strip=True)))
            # Парсинг лодок (id=priceShip)
            ship = p_soup.find('figure', id='priceShip')
            if ship:
                for row in ship.find_all('tr')[1:]:
                    tds = row.find_all('td')
                    if len(tds) >= 3:
                        t = tds[0].get_text(strip=True)
                        all_data.append((url, "Прокат лодки Пелла", extract_price(tds[1]), f"прокат лодки Пелла тариф {t} для проживающих"))
                        all_data.append((url, "Прокат лодки Пелла", extract_price(tds[2]), f"прокат лодки Пелла тариф {t} для непроживающих"))
            # Баня (id=priceSauna)
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
                cur.executemany("INSERT INTO `parsed_content` (url, title, price, content) VALUES (%s,%s,%s,%s)", all_data)
                conn.commit()
            return f"✅ Обновлено! Строк: {len(all_data)}"
        return "Нет данных"
    except Exception as e: return f"Ошибка: {e}"
