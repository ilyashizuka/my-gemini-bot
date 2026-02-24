import requests
import re
import time
from bs4 import BeautifulSoup
from db_worker import save_to_db

SITEMAP_URL = "https://vuoksa-virta.ru"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

def extract_data(url):
    """Парсит страницу товара/услуги"""
    try:
        time.sleep(1) # Небольшая пауза
        res = requests.get(url, headers=HEADERS, timeout=20)
        if res.status_code != 200: return None
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Поиск цены
        price_match = re.search(r'(\d[\d\s\xa0]*)руб', soup.get_text())
        price = re.sub(r'[^\d]', '', price_match.group(1)) if price_match else "0"
        
        # Поиск телефона
        phone_tag = soup.find('a', href=re.compile(r'^tel:\+7'))
        phone = phone_tag['href'].replace('tel:', '') if phone_tag else "N/A"
        
        title = soup.title.string.strip() if soup.title else "No Title"
        return title, price, phone
    except:
        return None

def start_render_parsing():
    print("--- STARTING RENDER PARSER (V4) ---")
    try:
        response = requests.get(SITEMAP_URL, headers=HEADERS, timeout=30)
        
        # Ищем все ссылки внутри тегов <loc> регулярным выражением (самый дуболомный метод)
        urls = re.findall(r'<loc>(.*?)</loc>', response.text)
        
        if not urls:
            print("ОШИБКА: Ссылки не найдены. Проверьте ответ сервера.")
            print(f"DEBUG: {response.text[:200]}")
            return

        print(f"Найдено ссылок: {len(urls)}")
        
        # Парсим первые 30 штук для теста
        for url in urls[:30]:
            if any(ext in url for ext in ['.jpg', '.png', '.xml']): continue
            
            print(f"Парсим: {url}")
            data = extract_data(url)
            if data:
                t, p, ph = data
                save_to_db(url, t, p, ph, "Render v4")
                print(f"--- OK: {p} rub ---")
                
        print("--- DONE ---")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    start_render_parsing()

