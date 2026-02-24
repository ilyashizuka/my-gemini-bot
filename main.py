import requests
import hashlib
import os
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from db_worker import save_to_db

SITEMAP_URL = "https://vuoksa-virta.ru"
HASH_FILE = "sitemap_hash.txt"

def extract_data(url):
    """Парсит страницу: ищет цену и телефон"""
    try:
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Поиск цены: ищем число перед "руб" или "рублей"
        # Регулярка ищет числа (с пробелами внутри), за которыми следует "руб"
        price_match = re.search(r'(\d[\d\s]*)руб(?:лей|ль|ля)?', soup.get_text())
        price = price_match.group(1).replace('\s', '').strip() if price_match else "0"
        
        # 2. Поиск телефона в атрибуте href="tel:..."
        phone_tag = soup.find('a', href=re.compile(r'^tel:\+7'))
        phone = phone_tag['href'].replace('tel:', '') if phone_tag else "Не найден"
        
        title = soup.title.string if soup.title else "Без заголовка"
        
        return title, price, phone
    except Exception as e:
        print(f"Ошибка при парсинге {url}: {e}")
        return None

def parse_sitemap(xml_content):
    root = ET.fromstring(xml_content)
    namespace = {'ns': 'http://www.sitemaps.org'}
    urls = [loc.text for loc in root.findall('.//ns:loc', namespace)]
    
    for url in urls:
        print(f"Обработка: {url}")
        result = extract_data(url)
        if result:
            title, price, phone = result
            # Сохраняем в базу (добавьте колонку phone в вашу таблицу)
            save_to_db(url, title, f"Цена: {price}, Тел: {phone}")

def check_and_run():
    # ... (код проверки хеша из предыдущего сообщения остается без изменений)
    pass 

if __name__ == "__main__":
    check_and_run()
