import requests
import re
import time
from bs4 import BeautifulSoup
from db_worker import save_to_db

# Списком стартовых страниц со слешами на конце!
START_URLS = [
    "https://vuoksa-virta.ru",
    "https://vuoksa-virta.ruprice/",
    "https://vuoksa-virta.rucategory/prokat-snaryazheniya/",
    "https://vuoksa-virta.rucategory/stoyanki/"
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
}

def extract_page_data(url):
    try:
        # Игнорируем системные файлы WordPress и картинки
        if any(x in url for x in ['xmlrpc', 'wp-json', 'wp-content', 'jpg', 'png', 'webp']):
            return None
            
        time.sleep(1)
        res = requests.get(url, headers=HEADERS, timeout=20)
        if res.status_code != 200: return None
        
        soup = BeautifulSoup(res.text, 'html.parser')
        text = soup.get_text()
        
        # Поиск цены
        price_match = re.search(r'(\d[\d\s\xa0]*)руб', text)
        price = re.sub(r'[^\d]', '', price_match.group(1)) if price_match else "0"
        
        # Поиск телефона
        phone_tag = soup.find('a', href=re.compile(r'^tel:\+7'))
        phone = phone_tag['href'].replace('tel:', '') if phone_tag else "Нет"
        
        title = soup.title.string.strip() if soup.title else "Без названия"
        return title, price, phone
    except:
        return None

def start_render_parsing():
    print("--- STARTING CORRECTED PARSER V7 ---")
    all_links = set()
    
    for start_url in START_URLS:
        print(f"Сканируем: {start_url}")
        try:
            res = requests.get(start_url, headers=HEADERS, timeout=20)
            # Улучшенный поиск ссылок внутри кавычек
            links = re.findall(r'href="(https://vuoksa-virta\.ru/[^"\s>]+)"', res.text)
            for l in links:
                # Берем только страницы (не файлы и не саму главную)
                if l != "https://vuoksa-virta.ru" and not any(x in l for x in ['.jpg', '.png', '.css', '.js']):
                    all_links.add(l)
        except Exception as e:
            print(f"Ошибка на {start_url}: {e}")

    print(f"Найдено полезных страниц: {len(all_links)}")
    
    count = 0
    # Парсим первые 40 страниц для теста
    for url in list(all_links)[:40]:
        print(f"Обработка: {url}")
        data = extract_page_data(url)
        if data:
            t, p, ph = data
            # Если цена нашлась или это страница услуги - сохраняем
            save_to_db(url, t, p, ph, "Render Final Build")
            print(f"--- OK: {p} руб. ---")
            count += 1
            
    print(f"--- ЗАВЕРШЕНО. Сохранено: {count} ---")

if __name__ == "__main__":
    start_render_parsing()
