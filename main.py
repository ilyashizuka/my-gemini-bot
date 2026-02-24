import requests
import hashlib
import os
import re
import time
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from db_worker import save_to_db

SITEMAP_URL = "https://vuoksa-virta.ru"

# Маскируемся под Googlebot, чтобы обойти защиту 403
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8',
    'Referer': 'https://www.google.com'
}

def extract_data(url):
    """Парсит одну страницу: заголовок, цена, телефон"""
    try:
        # Небольшая пауза, чтобы сайт не забанил за скорость
        time.sleep(1.5)
        
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code != 200:
            print(f"Ошибка {response.status_code} на {url}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Поиск цены (число перед руб)
        full_text = soup.get_text()
        price_match = re.search(r'(\d[\d\s\xa0]*)руб', full_text)
        price = re.sub(r'[^\d]', '', price_match.group(1)) if price_match else "0"
        
        # 2. Поиск телефона в ссылках tel:
        phone_tag = soup.find('a', href=re.compile(r'^tel:\+7'))
        phone = phone_tag['href'].replace('tel:', '') if phone_tag else "Не найден"
        
        # 3. Заголовок и контент
        title = soup.title.string.strip() if soup.title else "Без заголовка"
        content = soup.get_text(separator=' ', strip=True)[:1000]
        
        return title, price, phone, content
    except Exception as e:
        print(f"Ошибка парсинга {url}: {e}")
        return None

def start_parsing():
    print("--- ЗАПУСК ПАРСЕРА НА RENDER ---")
    try:
        response = requests.get(SITEMAP_URL, headers=HEADERS, timeout=30)
        print(f"Ответ sitemap (первые 150 симв): {response.text[:150]}")
        
        if response.status_code != 200:
            print(f"Sitemap недоступен: {response.status_code}")
            return

        # Попытка 1: Стандартный XML разбор
        urls = []
        try:
            root = ET.fromstring(response.content)
            namespace = {'ns': 'http://www.sitemaps.org'}
            urls = [loc.text for loc in root.findall('.//ns:loc', namespace)]
        except Exception as xml_err:
            print(f"Стандартный XML-парсер не справился: {xml_err}")
            # Попытка 2: BeautifulSoup (более гибкий к ошибкам в разметке)
            print("Пробую вытащить ссылки через BeautifulSoup...")
            soup = BeautifulSoup(response.content, 'xml') # Используем XML-парсер BS4
            urls = [loc.text for loc in soup.find_all('loc')]

        if not urls:
            print("КРИТИЧЕСКАЯ ОШИБКА: Ссылки в Sitemap не найдены!")
            return

        print(f"Успешно найдено ссылок: {len(urls)}")
        
        # Парсим первые 20 ссылок для проверки (потом можно убрать [:20])
        for url in urls[:20]:
            if url.endswith(('.jpg', '.png', '.pdf', '.xml')):
                continue
                
            print(f"Обработка: {url}")
            data = extract_data(url)
            
            if data:
                title, price, phone, content = data
                # Сохраняем в БД (функция из db_worker.py)
                save_to_db(url, title, price, phone, content)
                print(f"✅ Сохранено в БД: {price} руб.")
                
        print("--- ПАРСИНГ ЗАВЕРШЕН УСПЕШНО ---")

    except Exception as e:
        print(f"Глобальная ошибка скрипта: {e}")

if __name__ == "__main__":
    start_parsing()
