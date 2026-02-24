import requests
import re
import time
from bs4 import BeautifulSoup
from db_worker import save_to_db

# Список стартовых страниц для сбора ссылок
START_URLS = [
    "https://vuoksa-virta.ru",
    "https://vuoksa-virta.ruprice/",
    "https://vuoksa-virta.rucategory/prokat-snaryazheniya/",
    "https://vuoksa-virta.rucategory/stoyanki/"
]

# Максимально «человеческие» заголовки
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://www.google.com'
}

def extract_page_data(session, url):
    """Парсит данные с конкретной страницы через сессию"""
    try:
        time.sleep(2) # Большая задержка, чтобы не поймать бан
        res = session.get(url, headers=HEADERS, timeout=20)
        if res.status_code != 200: return None
        
        soup = BeautifulSoup(res.text, 'html.parser')
        text = soup.get_text()
        
        # Цена
        price_match = re.search(r'(\d[\d\s\xa0]*)руб', text)
        price = re.sub(r'[^\d]', '', price_match.group(1)) if price_match else "0"
        
        # Телефон
        phone_tag = soup.find('a', href=re.compile(r'^tel:\+7'))
        phone = phone_tag['href'].replace('tel:', '') if phone_tag else "N/A"
        
        title = soup.title.string.strip() if soup.title else "No Title"
        return title, price, phone
    except Exception as e:
        print(f"Ошибка парсинга {url}: {e}")
        return None

def start_render_parsing():
    print("--- STARTING SESSION PARSER (V7) ---")
    all_links = set()
    
    # Создаем сессию, чтобы сохранять куки (как в браузере)
    session = requests.Session()
    
    for start_url in START_URLS:
        print(f"Сканируем: {start_url}")
        try:
            res = session.get(start_url, headers=HEADERS, timeout=20)
            
            # Если сайт отдал хоть что-то, ищем все ссылки
            # Ищем и полные (http...), и относительные ( /category/... )
            found = re.findall(r'href=["\'](https://vuoksa-virta\.ru/[^"\']+)["\']', res.text)
            found += re.findall(r'href=["\'](/[a-z0-9\-_/]+)["\']', res.text)
            
            for l in found:
                full_url = l if l.startswith('http') else f"https://vuoksa-virta.ru{l}"
                # Фильтр мусора
                if not any(ext in full_url for ext in ['.jpg', '.png', '.css', '.js', '.pdf', '.xml', 'wp-json']):
                    if "vuoksa-virta.ru" in full_url:
                        all_links.add(full_url)
        except Exception as e:
            print(f"Ошибка доступа к {start_url}: {e}")

    # Удаляем саму главную из списка, чтобы не парсить её вечно
    all_links.discard("https://vuoksa-virta.ru")
    print(f"Найдено уникальных страниц: {len(all_links)}")
    
    if not all_links:
        print("DEBUG: Сайт вернул пустой HTML. Попробуйте сменить IP или использовать прокси.")
        return

    # Парсим первые 30 страниц
    count = 0
    for url in list(all_links)[:30]:
        print(f"Парсим данные: {url}")
        data = extract_page_data(session, url)
        if data:
            t, p, ph = data
            save_to_db(url, t, p, ph, "Session Parser V7")
            print(f"--- OK: {p} руб. ---")
            count += 1
            
    print(f"--- ЗАВЕРШЕНО. Добавлено записей: {count} ---")

if __name__ == "__main__":
    start_render_parsing()
