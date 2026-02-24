import requests
import hashlib
import os
import xml.etree.ElementTree as ET
from db_worker import save_to_db  # Импортируем функцию из первого файла

SITEMAP_URL = "https://vuoksa-virta.ru/sitemap.xml"
HASH_FILE = "sitemap_hash.txt"

def get_content_hash(content):
    return hashlib.md5(content).hexdigest()

def parse_sitemap(xml_content):
    """Извлекает ссылки из XML и запускает парсинг каждой"""
    root = ET.fromstring(xml_content)
    # Пространство имен sitemap (стандарт)
    namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    
    urls = [loc.text for loc in root.findall('.//ns:loc', namespace)]
    print(f"Найдено ссылок: {len(urls)}. Начинаю парсинг...")
    
    for url in urls:
        # Здесь должна быть ваша логика парсинга страницы (BeautifulSoup и т.д.)
        # Для примера просто сохраним заглушку:
        print(f"Парсим: {url}")
        save_to_db(url, "Заголовок страницы", "Текст контента...")

def check_and_run():
    response = requests.get(SITEMAP_URL)
    if response.status_code != 200:
        print("Ошибка загрузки sitemap")
        return

    current_hash = get_content_hash(response.content)
    
    # Читаем старый хеш
    old_hash = ""
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "r") as f:
            old_hash = f.read().strip()

    if current_hash != old_hash:
        print("Sitemap изменился! Запускаю парсер...")
        parse_sitemap(response.content)
        
        # Сохраняем новый хеш
        with open(HASH_FILE, "w") as f:
            f.write(current_hash)
    else:
        print("Изменений в sitemap не обнаружено. Отдыхаем.")

if __name__ == "__main__":
    check_and_run()
