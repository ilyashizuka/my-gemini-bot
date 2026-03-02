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
    if match:
        return re.sub(r'\D', '', match.group(1))
    digits = re.sub(r'\D', '', text)
    return digits if digits else "0"

def run_parser():
    base_url = "https://vuoksa-virta.ru"
    all_data = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}

    try:
        response = requests.get(base_url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.content, 'html.parser')
        menu = soup.find(id='menu')
        if not menu: return "Ошибка меню"
        
        links = set()
        for a in menu.find_all('a', href=True):
            href = a['href'].split('#')[0] # Убираем старые якоря
            if not href or href == '/': continue
            links.add(href if href.startswith('http') else f"{base_url}/{href.lstrip('/')}")

        for url in links:
            try:
                p_res = requests.get(url, headers=headers, timeout=15)
                p_soup = BeautifulSoup(p_res.content, 'html.parser')

                # 1. H3 объекты
                for h3 in p_soup.find_all('h3', id=True):
                    if h3.find_parent('figure', id=['priceShip', 'priceSauna']): continue
                    title = h3.get_text(strip=True)
                    price = extract_price(h3.find_next())
                    # Чтобы URL был уникальным для PRIMARY KEY, добавляем ID объекта
                    unique_url = f"{url}#{h3['id']}"
                    all_data.append((unique_url, title, price, title))

                # 2. Лодки
                ship = p_soup.find('figure', id='priceShip')
                if ship:
                    for i, row in enumerate(ship.find_all('tr')[1:]):
                        tds = row.find_all('td')
                        if len(tds) >= 3:
                            t = tds[0].get_text(strip=True)
                            p_in = extract_price(tds[1])
                            p_out = extract_price(tds[2])
                            # Генерируем уникальные URL для каждой строки тарифа
                            all_data.append((f"{url}#ship_in_{i}", "Прокат лодки Пелла", p_in, f"прокат лодки Пелла тариф {t} для проживающих"))
                            all_data.append((f"{url}#ship_out_{i}", "Прокат лодки Пелла", p_out, f"прокат лодки Пелла тариф {t} для непроживающих"))

                # 3. Баня
                sauna = p_soup.find('figure', id='priceSauna')
                if sauna:
                    for i, row in enumerate(sauna.find_all('tr')[1:]):
                        tds = row.find_all('td')
                        if len(tds) >= 2:
                            p_in = extract_price(tds[0])
                            p_out = extract_price(tds[1])
                            all_data.append((f"{url}#sauna_in_{i}", "Баня на дровах", p_in, "баня на дровах для проживающих"))
                            all_data.append((f"{url}#sauna_out_{i}", "Баня на дровах", p_out, "баня на дровах для непроживающих"))
            except: continue

        if all_data:
            connection = pymysql.connect(**DB_CONFIG)
            try:
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM `parsed_content`")
                    # Вставляем данные. Теперь URL всегда разные из-за знака #
                    sql = "INSERT INTO `parsed_content` (url, title, price, content) VALUES (%s, %s, %s, %s)"
                    cursor.executemany(sql, all_data)
                    connection.commit()
                return f"✅ Успех! В базе {len(all_data)} строк."
            finally:
                connection.close()
        return "Данные не найдены"
    except Exception as e:
        return f"Критическая ошибка: {e}"
