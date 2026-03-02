import os
import re
import requests
import pymysql
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
    current = h3_element.find_next_sibling()
    marker = "Стоимость (без учёта стоимости постельного белья):"
    while current and current.name != 'h3':
        if current.name == 'p':
            text = current.get_text().replace('\xa0', ' ').strip()
            if marker in text:
                match = re.search(r'белья\):\s*(\d[\d\s]*)\s*рублей', text)
                price = re.sub(r'\D', '', match.group(1)) if match else "0"
                return price, text
        current = current.find_next_sibling()
    return "0", h3_element.get_text(strip=True)

def run_parser():
    base_url = "https://vuoksa-virta.ru"
    all_data = []
    
    # Настраиваем сессию с повторными попытками
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.google.com'
    }

    try:
        # 1. Загружаем главную
        resp = session.get(base_url, headers=headers, timeout=20)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Ищем меню (пробуем разные варианты)
        menu = soup.find(id='menu') or soup.find('nav') or soup.find(class_='menu')
        
        if not menu:
            # Если не нашли, выводим начало HTML в логи для отладки
            print(f"DEBUG HTML: {resp.text[:500]}")
            return "Ошибка меню: сайт не отдал блок навигации."
        
        links = set()
        for a in menu.find_all('a', href=True):
            href = a['href'].split('#')[0]
            if not href or href in ['/', 'index.html']: continue
            full_url = href if href.startswith('http') else f"{base_url}/{href.lstrip('/')}"
            if "vuoksa-virta.ru" in full_url:
                links.add(full_url)

        # 2. Обход страниц
        for url in links:
            try:
                p_res = session.get(url, headers=headers, timeout=15)
                p_res.encoding = 'utf-8'
                p_soup = BeautifulSoup(p_res.content, 'html.parser')

                # Домики
                for h3 in p_soup.find_all('h3', id=True):
                    if h3['id'] in ['sauna', 'boat_rental']: continue
                    price, content = get_house_data(h3)
                    all_data.append((f"{url}?#{h3['id']}", h3.get_text(strip=True), price, content))

                # Лодки
                ship = p_soup.find('figure', id='priceShip')
                if ship:
                    for i, row in enumerate(ship.find_all('tr')[1:5]):
                        tds = row.find_all('td')
                        if len(tds) >= 3:
                            raw_t = tds[0].get_text(strip=True).replace('тариф', '').replace('Тариф', '').strip()
                            p_in = re.sub(r'\D', '', tds[1].get_text())
                            p_out = re.sub(r'\D', '', tds[2].get_text())
                            all_data.append((f"{url}#ship_in_{i}", "Прокат лодки Пелла", p_in, f"Пелла тариф {raw_t}: для проживающих"))
                            all_data.append((f"{url}#ship_out_{i}", "Прокат лодки Пелла", p_out, f"Пелла тариф {raw_t}: для непроживающих"))

                # Баня
                sauna = p_soup.find('figure', id='priceSauna')
                if sauna:
                    for i, row in enumerate(sauna.find_all('tr')[1:]):
                        tds = row.find_all('td')
                        if len(tds) >= 2:
                            p_in = re.sub(r'\D', '', tds[0].get_text())
                            p_out = re.sub(r'\D', '', tds[1].get_text())
                            all_data.append((f"{url}#sauna_in_{i}", "Баня на дровах", p_in, "баня на дровах: для проживающих"))
                            all_data.append((f"{url}#sauna_out_{i}", "Баня на дровах", p_out, "баня на дровах: для непроживающих"))
            except Exception as e:
                print(f"Ошибка на {url}: {e}")
                continue

        if all_data:
            conn = pymysql.connect(**DB_CONFIG)
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM `parsed_content`")
                    sql = "INSERT INTO `parsed_content` (url, title, price, content) VALUES (%s, %s, %s, %s)"
                    cur.executemany(sql, all_data)
                    conn.commit()
                return f"✅ Успех! В базе {len(all_data)} строк."
            finally:
                conn.close()
        return "⚠️ Данные не найдены."
    except Exception as e:
        return f"❌ Ошибка: {e}"
