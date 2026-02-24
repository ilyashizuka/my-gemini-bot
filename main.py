import requests
import hashlib
import os
import re
import time
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from db_worker import save_to_db

SITEMAP_URL = "https://vuoksa-virta.ru"

# Маскируемся под поискового робота Google (сайты их редко блокируют)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'https://www.google.com'
}

def extract_data(url):
    try:
        time.sleep(2) # Задержка 2 секунды, чтобы не злить сервер
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code != 200:
            print(f"Propusk {url}: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Поиск цены
        full_text = soup.get_text()
        price_match = re.search(r'(\d[\d\s\xa0]*)руб', full_text)
        price = re.sub(r'[^\d]', '', price_match.group(1)) if price_match else "0"
        
        # Поиск телефона
        phone_tag = soup.find('a', href=re.compile(r'^tel:\+7'))
        phone = phone_tag['href'].replace('tel:', '') if phone_tag else "N/A"
        
        title = soup.title.string.strip() if soup.title else "No Title"
        
        return title, price, phone
    except Exception as e:
        print(f"Error parsing {url}: {e}")
        return None

def start_parsing():
    print("Start Render Parsing...")
    try:
        response = requests.get(SITEMAP_URL, headers=HEADERS, timeout=30)
        if response.status_code != 200:
            print(f"Sitemap Error: {response.status_code}")
            return

        root = ET.fromstring(response.content)
        namespace = {'ns': 'http://www.sitemaps.org'}
        urls = [loc.text for loc in root.findall('.//ns:loc', namespace)]
        
        print(f"Links found: {len(urls)}")
        
        # Для первого теста на Render берем первые 20 ссылок
        for url in urls[:20]:
            print(f"Processing: {url}")
            data = extract_data(url)
            if data:
                title, price, phone = data
                save_to_db(url, title, price, phone, "Render automatic parse")
                print(f"--- Saved: {price} rub")
                
    except Exception as e:
        print(f"Global Error: {e}")

if __name__ == "__main__":
    start_parsing()
