import requests
import re
import time
from bs4 import BeautifulSoup
from db_worker import save_to_db

# Правильные стартовые адреса со слешами
START_URLS = [
    "https://vuoksa-virta.ru",
    "https://vuoksa-virta.ruprice/",
    "https://vuoksa-virta.rucategory/prokat-snaryazheniya/",
    "https://vuoksa-virta.rucategory/stoyanki/"
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}

def extract_page_data(url):
    try:
        # Не парсим картинки и API
        if any(x in url for x in ['.jpg', '.png', '.webp', 'wp-json', 'feed', 'woff2']):
            return None
            
        time.sleep(1)
        res = requests.get(url, headers=HEADERS, timeout=20)
        if res.status_code != 200: return None
        
        soup = BeautifulSoup(res.text, 'html.parser')
        text = soup.get_text()
        
        price_match = re.search(r'(\d[\d\s\xa0]*)руб', text)
        price = re.sub(r'[^\d]', '', price_match.group(1)) if price_match else "0"
        
        phone_tag = soup.find('a', href=re.compile(r'^tel:\+7'))
        phone = phone_tag['href'].replace('tel:', '') if phone_tag else "Нет"
        title = soup.title.string.strip() if soup.title else "Без названия"
        
        return title, price, phone
    except:
        return None

def start_render_parsing():
    print("--- STARTING CORRECTED PARSER ---")
    all_links = set()
    
    for start_url in START_URLS:
        print(f"Сканируем: {start_url}")
        try:
            res = requests.get(start_url, headers=HEADERS, timeout=20)
            # Ищем ссылки только на товары и категории (улучшенная регулярка)
            links = re.findall(r'href="(https://vuoksa-virta\.ru/[^"\s?]+)"', res.text)
            for l in links:
                # Фильтруем полезные страницы
                if not any(x in l for x in ['wp-content', 'wp-includes', 'wp-json', 'feed', 'comments']):
                    if l != "https://vuoksa-virta.ru":
                        all_links.add(l)
        except Exception as e:
            print(f"Ошибка на {start_url}: {e}")

    print(f"Найдено полезных страниц: {len(all_links)}")
    
    count = 0
    for url in list(all_links)[:40]: # Парсим 40 страниц за раз
        print(f"Парсим: {url}")
        data = extract_page_data(url)
        if data:
            t, p, ph = data
            save_to_db(url, t, p, ph, "Render Final")
            print(f"--- OK: {p} руб. ---")
            count += 1
            
    print(f"--- ЗАВЕРШЕНО. Сохранено: {count} ---")

if __name__ == "__main__":
    start_render_parsing()
