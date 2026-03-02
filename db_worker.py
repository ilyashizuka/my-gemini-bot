import os
import re
import requests
import pymysql
from bs4 import BeautifulSoup

# Настройки БД из секретов Render
DB_CONFIG = {
    'host': 'mysql9.hostland.ru',
    'port': 3306,
    'user': 'host1324224',
    'password': os.environ.get('DB_PASSWORD'),
    'database': 'host1324224_botanik',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def extract_price(element):
    """Ищет число перед 'рублей' или просто цифры в блоке"""
    if not element: return "0"
    text = element.get_text(separator=' ', strip=True).replace('\xa0', ' ')
    # Сначала ищем по ключевому слову 'рублей'
    match = re.search(r'(\d[\d\s]*)\s*рублей', text)
    if match:
        return re.sub(r'\D', '', match.group(1))
    # Если слова нет, забираем все цифры (для ячеек таблиц)
    digits = re.sub(r'\D', '', text)
    return digits if digits else "0"

def run_parser():
    base_url = "https://vuoksa-virta.ru"
    all_data = []
    
    # Имитируем реального пользователя (Headers)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://google.com'
    }

    try:
        print(f"--- Старт парсинга: {base_url} ---")
        response = requests.get(base_url, headers=headers, timeout=25)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return f"Ошибка: сайт ответил кодом {response.status_code}"
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Ищем меню (id=menu или nav)
        menu = soup.find(id='menu') or soup.find('nav')
        
        if not menu:
            print(f"DEBUG: Меню не найдено. HTML length: {len(response.text)}")
            return "Ошибка меню: не найден блок id='menu' на главной."
        
        # Собираем ссылки (очищаем от якорей)
        links = set()
        for a in menu.find_all('a', href=True):
            href = a['href'].split('#')[0] # Берем только путь до #
            if not href or href in ['/', 'index.html']: continue
            
            full_url = href if href.startswith('http') else f"{base_url}/{href.lstrip('/')}"
            if "vuoksa-virta.ru" in full_url:
                links.add(full_url)

        print(f"Найдено страниц для парсинга: {len(links)}")

        # --- ЦИКЛ ПО СТРАНИЦАМ ---
        for url in links:
            try:
                p_res = requests.get(url, headers=headers, timeout=15)
                p_res.encoding = 'utf-8'
                p_soup = BeautifulSoup(p_res.content, 'html.parser')
                print(f"Обработка: {url}")

                # 1. Объекты через H3 с ID (домики)
                for h3 in p_soup.find_all('h3', id=True):
                    if h3.find_parent('figure', id=['priceShip', 'priceSauna']): continue
                    title = h3.get_text(strip=True)
                    price = extract_price(h3.find_next())
                    # Уникальный URL для PRIMARY KEY (урл + якорь из id в h3)
                    unique_url = f"{url}#{h3['id']}"
                    all_data.append((unique_url, title, price, title))

                # 2. Таблица ЛОДКИ (priceShip)
                ship_fig = p_soup.find('figure', id='priceShip')
                if ship_fig:
                    for i, row in enumerate(ship_fig.find_all('tr')[1:]):
                        tds = row.find_all('td')
                        if len(tds) >= 3:
                            tariff = tds[0].get_text(strip=True)
                            p_in = extract_price(tds[1])
                            p_out = extract_price(tds[2])
                            all_data.append((f"{url}#ship_in_{i}", "Прокат лодки Пелла", p_in, f"прокат лодки Пелла тариф {tariff} для проживающих"))
                            all_data.append((f"{url}#ship_out_{i}", "Прокат лодки Пелла", p_out, f"прокат лодки Пелла тариф {tariff} для непроживающих"))

                # 3. Таблица БАНЯ (priceSauna)
                sauna_fig = p_soup.find('figure', id='priceSauna')
                if sauna_fig:
                    for i, row in enumerate(sauna_fig.find_all('tr')[1:]):
                        tds = row.find_all('td')
                        if len(tds) >= 2:
                            p_in = extract_price(tds[0])
                            p_out = extract_price(tds[1])
                            all_data.append((f"{url}#sauna_in_{i}", "Баня на дровах", p_in, "баня на дровах для проживающих"))
                            all_data.append((url + f"#sauna_out_{i}", "Баня на дровах", p_out, "баня на дровах для непроживающих"))
            except Exception as e:
                print(f"Ошибка на {url}: {e}")
                continue

        # --- ЗАПИСЬ В БД ---
        if all_data:
            connection = pymysql.connect(**DB_CONFIG)
            try:
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM `parsed_content`") # Очистка
                    sql = "INSERT INTO `parsed_content` (url, title, price, content) VALUES (%s, %s, %s, %s)"
                    cursor.executemany(sql, all_data)
                    connection.commit()
                return f"✅ Успех! В базе {len(all_data)} строк."
            finally:
                connection.close()
        
        return "⚠️ Парсер не нашел данных на страницах."

    except Exception as e:
        return f"❌ Критическая ошибка: {str(e)}"
