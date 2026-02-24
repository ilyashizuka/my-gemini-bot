import requests
import re
import time
import os
from bs4 import BeautifulSoup
from db_worker import save_to_db

SITEMAP_URL = "https://vuoksa-virta.ru"

# Используем заголовки обычного Chrome, чтобы сайт не подменял XML на HTML
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Referer': 'https://www.google.com'
}

def extract_data(url):
    try:
        time.sleep(1)
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
    print("--- STARTING RENDER PARSER (V5) ---")
    try:
        response = requests.get(SITEMAP_URL, headers=HEADERS, timeout=30)
        
        # Если пришел HTML вместо XML, ищем ссылки регуляркой во всем тексте
        # Это сработает, даже если сайт "хитрит"
        urls = re.findall(r'https://vuoksa-virta\.ru/[^<"\s\']+', response.text)
        
        # Убираем дубликаты и оставляем только страницы товаров/услуг
        unique_urls = sorted(list(set([u for u in urls if '/product/' in u or '/uslugi/' in u])))
        
        if not unique_urls:
            # План Б: если в Sitemap пусто, попробуем взять ссылки прямо с главной
            print("В Sitemap пусто или он заблокирован. Пробую главную страницу...")
            res_main = requests.get("https://vuoksa-virta.ru", headers=HEADERS)
            unique_urls = re.findall(r'https://vuoksa-virta\.ru/[^<"\s\']+', res_main.text)
            unique_urls = list(set([u for u in unique_urls if '/product/' in u]))

        print(f"Найдено ссылок для парсинга: {len(unique_urls)}")
        
        for url in unique_urls[:20]:
            print(f"Парсим: {url}")
            data = extract_data(url)
            if data:
                t, p, ph = data
                save_to_db(url, t, p, ph, "Render v5")
                print(f"--- OK: {p} rub ---")
                
        print("--- PARSING FINISHED ---")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    start_render_parsing()
