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
    'password': os.environ.get('DB_PASSWORD', '807bba4c'),
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
    
    # Имитируем реального пользователя
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
    }

    try:
        print(f"--- Запуск парсинга {base_url} ---")
        response = requests.get(base_url, headers=headers, timeout=20)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Ищем меню (пробуем разные варианты, если id изменился)
        menu = soup.find(id='menu') or soup.find('nav') or soup.find(class_='menu')
        
        if not menu:
            print("ОШИБКА: Блок меню не найден в HTML!")
            return "Ошибка меню: не найден блок id='menu' на главной."
        
        # Собираем уникальные ссылки из меню
        links = set()
        for a in menu.find_all('a', href=True):
            href = a['href']
            # Отрезаем якоря типа #sauna, оставляем только путь к странице
            clean_href = href.split('#')[0]
            if not clean_href or clean_href == '/': continue
            
            full_url = clean_href if clean_href.startswith('http') else f"{base_url}/{clean_href.lstrip('/')}"
            links.add(full_url)

        print(f"Найдено страниц для обхода: {len(links)}")

        for url in links:
            try:
                p_res = requests.get(url, headers=headers, timeout=15)
                p_res.encoding = 'utf-8'
                p_soup = BeautifulSoup(p_res.content, 'html.parser')

                # --- 1. Объекты через H3 с ID ---
                for h3 in p_soup.find_all('h3', id=True):
                    if h3.find_parent('figure', id=['priceShip', 'priceSauna']): continue
                    title = h3.get_text(strip=True)
                    # Ищем цену в следующем элементе
                    price = extract_price(h3.find_next())
                    all_data.append((url, title, price, title))

                # --- 2. Таблица ЛОДКИ (id=priceShip) ---
                ship_fig = p_soup.find('figure', id='priceShip')
                if ship_fig:
                    for row in ship_fig.find_all('tr')[1:]:
                        tds = row.find_all('td')
                        if len(tds) >= 3:
                            tariff = tds[0].get_text(strip=True)
                            p_in = extract_price(tds[1])
                            p_out = extract_price(tds[2])
                            
                            all_data.append((url, "Прокат лодки Пелла", p_in, f"прокат лодки Пелла тариф {tariff} для проживающих"))
                            all_data.append((url, "Прокат лодки Пелла", p_out, f"прокат лодки Пелла тариф {tariff} для непроживающих"))

                # --- 3. Таблица БАНЯ (id=priceSauna) ---
                sauna_fig = p_soup.find('figure', id='priceSauna')
                if sauna_fig:
                    for row in sauna_fig.find_all('tr')[1:]:
                        tds = row.find_all('td')
                        if len(tds) >= 2:
                            p_in = extract_price(tds[0])
                            p_out = extract_price(tds[1])
                            
                            all_data.append((url, "Баня на дровах", p_in, "баня на дровах для проживающих"))
                            all_data.append((url, "Баня на дровах", p_out, "баня на дровах для непроживающих"))
            except Exception as e:
                print(f"Ошибка при парсинге страницы {url}: {e}")
                continue

        # --- ЗАПИСЬ В БД ---
        if all_data:
            connection = pymysql.connect(**DB_CONFIG)
            try:
                with connection.cursor() as cursor:
                    # Чистим старое
                    cursor.execute("DELETE FROM `parsed_content`")
                    # Вставляем новое
                    sql = "INSERT INTO `parsed_content` (url, title, price, content) VALUES (%s, %s, %s, %s)"
                    cursor.executemany(sql, all_data)
                    connection.commit()
                return f"✅ База успешно обновлена! Найдено услуг: {len(all_data)}"
            finally:
                connection.close()
        
        return "⚠️ Парсер отработал, но данных не нашел."

    except Exception as e:
        return f"❌ Критическая ошибка парсера: {str(e)}"
