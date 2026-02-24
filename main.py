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
    """Парсит страницу: ищет заголовок, цену и телефон"""
    try:
        # Добавили Headers, чтобы сайт не блокировал парсер
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Поиск цены (число перед руб/рублей)
        # Ищет конструкции типа "1 500 руб" или "Цена: 12000рублей"
        full_text = soup.get_text()
        price_match = re.search(r'(\d[\d\s\xa0]*)руб', full_text)
        price = "0"
        if price_match:
            # Очищаем от пробелов и спецсимволов
            price = re.sub(r'[^\d]', '', price_match.group(1))
        
        # 2. Поиск телефона в формате tel:+7...
        phone_tag = soup.find('a', href=re.compile(r'^tel:\+7'))
        phone = phone_tag['href'].replace('tel:', '') if phone_tag else "Не найден"
        
        # 3. Заголовок
        title = soup.title.string.strip() if soup.title else "Без заголовка"
        
        # 4. Весь текст (контент) для поиска
        content = soup.get_text(separator=' ', strip=True)[:2000] # Берем первые 2000 символов
        
        return title, price, phone, content

    except Exception as e:
        print(f"Ошибка при парсинге {url}: {e}")
        return None

def parse_sitemap(xml_content):
    """Разбирает sitemap и запускает цикл по всем URL"""
    try:
        root = ET.fromstring(xml_content)
        namespace = {'ns': 'http://www.sitemaps.org'}
        urls = [loc.text for loc in root.findall('.//ns:loc', namespace)]
        
        print(f"Найдено ссылок: {len(urls)}")
        
        for url in urls:
            print(f"Парсим: {url}")
            data = extract_data(url)
            if data:
                title, price, phone, content = data
                save_to_db(url, title, price, phone, content)
                print(f"--- Сохранено: {price} руб., Тел: {phone}")
                
    except Exception as e:
        print(f"Ошибка XML: {e}")

def check_and_run():
    """Проверяет изменение sitemap по хешу и запускает парсинг"""
    print("Проверка sitemap...")
    try:
        response = requests.get(SITEMAP_URL, timeout=10)
        if response.status_code != 200:
            print(f"Сайт недоступен: {response.status_code}")
            return

        current_hash = hashlib.md5(response.content).hexdigest()
        
        old_hash = ""
        if os.path.exists(HASH_FILE):
            with open(HASH_FILE, "r") as f:
                old_hash = f.read().strip()

        if current_hash != old_hash:
            print("Sitemap обновился! Начинаю работу...")
            parse_sitemap(response.content)
            
            with open(HASH_FILE, "w") as f:
                f.write(current_hash)
            print("Готово. Хеш обновлен.")
        else:
            print("Изменений в sitemap.xml нет. Выход.")
            
    except Exception as e:
        print(f"Ошибка соединения: {e}")

if __name__ == "__main__":
    check_and_run()
