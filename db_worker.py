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
    """Ищет цену и полное описание (маркер) в абзацах под h3"""
    current = h3_element.find_next_sibling()
    marker = "Стоимость (без учёта стоимости постельного белья):"
    
    while current and current.name != 'h3':
        if current.name == 'p':
            text = current.get_text().replace('\xa0', ' ').strip()
            if marker in text:
                # 1. Извлекаем только цифры для поля price
                match = re.search(r'белья\):\s*(\d[\d\s]*)\s*рублей', text)
                price = re.sub(r'\D', '', match.group(1)) if match else "0"
                # 2. Возвращаем кортеж (цена, полный текст описания)
                return price, text
        current = current.find_next_sibling()
    return "0", h3_element.get_text(strip=True)

def run_parser():
    base_url = "https://vuoksa-virta.ru"
    all_data = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0'}
    exclude_anchors = ['sauna', 'boat_rental']

    try:
        resp = requests.get(base_url, headers=headers, timeout=20)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.content, 'html.parser')
        menu = soup.find(id='menu')
        if not menu: return "Ошибка меню"
        
        links = set()
        for a in menu.find_all('a', href=True):
            href = a['href'].split('#')
            if not href or href in ['/', 'index.html']: continue
            links.add(href if href.startswith('http') else f"{base_url}/{href.lstrip('/')}")

        for url in links:
            p_res = requests.get(url, headers=headers, timeout=15)
            p_res.encoding = 'utf-8'
            p_soup = BeautifulSoup(p_res.content, 'html.parser')

            # --- 1. ДОМИКИ ---
            for h3 in p_soup.find_all('h3', id=True):
                anchor = h3['id']
                if anchor in exclude_anchors: continue
                
                title = h3.get_text(strip=True)
                price, content = get_house_data(h3)
                
                all_data.append((f"{url}?#{anchor}", title, price, content))

            # --- 2. ЛОДКИ ---
            ship_fig = p_soup.find('figure', id='priceShip')
            if ship_fig:
                rows = ship_fig.find_all('tr')[1:5] # Строки 2-5
                for i, row in enumerate(rows):
                    tds = row.find_all('td')
                    if len(tds) >= 3:
                        # Берем чистый тариф из первой колонки
                        raw_t = tds[0].get_text(strip=True).replace('тариф', '').replace('Тариф', '').strip()
                        p_in = re.sub(r'\D', '', tds[1].get_text())
                        p_out = re.sub(r'\D', '', tds[2].get_text())
                        
                        # Формат: Пелла тариф День: для проживающих
                        all_data.append((f"{url}#ship_in_{i}", "Прокат лодки Пелла", p_in, f"Пелла тариф {raw_t}: для проживающих"))
                        all_data.append((f"{url}#ship_out_{i}", "Прокат лодки Пелла", p_out, f"Пелла тариф {raw_t}: для непроживающих"))

            # --- 3. БАНЯ ---
            sauna_fig = p_soup.find('figure', id='priceSauna')
            if sauna_fig:
                rows = sauna_fig.find_all('tr')[1:]
                for i, row in enumerate(rows):
                    tds = row.find_all('td')
                    if len(tds) >= 2:
                        p_in = re.sub(r'\D', '', tds[0].get_text())
                        p_out = re.sub(r'\D', '', tds[1].get_text())
                        all_data.append((f"{url}#sauna_in_{i}", "Баня на дровах", p_in, "баня на дровах: для проживающих"))
                        all_data.append((f"{url}#sauna_out_{i}", "Баня на дровах", p_out, "баня на дровах: для непроживающих"))

        if all_data:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                cur.execute("DELETE FROM `parsed_content`")
                cur.executemany("INSERT INTO `parsed_content` (url, title, price, content) VALUES (%s,%s,%s,%s)", all_data)
                conn.commit()
            return f"✅ Успех! Обновлено строк: {len(all_data)}"
        return "Данные не найдены."
    except Exception as e:
        return f"Критическая ошибка: {e}"
