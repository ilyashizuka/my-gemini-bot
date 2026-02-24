import requests
import re
import time
from bs4 import BeautifulSoup
from db_worker import save_to_db

# Список страниц, с которых мы точно соберем ссылки, если sitemap врет
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
    """Парсит конкретную страницу товара/услуги"""
    try:
        time.sleep(1.5)
        res = requests.get(url, headers=HEADERS, timeout=20)
        if res.status_code != 200: return None
        
        soup = BeautifulSoup(res.text, 'html.parser')
        text = soup.get_text()
        
        # 1. Цена (ищем число перед 'руб')
        price_match = re.search(r'(\d[\d\s\xa0]*)руб', text)
        price = re.sub(r'[^\d]', '', price_match.group(1)) if price_match else "0"
        
        # 2. Телефон
        phone_tag = soup.find('a', href=re.compile(r'^tel:\+7'))
        phone = phone_tag['href'].replace('tel:', '') if phone_tag else "Нет"
        
        # 3. Заголовок
        title = soup.title.string.strip() if soup.title else "Без названия"
        
        return title, price, phone
    except:
        return None

def start_render_parsing():
    print("--- STARTING UNIVERSAL PARSER (V6) ---")
    all_found_urls = set()
    
    # Пытаемся собрать ссылки со всех стартовых страниц
    for start_url in START_URLS:
        print(f"Ищем ссылки на: {start_url}")
        try:
            res = requests.get(start_url, headers=HEADERS, timeout=20)
            # Ищем все ссылки на этом домене
            links = re.findall(r'href="(https://vuoksa-virta\.ru/[^"]+)"', res.text)
            for l in links:
                # Фильтруем только полезные страницы (не картинки и не рубрики)
                if any(x in l for x in ['/product/', '/item/', '/services/']) or l.count('/') > 3:
                    all_found_urls.add(l)
        except Exception as e:
            print(f"Ошибка на {start_url}: {e}")

    print(f"Итого найдено уникальных адресов: {len(all_found_urls)}")
    
    # Парсим первые 30 найденных страниц
    count = 0
    for url in list(all_found_urls)[:30]:
        print(f"Парсим данные: {url}")
        data = extract_page_data(url)
        if data:
            t, p, ph = data
            save_to_db(url, t, p, ph, "Universal Parser V6")
            print(f"--- OK: {p} руб. ---")
            count += 1
            
    print(f"--- ЗАВЕРШЕНО. Сохранено записей: {count} ---")

if __name__ == "__main__":
    start_render_parsing()
