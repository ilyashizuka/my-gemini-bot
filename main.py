import requests
import hashlib
import os
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from db_worker import save_to_db

SITEMAP_URL = "https://vuoksa-virta.ru"
HASH_FILE = "sitemap_hash.txt"

# Заголовки, чтобы сайт думал, что заходит обычный человек через Chrome
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}

def extract_data(url):
    """Парсит страницу: ищет заголовок, цену и телефон"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"Пропуск {url}: код {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Поиск цены (число перед руб/рублей)
        full_text = soup.get_text()
        # Ищем цифры, за которыми идет "руб"
        price_match = re.search(r'(\d[\d\s\xa0]*)руб', full_text)
        price = "0"
        if price_match:
            # Оставляем только цифры
            price = re.sub(r'[^\d]', '', price_match.group(1))
        
        # 2. Поиск телефона в формате tel:+7...
        phone_tag = soup.find('a', href=re.compile(r'^tel:\+7'))
        phone = phone_tag['href'].replace('tel:', '') if phone_tag else "Не найден"
        
        # 3. Заголовок
        title = soup.title.string.strip() if soup.title else "Без заголовка"
        
        # 4. Контент (первые 1000 символов для истории)
        content = soup.get_text(separator=' ', strip=True)[:1000]
        
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
        
        print(f"Найдено ссылок в Sitemap: {len(urls)}")
        
        for url in urls:
            # Пропускаем сам sitemap и картинки, если они попали
            if url.endswith('.xml') or url.endswith('.jpg') or url.endswith('.png'):
                continue
                
            print(f"Обработка: {url}")
            data = extract_data(url)
            if data:
                title, price, phone, content = data
                save_to_db(url, title, price, phone, content)
                print(f"✅ Сохранено: {price} руб.")
                
    except Exception as e:
        print(f"Ошибка разбора XML: {e}")

def check_and_run():
    """Проверяет изменение sitemap по хешу и запускает парсинг"""
    print("Запуск проверки sitemap.xml...")
    try:
        # Важно: здесь тоже используем HEADERS
        response = requests.get(SITEMAP_URL, headers=HEADERS, timeout=20)
        
        if response.status_code == 403:
            print("Критическая ошибка 403: Сайт всё еще блокирует бота. Нужно менять IP или User-Agent.")
            return

        if response.status_code != 200:
            print(f"Сайт недоступен: {response.status_code}")
            return

        current_hash = hashlib.md5(response.content).hexdigest()
        
        # Проверка хеша (если файл хеша есть — читаем его)
        old_hash = ""
        if os.path.exists(HASH_FILE):
            with open(HASH_FILE, "r") as f:
                old_hash = f.read().strip()

        # Если вы хотите принудительно запустить парсер ПЕРВЫЙ раз, 
        # можно временно закомментировать условие `if current_hash != old_hash:`
        if current_hash != old_hash:
            print("Обнаружены изменения в Sitemap. Начинаю парсинг...")
            parse_sitemap(response.content)
            
            # Сохраняем новый хеш
            with open(HASH_FILE, "w") as f:
                f.write(current_hash)
            print("Парсинг успешно завершен.")
        else:
            print("Sitemap не изменился со времени последнего запуска. Задач нет.")
            
    except Exception as e:
        print(f"Ошибка соединения: {e}")

if __name__ == "__main__":
    check_and_run()
